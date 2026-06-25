"""Local weather-adaptive control policy inspired by the AT5 console."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Any

from ..session.queue import TransactionSpec
from .commands import CommandRequestError, build_transaction


ADAPTIVE_MODES = ("off", "recommend", "auto_off", "adaptive")


@dataclass(frozen=True)
class AdaptiveConfig:
    mode: str = "off"
    cool_diff: int = 4
    cool_comfort_temp: int = 24
    heat_diff: int = 4
    heat_comfort_temp: int = 20
    check_interval: float = 60.0
    command_cooldown: float = 300.0


class AdaptiveController:
    def __init__(self, config: AdaptiveConfig = AdaptiveConfig()) -> None:
        self.config = _validated_config(config)
        self._next_check = 0.0
        self._last_command: dict[str, tuple[int | bool, float]] = {}
        self._adapted_ac: dict[int, dict[str, int]] = {}
        self._adapted_group: dict[int, dict[str, int]] = {}
        self._status: dict[str, Any] = self._empty_status()

    def status(self) -> dict[str, Any]:
        return dict(self._status)

    def update_config(self, values: dict[str, Any]) -> dict[str, Any]:
        data = {field: getattr(self.config, field) for field in self.config.__dataclass_fields__}
        for key in data:
            if key in values and values[key] is not None:
                data[key] = values[key]
        self.config = _validated_config(AdaptiveConfig(**data))
        self._next_check = 0.0
        self._status = {**self._status, "config": self.public_config(), "mode": self.config.mode}
        return self.public_config()

    def public_config(self) -> dict[str, Any]:
        return {
            "mode": self.config.mode,
            "cool_diff": self.config.cool_diff,
            "cool_comfort_temp": self.config.cool_comfort_temp,
            "heat_diff": self.config.heat_diff,
            "heat_comfort_temp": self.config.heat_comfort_temp,
            "check_interval": self.config.check_interval,
            "command_cooldown": self.config.command_cooldown,
        }

    def evaluate(self, runtime_snapshot: dict[str, Any] | None, integrations: dict[str, Any], *, now: float | None = None) -> list[TransactionSpec]:
        now = time.monotonic() if now is None else now
        if now < self._next_check:
            return []
        self._next_check = now + max(5.0, self.config.check_interval)
        status = self._empty_status()
        status["config"] = self.public_config()
        if runtime_snapshot is None:
            status["note"] = "Runtime state is not available"
            self._status = self._final_status(status)
            return []
        state = runtime_snapshot.get("state") or {}
        weather = ((integrations.get("weather") or {}).get("state") or {}) if integrations else {}
        outside = _weather_temperature_c(weather)
        status["outside_temperature"] = outside
        if outside is None:
            status["note"] = "Outside temperature is not available"
            specs = self._restore_all(state, status, now) if self.config.mode != "off" else []
            self._status = self._final_status(status)
            return specs
        mode = self.config.mode
        if mode == "off":
            specs = self._restore_all(state, status, now)
            self._status = self._final_status(status)
            return specs
        specs: list[TransactionSpec] = []
        for ac_id, ac in _iter_acs(state):
            ac_status = ac.get("status") or {}
            ac_mode = ac_status.get("mode")
            power_on = ac_status.get("power_on") is True
            if not power_on or ac_mode not in (1, 4):
                specs.extend(self._restore_ac(state, ac_id, status, now))
                continue
            if mode in {"recommend", "auto_off"}:
                specs.extend(self._basic_action(state, ac_id, ac, outside, status, now))
            elif mode == "adaptive":
                specs.extend(self._adaptive_action(state, ac_id, ac, outside, status, now))
        self._status = self._final_status(status)
        return specs

    def _basic_action(self, state: dict[str, Any], ac_id: int, ac: dict[str, Any], outside: float, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        ac_status = ac.get("status") or {}
        ac_mode = ac_status.get("mode")
        setpoint = _number(ac_status.get("setpoint"))
        if setpoint is None:
            return []
        outside_round = round(outside)
        should_stop = (ac_mode == 4 and setpoint > outside_round) or (ac_mode == 1 and setpoint < outside_round)
        if not should_stop:
            return []
        name = _ac_name(ac_id, ac)
        recommendation = f"{name}: Outside {outside_round}° is favourable versus setpoint {setpoint}°"
        status["recommendations"].append(recommendation)
        if self.config.mode != "auto_off":
            return []
        key = f"ac:{ac_id}:power"
        if not self._should_send(key, False, now):
            return []
        try:
            spec = build_transaction("ac_status", {"ac": ac_id, "power_on": False}, state=state)
        except CommandRequestError as exc:
            status["errors"].append(str(exc))
            return []
        status["actions"].append(f"{name}: Auto Off")
        return [spec]

    def _adaptive_action(self, state: dict[str, Any], ac_id: int, ac: dict[str, Any], outside: float, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        specs: list[TransactionSpec] = []
        ac_status = ac.get("status") or {}
        ac_mode = ac_status.get("mode")
        cooling = ac_mode == 4
        target = self._target_setpoint(outside, cooling)
        setpoint = _number(ac_status.get("setpoint"))
        name = _ac_name(ac_id, ac)
        if setpoint is not None and self._needs_relax(setpoint, target, cooling):
            self._adapted_ac.setdefault(ac_id, {"original": int(setpoint), "target": target})
            self._adapted_ac[ac_id]["target"] = target
            spec = self._set_ac_setpoint(state, ac_id, target, status, now)
            if spec is not None:
                specs.append(spec)
                status["actions"].append(f"{name}: Setpoint {target}°")
        else:
            specs.extend(self._restore_ac_setpoint(state, ac_id, status, now))
        for group_id, group in _groups_for_ac(state, ac_id, ac):
            group_status = group.get("status") or {}
            if group_status.get("power_name") not in {"on", "turbo"} or group_status.get("sensor_control") is not True:
                specs.extend(self._restore_group_setpoint(state, group_id, status, now))
                continue
            group_setpoint = _number(group_status.get("setpoint"))
            if group_setpoint is None:
                continue
            if self._needs_relax(group_setpoint, target, cooling):
                self._adapted_group.setdefault(group_id, {"original": int(group_setpoint), "target": target})
                self._adapted_group[group_id]["target"] = target
                spec = self._set_group_setpoint(state, group_id, target, status, now)
                if spec is not None:
                    specs.append(spec)
                    status["actions"].append(f"{_group_name(group_id, group)}: Setpoint {target}°")
            else:
                specs.extend(self._restore_group_setpoint(state, group_id, status, now))
        return specs

    def _target_setpoint(self, outside: float, cooling: bool) -> int:
        outside_round = round(outside)
        if cooling:
            return min(outside_round - self.config.cool_diff, self.config.cool_comfort_temp)
        return max(outside_round + self.config.heat_diff, self.config.heat_comfort_temp)

    @staticmethod
    def _needs_relax(current: float, target: int, cooling: bool) -> bool:
        return current < target if cooling else current > target

    def _restore_all(self, state: dict[str, Any], status: dict[str, Any], now: float) -> list[TransactionSpec]:
        specs: list[TransactionSpec] = []
        for ac_id in list(self._adapted_ac):
            specs.extend(self._restore_ac_setpoint(state, ac_id, status, now))
        for group_id in list(self._adapted_group):
            specs.extend(self._restore_group_setpoint(state, group_id, status, now))
        return specs

    def _restore_ac(self, state: dict[str, Any], ac_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        specs = self._restore_ac_setpoint(state, ac_id, status, now)
        ac = _indexed(state.get("acs") or {}, ac_id) or {}
        for group_id, _group in _groups_for_ac(state, ac_id, ac):
            specs.extend(self._restore_group_setpoint(state, group_id, status, now))
        return specs

    def _restore_ac_setpoint(self, state: dict[str, Any], ac_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        record = self._adapted_ac.get(ac_id)
        ac = _indexed(state.get("acs") or {}, ac_id) or {}
        current = _number((ac.get("status") or {}).get("setpoint")) if isinstance(ac, dict) else None
        if record is None:
            return []
        if current != record["target"]:
            self._adapted_ac.pop(ac_id, None)
            return []
        spec = self._set_ac_setpoint(state, ac_id, record["original"], status, now)
        if spec is None:
            return []
        self._adapted_ac.pop(ac_id, None)
        status["actions"].append(f"{_ac_name(ac_id, ac)}: Restore {record['original']}°")
        return [spec]

    def _restore_group_setpoint(self, state: dict[str, Any], group_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        record = self._adapted_group.get(group_id)
        group = _indexed(state.get("groups") or {}, group_id) or {}
        current = _number((group.get("status") or {}).get("setpoint")) if isinstance(group, dict) else None
        if record is None:
            return []
        if current != record["target"]:
            self._adapted_group.pop(group_id, None)
            return []
        spec = self._set_group_setpoint(state, group_id, record["original"], status, now)
        if spec is None:
            return []
        self._adapted_group.pop(group_id, None)
        status["actions"].append(f"{_group_name(group_id, group)}: Restore {record['original']}°")
        return [spec]

    def _set_ac_setpoint(self, state: dict[str, Any], ac_id: int, setpoint: int, status: dict[str, Any], now: float) -> TransactionSpec | None:
        key = f"ac:{ac_id}:setpoint"
        if not self._should_send(key, setpoint, now):
            return None
        try:
            return build_transaction("ac_status", {"ac": ac_id, "setpoint": setpoint}, state=state)
        except CommandRequestError as exc:
            status["errors"].append(str(exc))
            return None

    def _set_group_setpoint(self, state: dict[str, Any], group_id: int, setpoint: int, status: dict[str, Any], now: float) -> TransactionSpec | None:
        key = f"group:{group_id}:setpoint"
        if not self._should_send(key, setpoint, now):
            return None
        try:
            return build_transaction("group_setpoint", {"group": group_id, "setpoint": setpoint}, state=state)
        except CommandRequestError as exc:
            status["errors"].append(str(exc))
            return None

    def _should_send(self, key: str, value: int | bool, now: float) -> bool:
        last = self._last_command.get(key)
        if last is not None and last[0] == value and now - last[1] < max(1.0, self.config.command_cooldown):
            return False
        self._last_command[key] = (value, now)
        return True

    def _empty_status(self) -> dict[str, Any]:
        return {
            "mode": self.config.mode,
            "config": self.public_config(),
            "outside_temperature": None,
            "recommendations": [],
            "actions": [],
            "errors": [],
            "active_ac": sorted(self._adapted_ac),
            "active_groups": sorted(self._adapted_group),
        }

    def _final_status(self, status: dict[str, Any]) -> dict[str, Any]:
        status["active_ac"] = sorted(self._adapted_ac)
        status["active_groups"] = sorted(self._adapted_group)
        return status


def _validated_config(config: AdaptiveConfig) -> AdaptiveConfig:
    mode = str(config.mode or "off").lower()
    if mode not in ADAPTIVE_MODES:
        raise ValueError(f"adaptive mode must be one of {', '.join(ADAPTIVE_MODES)}")
    return replace(
        config,
        mode=mode,
        cool_diff=_int_range("cool_diff", config.cool_diff, 0, 15),
        cool_comfort_temp=_int_range("cool_comfort_temp", config.cool_comfort_temp, 16, 32),
        heat_diff=_int_range("heat_diff", config.heat_diff, 0, 15),
        heat_comfort_temp=_int_range("heat_comfort_temp", config.heat_comfort_temp, 16, 32),
        check_interval=max(5.0, float(config.check_interval)),
        command_cooldown=max(1.0, float(config.command_cooldown)),
    )


def _int_range(name: str, value: Any, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= number <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return number


def _weather_temperature_c(weather: dict[str, Any]) -> float | None:
    value = _number(weather.get("temperature"))
    if value is None:
        return None
    unit = str(weather.get("temperature_unit") or weather.get("unit_of_measurement") or "C").upper()
    if "F" in unit:
        return (value - 32.0) * 5.0 / 9.0
    return value


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


def _indexed(mapping: Any, key: int) -> Any:
    if not isinstance(mapping, dict):
        return None
    return mapping.get(key) if key in mapping else mapping.get(str(key))


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


def _group_name(group_id: int, group: dict[str, Any]) -> str:
    return str(group.get("name") or f"Zone {group_id + 1}")
