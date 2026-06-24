"""Reference-only mobile/client payload decoders for offline capture archaeology.

These codecs are intentionally outside the replacement-touchscreen runtime.
They are useful for recognizing traffic from mobile/API clients seen on the bus,
but they must not drive emulation state, session logic, or command builders.
"""

from __future__ import annotations

from typing import Any

from ..packet import hex_bytes
from .common import bit, decode_api_temperature, u16be


def decode_group_control(payload: bytes) -> dict[str, Any]:
    if len(payload) < 3:
        return {"type": "group_control_client", "truncated": True}
    setting_type = (payload[1] & 0xE0) >> 5
    setting = None
    if setting_type == 2:
        setting = {"action": "decrease"}
    elif setting_type == 3:
        setting = {"action": "increase"}
    elif setting_type == 4:
        setting = {"damper_percentage": payload[2]}
    elif setting_type == 5:
        setting = {"setpoint": payload[2]}
    return {
        "type": "group_control_client",
        "group": payload[0],
        "ui_zone": payload[0] + 1,
        "power_code": payload[1] & 0x07,
        "power_name": {0: "unchanged", 1: "toggle", 2: "off", 3: "on", 5: "turbo"}.get(payload[1] & 0x07),
        "control_method_code": (payload[1] & 0x18) >> 3,
        "control_method": {0: "unchanged", 1: "change", 2: "damper", 3: "temperature"}.get((payload[1] & 0x18) >> 3),
        "setting_type": setting_type,
        "setting": setting,
        "unused_tail": hex_bytes(payload[3:]) if len(payload) > 3 else "",
    }


def decode_group_status(payload: bytes) -> dict[str, Any]:
    if not payload:
        return {
            "type": "group_status_client_request",
            "note": "Zero-length AT4 client/API group status request.",
        }
    records = []
    for offset in range(0, len(payload) - 5, 6):
        rec = payload[offset:offset + 6]
        temp_word = u16be(rec, 4)
        has_sensor = bit(rec[3], 0x80)
        temp_encoded = temp_word & 0xFFE0
        records.append({
            "group": rec[0] & 0x3F,
            "power_code": (rec[0] & 0xC0) >> 6,
            "power_name": {0: "off", 1: "on", 3: "turbo"}.get((rec[0] & 0xC0) >> 6, "reserved"),
            "control_method": "temperature" if bit(rec[1], 0x80) else "damper",
            "percentage": rec[1] & 0x7F,
            "low_battery": bit(rec[2], 0x80),
            "turbo_supported": bit(rec[2], 0x40),
            "setpoint": rec[2] & 0x3F if has_sensor else None,
            "has_sensor": has_sensor,
            "temperature": None if not has_sensor or temp_encoded == 0xFF00 else decode_api_temperature(temp_encoded),
            "spill_on": bit(temp_word, 0x10),
            "raw": hex_bytes(rec),
        })
    return {
        "type": "group_status_client",
        "record_count": len(records),
        "records": records,
        "trailing": hex_bytes(payload[len(records) * 6:]),
    }


def decode_ac_control(payload: bytes) -> dict[str, Any]:
    if len(payload) < 3:
        return {"type": "ac_control_client", "truncated": True}
    setpoint_control = (payload[2] & 0xC0) >> 6
    return {
        "type": "ac_control_client",
        "ac": payload[0] & 0x3F,
        "power_code": (payload[0] & 0xC0) >> 6,
        "power_name": {0: "unchanged", 1: "toggle", 2: "off", 3: "on"}.get((payload[0] & 0xC0) >> 6),
        "mode": (payload[1] & 0xF0) >> 4,
        "fan": payload[1] & 0x0F,
        "setpoint_control": {0: "unchanged", 1: "value", 2: "decrease", 3: "increase"}.get(setpoint_control),
        "setpoint": payload[2] & 0x3F if setpoint_control == 1 else None,
        "unused_tail": hex_bytes(payload[3:]) if len(payload) > 3 else "",
    }


def decode_ac_status(payload: bytes) -> dict[str, Any]:
    if not payload:
        return {
            "type": "ac_status_client_request",
            "note": "Zero-length AT4 client/API AC status request.",
        }
    records = []
    for offset in range(0, len(payload) - 7, 8):
        rec = payload[offset:offset + 8]
        encoded_temp = u16be(rec, 4)
        records.append({
            "ac": rec[0] & 0x3F,
            "power_on": ((rec[0] & 0xC0) >> 6) == 1,
            "mode": (rec[1] & 0xF0) >> 4,
            "fan": rec[1] & 0x0F,
            "spill_on": bit(rec[2], 0x80),
            "timer_on": bit(rec[2], 0x40),
            "setpoint": rec[2] & 0x3F,
            "sensor_temp": decode_api_temperature(encoded_temp),
            "error_code": u16be(rec, 6),
            "raw": hex_bytes(rec),
        })
    return {
        "type": "ac_status_client",
        "record_count": len(records),
        "records": records,
        "trailing": hex_bytes(payload[len(records) * 8:]),
    }


def decode_bulk_info(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "bulk_info_client",
        "scope": "client_api_reference",
        "payload_len": len(payload),
        "raw_prefix": hex_bytes(payload[:32]),
    }
    if len(payload) == 2:
        result.update({
            "request_args": hex_bytes(payload),
            "note": "AT4 mobile/client bulk-info request, often 03 FF.",
        })
        return result

    ascii_runs = []
    current = bytearray()
    for byte in payload:
        if 32 <= byte <= 126:
            current.append(byte)
        else:
            if len(current) >= 3:
                ascii_runs.append(current.decode("ascii", errors="replace"))
            current = bytearray()
    if len(current) >= 3:
        ascii_runs.append(current.decode("ascii", errors="replace"))
    result["ascii_runs"] = ascii_runs
    return result
