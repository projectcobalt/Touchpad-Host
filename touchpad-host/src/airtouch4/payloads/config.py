"""Configuration, grouping, spill, sensor, and AC capability payloads."""

from __future__ import annotations

from typing import Any

from ..packet import hex_bytes
from .common import SENSOR_SELECTORS, bcd_string, bit, parse_internal_temperature, signed_hex, u16be


def decode_parameters(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "parameters"}
    if len(payload) < 15:
        result.update({"truncated": True, "raw": hex_bytes(payload)})
        return result
    flags = payload[4]
    result.update({
        "group_count": payload[0] + 1,
        "damper_rpm": payload[1],
        "touchpad_1_location": payload[2],
        "touchpad_2_location": payload[3],
        "ac_button_blocked": bit(flags, 0x80),
        "zimi_control_enabled": bit(flags, 0x40),
        "show_outside_temp": bit(flags, 0x01),
        "lock_to_temp_control": bit(flags, 0x02),
        "show_control_sensor": bit(flags, 0x04),
        "device_id": bcd_string(payload[5:9]),
        "hardware_version_raw": hex_bytes(payload[9:11]),
        "firmware_version_raw": hex_bytes(payload[11:13]),
        "boot_version_raw": hex_bytes(payload[13:15]),
    })
    return result


def decode_set_parameters(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "set_parameters", "raw": hex_bytes(payload)}
    if len(payload) >= 5:
        flags = payload[4]
        result.update({
            "group_count": payload[0] + 1,
            "damper_rpm": payload[1],
            "touchpad_1_location": payload[2],
            "touchpad_2_location": payload[3],
            "ac_button_blocked": bit(flags, 0x80),
            "zimi_control_enabled": bit(flags, 0x40),
            "show_outside_temp": bit(flags, 0x01),
            "lock_to_temp_control": bit(flags, 0x02),
            "show_control_sensor": bit(flags, 0x04),
            "tail": hex_bytes(payload[5:]),
        })
    else:
        result["truncated"] = True
    return result


def decode_balance(payload: bytes) -> dict[str, Any]:
    zones = []
    for offset in range(0, len(payload) - 1, 2):
        zones.append({
            "zone": offset // 2,
            "set_value": payload[offset],
            "current_value": payload[offset + 1],
        })
    return {
        "type": "balance",
        "zones": zones,
        "trailing": hex_bytes(payload[len(zones) * 2:]),
    }


def decode_balance_control(payload: bytes) -> dict[str, Any]:
    return {
        "type": "balance_control",
        "set_values": list(payload[:16]),
        "zones": [
            {"zone": index, "set_value": value}
            for index, value in enumerate(payload[:16])
        ],
        "trailing": hex_bytes(payload[16:]),
    }


def decode_set_grouping(payload: bytes) -> dict[str, Any]:
    if len(payload) < 4:
        return {"type": "set_grouping", "truncated": True, "raw": hex_bytes(payload)}
    thermostat = payload[3]
    return {
        "type": "set_grouping",
        "group": payload[0],
        "ui_zone": payload[0] + 1,
        "zone_start": payload[1] & 0x3F,
        "zone_count": ((payload[1] & 0xC0) >> 6) + 1,
        "min_percent": payload[2],
        "thermostat": thermostat,
        "thermostat_name": SENSOR_SELECTORS.get(thermostat, f"sensor_addr_{thermostat}"),
        "tail": hex_bytes(payload[4:]),
    }


def _available_grouping_selectors(flags: int) -> list[str]:
    selectors = []
    if bit(flags, 0x01):
        selectors.append("rf_sensor_1")
    if bit(flags, 0x02):
        selectors.append("rf_sensor_2")
    if bit(flags, 0x04):
        selectors.append("touchpad_1")
    if bit(flags, 0x08):
        selectors.append("touchpad_2")
    if bit(flags, 0x10):
        selectors.append("average")
    return selectors


def decode_grouping(payload: bytes) -> dict[str, Any]:
    records = []
    for offset in range(0, len(payload) - 4, 5):
        rec = payload[offset:offset + 5]
        flags = rec[4]
        thermostat = rec[3]
        records.append({
            "group": rec[0],
            "ui_zone": rec[0] + 1,
            "zone_start": rec[1] & 0x3F,
            "zone_count": ((rec[1] & 0xC0) >> 6) + 1,
            "min_percent": rec[2],
            "thermostat": thermostat,
            "thermostat_name": SENSOR_SELECTORS.get(thermostat, f"sensor_addr_{thermostat}"),
            "available_selectors": _available_grouping_selectors(flags),
            "has_sensor_1": bit(flags, 0x01),
            "has_sensor_2": bit(flags, 0x02),
            "has_touchpad_1": bit(flags, 0x04),
            "has_touchpad_2": bit(flags, 0x08),
            "has_average": bit(flags, 0x10),
            "raw": hex_bytes(rec),
        })
    return {
        "type": "grouping",
        "record_count": len(records),
        "records": records,
        "trailing": hex_bytes(payload[len(records) * 5:]),
    }


