"""Intent-level command mapping for app/API callers."""

from __future__ import annotations

from typing import Any

from .. import commands
from ..session.queue import TransactionSpec


class CommandRequestError(ValueError):
    """Raised when an API command request is invalid or unsupported."""


def build_transaction(action: str, data: dict[str, Any]) -> TransactionSpec:
    """Build a runtime transaction from a UI/API command intent."""
    spec = _build_command_spec(action, data)
    return TransactionSpec.from_command(spec, name=action)


def _build_command_spec(action: str, data: dict[str, Any]) -> commands.CommandSpec:
    try:
        if action == "group_power":
            sensor_control = _optional_bool(data, "sensor_control")
            if sensor_control is None:
                sensor_control = True
            value = _group_control_value(data, sensor_control)
            return commands.group_power_command(_int(data, "group"), _bool(data, "on"), sensor_control=sensor_control, value=value)
        if action == "group_percentage":
            return commands.group_percentage_command(_int(data, "group"), _int(data, "percentage"))
        if action == "group_setpoint":
            return commands.group_setpoint_command(_int(data, "group"), _int(data, "setpoint"))
        if action == "group_turbo":
            sensor_control = _optional_bool(data, "sensor_control")
            if sensor_control is None:
                sensor_control = True
            value = _group_control_value(data, sensor_control)
            return commands.raw_command(0x20, commands.set_group_turbo(_int(data, "group"), sensor_control=sensor_control, value=value))
        if action == "ac_status":
            return commands.ac_status_command(
                _int(data, "ac"),
                power_on=_optional_bool(data, "power_on"),
                mode=_optional_int(data, "mode"),
                fan=_optional_int(data, "fan"),
                setpoint=_optional_int(data, "setpoint"),
            )
        if action == "active_favourite":
            return commands.active_favourite_command(_int(data, "favourite"))
        if action == "favourite":
            return commands.favourite_command(_int(data, "favourite"), _str(data, "name"), _int_list(data, "groups"))
        if action == "ac_timer":
            hour = _optional_int(data, "hour")
            minute = _optional_int(data, "minute")
            return commands.ac_timer_command(_int(data, "ac"), hour=hour, minute=minute)
        if action == "group_name":
            return commands.group_name_command(_int(data, "group"), _str(data, "name"))
        if action == "preference":
            return commands.preference_command(_str(data, "system_name"))
        if action == "service":
            return commands.service_command(_str(data, "company"), _str(data, "phone"), _hex_bytes(data, "tail", default=b""))
        if action == "grouping":
            return commands.grouping_command(
                _int(data, "group"),
                zone_start=_int(data, "zone_start"),
                zone_count=_int(data, "zone_count"),
                min_percent=_int(data, "min_percent"),
                thermostat=_int(data, "thermostat"),
            )
        if action == "spill":
            return commands.spill_command(_int_list(data, "ac_spill_types"), _int_list(data, "spill_groups"))
        if action == "pair_sensor":
            return commands.pair_sensor_command(_bool(data, "pairing"))
        if action == "balance_start":
            return commands.raw_command(0x74, commands.start_balance())
        if action == "balance_stop":
            return commands.raw_command(0x75, commands.stop_balance())
        if action == "sensor_temperature":
            return commands.sensor_temperature_command(_int(data, "sensor"), _int(data, "encoded_temperature"))
        if action == "raw":
            return commands.raw_command(_int(data, "command"), _hex_bytes(data, "payload", default=b""))
    except commands.CommandBuildError as exc:
        raise CommandRequestError(str(exc)) from exc

    raise CommandRequestError(f"unsupported command action: {action}")


def _int(data: dict[str, Any], key: str) -> int:
    if key not in data:
        raise CommandRequestError(f"missing required field: {key}")
    value = data[key]
    if isinstance(value, bool):
        raise CommandRequestError(f"{key} must be an integer")
    try:
        return int(value, 0) if isinstance(value, str) else int(value)
    except (TypeError, ValueError) as exc:
        raise CommandRequestError(f"{key} must be an integer") from exc


def _optional_int(data: dict[str, Any], key: str) -> int | None:
    if key not in data or data[key] is None:
        return None
    return _int(data, key)


def _bool(data: dict[str, Any], key: str) -> bool:
    if key not in data:
        raise CommandRequestError(f"missing required field: {key}")
    return _coerce_bool(data[key], key)


def _optional_bool(data: dict[str, Any], key: str) -> bool | None:
    if key not in data or data[key] is None:
        return None
    return _coerce_bool(data[key], key)


def _coerce_bool(value: Any, key: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"true", "on", "yes", "1"}:
            return True
        if lowered in {"false", "off", "no", "0"}:
            return False
    raise CommandRequestError(f"{key} must be a boolean")


def _group_control_value(data: dict[str, Any], sensor_control: bool) -> int:
    if "value" in data and data["value"] is not None:
        return _int(data, "value")
    if sensor_control:
        return _optional_int(data, "setpoint") or 23
    return _optional_int(data, "percentage") or 0


def _str(data: dict[str, Any], key: str) -> str:
    if key not in data:
        raise CommandRequestError(f"missing required field: {key}")
    return str(data[key])


def _int_list(data: dict[str, Any], key: str) -> list[int]:
    if key not in data:
        raise CommandRequestError(f"missing required field: {key}")
    value = data[key]
    if not isinstance(value, list):
        raise CommandRequestError(f"{key} must be a list")
    return [int(item, 0) if isinstance(item, str) else int(item) for item in value]


def _hex_bytes(data: dict[str, Any], key: str, *, default: bytes | None = None) -> bytes:
    if key not in data:
        if default is not None:
            return default
        raise CommandRequestError(f"missing required field: {key}")
    value = data[key]
    if isinstance(value, bytes):
        return value
    if isinstance(value, list):
        return bytes(int(item) & 0xFF for item in value)
    if isinstance(value, str):
        compact = value.replace(" ", "").replace(":", "").replace("-", "")
        if len(compact) % 2:
            raise CommandRequestError(f"{key} must contain whole hex bytes")
        return bytes.fromhex(compact)
    raise CommandRequestError(f"{key} must be hex text or a byte list")
