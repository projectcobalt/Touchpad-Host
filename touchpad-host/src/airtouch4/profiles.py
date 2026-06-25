"""Protocol profiles for AirTouch touchscreen-host behavior.

The frame shell is shared across AirTouch generations, but command ids,
payloads, and boot sequences are profile-owned.  AT4 is the implemented runtime
profile.  AT5 is represented deliberately as a detected-but-unsupported profile
until its 16-bit command payload model is implemented.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .payloads import decode_mainboard_payload
from .session.init import InitStep, default_init_steps
from .session.queue import TransactionSpec


class ProtocolProfile(Protocol):
    """Profile-owned command semantics layered over the shared frame shell."""

    name: str
    display_name: str

    def decode_payload(self, command: int, payload: bytes) -> dict:
        ...

    def init_steps(self) -> list[InitStep]:
        ...

    def init_transactions(self) -> list[TransactionSpec]:
        ...

    def detect_response(self, command: int, payload: bytes) -> str | None:
        ...


@dataclass(frozen=True)
class AT4Profile:
    name: str = "at4"
    display_name: str = "AirTouch 4"

    def decode_payload(self, command: int, payload: bytes) -> dict:
        return decode_mainboard_payload(command, payload)

    def init_steps(self) -> list[InitStep]:
        return default_init_steps()

    def init_transactions(self) -> list[TransactionSpec]:
        return [
            TransactionSpec(
                command=step.command,
                payload=step.payload,
                expected_commands=(step.command,),
                name=step.name,
                max_attempts=step.max_attempts,
                timeout=step.retry_interval,
                require_match=True,
                block_on_failure=step.required,
            )
            for step in self.init_steps()
        ]

    def detect_response(self, command: int, payload: bytes) -> str | None:
        if command == 0x55:
            return self.name
        return None


@dataclass(frozen=True)
class AT5Profile:
    name: str = "at5"
    display_name: str = "AirTouch 5"

    def decode_payload(self, command: int, payload: bytes) -> dict:
        return {
            "type": "unsupported_profile",
            "profile": self.name,
            "payload_len": len(payload),
        }

    def init_steps(self) -> list[InitStep]:
        return []

    def init_transactions(self) -> list[TransactionSpec]:
        return []

    def detect_response(self, command: int, payload: bytes) -> str | None:
        if command in {
            0xC021,
            0xC023,
            0xC027,
            0xC033,
            0xC045,
            0xC073,
        }:
            return self.name
        return None


AT4 = AT4Profile()
AT5 = AT5Profile()


def get_profile(name: str | None) -> ProtocolProfile:
    normalized = (name or "at4").lower()
    if normalized in {"auto", "at4", "airtouch4", "airtouch_4"}:
        return AT4
    if normalized in {"at5", "airtouch5", "airtouch_5"}:
        return AT5
    raise ValueError(f"unknown AirTouch protocol profile: {name}")