def decode_spill(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "spill"}
    if len(payload) < 6:
        result.update({"truncated": True, "raw": hex_bytes(payload)})
        return result
    spill_types = []
    for ac in range(4):
        value = (payload[0] >> (ac * 2)) & 0x03
        spill_types.append({
            "ac": ac,
            "value": value,
            "name": {0: "none", 1: "spill", 2: "bypass"}.get(value, "reserved"),
        })
    groups = []
    for group in range(16):
        byte = payload[4 + (group // 8)]
        if bit(byte, 1 << (group % 8)):
            groups.append(group)
    result.update({
        "ac_spill_types": spill_types,
        "spill_groups_zero_based": groups,
        "spill_groups_one_based": [group + 1 for group in groups],
        "unused_bytes_1_3": hex_bytes(payload[1:4]),
        "tail": hex_bytes(payload[6:]),
    })
    return result


def decode_pair_sensor(payload: bytes) -> dict[str, Any]:
    return {
        "type": "pair_sensor",
        "pairing": bool(payload and bit(payload[0], 0x80)),
        "raw": hex_bytes(payload),
    }


def decode_sensor_list(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "sensor_list"}
    if len(payload) < 10:
        result.update({"truncated": True, "raw": hex_bytes(payload)})
        return result
    rf_sensor_addresses = []
    for bank in range(4):
        byte = payload[1 + bank]
        for bit_index in range(8):
            if bit(byte, 1 << bit_index):
                rf_sensor_addresses.append((bank * 8) + bit_index)
    touchpad_addresses = []
    if bit(payload[5], 0x01):
        touchpad_addresses.append(0x90)
    if bit(payload[5], 0x02):
        touchpad_addresses.append(0x91)
    sensor_addresses = rf_sensor_addresses + touchpad_addresses
    supply_air = []
    for ac in range(4):
        raw = payload[6 + ac]
        supply_air.append({
            "ac": ac,
            "raw": signed_hex(raw),
            "status": "disabled" if raw == 0xFF else "error" if raw == 0xFE else "ok",
            "temperature": None if raw in (0xFF, 0xFE) else parse_internal_temperature(raw),
        })
    result.update({
        "pairing": bit(payload[0], 0x80),
        "rf_sensor_addresses": rf_sensor_addresses,
        "touchpad_addresses": touchpad_addresses,
        "sensor_addresses": sensor_addresses,
        "sensor_count": len(sensor_addresses),
        "rf_sensor_count": len(rf_sensor_addresses),
        "touchpad_count": len(touchpad_addresses),
        "supply_air": supply_air,
        "tail": hex_bytes(payload[10:]),
    })
    return result


def decode_set_sensor_temp(payload: bytes) -> dict[str, Any]:
    if len(payload) < 2:
        return {"type": "set_sensor_temp", "truncated": True, "raw": hex_bytes(payload)}
    temperature = payload[1] - 256 if payload[1] > 127 else payload[1]
    return {
        "type": "set_sensor_temp",
        "sensor": payload[0],
        "temperature_raw": payload[1],
        "temperature": temperature,
        "tail": hex_bytes(payload[2:]),
    }


def decode_sensor_info(payload: bytes) -> dict[str, Any]:
    records = []
    for offset in range(0, len(payload) - 11, 12):
        rec = payload[offset:offset + 12]
        signal_raw = rec[3]
        temperature = parse_internal_temperature(rec[1])
        sensor = rec[0]
        if sensor in (0x90, 0x91):
            status = "ok"
            kind = "touchpad"
            battery = None
            low_battery = None
            signal = None
            mac = None
        else:
            kind = "rf"
            status = "missing" if signal_raw == 0xFF else "lost" if signal_raw == 0xFE else "ok"
            if status == "missing":
                temperature = None
                battery = None
                low_battery = None
                mac = None
            else:
                battery = rec[2] & 0x7F
                low_battery = bit(rec[2], 0x80)
                mac = bcd_string(rec[4:12])
            signal = None if status != "ok" else -signal_raw
        records.append({
            "sensor": sensor,
            "sensor_name": SENSOR_SELECTORS.get(sensor, f"rf_sensor_{sensor}"),
            "kind": kind,
            "temperature_raw": signed_hex(rec[1]),
            "temperature": temperature,
            "low_battery": low_battery,
            "battery": battery,
            "status": status,
            "missing": status == "missing",
            "lost": status == "lost",
            "signal_raw": signed_hex(signal_raw),
            "signal": signal,
            "mac": mac,
            "raw": hex_bytes(rec),
        })
    return {
        "type": "sensor_info",
        "record_count": len(records),
        "records": records,
        "trailing": hex_bytes(payload[len(records) * 12:]),
    }


def decode_ac_base_info(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "ac_base_info"}
    if len(payload) < 14:
        result.update({"truncated": True, "raw": hex_bytes(payload)})
        return result
    records = []
    for offset in range(2, len(payload) - 11, 12):
        rec = payload[offset:offset + 12]
        group_start = (rec[0] & 0x30) + (rec[1] & 0x0F)
        group_count = ((rec[0] >> 2) & 0x30) + ((rec[1] >> 4) & 0x0F)
        records.append({
            "ac": rec[0] & 0x0F,
            "raw_group_pack_0": signed_hex(rec[0]),
            "raw_group_pack_1": signed_hex(rec[1]),
            "group_start": group_start,
            "group_count": group_count,
            "brand": u16be(rec, 2),
            "name": rec[4:12].rstrip(b"\x00 ").decode("ascii", errors="replace"),
            "raw": hex_bytes(rec),
        })
    result.update({
        "ac_count": payload[0],
        "one_duct_system": payload[1] == 1,
        "records": records,
        "trailing": hex_bytes(payload[2 + len(records) * 12:]),
    })
    return result


def decode_set_ac_base_info(payload: bytes) -> dict[str, Any]:
    decoded = decode_ac_base_info(payload)
    decoded["type"] = "set_ac_base_info"
    return decoded


def decode_ac_setting_new(payload: bytes) -> dict[str, Any]:
    records = []
    offset = 0
    while offset + 2 <= len(payload):
        ac_byte = payload[offset]
        data_len = payload[offset + 1]
        start = offset + 2
        end = start + data_len
        if data_len < 13 or end > len(payload):
            break
        rec = payload[start:end]
        records.append({
            "ac": ac_byte & 0x0F,
            "hide_spill_group": bit(ac_byte, 0x80),
            "record_len": data_len,
            "ctrl_thermostat": rec[0],
            "cool_adjust": ((rec[1] >> 4) & 0x0F) - 8,
            "heat_adjust": (rec[1] & 0x0F) - 8,
            "modes": {
                "cool": bit(rec[2], 0x10),
                "fan": bit(rec[2], 0x08),
                "dry": bit(rec[2], 0x04),
                "heat": bit(rec[2], 0x02),
                "auto": bit(rec[2], 0x01),
            },
            "fan_values": {
                "auto": rec[3] & 0x0F,
                "quiet": (rec[3] >> 4) & 0x0F,
                "low": rec[4] & 0x0F,
                "medium": (rec[4] >> 4) & 0x0F,
                "high": rec[5] & 0x0F,
                "powerful": (rec[5] >> 4) & 0x0F,
                "turbo": rec[6] & 0x0F,
            },
            "auto_off": bit(rec[7], 0x10),
            "on_time_limit": rec[7] & 0x0F,
            "max_setpoint": rec[8],
            "min_setpoint": rec[9],
            "selector_visibility": {
                "auto": bit(rec[10], 0x02),
                "touchpad_1": bit(rec[10], 0x04),
                "touchpad_2": bit(rec[10], 0x08),
                "average": bit(rec[10], 0x10),
                "economy": bit(rec[10], 0x20),
                "groups_1_8_bitmap": rec[11],
                "groups_9_16_bitmap": rec[12],
            },
            "raw": hex_bytes(payload[offset:end]),
        })
        offset = end
    return {
        "type": "ac_setting_new",
        "record_count": len(records),
        "records": records,
        "trailing": hex_bytes(payload[offset:]),
    }


def decode_ac_setting(payload: bytes) -> dict[str, Any]:
    decoded = decode_ac_setting_new(payload)
    decoded["type"] = "ac_setting"
    return decoded


def decode_set_ac_setting_new(payload: bytes) -> dict[str, Any]:
    decoded = decode_ac_setting_new(payload)
    decoded["type"] = "set_ac_setting_new"
    return decoded
