"""Serial command transaction queue for the internal AirTouch bus."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque

from ..commands import CommandSpec
from ..packet import AirTouchPacket


RESPONSE_COMMANDS: dict[int, tuple[int, ...]] = {
    0x20: (0x21,),
    0x21: (0x21,),
    0x22: (0x23,),
    0x23: (0x23,),
    0x30: (0x33,),
    0x32: (0x33,),
    0x33: (0x33,),
    0x36: (0x37,),
    0x37: (0x37,),
    0x3C: (0x3D,),
    0x3D: (0x3D,),
    0x40: (0x41,),
    0x43: (0x43,),
    0x51: (0x51,),
    0x52: (0x53,),
    0x53: (0x53,),
    0x54: (0x55,),
    0x55: (0x55,),
    0x60: (0x61,),
    0x61: (0x61,),
    0x62: (0x63,),
    0x64: (0x63,),
    0x66: (0x67,),
    0x67: (0x67,),
    0x68: (0x69,),
    0x69: (0x69,),
    0x6A: (0x6B,),
    0x6B: (0x6B,),
    0x6C: (0x6D,),
    0x6D: (0x6D,),
    0x6E: (0x6F,),
    0x70: (0x71, 0x73),
    0x71: (0x71,),
    0x72: (0x73,),
    0x73: (0x73,),
    0x74: (0x75,),
    0x75: (0x75,),
    0x78: (0x79,),
    0x79: (0x79,),
}


@dataclass(frozen=True)
class TransactionSpec:
    command: int
    payload: bytes = b""
    expected_commands: tuple[int, ...] = ()
    name: str = ""
    max_attempts: int = 3
    timeout: float = 3.0
    require_match: bool = True
    block_on_failure: bool = False

    @classmethod
    def from_command(cls, spec: CommandSpec, **kwargs: object) -> "TransactionSpec":
        return cls(command=spec.command, payload=spec.payload, **kwargs)

    def with_default_response(self) -> "TransactionSpec":
        if self.expected_commands:
            return self
        return TransactionSpec(
            command=self.command,
            payload=self.payload,
            expected_commands=RESPONSE_COMMANDS.get(self.command, (self.command,)),
            name=self.name,
            max_attempts=self.max_attempts,
            timeout=self.timeout,
            require_match=self.require_match,
            block_on_failure=self.block_on_failure,
        )


@dataclass(frozen=True)
class TransactionEvent:
    event: str
    command: int
    expected_commands: tuple[int, ...]
    name: str
    attempt: int = 0
    detail: str = ""

    def to_record(self) -> dict:
        return {
            "event": "transaction",
            "transaction_event": self.event,
            "cmd": f"0x{self.command:02X}",
            "expected": [f"0x{command:02X}" for command in self.expected_commands],
            "name": self.name,
            "attempt": self.attempt,
            "detail": self.detail,
        }


@dataclass
class TransactionRuntime:
    spec: TransactionSpec
    attempts: int = 0
    last_sent: float | None = None
    done: bool = False
    failed: bool = False


@dataclass
class TransactionQueue:
    pending: Deque[TransactionRuntime] = field(default_factory=deque)
    current: TransactionRuntime | None = None
    completed: list[TransactionSpec] = field(default_factory=list)
    failed: list[TransactionSpec] = field(default_factory=list)

    def enqueue(self, spec: TransactionSpec) -> None:
        self.pending.append(TransactionRuntime(spec.with_default_response()))

    def enqueue_many(self, specs: list[TransactionSpec] | tuple[TransactionSpec, ...]) -> None:
        for spec in specs:
            self.enqueue(spec)

    def observe(self, packet: AirTouchPacket) -> list[TransactionEvent]:
        if self.current is None:
            return []
        runtime = self.current
        spec = runtime.spec
        if spec.require_match and packet.command not in spec.expected_commands:
            return []
        runtime.done = True
        self.completed.append(spec)
        self.current = None
        return [TransactionEvent("complete", spec.command, spec.expected_commands, spec.name, runtime.attempts, f"matched 0x{packet.command:02X}")]

    def poll(self, now: float) -> tuple[list[TransactionEvent], TransactionSpec | None]:
        events: list[TransactionEvent] = []
        if self.current is None and self.pending:
            self.current = self.pending.popleft()

        if self.current is None:
            return events, None

        runtime = self.current
        spec = runtime.spec
        if runtime.failed:
            return events, None

        due = runtime.last_sent is None or now - runtime.last_sent >= spec.timeout
        if not due:
            return events, None

        if runtime.attempts >= spec.max_attempts:
            runtime.failed = True
            self.failed.append(spec)
            events.append(TransactionEvent("failed", spec.command, spec.expected_commands, spec.name, runtime.attempts, "response not received"))
            if not spec.block_on_failure:
                self.current = None
            return events, None

        runtime.attempts += 1
        runtime.last_sent = now
        events.append(TransactionEvent("request", spec.command, spec.expected_commands, spec.name, runtime.attempts))
        return events, spec

    def idle(self) -> bool:
        return self.current is None and not self.pending

    def summary(self) -> dict:
        return {
            "idle": self.idle(),
            "pending": len(self.pending),
            "current": None if self.current is None else {
                "cmd": f"0x{self.current.spec.command:02X}",
                "name": self.current.spec.name,
                "attempts": self.current.attempts,
            },
            "completed": [f"0x{spec.command:02X}" for spec in self.completed],
            "failed": [f"0x{spec.command:02X}" for spec in self.failed],
        }
