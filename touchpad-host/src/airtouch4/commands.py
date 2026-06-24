"""Payload builders for UI-relevant internal AirTouch commands."""

from __future__ import annotations

from dataclasses import dataclass


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


def set_group_power(group: int, on: bool) -> bytes:
    group = _check_range("group", group, 0, 15)
    power_code = 1 if on else 0
    return bytes(((power_code << 6) | group, 0x00))


def set_group_percentage(group: int, percentage: int) -> bytes:
    group = _check_range("group", group, 0, 15)
    percentage = _check_range("percentage", percentage, 0, 100)
    return bytes(((2 << 6) | group, percentage))


def set_group_setpoint(group: int, setpoint: int) -> bytes:
    group = _check_range("group", group, 0, 15)
    setpoint = _check_range("setpoint", setpoint, 4, 35)
    return bytes(((2 << 6) | group, 0x80 | (setpoint - 4)))


def set_group_turbo(group: int) -> bytes:
    group = _check_range("group", group, 0, 15)
    return bytes(((3 << 6) | group, 0x00))


def set_active_favourite(favourite: int) -> bytes:
    return bytes((_check_range("favourite", favourite, 0, 3),))


def set_ac_status(ac: int, *, power_on: bool | None = None, mode: int | None = None, fan: int | None = None, setpoint: int | None = None) -> bytes:
    ac = _check_range("ac", ac, 0, 3)
    power_bits = 0x00 if power_on is None else 0xC0 if power_on else 0x80
    mode_value = 0x00 if mode is None else _check_range("mode", mode, 0, 15)
    fan_value = 0x00 if fan is None else _check_range("fan", fan, 0, 15)
    setpoint_value = 0x1F if setpoint is None else _check_range("setpoint", setpoint, 4, 35) - 4
    return bytes((power_bits | ac, (mode_value << 4) | fan_value, setpoint_value))


def set_group_name(group: int, name: str) -> bytes:
    group = _check_range("group", group, 0, 15)
    return bytes((group,)) + _ascii_fixed(name, 8)


def set_favourite(favourite: int, name: str, groups: list[int] | tuple[int, ...]) -> bytes:
    favourite = _check_range("favourite", favourite, 0, 3)
    bitmap = _group_bitmap(groups)
    return bytes((favourite,)) + _ascii_fixed(name, 8) + bytes(bitmap)


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


def set_sensor_temperature(sensor: int, encoded_temperature: int) -> bytes:
    sensor = _check_range("sensor", sensor, 0, 255)
    encoded_temperature = _check_range("encoded_temperature", encoded_temperature, 0, 255)
    return bytes((sensor, encoded_temperature))


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


def set_timer(hour: int | None, minute: int | None) -> bytes:
    if hour is None or minute is None:
        return b"\x80\x00"
    return bytes((
        _check_range("hour", hour, 0, 23),
        _check_range("minute", minute, 0, 59),
    ))


def set_ac_timer(ac: int, *, hour: int | None, minute: int | None) -> bytes:
    return bytes((_check_range("ac", ac, 0, 3),)) + set_timer(hour, minute)


def set_password_info(page: int, payload: bytes) -> bytes:
    return bytes((_check_range("page", page, 1, 2),)) + bytes(payload)


def set_service(company: str, phone: str, tail: bytes = b"") -> bytes:
    return _ascii_fixed(company, 10) + _ascii_fixed(phone, 12) + bytes(tail)


def clear_notification(notification: int = 0) -> bytes:
    return bytes((_check_range("notification", notification, 0, 255),))


def start_balance() -> bytes:
    return b""


def stop_balance() -> bytes:
    return b""


def raw_payload(payload: bytes | bytearray) -> bytes:
    return bytes(payload)


def _group_bitmap(groups: list[int] | tuple[int, ...]) -> tuple[int, int]:
    bitmap = [0, 0]
    for group in groups:
        group = _check_range("group", group, 0, 15)
        bitmap[group // 8] |= 1 << (group % 8)
    return bitmap[0], bitmap[1]


@dataclass(frozen=True)
class CommandSpec:
    command: int
    payload: bytes


def group_power_command(group: int, on: bool) -> CommandSpec:
    return CommandSpec(0x20, set_group_power(group, on))


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


def group_name_command(group: int, name: str) -> CommandSpec:
    return CommandSpec(0x52, set_group_name(group, name))


def preference_command(system_name: str) -> CommandSpec:
    return CommandSpec(0x54, set_preference(system_name))


def datetime_command(**kwargs: int) -> CommandSpec:
    return CommandSpec(0x40, set_datetime(**kwargs))


def grouping_command(group: int, *, zone_start: int, zone_count: int, min_percent: int, thermostat: int) -> CommandSpec:
    return CommandSpec(0x66, set_grouping(group, zone_start=zone_start, zone_count=zone_count, min_percent=min_percent, thermostat=thermostat))


def spill_command(ac_spill_types: list[int] | tuple[int, ...], spill_groups: list[int] | tuple[int, ...]) -> CommandSpec:
    return CommandSpec(0x68, set_spill(ac_spill_types, spill_groups))


def service_command(company: str, phone: str, tail: bytes = b"") -> CommandSpec:
    return CommandSpec(0x6A, set_service(company, phone, tail))


def password_info_command(page: int, payload: bytes) -> CommandSpec:
    return CommandSpec(0x6C, set_password_info(page, payload))


def pair_sensor_command(pairing: bool) -> CommandSpec:
    return CommandSpec(0x70, set_pair_sensor(pairing))


def sensor_temperature_command(sensor: int, encoded_temperature: int) -> CommandSpec:
    return CommandSpec(0x72, set_sensor_temperature(sensor, encoded_temperature))


def raw_command(command: int, payload: bytes | bytearray = b"") -> CommandSpec:
    return CommandSpec(_check_range("command", command, 0, 255), raw_payload(payload))
