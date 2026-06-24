"""Payload decoder registry.

The replacement-touchscreen implementation is APK-first.  MAINBOARD_DECODERS
contains the internal RS485 surface derived from the touchscreen APK and bus
captures.  REFERENCE_DECODERS is kept only for offline capture archaeology of
mobile/client traffic observed on the same packet family.
"""

from __future__ import annotations

from typing import Any, Callable

from . import client_api, config, expanded, internal_misc, internal_status, ui_config

Decoder = Callable[[bytes], dict[str, Any]]

MAINBOARD_DECODERS: dict[int, Decoder] = {
    0x1F: expanded.decode_expanded,
    0x20: internal_status.decode_set_group_status,
    0x21: internal_status.decode_group_status,
    0x22: internal_status.decode_set_ac_status,
    0x23: internal_status.decode_ac_status,
    0x24: internal_misc.decode_expansion_damper_status,
    0x26: internal_status.decode_touchpad_temperature,
    0x27: internal_status.decode_led_response,
    0x30: ui_config.decode_set_active_favourite,
    0x31: ui_config.decode_active_favourite,
    0x32: ui_config.decode_set_favourite,
    0x33: ui_config.decode_favourite,
    0x35: ui_config.decode_program_define,
    0x36: ui_config.decode_set_ac_timer,
    0x37: ui_config.decode_ac_timer,
    0x3C: ui_config.decode_set_program_define_new,
    0x3D: ui_config.decode_program_define_new,
    0x40: ui_config.decode_datetime,
    0x41: ui_config.decode_datetime,
    0x43: ui_config.decode_ac_runtime_status,
    0x50: ui_config.decode_turbo_group,
    0x51: ui_config.decode_turbo_group,
    0x52: ui_config.decode_group_name,
    0x53: ui_config.decode_group_name,
    0x54: ui_config.decode_preference,
    0x55: ui_config.decode_preference,
    0x59: ui_config.decode_main_display_new,
    0x5B: ui_config.decode_main_display,
    0x5F: ui_config.decode_setting_data,
    0x60: config.decode_set_parameters,
    0x61: config.decode_parameters,
    0x62: config.decode_balance_control,
    0x63: config.decode_balance,
    0x64: config.decode_balance_control,
    0x66: config.decode_set_grouping,
    0x67: config.decode_grouping,
    0x68: config.decode_spill,
    0x69: config.decode_spill,
    0x6A: ui_config.decode_set_service,
    0x6B: ui_config.decode_service,
    0x6C: ui_config.decode_set_password_info,
    0x6D: ui_config.decode_password_info,
    0x6E: ui_config.decode_clear_notification,
    0x6F: ui_config.decode_dialog_message,
    0x70: config.decode_pair_sensor,
    0x71: config.decode_sensor_list,
    0x72: config.decode_set_sensor_temp,
    0x73: config.decode_sensor_info,
    0x74: config.decode_set_ac_base_info,
    0x75: config.decode_ac_base_info,
    0x77: config.decode_ac_setting,
    0x78: config.decode_set_ac_setting_new,
    0x79: config.decode_ac_setting_new,
    0x81: ui_config.decode_debug_info,
    0x83: ui_config.decode_gateway_info,
}

REFERENCE_DECODERS: dict[int, Decoder] = {
    0x2A: client_api.decode_group_control,
    0x2B: client_api.decode_group_status,
    0x2C: client_api.decode_ac_control,
    0x2D: client_api.decode_ac_status,
    0x2F: client_api.decode_bulk_info,
}

DECODERS: dict[int, Decoder] = {
    **MAINBOARD_DECODERS,
    **REFERENCE_DECODERS,
}


def decode_mainboard_payload(command: int, payload: bytes) -> dict[str, Any]:
    """Decode only commands relevant to replacing the touchscreen on RS485."""
    decoder = MAINBOARD_DECODERS.get(command)
    if decoder is None:
        return {"type": "unknown", "payload_len": len(payload)}
    try:
        return decoder(payload)
    except Exception as exc:
        return {
            "type": "decode_error",
            "error": f"{type(exc).__name__}: {exc}",
            "payload_len": len(payload),
        }


def decode_capture_payload(command: int, payload: bytes) -> dict[str, Any]:
    """Decode known payloads for offline capture analysis, including reference-only commands."""
    decoder = DECODERS.get(command)
    if decoder is None:
        return {"type": "unknown", "payload_len": len(payload)}
    try:
        return decoder(payload)
    except Exception as exc:
        return {
            "type": "decode_error",
            "error": f"{type(exc).__name__}: {exc}",
            "payload_len": len(payload),
        }
