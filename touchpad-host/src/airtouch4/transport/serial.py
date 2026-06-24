"""USB-RS485 serial transport for the AirTouch main-board bus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class SerialDependencyError(RuntimeError):
    """Raised when pyserial is not installed."""


@dataclass(frozen=True)
class SerialConfig:
    port: str
    baudrate: int = 115200
    timeout: float = 0.05
    write_timeout: float = 1.0


class SerialRs485Transport:
    def __init__(self, config: SerialConfig) -> None:
        self.config = config
        self._serial = None

    def __enter__(self) -> "SerialRs485Transport":
        try:
            import serial  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:
            raise SerialDependencyError(
                "pyserial is required for live serial runs. Install it with: python -m pip install pyserial"
            ) from exc

        self._serial = serial.Serial(
            port=self.config.port,
            baudrate=self.config.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.config.timeout,
            write_timeout=self.config.write_timeout,
        )
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def read(self, size: int = 512) -> bytes:
        if self._serial is None:
            raise RuntimeError("serial transport is not open")
        return bytes(self._serial.read(size))

    def write(self, data: bytes | bytearray | Iterable[int]) -> int:
        if self._serial is None:
            raise RuntimeError("serial transport is not open")
        return int(self._serial.write(bytes(data)))
