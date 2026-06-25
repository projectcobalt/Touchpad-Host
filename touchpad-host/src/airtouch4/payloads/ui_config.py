"""UI-facing configuration payloads from the touchscreen init path."""

from __future__ import annotations

from typing import Any

from ..packet import hex_bytes
from .common import bit, signed_hex, u16be


def ascii_field(data: bytes) -> str:
    return data.rstrip(b"\x00 ").decode("ascii", errors="replace")


def decode_timer(hour_byte: int, minute_byte: int) -> dict[str, Any]:
    if bit(hour_byte, 0x80):
        return {"enabled": False}
    return {
        "enabled": True,
        "hour": hour_byte & 0x1F,
        "minute": minute_byte & 0x3F,
    }


def decode_preference(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "preference",
        "raw": hex_bytes(payload),
    }
    if len(payload) >= 16:
        result["system_name"] = ascii_field(payload[:16])
    if len(payload) >= 23:
        result.update({
            "unknown_16_17": hex_bytes(payload[16:18]),
            "address_or_location": payload[18],
            "version_or_flags": hex_bytes(payload[19:23]),
        })
    elif len(payload) >= 19:
        flags_16 = payload[16]
        flags_17 = payload[17]
        flags_18 = payload[18]
        result.update({
            "show_ac_errors": bit(flags_16, 0x20),
            "show_outside_temp": bit(flags_16, 0x08),
            "show_control_sensor": bit(flags_16, 0x04),
            "use_fahrenheit": bit(flags_17, 0x80),
            "location": flags_17 & 0x7F,
            "screensaver_enabled": bit(flags_18, 0x80),
            "screensaver_timeout": flags_18 & 0x7F,
        })
    else:
        result["tail"] = hex_bytes(payload[16:])
    return result


def decode_group_name(payload: bytes) -> dict[str, Any]:
    records = []
    for offset in range(0, len(payload) - 8, 9):
        rec = payload[offset:offset + 9]
        records.append({
            "group": rec[0],
            "name": ascii_field(rec[1:9]),
            "raw": hex_bytes(rec),
        })
    return {
        "type": "group_name",
        "record_count": len(records),
        "records": records,
        "trailing": hex_bytes(payload[len(records) * 9:]),
    }


def decode_main_display_new(payload: bytes) -> dict[str, Any]:
    records = []
    for offset in range(0, len(payload) - 4, 5):
        rec = payload[offset:offset + 5]
        records.append({
            "ac": rec[0] & 0x0F,
            "hidden": bit(rec[0], 0x80),
            "bytes_1_4": hex_bytes(rec[1:5]),
            "raw": hex_bytes(rec),
        })
    return {
        "type": "main_display_new",
        "record_count": len(records),
        "records": records,
        "trailing": hex_bytes(payload[len(records) * 5:]),
    }


def decode_favourite(payload: bytes) -> dict[str, Any]:
    records = []
    for offset in range(0, len(payload) - 10, 11):
        rec = payload[offset:offset + 11]
        records.append({
            "favourite": rec[0],
            "name": ascii_field(rec[1:9]),
            "groups_1_8_bitmap": rec[9],
            "groups_9_16_bitmap": rec[10],
            "raw": hex_bytes(rec),
        })
    return {
        "type": "favourite",
        "record_count": len(records),
        "records": records,
        "trailing": hex_bytes(payload[len(records) * 11:]),
    }


def decode_active_favourite(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "active_favourite",
        "raw": hex_bytes(payload),
    }
    if not payload:
        result["truncated"] = True
        return result
    result["active_favourite"] = payload[0]
    names = []
    offset = 1
    index = 0
    while offset + 8 <= len(payload):
        names.append({
            "favourite": index,
            "name": ascii_field(payload[offset:offset + 8]),
            "raw": hex_bytes(payload[offset:offset + 8]),
        })
        offset += 8
        index += 1
    result["names"] = names
    result["trailing"] = hex_bytes(payload[offset:])
    return result


def decode_set_active_favourite(payload: bytes) -> dict[str, Any]:
    if len(payload) < 1:
        return {"type": "set_active_favourite", "truncated": True, "raw": hex_bytes(payload)}
    return {
        "type": "set_active_favourite",
        "favourite": payload[0],
        "tail": hex_bytes(payload[1:]),
    }


