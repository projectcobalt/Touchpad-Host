"""Expanded command payloads, including touchpad address presence."""

from __future__ import annotations

from typing import Any

from ..packet import hex_bytes
from .common import bcd_string, bit


def decode_expanded(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "expanded",
        "subtype": hex_bytes(payload[:2]),
    }
    if len(payload) >= 2 and payload[0] == 0xFF and payload[1] == 0x01:
        result["expanded_name"] = "touchpad_address_presence"
        if len(payload) == 2:
            result["request"] = "ask_touchpad_info"
        elif len(payload) >= 21:
            flags_a = payload[10]
            flags_b = payload[19]
            sw_len = payload[20]
            result.update({
                "touchpad_id": bcd_string(payload[2:10]),
                "address_raw": flags_a,
                "address": flags_a & 0x0F,
                "connected_to_server": bit(flags_a, 0x40) or bit(flags_b, 0x40),
                "is_master": bit(flags_a, 0x80) or bit(flags_a, 0x10) or bit(flags_b, 0x10),
                "wifi_connected": bit(flags_b, 0x20),
                "association_time_raw": hex_bytes(payload[11:19]),
                "software_len": sw_len,
                "software_version": payload[21:21 + sw_len].decode("ascii", errors="replace"),
            })
    elif len(payload) >= 2 and payload[0] == 0xFD:
        result["expanded_name"] = "debug"
    return result
