"""Intent-level command mapping for app/API callers."""

from __future__ import annotations

from typing import Any

from .. import commands
from ..session.queue import TransactionSpec


class CommandRequestError(ValueError):
    """Raised when an API command request is invalid or unsupported."""


def build_transaction(action: str, data: dict[str, Any], *, state: dict[str, Any] | None = None) -> TransactionSpec:
    """Build a runtime transaction from a UI/API command intent."""
    _validate_smart_limits(action, data, state or {})
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
        if action == "ac_timer_table":
            return commands.ac_timer_table_command(_record_list(data, "records"), ac_count=_optional_int(data, "ac_count") or 4)
        if action == "group_name":
            return commands.group_name_command(_int(data, "group"), _str(data, "name"))
        if action == "turbo_group":
            return commands.turbo_group_command(
                _int(data, "ac"),
                _int(data, "group"),
                _optional_int_list(data, "current_groups"),
                one_duct_system=_optional_bool(data, "one_duct_system") or False,
                ac_count=_optional_int(data, "ac_count"),
            )
        if action == "preference":
            if _has_any(data, (
                "show_ac_errors",
                "show_outside_temp",
                "show_control_sensor",
                "use_fahrenheit",
                "location",
                "screensaver_enabled",
                "screensaver_timeout",
            )):
                return commands.preference_full_command(
                    _str(data, "system_name"),
                    show_ac_errors=_optional_bool(data, "show_ac_errors") or False,
                    show_outside_temp=_optional_bool(data, "show_outside_temp") or False,
                    show_control_sensor=_optional_bool(data, "show_control_sensor") or False,
                    use_fahrenheit=_optional_bool(data, "use_fahrenheit") or False,
                    location=_optional_int(data, "location") or 0,
                    screensaver_enabled=_optional_bool(data, "screensaver_enabled") or False,
                    screensaver_timeout=_optional_int(data, "screensaver_timeout") or 0,
                )
            return commands.preference_command(_str(data, "system_name"))
        if action == "service":
            return commands.service_command(
                _str(data, "company"),
                _str(data, "phone"),
                show_service_due=_optional_bool(data, "show_service_due") or False,
                service_due_locked=_optional_bool(data, "service_due_locked") or False,
                filter_clean_due=_optional_bool(data, "filter_clean_due") or False,
                maintenance_due=_optional_bool(data, "maintenance_due") or False,
                months=_optional_int(data, "months") or 0,
                days=_optional_int(data, "days") or 0,
                runtime_hours=_optional_int(data, "runtime_hours") or 0,
                tail=_hex_bytes(data, "tail", default=b""),
            )
        if action == "parameters":
            return commands.parameters_command(
                _int(data, "group_count"),
                damper_rpm=_int(data, "damper_rpm"),
                touchpad_1_location=_int(data, "touchpad_1_location"),
                touchpad_2_location=_int(data, "touchpad_2_location"),
                ac_button_blocked=_optional_bool(data, "ac_button_blocked") or False,
                show_outside_temp=_optional_bool(data, "show_outside_temp") or False,
                lock_to_temp_control=_optional_bool(data, "lock_to_temp_control") or False,
                show_control_sensor=_optional_bool(data, "show_control_sensor") or False,
            )
        if action == "ac_base_info":
            return commands.ac_base_info_command(
                _record_list(data, "records"),
                one_duct_system=_optional_bool(data, "one_duct_system") or False,
                ac_count=_optional_int(data, "ac_count"),
            )
        if action == "ac_setting_new":
            return commands.ac_setting_new_command(_record_list(data, "records"))
        if action == "program_define_new":
            return commands.program_define_new_command(
                _record_list(data, "records"),
                program_count=_optional_int(data, "program_count"),
                linked_ac=_optional_bool(data, "linked_ac") or False,
            )
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
            return commands.balance_start_command(
                _optional_int_list(data, "current_values"),
                zone=_optional_int(data, "zone"),
                value=_optional_int(data, "value") or 0,
            )
        if action == "balance_stop":
            return commands.balance_stop_command(_optional_int_list(data, "current_values"))
        if action == "sensor_temperature":
            temperature = _optional_int(data, "temperature")
            if temperature is None:
                raw_temperature = _int(data, "encoded_temperature")
                temperature = raw_temperature - 256 if raw_temperature > 127 else raw_temperature
            return commands.sensor_temperature_command(_int(data, "sensor"), temperature)
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