def decode_set_favourite(payload: bytes) -> dict[str, Any]:
    decoded = decode_favourite(payload)
    decoded["type"] = "set_favourite"
    return decoded


def decode_password_info(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "password_info",
        "raw": hex_bytes(payload),
    }
    if not payload:
        result["truncated"] = True
        return result
    result["page"] = payload[0]
    if payload[0] == 1 and len(payload) >= 11:
        result.update({
            "enabled": bool(payload[1]),
            "length": payload[2],
            "password": ascii_field(payload[3:11]),
        })
    elif payload[0] == 2 and len(payload) >= 3:
        result.update({
            "lock_flags": payload[1],
            "timeout_or_mode": payload[2],
        })
    else:
        result["tail"] = hex_bytes(payload[1:])
    return result


def decode_set_password_info(payload: bytes) -> dict[str, Any]:
    decoded = decode_password_info(payload)
    decoded["type"] = "set_password_info"
    return decoded


def decode_service(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "service",
        "raw": hex_bytes(payload),
    }
    if len(payload) >= 22:
        result.update({
            "company": ascii_field(payload[:10]),
            "phone": ascii_field(payload[10:22]),
            "tail": hex_bytes(payload[22:]),
        })
        if len(payload) >= 30:
            flags = payload[22]
            result.update({
                "show_service_due": bit(flags, 0x80),
                "service_due_locked": bit(flags, 0x01),
                "filter_clean_due": bit(flags, 0x02),
                "maintenance_due": bit(flags, 0x04),
                "months": payload[23],
                "days": u16be(payload, 24),
                "runtime_hours": int.from_bytes(payload[26:30], "big"),
                "tail": hex_bytes(payload[30:]),
            })
    else:
        result["ascii"] = ascii_field(payload)
    return result


def decode_set_service(payload: bytes) -> dict[str, Any]:
    decoded = decode_service(payload)
    decoded["type"] = "set_service"
    return decoded


def decode_clear_notification(payload: bytes) -> dict[str, Any]:
    return {
        "type": "clear_notification",
        "notification": payload[0] if payload else None,
        "raw": hex_bytes(payload),
        "truncated": not payload,
    }


def decode_dialog_message(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "dialog_message",
        "raw": hex_bytes(payload),
    }
    if not payload:
        result["request"] = True
        return result
    if len(payload) >= 49:
        result.update({
            "message_id": payload[0],
            "pin_or_code": ascii_field(payload[1:5]),
            "password_length": payload[5],
            "password": ascii_field(payload[6:14]),
            "company": ascii_field(payload[23:33]),
            "phone": ascii_field(payload[33:45]),
            "tail": hex_bytes(payload[45:]),
        })
    else:
        result["ascii"] = ascii_field(payload)
    return result


def decode_program_define_new(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "program_define_new", "raw": hex_bytes(payload)}
    if len(payload) < 4:
        result["truncated"] = True
        return result
    record_len = payload[3]
    result.update({
        "program_count": payload[0],
        "linked_ac": bit(payload[1], 0x01),
        "record_len": record_len,
    })
    records = []
    offset = 4
    while record_len > 0 and offset + record_len <= len(payload):
        rec = payload[offset:offset + record_len]
        entry: dict[str, Any] = {
            "program": rec[0] & 0x07 if rec else None,
            "enabled": bit(rec[0], 0x80) if rec else None,
            "raw": hex_bytes(rec),
        }
        if len(rec) >= 26:
            entry.update({
                "days_bitmap": rec[1] & 0x7F,
                "name": ascii_field(rec[2:10]),
                "groups_1_8_bitmap": rec[10],
                "groups_9_16_bitmap": rec[11],
                "active_ac_bitmap": rec[18] & 0x0F,
                "on_timer": decode_timer(rec[20], rec[21]),
                "on_setpoint": rec[22] & 0x3F,
                "off_timer": decode_timer(rec[24], rec[25]),
            })
        records.append(entry)
        offset += record_len
    result["records"] = records
    result["trailing"] = hex_bytes(payload[offset:])
    return result


