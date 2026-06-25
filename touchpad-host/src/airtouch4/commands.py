"""Payload builders for UI-relevant internal AirTouch commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class CommandBuildError(ValueError):
    """Raised when a requested command payload would be outside known bounds."""


def _check_range(name: str, value: int, minimum: int, maximum: int) -> int:
    if not minimum <= value <= maximum:
        raise CommandBuildError(f"{name} must be between {minimum} and {maximum}, got {value}")
    return value


def _ascii_fixed(text: str, length: int) -> bytes:
    encoded = text.encode("ascii", errors="replace")[:length]
    return encoded.ljust(length, b"\x00")


def request_payload(*values: int) -> bytes:
    return bytes(_check_range("byte", value, 0, 255) for value in values)


def set_group_control(group: int, power_code: int, *, sensor_control: bool, value: int) -> bytes:
    group = _check_range("group", group, 0, 15)
    power_code = _check_range("power_code", power_code, 0, 3)
    if sensor_control:
        value_byte = 0x80 | (_check_range("setpoint", value, 4, 35) - 4)
    else:
        value_byte = _check_range("percentage", value, 0, 100)
    return bytes(((power_code << 6) | group, value_byte, 0x00, 0x00))


def set_group_power(group: int, on: bool, *, sensor_control: bool = True, value: int = 23) -> bytes:
    return set_group_control(group, 1 if on else 0, sensor_control=sensor_control, value=value)


def set_group_percentage(group: int, percentage: int) -> bytes:
    return set_group_control(group, 2, sensor_control=False, value=percentage)


def set_group_setpoint(group: int, setpoint: int) -> bytes:
    return set_group_control(group, 2, sensor_control=True, value=setpoint)


def set_group_turbo(group: int, *, sensor_control: bool = True, value: int = 23) -> bytes:
    return set_group_control(group, 3, sensor_control=sensor_control, value=value)


def set_active_favourite(favourite: int) -> bytes:
    return bytes((_check_range("favourite", favourite, 0, 3),))


def set_ac_status(ac: int, *, power_on: bool | None = None, mode: int | None = None, fan: int | None = None, setpoint: int | None = None) -> bytes:
    ac = _check_range("ac", ac, 0, 3)
    power_bits = 0x00 if power_on is None else 0xC0 if power_on else 0x80
    mode_value = 7 if mode is None else _check_range("mode", mode, 0, 15)
    fan_value = 7 if fan is None else _check_range("fan", fan, 0, 15)
    if fan_value > 6:
        fan_value = 7
    if mode_value > 4:
        mode_fan = 0x80 | fan_value
    else:
        mode_fan = (mode_value << 4) | fan_value
    setpoint_value = 0x1F if setpoint is None else (_check_range("setpoint", setpoint, 4, 35) - 4) & 0x1F
    return bytes((power_bits | ac, mode_fan, setpoint_value, 0x00))


def set_group_name(group: int, name: str) -> bytes:
    group = _check_range("group", group, 0, 15)
    return bytes((group,)) + _ascii_fixed(name, 8)


def set_favourite(favourite: int, name: str, groups: list[int] | tuple[int, ...]) -> bytes:
    favourite = _check_range("favourite", favourite, 0, 3)
    bitmap = _group_bitmap(groups)
    return bytes((0x80 | favourite,)) + _ascii_fixed(name, 8) + bytes(bitmap)


def set_grouping(group: int, *, zone_start: int, zone_count: int, min_percent: int, thermostat: int) -> bytes:
    group = _check_range("group", group, 0, 15)
    zone_start = _check_range("zone_start", zone_start, 0, 63)
    zone_count = _check_range("zone_count", zone_count, 1, 4)
    min_percent = _check_range("min_percent", min_percent, 0, 100)
    thermostat = _check_range("thermostat", thermostat, 0, 255)
    zone_pack = zone_start | ((zone_count - 1) << 6)
    return bytes((group, zone_pack, min_percent, thermostat))


def set_spill(ac_spill_types: list[int] | tuple[int, ...], spill_groups: list[int] | tuple[int, ...]) -> bytes:
    spill_type_byte = 0
    for ac, value in enumerate(ac_spill_types[:4]):
        value = _check_range("spill_type", value, 0, 3)
        spill_type_byte |= value << (ac * 2)
    bitmap = [0, 0]
    for group in spill_groups:
        group = _check_range("spill_group", group, 0, 15)
        bitmap[group // 8] |= 1 << (group % 8)
    return bytes((spill_type_byte, 0x00, 0x00, 0x00, bitmap[0], bitmap[1]))


def set_pair_sensor(pairing: bool) -> bytes:
    return bytes((0x80 if pairing else 0x00,))


def set_sensor_temperature(sensor: int, temperature: int) -> bytes:
    sensor = _check_range("sensor", sensor, 0, 255)
    temperature = _check_range("temperature", temperature, -10, 40)
    return bytes((sensor, temperature & 0xFF))


def set_datetime(*, year: int, month: int, day: int, weekday: int, hour: int, minute: int, second: int) -> bytes:
    year = _check_range("year", year, 2000, 2255) - 2000
    return bytes((
        0x00,
        year,
        _check_range("month", month, 1, 12),
        _check_range("day", day, 1, 31),
        _check_range("weekday", weekday, 0, 7),
        _check_range("hour", hour, 0, 23),
        _check_range("minute", minute, 0, 59),
        _check_range("second", second, 0, 59),
    ))


def set_preference(system_name: str) -> bytes:
    return _ascii_fixed(system_name, 16)


def set_preference_full(
    system_name: str,
    *,
    show_ac_errors: bool = False,
    show_outside_temp: bool = False,
    show_control_sensor: bool = False,
    use_fahrenheit: bool = False,
    location: int = 0,
    screensaver_enabled: bool = False,
    screensaver_timeout: int = 0,
) -> bytes:
    flags_16 = 0x10
    if show_ac_errors:
        flags_16 |= 0x20
    if show_outside_temp:
        flags_16 |= 0x08
    if show_control_sensor:
        flags_16 |= 0x04
    byte_17 = _check_range("location", location, 0, 127)
    if use_fahrenheit:
        byte_17 |= 0x80
    byte_18 = _check_range("screensaver_timeout", screensaver_timeout, 0, 127)
    if screensaver_enabled:
        byte_18 |= 0x80
    return _ascii_fixed(system_name, 16) + bytes((flags_16, byte_17, byte_18))


def set_ac_base_info(
    records: Sequence[Mapping[str, Any]],
    *,
    one_duct_system: bool = False,
    ac_count: int | None = None,
) -> bytes:
    count = len(records) if ac_count is None else _check_range("ac_count", ac_count, 1, 4)
    if len(records) != count:
        raise CommandBuildError(f"expected {count} AC base records, got {len(records)}")

    payload = bytearray(2 + count * 12)
    payload[0] = count
    payload[1] = 1 if one_duct_system else 0

    records_by_ac = {int(record.get("ac", index)): record for index, record in enumerate(records)}
    for ac in range(count):
        if ac not in records_by_ac:
            raise CommandBuildError(f"missing AC base record for ac {ac}")
        record = records_by_ac[ac]
        group_start = _check_range("group_start", int(record.get("group_start", 0)), 0, 63)
        group_count = _check_range("group_count", int(record.get("group_count", 0)), 0, 63)
        brand = _check_range("brand", int(record.get("brand", 0)), 0, 0xFFFF)
        name = str(record.get("name", ""))

        offset = 2 + ac * 12
        payload[offset] = ac | ((group_start // 16) << 4) | ((group_count // 16) << 6)
        payload[offset + 1] = (group_start & 0x0F) | ((group_count & 0x0F) << 4)
        payload[offset + 2:offset + 4] = brand.to_bytes(2, "big")
        payload[offset + 4:offset + 12] = _ascii_fixed(name, 8)

    return bytes(payload)


def set_ac_group_counts(
    records: Sequence[Mapping[str, Any]],
    group_counts: Sequence[int],
    *,
    one_duct_system: bool = False,
) -> bytes:
    updated: list[dict[str, Any]] = []
    group_start = 0
    for index, record in enumerate(records):
        if index >= len(group_counts):
            raise CommandBuildError(f"missing group_count for ac {index}")
        group_count = _check_range("group_count", int(group_counts[index]), 0, 63)
        next_record = dict(record)
        next_record["group_start"] = group_start
        next_record["group_count"] = group_count
        updated.append(next_record)
        group_start += group_count
    return set_ac_base_info(updated, one_duct_system=one_duct_system)


def set_ac_name(
    records: Sequence[Mapping[str, Any]],
    ac: int,
    name: str,
    *,
    one_duct_system: bool = False,
) -> bytes:
    ac = _check_range("ac", ac, 0, 3)
    updated = []
    seen = False
    for record in records:
        next_record = dict(record)
        if int(next_record.get("ac", -1)) == ac:
            next_record["name"] = name
            seen = True
        updated.append(next_record)
    if not seen:
        raise CommandBuildError(f"missing AC base record for ac {ac}")
    return set_ac_base_info(updated, one_duct_system=one_duct_system)


def set_duct_system(records: Sequence[Mapping[str, Any]], one_duct_system: bool) -> bytes:
    return set_ac_base_info(records, one_duct_system=one_duct_system)


def set_ac_setting_record(
    ac: int,
    *,
    hide_spill_group: bool = False,
    ctrl_thermostat: int = 0,
    cool_adjust: int = 0,
    heat_adjust: int = 0,
    modes: Mapping[str, bool] | None = None,
    fan_values: Mapping[str, int] | None = None,
    auto_off: bool = False,
    on_time_limit: int = 0,
    max_setpoint: int = 30,
    min_setpoint: int = 16,
    selector_visibility: Mapping[str, Any] | None = None,
) -> bytes:
    ac = _check_range("ac", ac, 0, 3)
    cool_adjust = _check_range("cool_adjust", cool_adjust, -8, 7)
    heat_adjust = _check_range("heat_adjust", heat_adjust, -8, 7)
    modes = modes or {}
    fan_values = fan_values or {}
    selector_visibility = selector_visibility or {}

    payload = bytearray(15)
    payload[0] = ac | (0x80 if hide_spill_group else 0x00)
    payload[1] = 13
    payload[2] = _check_range("ctrl_thermostat", ctrl_thermostat, 0, 255)
    payload[3] = ((cool_adjust + 8) << 4) | (heat_adjust + 8)
    payload[4] = (
        (0x10 if bool(modes.get("cool", False)) else 0)
        | (0x08 if bool(modes.get("fan", False)) else 0)
        | (0x04 if bool(modes.get("dry", False)) else 0)
        | (0x02 if bool(modes.get("heat", False)) else 0)
        | (0x01 if bool(modes.get("auto", False)) else 0)
    )
    payload[5] = _fan_nibble(fan_values, "auto") | (_fan_nibble(fan_values, "quiet") << 4)
    payload[6] = _fan_nibble(fan_values, "low") | (_fan_nibble(fan_values, "medium") << 4)
    payload[7] = _fan_nibble(fan_values, "high") | (_fan_nibble(fan_values, "powerful") << 4)
    payload[8] = _fan_nibble(fan_values, "turbo")
    payload[9] = _check_range("on_time_limit", on_time_limit, 0, 15) | (0x10 if auto_off else 0x00)
    payload[10] = _check_range("max_setpoint", max_setpoint, 0, 255)
    payload[11] = _check_range("min_setpoint", min_setpoint, 0, 255)
    payload[12] = _selector_visibility_byte(selector_visibility)
    payload[13] = _check_range("groups_1_8_bitmap", int(selector_visibility.get("groups_1_8_bitmap", 0)), 0, 255)
    payload[14] = _check_range("groups_9_16_bitmap", int(selector_visibility.get("groups_9_16_bitmap", 0)), 0, 255)
    return bytes(payload)


def set_ac_setting_new(records: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(
        set_ac_setting_record(
            int(record.get("ac", 0)),
            hide_spill_group=bool(record.get("hide_spill_group", False)),
            ctrl_thermostat=int(record.get("ctrl_thermostat", 0)),
            cool_adjust=int(record.get("cool_adjust", 0)),
            heat_adjust=int(record.get("heat_adjust", 0)),
            modes=record.get("modes"),
            fan_values=record.get("fan_values"),
            auto_off=bool(record.get("auto_off", False)),
            on_time_limit=int(record.get("on_time_limit", 0)),
            max_setpoint=int(record.get("max_setpoint", 30)),
            min_setpoint=int(record.get("min_setpoint", 16)),
            selector_visibility=record.get("selector_visibility"),
        )
        for record in records
    )


def set_parameters(
    group_count: int,
    *,
    damper_rpm: int,
    touchpad_1_location: int,
    touchpad_2_location: int,
    ac_button_blocked: bool = False,
    show_outside_temp: bool = False,
    lock_to_temp_control: bool = False,
    show_control_sensor: bool = False,
) -> bytes:
    flags = 0x80 if ac_button_blocked else 0x00
    if show_outside_temp:
        flags |= 0x01
    if lock_to_temp_control:
        flags |= 0x02
    if show_control_sensor:
        flags |= 0x04
    return bytes((
        _check_range("group_count", group_count, 1, 16) - 1,
        _check_range("damper_rpm", damper_rpm, 0, 255),
        _check_range("touchpad_1_location", touchpad_1_location, 0, 255),
        _check_range("touchpad_2_location", touchpad_2_location, 0, 255),
        flags,
    ))


def set_timer(hour: int | None, minute: int | None) -> bytes:
    if hour is None or minute is None:
        return b"\x80\x00"
    return bytes((
        _check_range("hour", hour, 0, 23),
        _check_range("minute", minute, 0, 59),
    ))


def set_timer_value(timer: Mapping[str, Any] | None) -> bytes:
    if not timer or not bool(timer.get("enabled", False)):
        hour = int(timer.get("hour", 0)) if timer else 0
        minute = int(timer.get("minute", 0)) if timer else 0
        return bytes((
            _check_range("hour", hour, 0, 23) | 0x80,
            _check_range("minute", minute, 0, 59),
        ))
    return set_timer(_check_range("hour", int(timer.get("hour", 0)), 0, 23), _check_range("minute", int(timer.get("minute", 0)), 0, 59))


def set_ac_timer(ac: int, *, hour: int | None, minute: int | None) -> bytes:
    return bytes((_check_range("ac", ac, 0, 3),)) + set_timer(hour, minute)


def set_ac_timer_table(records: Sequence[Mapping[str, Any]], *, ac_count: int = 4) -> bytes:
    ac_count = _check_range("ac_count", ac_count, 1, 4)
    payload = bytearray(32)
    records_by_ac = {int(record.get("ac", index)): record for index, record in enumerate(records)}
    for ac in range(ac_count):
        record = records_by_ac.get(ac, {})
        offset = ac * 8
        payload[offset:offset + 2] = set_timer_value(record.get("on_timer") or record.get("timer"))
        payload[offset + 2:offset + 4] = set_timer_value(record.get("off_timer"))
    return bytes(payload)


def set_turbo_group(
    ac: int,
    group: int,
    current_groups: Sequence[int] | None = None,
    *,
    one_duct_system: bool = False,
    ac_count: int | None = None,
) -> bytes:
    if one_duct_system:
        return bytes((_turbo_group_byte(group),))
    ac = _check_range("ac", ac, 0, 3)
    count = max(ac + 1, len(current_groups or [])) if ac_count is None else _check_range("ac_count", ac_count, 1, 4)
    ac = _check_range("ac", ac, 0, count - 1)
    payload = bytearray(count)
    for index in range(count):
        value = group if index == ac else (current_groups[index] if current_groups and index < len(current_groups) else 0)
        payload[index] = _turbo_group_byte(value)
    return bytes(payload)


def set_balance_values(
    current_values: Sequence[int] | None = None,
    *,
    zone: int | None = None,
    value: int = 0,
) -> bytes:
    payload = bytearray(16)
    for index, current in enumerate((current_values or [])[:16]):
        payload[index] = _check_range("balance_value", int(current), 0, 255)
    if zone is not None:
        payload[_check_range("zone", zone, 0, 15)] = _check_range("balance_value", value, 0, 255)
    return bytes(payload)


def set_program_define_new(
    records: Sequence[Mapping[str, Any]],
    *,
    program_count: int | None = None,
    linked_ac: bool = False,
) -> bytes:
    count = len(records) if program_count is None else _check_range("program_count", program_count, 0, 8)
    payload = bytearray(260)
    payload[0] = count
    payload[1] = 1 if linked_ac else 0
    payload[3] = 32

    records_by_program = {int(record.get("program", index)): record for index, record in enumerate(records)}
    for program in range(8):
        record = records_by_program.get(program)
        payload[4 + program * 32:4 + (program + 1) * 32] = _program_record(program, record)
    return bytes(payload)


def set_program_count(
    records: Sequence[Mapping[str, Any]],
    count: int,
    *,
    linked_ac: bool = False,
) -> bytes:
    return set_program_define_new(records, program_count=count, linked_ac=linked_ac)


def set_password_info(page: int, payload: bytes) -> bytes:
    return bytes((_check_range("page", page, 1, 2),)) + bytes(payload)


def set_service(
    company: str,
    phone: str,
    *,
    show_service_due: bool = False,
    service_due_locked: bool = False,
    filter_clean_due: bool = False,
    maintenance_due: bool = False,
    months: int = 0,
    days: int = 0,
    runtime_hours: int = 0,
    tail: bytes = b"",
) -> bytes:
    payload = bytearray(30)
    payload[0:10] = _ascii_fixed(company, 10)
    payload[10:22] = _ascii_fixed(phone, 12)
    if show_service_due:
        payload[22] |= 0x80
    if service_due_locked:
        payload[22] |= 0x01
    if filter_clean_due:
        payload[22] |= 0x02
    if maintenance_due:
        payload[22] |= 0x04
    payload[23] = _check_range("months", months, 0, 255)
    payload[24:26] = _check_range("days", days, 0, 65535).to_bytes(2, "big")
    payload[26:30] = _check_range("runtime_hours", runtime_hours, 0, 0xFFFFFFFF).to_bytes(4, "big")
    if tail:
        payload.extend(tail)
    return bytes(payload)


def clear_notification(notification: int = 0) -> bytes:
    return bytes((_check_range("notification", notification, 0, 255),))


def start_balance() -> bytes:
    return set_balance_values()


def stop_balance() -> bytes:
    return set_balance_values()


def raw_payload(payload: bytes | bytearray) -> bytes:
    return bytes(payload)


def _group_bitmap(groups: list[int] | tuple[int, ...]) -> tuple[int, int]:
    bitmap = [0, 0]
    for group in groups:
        group = _check_range("group", group, 0, 15)
        bitmap[group // 8] |= 1 << (group % 8)
    return bitmap[0], bitmap[1]


def _fan_nibble(values: Mapping[str, int], name: str) -> int:
    return _check_range(f"fan_{name}", int(values.get(name, 0)), 0, 15)


def _selector_visibility_byte(values: Mapping[str, Any]) -> int:
    return (
        (0x02 if bool(values.get("auto", False)) else 0)
        | (0x04 if bool(values.get("touchpad_1", False)) else 0)
        | (0x08 if bool(values.get("touchpad_2", False)) else 0)
        | (0x10 if bool(values.get("average", False)) else 0)
        | (0x20 if bool(values.get("economy", False)) else 0)
    )


def _turbo_group_byte(group: int) -> int:
    if group < 0 or group > 16:
        return 0xFF
    return group


def _program_record(program: int, record: Mapping[str, Any] | None) -> bytes:
    payload = bytearray(_raw_record(record, 32) if record else b"\x00" * 32)
    payload[0] = _check_range("program", program, 0, 7) | (0x80 if bool((record or {}).get("enabled", False)) else 0x00)
    if record is None:
        payload[2:10] = _ascii_fixed(f"Program{program + 1}", 8)
        payload[20] = 0x80
        payload[22] = 0x1A
        payload[24] = 0x80
        return bytes(payload)

    payload[1] = _check_range("days_bitmap", int(record.get("days_bitmap", payload[1] & 0x7F)), 0, 0x7F)
    payload[2:10] = _ascii_fixed(str(record.get("name", _ascii_fixed(f"Program{program + 1}", 8).decode("ascii"))), 8)
    payload[10] = _check_range("groups_1_8_bitmap", int(record.get("groups_1_8_bitmap", payload[10])), 0, 255)
    payload[11] = _check_range("groups_9_16_bitmap", int(record.get("groups_9_16_bitmap", payload[11])), 0, 255)
    payload[18] = _check_range("active_ac_bitmap", int(record.get("active_ac_bitmap", payload[18] & 0x0F)), 0, 0x0F)
    payload[20:22] = set_timer_value(record.get("on_timer"))
    payload[22] = _check_range("on_setpoint", int(record.get("on_setpoint", payload[22] or 0x1A)), 0, 63)
    payload[24:26] = set_timer_value(record.get("off_timer"))
    return bytes(payload)


def _raw_record(record: Mapping[str, Any] | None, length: int) -> bytes:
    if not record or "raw" not in record:
        return b"\x00" * length
    raw = record["raw"]
    if isinstance(raw, bytes | bytearray):
        data = bytes(raw)
    elif isinstance(raw, str):
        compact = raw.replace(" ", "").replace(":", "").replace("-", "")
        data = bytes.fromhex(compact)
    else:
        data = bytes(int(item) & 0xFF for item in raw)
    return data[:length].ljust(length, b"\x00")


@dataclass(frozen=True)
class CommandSpec:
    command: int
    payload: bytes


def group_power_command(group: int, on: bool, *, sensor_control: bool = True, value: int = 23) -> CommandSpec:
    return CommandSpec(0x20, set_group_power(group, on, sensor_control=sensor_control, value=value))


def group_percentage_command(group: int, percentage: int) -> CommandSpec:
    return CommandSpec(0x20, set_group_percentage(group, percentage))


def group_setpoint_command(group: int, setpoint: int) -> CommandSpec:
    return CommandSpec(0x20, set_group_setpoint(group, setpoint))


def ac_status_command(ac: int, **kwargs: int | bool | None) -> CommandSpec:
    return CommandSpec(0x22, set_ac_status(ac, **kwargs))


def active_favourite_command(favourite: int) -> CommandSpec:
    return CommandSpec(0x30, set_active_favourite(favourite))


def favourite_command(favourite: int, name: str, groups: list[int] | tuple[int, ...]) -> CommandSpec:
    return CommandSpec(0x32, set_favourite(favourite, name, groups))


def ac_timer_command(ac: int, *, hour: int | None, minute: int | None) -> CommandSpec:
    return CommandSpec(0x36, set_ac_timer(ac, hour=hour, minute=minute))


def ac_timer_table_command(records: Sequence[Mapping[str, Any]], *, ac_count: int = 4) -> CommandSpec:
    return CommandSpec(0x36, set_ac_timer_table(records, ac_count=ac_count))


def group_name_command(group: int, name: str) -> CommandSpec:
    return CommandSpec(0x52, set_group_name(group, name))


def turbo_group_command(
    ac: int,
    group: int,
    current_groups: Sequence[int] | None = None,
    *,
    one_duct_system: bool = False,
    ac_count: int | None = None,
) -> CommandSpec:
    return CommandSpec(0x50, set_turbo_group(ac, group, current_groups, one_duct_system=one_duct_system, ac_count=ac_count))


def preference_command(system_name: str) -> CommandSpec:
    return CommandSpec(0x54, set_preference(system_name))


def preference_full_command(system_name: str, **kwargs: bool | int) -> CommandSpec:
    return CommandSpec(0x54, set_preference_full(system_name, **kwargs))


def ac_base_info_command(records: Sequence[Mapping[str, Any]], **kwargs: bool | int | None) -> CommandSpec:
    return CommandSpec(0x74, set_ac_base_info(records, **kwargs))


def ac_setting_new_command(records: Sequence[Mapping[str, Any]]) -> CommandSpec:
    return CommandSpec(0x78, set_ac_setting_new(records))


def program_define_new_command(records: Sequence[Mapping[str, Any]], **kwargs: bool | int | None) -> CommandSpec:
    return CommandSpec(0x3C, set_program_define_new(records, **kwargs))


def parameters_command(group_count: int, **kwargs: int | bool) -> CommandSpec:
    return CommandSpec(0x60, set_parameters(group_count, **kwargs))


def datetime_command(**kwargs: int) -> CommandSpec:
    return CommandSpec(0x40, set_datetime(**kwargs))


def grouping_command(group: int, *, zone_start: int, zone_count: int, min_percent: int, thermostat: int) -> CommandSpec:
    return CommandSpec(0x66, set_grouping(group, zone_start=zone_start, zone_count=zone_count, min_percent=min_percent, thermostat=thermostat))


def spill_command(ac_spill_types: list[int] | tuple[int, ...], spill_groups: list[int] | tuple[int, ...]) -> CommandSpec:
    return CommandSpec(0x68, set_spill(ac_spill_types, spill_groups))


def service_command(company: str, phone: str, **kwargs: bool | int | bytes) -> CommandSpec:
    return CommandSpec(0x6A, set_service(company, phone, **kwargs))


def balance_start_command(current_values: Sequence[int] | None = None, *, zone: int | None = None, value: int = 0) -> CommandSpec:
    return CommandSpec(0x62, set_balance_values(current_values, zone=zone, value=value))


def balance_stop_command(current_values: Sequence[int] | None = None) -> CommandSpec:
    return CommandSpec(0x64, set_balance_values(current_values))


def password_info_command(page: int, payload: bytes) -> CommandSpec:
    return CommandSpec(0x6C, set_password_info(page, payload))


def pair_sensor_command(pairing: bool) -> CommandSpec:
    return CommandSpec(0x70, set_pair_sensor(pairing))


def sensor_temperature_command(sensor: int, temperature: int) -> CommandSpec:
    return CommandSpec(0x72, set_sensor_temperature(sensor, temperature))


def raw_command(command: int, payload: bytes | bytearray = b"") -> CommandSpec:
    return CommandSpec(_check_range("command", command, 0, 255), raw_payload(payload))
