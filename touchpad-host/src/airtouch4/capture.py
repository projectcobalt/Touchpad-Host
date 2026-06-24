"""Capture file helpers for AirTouch 4 JSONL and text logs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from .payloads import decode_capture_payload
from .packet import AirTouchPacket, extract_packets, hex_bytes

LIKELY_HEX_KEYS = (
    "hex",
    "raw",
    "payload",
    "message",
    "data",
    "value",
    "bytes",
    "frame",
)

HEX_PAIR_RE = re.compile(r"(?i)(?:0x)?[0-9a-f]{2}")


def parse_hex_from_string(text: str) -> bytes | None:
    pairs = HEX_PAIR_RE.findall(text)
    if len(pairs) < 2:
        return None
    return bytes(int(pair[-2:], 16) for pair in pairs)


def find_hex_value(obj: Any) -> tuple[bytes | None, str | None]:
    if isinstance(obj, str):
        return parse_hex_from_string(obj), None
    if not isinstance(obj, dict):
        return None, None

    for key in LIKELY_HEX_KEYS:
        value = obj.get(key)
        if isinstance(value, str):
            parsed = parse_hex_from_string(value)
            if parsed:
                return parsed, key
        if isinstance(value, list) and all(isinstance(item, int) for item in value):
            return bytes(item & 0xFF for item in value), key

    best: tuple[int, bytes, str] | None = None
    for key, value in obj.items():
        if isinstance(value, str):
            parsed = parse_hex_from_string(value)
            if parsed and (best is None or len(parsed) > best[0]):
                best = (len(parsed), parsed, str(key))
    if best:
        return best[1], best[2]
    return None, None


def metadata_from_json(obj: Any, source_field: str | None) -> dict[str, Any]:
    if not isinstance(obj, dict):
        return {}
    meta: dict[str, Any] = {}
    for key in ("ts", "time", "timestamp", "datetime", "topic", "direction", "source"):
        if key in obj:
            meta[key] = obj[key]
    if source_field:
        meta["hex_source_field"] = source_field
    return meta


def iter_capture_lines(path: Path) -> Iterable[tuple[int, bytes, dict[str, Any], str]]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed_obj = json.loads(stripped)
            except json.JSONDecodeError:
                parsed_obj = stripped
            payload, field = find_hex_value(parsed_obj)
            if payload is None:
                payload = parse_hex_from_string(stripped)
            if payload:
                yield line_no, payload, metadata_from_json(parsed_obj, field), stripped


def decode_capture(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, data, meta, original in iter_capture_lines(path):
        packets = extract_packets(data)
        if not packets and data and not data.startswith(b"\x55\x55"):
            packets = extract_packets(b"\x55\x55" + data)
        if not packets:
            records.append({
                "file": str(path),
                "line": line_no,
                "event": "no_frame",
                "meta": meta,
                "raw_candidate": hex_bytes(data),
                "original": original,
            })
            continue
        for frame_index, packet in enumerate(packets):
            record = packet.to_record()
            record["decoded"] = decode_capture_payload(packet.command, packet.payload)
            record.update({
                "file": str(path),
                "line": line_no,
                "frame_index": frame_index,
                "meta": meta,
            })
            records.append(record)
    return records


def iter_packets(path: Path) -> Iterable[tuple[int, AirTouchPacket, dict[str, Any]]]:
    for line_no, data, meta, _original in iter_capture_lines(path):
        for packet in extract_packets(data):
            yield line_no, packet, meta
