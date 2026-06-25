"""Internal touchpanel/main-board status and control payloads."""

from __future__ import annotations

from typing import Any

from ..packet import hex_bytes
from .common import bit, parse_internal_temperature, u16be


def decode_set_group_status(payload: bytes) -> dict[str, Any]:
    if len(payload) < 2:
        return {"type": "set_group_status_internal", "truncated": True}
    power_code = (payload[0] >> 6) & 0x03
    sensor_ctrl = bit(payload[1], 0x80)
    value = payload[1] & 0x7F
    return {
        "type": "set_group_status_internal",
        "group": payload[0] & 0x3F,
        "power_code": power_code,
        "power_name": {0: "off", 1: "on", 2: "value_change", 3: "turbo"}.get(power_code),
        "sensor_control": sensor_ctrl,
        "setpoint": value + 4 if sensor_ctrl else None,
        "percentage": None if sensor_ctrl else value,
        "unused_tail": hex_bytes(payload[2:]) if len(payload) > 2 else "",
    }


def decode_group_status(payload: bytes) -> dict[str, Any]:
    records = []
    for offset in range(0, len(payload) - 5, 6):
        rec = payload[offset:offset + 6]
        power_code = (rec[0] >> 6) & 0x03
        records.append({
            "group": rec[0] & 0x3F,
            "power_code": power_code,
            "power_name": {0: "off", 1: "on", 3: "turbo"}.get(power_code, "reserved"),
            "sensor_control": bit(rec[1], 0x80),
            "percentage": rec[1] & 0x7F,
            "low_battery": bit(rec[2], 0x80),
            "turbo_supported": bit(rec[2], 0x40),
            "timer_on": bit(rec[2], 0x20),
            "setpoint": (rec[2] & 0x1F) + 4,
            "has_sensor": bit(rec[3], 0x80),
            "temperature": parse_internal_temperature(rec[4]),
            "spill_on": (rec[5] & 0xE0) == 0x20,
            "raw": hex_bytes(rec),
        })
    return {
        "type": "group_status_internal",
        "record_count": len(records),
        "records": records,
        "trailing": hex_bytes(payload[len(records) * 6:]),
    }


def decode_set_ac_status(payload: bytes) -> dict[str, Any]:
    if len(payload) < 3:
        return {"type": "set_ac_status_internal", "truncated": True}
    power_bits = payload[0] & 0xC0
    return {
        "type": "set_ac_status_internal",
        "ac": payload[0] & 0x3F,
        "power_name": {0x80: "off", 0xC0: "on"}.get(power_bits, "unchanged"),
        "mode": (payload[1] >> 4) & 0x0F,
        "fan": payload[1] & 0x0F,
        "setpoint": None if payload[2] == 0x1F else (payload[2] & 0x1F) + 4,
        "unused_tail": hex_bytes(payload[3:]) if len(payload) > 3 else "",
    }


def decode_ac_status(payload: bytes) -> dict[str, Any]:
    records = []
    for offset in range(0, len(payload) - 7, 8):
        rec = payload[offset:offset + 8]
        available = not bit(rec[0], 0x80)
        records.append({
            "ac": rec[0] & 0x3F,
            "available": available,
            "power_on": bit(rec[0], 0x40) if available else None,
            "mode": (rec[1] >> 4) & 0x0F if available else None,
            "fan": rec[1] & 0x0F if available else None,
            "setpoint": None if rec[2] >= 32 else rec[2] + 4,
            "sensor_temp": parse_internal_temperature(rec[4]) if available else None,
            "has_timer": bit(rec[5], 0x01) if available else None,
            "error_code": u16be(rec, 6) if available else None,
            "raw": hex_bytes(rec),
        })
    return {
        "type": "ac_status_internal",
        "record_count": len(records),
        "records": records,
        "trailing": hex_bytes(payload[len(records) * 8:]),
    }


def decode_touchpad_temperature(payload: bytes) -> dict[str, Any]:
    if len(payload) < 3:
        return {"type": "touchpad_temperature", "truncated": True, "raw": hex_bytes(payload)}
    return {
        "type": "touchpad_temperature",
        "touchpad": payload[0],
        "temperature_raw": payload[1],
        "temperature": parse_internal_temperature(payload[1]),
        "tail": hex_bytes(payload[2:]),
    }


def decode_led_response(payload: bytes) -> dict[str, Any]:
    if len(payload) < 1:
        return {"type": "led_response", "truncated": True}
    return {
        "type": "led_response",
        "led_code": payload[0],
        "led_name": {
            0x00: "blue_off",
            0x01: "blue_on",
            0x16: "alternating_blue_red_0_5hz",
        }.get(payload[0], "unknown"),
        "tail": hex_bytes(payload[1:]),
    }
