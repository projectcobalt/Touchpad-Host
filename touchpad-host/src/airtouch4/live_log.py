"""JSONL logging helpers for live AirTouch bus sessions."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, TextIO

from .packet import AirTouchPacket, hex_bytes, parse_packet
from .payloads import decode_mainboard_payload


class JsonlBusLogger:
    def __init__(self, path: Path | None) -> None:
        self.path = path
        self._handle: TextIO | None = None

    def __enter__(self) -> "JsonlBusLogger":
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = self.path.open("a", encoding="utf-8")
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def write(self, event: dict[str, Any]) -> None:
        event.setdefault("host_epoch", time.time())
        event.setdefault("host_ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        line = json.dumps(event, sort_keys=True, separators=(",", ":"))
        if self._handle is not None:
            self._handle.write(line + "\n")
            self._handle.flush()

    def log_rx(self, packet: AirTouchPacket, *, wire: bytes | None = None) -> None:
        record = packet.to_record()
        record.update({
            "event": "rx",
            "decoded": decode_mainboard_payload(packet.command, packet.payload),
        })
        if wire is not None:
            record["wire"] = hex_bytes(wire)
        self.write(record)

    def log_tx(self, packet: AirTouchPacket, wire: bytes) -> None:
        logged_packet = parse_packet(wire)
        record = logged_packet.to_record()
        record.update({
            "event": "tx",
            "decoded": decode_mainboard_payload(logged_packet.command, logged_packet.payload),
            "wire": hex_bytes(wire),
        })
        self.write(record)