def decode_program_define(payload: bytes) -> dict[str, Any]:
    decoded = decode_program_define_new(payload)
    decoded["type"] = "program_define"
    return decoded


def decode_set_program_define_new(payload: bytes) -> dict[str, Any]:
    decoded = decode_program_define_new(payload)
    decoded["type"] = "set_program_define_new"
    return decoded


def decode_ac_runtime_status(payload: bytes) -> dict[str, Any]:
    records = []
    for offset in range(0, len(payload) - 3, 4):
        rec = payload[offset:offset + 4]
        running_hours = u16be(rec, 0)
        records.append({
            "ac": offset // 4,
            "running_hours": running_hours,
            "minutes_or_flags": running_hours,
            "raw_word_2": u16be(rec, 2),
            "raw": hex_bytes(rec),
        })
    return {
        "type": "ac_runtime_status",
        "record_count": len(records),
        "records": records,
        "trailing": hex_bytes(payload[len(records) * 4:]),
    }


def decode_main_display(payload: bytes) -> dict[str, Any]:
    decoded = decode_main_display_new(payload)
    decoded["type"] = "main_display"
    return decoded


def decode_setting_data(payload: bytes) -> dict[str, Any]:
    return {
        "type": "setting_data",
        "raw": hex_bytes(payload),
        "ascii": ascii_field(payload),
    }


def decode_ac_timer(payload: bytes) -> dict[str, Any]:
    records = []
    if len(payload) >= 8 and len(payload) % 8 == 0:
        for offset in range(0, len(payload), 8):
            rec = payload[offset:offset + 8]
            records.append({
                "ac": offset // 8,
                "on_timer": decode_timer(rec[0], rec[1]),
                "off_timer": decode_timer(rec[2], rec[3]),
                "reserved": hex_bytes(rec[4:8]),
                "raw": hex_bytes(rec),
            })
        consumed = len(records) * 8
    else:
        for offset in range(0, len(payload) - 1, 2):
            records.append({
                "ac": offset // 2,
                "timer": decode_timer(payload[offset], payload[offset + 1]),
                "raw": hex_bytes(payload[offset:offset + 2]),
            })
        consumed = len(records) * 2
    return {
        "type": "ac_timer",
        "record_count": len(records),
        "records": records,
        "trailing": hex_bytes(payload[consumed:]),
    }


def decode_set_ac_timer(payload: bytes) -> dict[str, Any]:
    result = decode_ac_timer(payload[1:] if len(payload) % 2 == 1 else payload)
    result["type"] = "set_ac_timer"
    if payload and len(payload) % 2 == 1:
        result["target_ac"] = payload[0]
        result["raw"] = hex_bytes(payload)
    return result


def decode_turbo_group(payload: bytes) -> dict[str, Any]:
    records = []
    groups = []
    for ac, value in enumerate(payload):
        group = None if value == 0xFF else value
        records.append({
            "ac": ac,
            "group": group,
            "ui_zone": group + 1 if group is not None and group < 16 else None,
            "raw": signed_hex(value),
        })
        if group is not None:
            groups.append(group)
    return {
        "type": "turbo_group",
        "record_count": len(records),
        "records": records,
        "groups_zero_based": groups,
        "groups_one_based": [group + 1 for group in groups],
        "raw": hex_bytes(payload),
    }


def decode_datetime(payload: bytes) -> dict[str, Any]:
    if len(payload) < 8:
        return {"type": "datetime", "truncated": True, "raw": hex_bytes(payload)}
    return {
        "type": "datetime",
        "status_or_prefix": payload[0],
        "year": 2000 + payload[1],
        "month": payload[2],
        "day": payload[3],
        "weekday": payload[4],
        "hour": payload[5],
        "minute": payload[6],
        "second": payload[7],
        "raw": hex_bytes(payload),
    }


def decode_debug_info(payload: bytes) -> dict[str, Any]:
    return {
        "type": "debug_info",
        "text": ascii_field(payload),
        "raw": hex_bytes(payload),
    }


def decode_gateway_info(payload: bytes) -> dict[str, Any]:
    return {
        "type": "gateway_info",
        "text": ascii_field(payload),
        "raw": hex_bytes(payload),
    }
