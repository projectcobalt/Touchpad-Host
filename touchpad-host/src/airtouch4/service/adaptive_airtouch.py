"""AirTouch runtime snapshot translator for the adaptive core."""

from __future__ import annotations

from typing import Any

from .adaptive_model import AdaptiveDevice, AdaptiveRoom, AdaptiveSnapshot


def translate_airtouch_snapshot(state: dict[str, Any], *, control_zones: tuple[int, ...] = ()) -> AdaptiveSnapshot:
    devices: list[AdaptiveDevice] = []
    control_zone_set = set(control_zones)
    for ac_id, ac in _iter_acs(state):
        status = ac.get("status") or {}
        settings = ac.get("settings") or {}
        rooms = tuple(
            _room_from_group(group_id, group, ac_id=ac_id, control_zone_set=control_zone_set)
            for group_id, group in _groups_for_ac(state, ac_id, ac)
        )
        rooms = _with_power_fractions(rooms)
        devices.append(
            AdaptiveDevice(
                ac_id=ac_id,
                name=_ac_name(ac_id, ac),
                mode=status.get("mode") if isinstance(status.get("mode"), int) else None,
                power_on=status.get("power_on") is True,
                setpoint=_number(status.get("setpoint")),
                min_setpoint=_number(settings.get("min_setpoint")),
                max_setpoint=_number(settings.get("max_setpoint")),
                rooms=rooms,
            )
        )
    return AdaptiveSnapshot(devices=tuple(devices))


def _room_from_group(
    group_id: int,
    group: dict[str, Any],
    *,
    ac_id: int,
    control_zone_set: set[int],
) -> AdaptiveRoom:
    status = group.get("status") or {}
    temperature = _number(status.get("temperature"))
    return AdaptiveRoom(
        id=group_id,
        name=str(group.get("name") or f"Zone {group_id + 1}"),
        ac_id=ac_id,
        temperature=temperature,
        setpoint=_number(status.get("setpoint")),
        active=status.get("power_name") in {"on", "turbo"},
        learn=_room_learning_enabled(status, temperature),
        control_enabled=group_id in control_zone_set,
        power_fraction=_group_weight(status) or 0.0,
    )


def _room_learning_enabled(status: dict[str, Any], temperature: float | None) -> bool:
    if status.get("has_sensor") is True:
        return True
    if status.get("temperature_enabled") is True or status.get("temp_enabled") is True:
        return True
    return temperature is not None


def _with_power_fractions(rooms: tuple[AdaptiveRoom, ...]) -> tuple[AdaptiveRoom, ...]:
    active_rooms = [room for room in rooms if room.active]
    if not active_rooms:
        return rooms
    weights = {room.id: _damper_weight(room) for room in active_rooms}
    if all(weight is None for weight in weights.values()):
        share = 1.0 / len(active_rooms)
        return tuple(_replace_room_fraction(room, share if room.active else 0.0) for room in rooms)
    normalized_weights = {room_id: weight if weight is not None else 1.0 for room_id, weight in weights.items()}
    total = sum(max(0.0, weight) for weight in normalized_weights.values())
    if total <= 0.0:
        share = 1.0 / len(active_rooms)
        return tuple(_replace_room_fraction(room, share if room.active else 0.0) for room in rooms)
    return tuple(
        _replace_room_fraction(room, max(0.0, normalized_weights.get(room.id, 0.0)) / total if room.active else 0.0)
        for room in rooms
    )


def _replace_room_fraction(room: AdaptiveRoom, power_fraction: float) -> AdaptiveRoom:
    return AdaptiveRoom(
        id=room.id,
        name=room.name,
        ac_id=room.ac_id,
        temperature=room.temperature,
        setpoint=room.setpoint,
        active=room.active,
        learn=room.learn,
        control_enabled=room.control_enabled,
        power_fraction=round(power_fraction, 4),
    )


def _damper_weight(room: AdaptiveRoom) -> float | None:
    return room.power_fraction if room.power_fraction > 0.0 else None


def _group_weight(status: dict[str, Any]) -> float | None:
    for key in ("percentage", "damper_percentage", "open_percentage", "opening", "damper", "percent"):
        value = _number(status.get(key))
        if value is not None:
            return max(0.0, value)
    return None


def _iter_acs(state: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    result = []
    for key, value in (state.get("acs") or {}).items():
        try:
            ac_id = int(key)
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict):
            result.append((ac_id, value))
    return sorted(result)


def _groups_for_ac(state: dict[str, Any], ac_id: int, ac: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    base = ac.get("base") or {}
    groups = state.get("active_groups") or state.get("groups") or {}
    start = base.get("group_start")
    count = base.get("group_count")
    result = []
    for key, value in groups.items():
        try:
            group_id = int(key)
        except (TypeError, ValueError):
            continue
        if not isinstance(value, dict):
            continue
        if isinstance(start, int) and isinstance(count, int) and not (start <= group_id < start + count):
            continue
        result.append((group_id, value))
    return sorted(result)


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _ac_name(ac_id: int, ac: dict[str, Any]) -> str:
    base = ac.get("base") or {}
    return str(base.get("name") or f"AC {ac_id + 1}")
