"""Startup initialisation state machine for touchscreen emulation."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..packet import AirTouchPacket
from .queue import TransactionSpec


@dataclass(frozen=True)
class InitStep:
    command: int
    payload: bytes = b""
    name: str = ""
    required: bool = False
    capability: str = "general"
    max_attempts: int = 3
    retry_interval: float = 3.0

    @property
    def key(self) -> str:
        suffix = "" if not self.payload else ":" + self.payload.hex(" ").upper()
        return f"0x{self.command:02X}{suffix}"


@dataclass(frozen=True)
class InitRequest:
    step_index: int
    command: int
    payload: bytes
    attempt: int
    name: str


@dataclass(frozen=True)
class InitEvent:
    event: str
    step_index: int
    command: int
    payload: bytes
    name: str
    required: bool
    capability: str
    detail: str = ""

    def to_record(self) -> dict:
        return {
            "event": "init",
            "init_event": self.event,
            "step_index": self.step_index,
            "cmd": f"0x{self.command:02X}",
            "payload": self.payload.hex(" ").upper(),
            "name": self.name,
            "required": self.required,
            "capability": self.capability,
            "detail": self.detail,
        }


@dataclass
class _StepRuntime:
    attempts: int = 0
    last_sent: float | None = None
    done: bool = False
    skipped: bool = False
    failed: bool = False


def _parameter_steps(
    command: int,
    values: tuple[int, ...],
    *,
    name: str,
    required: bool,
    capability: str,
    max_attempts: int = 3,
) -> list[InitStep]:
    return [
        InitStep(
            command=command,
            payload=bytes((value,)),
            name=f"{name} {value}",
            required=required,
            capability=capability,
            max_attempts=max_attempts,
        )
        for value in values
    ]


def default_init_steps() -> list[InitStep]:
    """APK-derived init order with HA-friendly fallback classifications."""
    steps: list[InitStep] = [
        InitStep(0x55, name="preference", capability="ui_preferences"),
        InitStep(0x61, name="parameters", required=True, capability="system"),
        InitStep(0x75, name="ac base info", capability="ac_capability"),
        InitStep(0x79, name="ac settings", capability="ac_capability"),
        InitStep(0x23, name="ac status", capability="ac_runtime"),
    ]
    steps.extend(_parameter_steps(0x53, (0, 1, 2, 3), name="group names page", required=True, capability="groups"))
    steps.extend(
        [
            InitStep(0x21, name="group status", required=True, capability="groups"),
            InitStep(0x59, name="main display", required=True, capability="groups"),
        ]
    )
    steps.extend(_parameter_steps(0x33, (0, 1, 2, 3), name="favourites page", required=False, capability="favourites"))
    steps.extend(
        [
            InitStep(0x6D, payload=b"\x01", name="password info 1", capability="security"),
            InitStep(0x6D, payload=b"\x02", name="password info 2", capability="security"),
            InitStep(0x6B, name="service", capability="service"),
            InitStep(0x3D, name="programs", capability="programs"),
            InitStep(0x43, name="ac runtime", capability="ac_runtime"),
            InitStep(0x37, name="ac timer", capability="ac_runtime"),
            InitStep(0x51, name="turbo group", capability="groups"),
            InitStep(0x67, name="grouping", required=True, capability="groups"),
            InitStep(0x69, name="spill", required=True, capability="groups"),
            InitStep(0x63, name="balance", capability="groups"),
            InitStep(0x71, name="sensor list", required=True, capability="sensors"),
        ]
    )
    return steps


def default_init_transactions() -> list[TransactionSpec]:
    from ..profiles import AT4

    return AT4.init_transactions()


@dataclass
class TouchscreenInitStateMachine:
    steps: list[InitStep] = field(default_factory=default_init_steps)
    current_index: int = 0
    _runtime: list[_StepRuntime] = field(init=False, repr=False)
    _finished_emitted: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        self._runtime = [_StepRuntime() for _step in self.steps]

    @property
    def complete(self) -> bool:
        return self.current_index >= len(self.steps)

    @property
    def failed(self) -> bool:
        return any(runtime.failed for runtime in self._runtime)

    @property
    def degraded(self) -> bool:
        return any(runtime.skipped for runtime in self._runtime)

    def observe(self, packet: AirTouchPacket) -> list[InitEvent]:
        if self.complete:
            return []
        step = self.steps[self.current_index]
        if packet.command != step.command:
            return []
        runtime = self._runtime[self.current_index]
        was_failed = runtime.failed
        runtime.done = True
        runtime.failed = False
        event = self._event("complete", self.current_index, "matching response received")
        if was_failed:
            event = self._event("recovered", self.current_index, "late matching response received")
        self.current_index += 1
        return [event, *self._advance_finished()]

    def poll(self, now: float) -> tuple[list[InitEvent], InitRequest | None]:
        events = self._advance_finished()
        if self.complete:
            return events, None

        step = self.steps[self.current_index]
        runtime = self._runtime[self.current_index]
        if runtime.failed:
            return events, None

        due = runtime.last_sent is None or now - runtime.last_sent >= step.retry_interval
        if not due:
            return events, None

        if runtime.attempts >= step.max_attempts:
            if step.required:
                runtime.failed = True
                events.append(self._event("failed", self.current_index, "required response not received"))
                return events, None
            runtime.skipped = True
            events.append(self._event("degraded", self.current_index, "optional response not received"))
            self.current_index += 1
            more_events, request = self.poll(now)
            return [*events, *more_events], request

        runtime.attempts += 1
        runtime.last_sent = now
        request = InitRequest(
            step_index=self.current_index,
            command=step.command,
            payload=step.payload,
            attempt=runtime.attempts,
            name=step.name,
        )
        events.append(self._event("request", self.current_index, f"attempt {runtime.attempts}"))
        return events, request

    def summary(self) -> dict:
        skipped = [self.steps[index].key for index, runtime in enumerate(self._runtime) if runtime.skipped]
        failed = [self.steps[index].key for index, runtime in enumerate(self._runtime) if runtime.failed]
        completed = [self.steps[index].key for index, runtime in enumerate(self._runtime) if runtime.done]
        state = "complete" if self.complete and not failed else "failed" if failed else "running"
        if state == "complete" and skipped:
            state = "degraded"
        return {
            "state": state,
            "current_index": self.current_index,
            "total_steps": len(self.steps),
            "completed": completed,
            "skipped_optional": skipped,
            "failed_required": failed,
        }

    def _advance_finished(self) -> list[InitEvent]:
        events: list[InitEvent] = []
        while not self.complete:
            runtime = self._runtime[self.current_index]
            if not runtime.done and not runtime.skipped:
                break
            self.current_index += 1
        if self.complete and not self._finished_emitted:
            self._finished_emitted = True
            events.append(InitEvent("finished", len(self.steps), 0, b"", "init", False, "session", "init sequence ended"))
        return events

    def _event(self, event: str, step_index: int, detail: str) -> InitEvent:
        step = self.steps[step_index]
        return InitEvent(
            event=event,
            step_index=step_index,
            command=step.command,
            payload=step.payload,
            name=step.name,
            required=step.required,
            capability=step.capability,
            detail=detail,
        )