def _optional_int_list(data: dict[str, Any], key: str) -> list[int] | None:
    if key not in data or data[key] is None:
        return None
    return _int_list(data, key)


def _validate_smart_limits(action: str, data: dict[str, Any], state: dict[str, Any]) -> None:
    if not state:
        return
    setpoint = _command_setpoint(action, data)
    if setpoint is None:
        return
    ac = _command_ac(action, data, state)
    if ac is None:
        return
    limits = _ac_setpoint_limits(state, ac)
    if limits is None:
        return
    minimum, maximum = limits
    if not minimum <= setpoint <= maximum:
        raise CommandRequestError(f"setpoint must be between {minimum} and {maximum} for AC {ac + 1}, got {setpoint}")


def _command_setpoint(action: str, data: dict[str, Any]) -> int | None:
    if action == "ac_status":
        return _optional_int(data, "setpoint")
    if action == "group_setpoint":
        return _int(data, "setpoint")
    if action in {"group_power", "group_turbo"}:
        sensor_control = _optional_bool(data, "sensor_control")
        if sensor_control is False:
            return None
        return _optional_int(data, "setpoint") or 23
    return None


def _command_ac(action: str, data: dict[str, Any], state: dict[str, Any]) -> int | None:
    if action == "ac_status":
        return _int(data, "ac")
    if action in {"group_setpoint", "group_power", "group_turbo"}:
        return _ac_for_group(state, _int(data, "group"))
    return None


def _ac_setpoint_limits(state: dict[str, Any], ac: int) -> tuple[int, int] | None:
    record = _indexed(state.get("acs") or {}, ac)
    if not isinstance(record, dict):
        return None
    settings = record.get("settings") or {}
    if not isinstance(settings, dict):
        return None
    minimum = settings.get("min_setpoint")
    maximum = settings.get("max_setpoint")
    if not isinstance(minimum, int) or not isinstance(maximum, int) or minimum > maximum:
        return None
    return max(4, minimum), min(35, maximum)


def _ac_for_group(state: dict[str, Any], group: int) -> int | None:
    acs = state.get("acs") or {}
    if not isinstance(acs, dict):
        return None
    for key, record in acs.items():
        if not isinstance(record, dict):
            continue
        base = record.get("base") or {}
        if not isinstance(base, dict):
            continue
        start = base.get("group_start")
        count = base.get("group_count")
        if isinstance(start, int) and isinstance(count, int) and start <= group < start + count:
            try:
                return int(key)
            except (TypeError, ValueError):
                ac = base.get("ac")
                return ac if isinstance(ac, int) else None
    if len(acs) == 1:
        only_key = next(iter(acs))
        try:
            return int(only_key)
        except (TypeError, ValueError):
            record = acs[only_key]
            if isinstance(record, dict):
                base = record.get("base") or {}
                ac = base.get("ac") if isinstance(base, dict) else None
                return ac if isinstance(ac, int) else None
    return None


def _indexed(mapping: Any, key: int) -> Any:
    if not isinstance(mapping, dict):
        return None
    return mapping.get(key) if key in mapping else mapping.get(str(key))


def _record_list(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    if key not in data:
        raise CommandRequestError(f"missing required field: {key}")
    value = data[key]
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise CommandRequestError(f"{key} must be a list of objects")
    return value


def _has_any(data: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return any(key in data and data[key] is not None for key in keys)


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
