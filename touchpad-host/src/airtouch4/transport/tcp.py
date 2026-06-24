"""TCP serial-bridge transport for the AirTouch main-board bus."""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TcpSerialConfig:
    host: str
    port: int
    connect_timeout: float = 3.0
    read_timeout: float = 0.05


class TcpSerialTransport:
    def __init__(self, config: TcpSerialConfig) -> None:
        self.config = config
        self._socket: socket.socket | None = None

    def __enter__(self) -> "TcpSerialTransport":
        sock = socket.create_connection((self.config.host, self.config.port), timeout=self.config.connect_timeout)
        sock.settimeout(self.config.read_timeout)
        self._socket = sock
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def read(self, size: int = 512) -> bytes:
        if self._socket is None:
            raise RuntimeError("TCP serial transport is not open")
        try:
            return self._socket.recv(size)
        except socket.timeout:
            return b""

    def write(self, data: bytes | bytearray | Iterable[int]) -> int:
        if self._socket is None:
            raise RuntimeError("TCP serial transport is not open")
        wire = bytes(data)
        self._socket.sendall(wire)
        return len(wire)
