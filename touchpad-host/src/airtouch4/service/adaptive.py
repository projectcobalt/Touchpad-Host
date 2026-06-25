"""Local weather-adaptive control policy inspired by the AT5 console."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, replace
from typing import Any

from ..session.queue import TransactionSpec
from .commands import CommandRequestError, build_transaction
from .adaptive_airtouch import translate_airtouch_snapshot
from .adaptive_mpc import AdaptiveMpcEngine
from .adaptive_model import AdaptiveDevice


ADAPTIVE_MODES = ("off", "recommend", "auto_off", "adaptive")
ADAPTIVE_LEARNING_MODES = ("off", "control")
_LEGACY_LEARNING_MODES = ("learn",)


@dataclass(frozen=True)
class AdaptiveConfig:
    mode: str = "off"
    cool_diff: int = 4
    cool_comfort_temp: int = 24
    heat_diff: int = 4
    heat_comfort_temp: int = 20
    check_interval: float = 60.0
    command_cooldown: float = 300.0
    learning_mode: str = "off"
    mpc_horizon_hours: int = 6
    compressor_min_run_time: float = 0.0
    compressor_min_off_time: float = 0.0
    compressor_groups: tuple[tuple[int, ...], ...] = ()
    control_zones: tuple[int, ...] = ()


@dataclass(frozen=True)
class ClimateSignal:
    indoor_temperature: float | None = None
    indoor_source: str | None = None
    humidity: float | None = None
    humidity_source: str | None = None


@dataclass(frozen=True)
class WeatherSignal:
    outside_temperature: float | None = None
    forecast_temperatures: tuple[float, ...] = ()
    humidity: float | None = None


@dataclass(frozen=True)
class SolarSignal:
    q_solar: float = 0.0
    source: str = "none"
    irradiance_w_m2: float | None = None
    cloud_cover: float | None = None
    sun_elevation: float | None = None
    error: str | None = None


class AdaptiveController:
    def __init__(self, config: AdaptiveConfig = AdaptiveConfig()) -> None:
        self.config = _validated_config(config)
        self._next_check = 0.0
        self._last_command: dict[str, tuple[int | bool, float]] = {}
        self._adapted_ac: dict[int, dict[str, int]] = {}
        self._adapted_group: dict[int, dict[str, int]] = {}
        self._mpc = AdaptiveMpcEngine()
        self._compressor_groups = self.config.compressor_groups
        self._mpc.compressor.configure(self._compressor_groups)
        self._status: dict[str, Any] = self._empty_status()

    def status(self) -> dict[str, Any]:
        return dict(self._status)

    def update_config(self, values: dict[str, Any]) -> dict[str, Any]:
        data = {field: getattr(self.config, field) for field in self.config.__dataclass_fields__}
        for key in data:
            if key in values and values[key] is not None:
                data[key] = values[key]
        self.config = _validated_config(AdaptiveConfig(**data))
        self._set_compressor_groups(self.config.compressor_groups)
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
            "learning_mode": self.config.learning_mode,
            "learning_control": self.config.learning_mode == "control",
            "mpc_horizon_hours": self.config.mpc_horizon_hours,
            "compressor_min_run_time": self.config.compressor_min_run_time,
            "compressor_min_off_time": self.config.compressor_min_off_time,
            "compressor_groups": [list(group) for group in self.config.compressor_groups],
            "control_zones": list(self.config.control_zones),
        }

    def export_learning(self) -> dict[str, Any]:
        return self._mpc.to_dict()

    def import_learning(self, payload: dict[str, Any]) -> None:
        self._mpc.load_dict(payload)
        self._status = {**self._status, "learning": self._mpc.status(time.monotonic())}

    def manage_learning(self, values: dict[str, Any]) -> dict[str, Any]:
        action = str(values.get("action") or "").lower()
        if action == "reset_all":
            self._mpc.reset_all()
        elif action == "reset_zone":
            self._mpc.reset_zone(_zone_id(values.get("zone")))
        elif action == "accelerate_zone":
            self._mpc.set_accelerated_learning_at(
                _zone_id(values.get("zone")),
                bool(values.get("enabled", True)),
                now=time.monotonic(),
            )
        else:
            raise ValueError("adaptive model action must be reset_all, reset_zone, or accelerate_zone")
        self._status = {**self._status, "learning": self._mpc.status(time.monotonic())}
        return self._status["learning"]

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
        weather = ((integrations.get("weather") or {}).get("state") or {}) if integrations else {}
        indoor = ((integrations.get("indoor") or {}).get("state") or {}) if integrations else {}
        weather_signal = _weather_signal(weather, integrations)
        solar_signal = _solar_signal(weather, integrations)
        state = runtime_snapshot.get("state") or {}
        self._set_compressor_groups(_compressor_groups_from_zone_map(state) or self.config.compressor_groups)
        adaptive_snapshot = translate_airtouch_snapshot(state, control_zones=self.config.control_zones)
        self._mpc.observe(
            adaptive_snapshot,
            now=now,
            outside_temperature=weather_signal.outside_temperature,
            q_solar=solar_signal.q_solar,
        )
        outside = weather_signal.outside_temperature
        status["outside_temperature"] = outside
        status["forecast_temperatures"] = list(weather_signal.forecast_temperatures)
        status["solar"] = {
            "q_solar": solar_signal.q_solar,
            "source": solar_signal.source,
            "irradiance_w_m2": solar_signal.irradiance_w_m2,
            "cloud_cover": solar_signal.cloud_cover,
            "sun_elevation": solar_signal.sun_elevation,
        }
        if solar_signal.error is not None:
            status["errors"].append(f"Solar: {solar_signal.error}")
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
        planned_power_off: set[int] = set()
        for device in adaptive_snapshot.devices:
            ac_id = device.ac_id
            ac = _indexed(state.get("acs") or {}, ac_id) or {}
            if not device.power_on or device.mode not in (1, 4):
                specs.extend(self._restore_ac(state, ac_id, status, now))
                continue
            climate = _climate_for_ac(state, ac_id, ac, indoor, weather_signal)
            status["evaluations"].append({
                "ac": ac_id,
                "name": _ac_name(ac_id, ac),
                "indoor_temperature": climate.indoor_temperature,
                "indoor_source": climate.indoor_source,
                "humidity": climate.humidity,
                "humidity_source": climate.humidity_source,
            })
            if mode in {"recommend", "auto_off"}:
                specs.extend(self._basic_action(state, ac_id, ac, outside, weather_signal, climate, status, now, planned_power_off))
            elif mode == "adaptive":
                specs.extend(self._adaptive_action(state, device, ac, outside, weather_signal, solar_signal, climate, status, now))
        self._status = self._final_status(status)
        return specs

    def _set_compressor_groups(self, groups: tuple[tuple[int, ...], ...]) -> None:
        groups = tuple(tuple(group) for group in groups)
        if groups == self._compressor_groups:
            return
        self._compressor_groups = groups
        self._mpc.compressor.configure(groups)

    def _basic_action(
        self,
        state: dict[str, Any],
        ac_id: int,
        ac: dict[str, Any],
        outside: float,
        weather: WeatherSignal,
        climate: ClimateSignal,
        status: dict[str, Any],
        now: float,
        planned_power_off: set[int],
    ) -> list[TransactionSpec]:
        ac_status = ac.get("status") or {}
        ac_mode = ac_status.get("mode")
        setpoint = _number(ac_status.get("setpoint"))
        if setpoint is None:
            return []
        outside_round = round(outside)
        cooling = ac_mode == 4
        should_stop = (cooling and setpoint > outside_round) or (not cooling and setpoint < outside_round)
        if not should_stop:
            return []
        name = _ac_name(ac_id, ac)
        recommendation = f"{name}: Outside {outside_round}° is favourable versus setpoint {setpoint}°"
        status["recommendations"].append(recommendation)
        if self.config.mode != "auto_off":
            return []
        if not self._mpc.compressor.can_power_off(
            ac_id,
            now,
            self.config.compressor_min_run_time,
            planned_off=planned_power_off,
        ):
            status["recommendations"].append(f"{name}: Auto Off held by compressor minimum run time")
            return []
        if not _indoor_allows_auto_off(climate.indoor_temperature, setpoint, cooling):
            status["recommendations"].append(f"{name}: Auto Off held by indoor temperature")
            return []
        if not _forecast_allows_auto_off(weather.forecast_temperatures, setpoint, cooling):
            status["recommendations"].append(f"{name}: Auto Off held by forecast")
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
        planned_power_off.add(ac_id)
        return [spec]

    def _adaptive_action(
        self,
        state: dict[str, Any],
        device: AdaptiveDevice,
        ac: dict[str, Any],
        outside: float,
        weather: WeatherSignal,
        solar: SolarSignal,
        climate: ClimateSignal,
        status: dict[str, Any],
        now: float,
    ) -> list[TransactionSpec]:
        specs: list[TransactionSpec] = []
        ac_id = device.ac_id
        ac_status = ac.get("status") or {}
        cooling = device.mode == 4
        target = self._target_setpoint(outside, cooling)
        forecast_target = self._forecast_target(target, weather.forecast_temperatures, cooling)
        target = self._humidity_adjusted_target(forecast_target, climate.humidity, cooling)
        target = _clamp_setpoint(target, ac)
        groups = _groups_for_ac(state, ac_id, ac)
        controlled_rooms = tuple(room for room in device.rooms if room.active and room.control_enabled and room.temperature is not None)
        controlled_group_ids = {room.id for room in controlled_rooms}
        proposal = None
        if self.config.learning_mode == "control":
            proposal = self._mpc.propose(
                ac_id=ac_id,
                rooms=controlled_rooms,
                baseline_target=target,
                cooling=cooling,
                horizon_hours=self.config.mpc_horizon_hours,
                outside_temperature=outside,
                outside_forecast=weather.forecast_temperatures,
                humidity=climate.humidity,
                q_solar=solar.q_solar,
            )
            if proposal is not None:
                target = _clamp_setpoint(proposal.target, ac)
        setpoint = _number(ac_status.get("setpoint"))
        name = _ac_name(ac_id, ac)
        status["evaluations"][-1].update({
            "target": target,
            "forecast_target": forecast_target,
            "mpc": None if proposal is None else {
                "target": proposal.target,
                "source": proposal.source,
                "confidence": proposal.confidence,
                "predicted_temperatures": proposal.predicted_temperatures,
                "reason": proposal.reason,
                "action": proposal.action,
                "power_fraction": proposal.power_fraction,
            },
            "solar": {
                "q_solar": solar.q_solar,
                "source": solar.source,
            },
            "relaxation_allowed": _indoor_allows_relax(climate.indoor_temperature, target, cooling),
        })
        if not _indoor_allows_relax(climate.indoor_temperature, target, cooling):
            status["recommendations"].append(f"{name}: Holding setpoint, indoor temperature is outside comfort band")
            specs.extend(self._restore_ac(state, ac_id, status, now))
            return specs
        if setpoint is not None and controlled_rooms and self._needs_relax(setpoint, target, cooling):
            self._adapted_ac.setdefault(ac_id, {"original": int(setpoint), "target": target})
            self._adapted_ac[ac_id]["target"] = target
            spec = self._set_ac_setpoint(state, ac_id, target, status, now)
            if spec is not None:
                specs.append(spec)
                status["actions"].append(f"{name}: Setpoint {target}°")
        else:
            specs.extend(self._restore_ac_setpoint(state, ac_id, status, now))
        for group_id, group in groups:
            group_status = group.get("status") or {}
            if group_id not in controlled_group_ids:
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

    def _forecast_target(self, current_target: int, forecast_temperatures: tuple[float, ...], cooling: bool) -> int:
        if not forecast_temperatures:
            return current_target
        targets = [self._target_setpoint(temperature, cooling) for temperature in forecast_temperatures[:6]]
        if cooling:
            return min([current_target, *targets])
        return max([current_target, *targets])

    def _humidity_adjusted_target(self, target: int, humidity: float | None, cooling: bool) -> int:
        if not cooling or humidity is None:
            return target
        if humidity >= 70:
            return target - 2
        if humidity >= 60:
            return target - 1
        return target

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
            "evaluations": [],
            "forecast_temperatures": [],
            "solar": {"q_solar": 0.0, "source": "none", "irradiance_w_m2": None, "cloud_cover": None, "sun_elevation": None},
            "learning": self._mpc.status(time.monotonic()),
            "active_ac": sorted(self._adapted_ac),
            "active_groups": sorted(self._adapted_group),
        }

    def _final_status(self, status: dict[str, Any]) -> dict[str, Any]:
        status["active_ac"] = sorted(self._adapted_ac)
        status["active_groups"] = sorted(self._adapted_group)
        status["learning"] = self._mpc.status(time.monotonic())
        return status


def _validated_config(config: AdaptiveConfig) -> AdaptiveConfig:
    mode = str(config.mode or "off").lower()
    if mode not in ADAPTIVE_MODES:
        raise ValueError(f"adaptive mode must be one of {', '.join(ADAPTIVE_MODES)}")
    learning_mode = str(config.learning_mode or "off").lower()
    if learning_mode in _LEGACY_LEARNING_MODES:
        learning_mode = "off"
    if learning_mode not in ADAPTIVE_LEARNING_MODES:
        raise ValueError(f"adaptive learning mode must be one of {', '.join(ADAPTIVE_LEARNING_MODES)}")
    return replace(
        config,
        mode=mode,
        learning_mode=learning_mode,
        cool_diff=_int_range("cool_diff", config.cool_diff, 0, 15),
        cool_comfort_temp=_int_range("cool_comfort_temp", config.cool_comfort_temp, 16, 32),
        heat_diff=_int_range("heat_diff", config.heat_diff, 0, 15),
        heat_comfort_temp=_int_range("heat_comfort_temp", config.heat_comfort_temp, 16, 32),
        check_interval=max(5.0, float(config.check_interval)),
        command_cooldown=max(1.0, float(config.command_cooldown)),
        mpc_horizon_hours=_int_range("mpc_horizon_hours", config.mpc_horizon_hours, 1, 24),
        compressor_min_run_time=max(0.0, float(config.compressor_min_run_time)),
        compressor_min_off_time=max(0.0, float(config.compressor_min_off_time)),
        compressor_groups=_validated_compressor_groups(config.compressor_groups),
        control_zones=_validated_control_zones(config.control_zones),
    )


def _int_range(name: str, value: Any, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= number <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return number


def _weather_signal(weather: dict[str, Any], integrations: dict[str, Any]) -> WeatherSignal:
    return WeatherSignal(
        outside_temperature=_weather_temperature_c(weather),
        forecast_temperatures=_forecast_temperatures_c(weather, integrations),
        humidity=_number(weather.get("humidity")),
    )


def _weather_temperature_c(weather: dict[str, Any]) -> float | None:
    value = _number(weather.get("temperature"))
    if value is None:
        return None
    return _temperature_to_c(value, weather.get("temperature_unit") or weather.get("unit_of_measurement") or "C")


def _temperature_to_c(value: float, unit: Any) -> float:
    unit_name = str(unit or "C").upper()
    if "F" in unit_name:
        return (value - 32.0) * 5.0 / 9.0
    return value


def _forecast_temperatures_c(weather: dict[str, Any], integrations: dict[str, Any]) -> tuple[float, ...]:
    sources: list[Any] = [weather.get("forecast")]
    if integrations:
        forecast_state = (integrations.get("forecast") or {}).get("state")
        if isinstance(forecast_state, dict):
            sources.extend([forecast_state.get("forecast"), forecast_state.get("hourly"), forecast_state.get("daily")])
        else:
            sources.append(forecast_state)
    result: list[float] = []
    default_unit = weather.get("temperature_unit") or weather.get("unit_of_measurement") or "C"
    for source in sources:
        if not source:
            continue
        entries = source if isinstance(source, list) else [source]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            value = _number(
                entry.get("temperature")
                if entry.get("temperature") is not None
                else entry.get("native_temperature")
                if entry.get("native_temperature") is not None
                else entry.get("templow")
            )
            if value is None:
                continue
            unit = entry.get("temperature_unit") or entry.get("native_temperature_unit") or default_unit
            result.append(_temperature_to_c(value, unit))
    return tuple(result[:12])


def _solar_signal(weather: dict[str, Any], integrations: dict[str, Any]) -> SolarSignal:
    solar_pipe = (integrations.get("solar") or {}) if integrations else {}
    sun_pipe = (integrations.get("sun") or {}) if integrations else {}
    error = solar_pipe.get("error") if isinstance(solar_pipe, dict) else None
    solar_state = solar_pipe.get("state") if isinstance(solar_pipe, dict) else None
    if not isinstance(solar_state, dict):
        solar_state = {}
    sun_state = sun_pipe.get("state") if isinstance(sun_pipe, dict) else None
    if not isinstance(sun_state, dict):
        sun_state = {}
    sun_elevation = _number(sun_state.get("elevation"))
    irradiance = _number(solar_state.get("irradiance"))
    irradiance_unit = solar_state.get("irradiance_unit") or ""
    if irradiance is not None:
        irradiance_w_m2 = _irradiance_to_w_m2(irradiance, irradiance_unit)
        return SolarSignal(
            q_solar=_clamp_float(irradiance_w_m2 / 1000.0, 0.0, 1.2),
            source="ha_irradiance",
            irradiance_w_m2=round(irradiance_w_m2, 2),
            cloud_cover=_cloud_cover_from_sources(weather, solar_state),
            sun_elevation=None if sun_elevation is None else round(sun_elevation, 2),
            error=str(error) if error else None,
        )
    cloud_cover = _cloud_cover_from_sources(weather, solar_state)
    if cloud_cover is not None and sun_elevation is not None:
        daylight = _clamp_float(math.sin(math.radians(max(0.0, sun_elevation))), 0.0, 1.0)
        cloud_factor = _clamp_float(1.0 - (cloud_cover / 100.0), 0.0, 1.0)
        return SolarSignal(
            q_solar=round(daylight * cloud_factor, 3),
            source="sun_cloud_cover",
            cloud_cover=round(cloud_cover, 2),
            sun_elevation=round(sun_elevation, 2),
            error=str(error) if error else None,
        )
    if cloud_cover is not None:
        return SolarSignal(
            q_solar=0.0,
            source="cloud_cover_diagnostic",
            cloud_cover=round(cloud_cover, 2),
            sun_elevation=None if sun_elevation is None else round(sun_elevation, 2),
            error=str(error) if error else None,
        )
    return SolarSignal(sun_elevation=None if sun_elevation is None else round(sun_elevation, 2), error=str(error) if error else None)


def _cloud_cover_from_sources(weather: dict[str, Any], solar_state: dict[str, Any]) -> float | None:
    for source in (solar_state, weather):
        for key in ("cloud_cover", "cloud_coverage", "clouds", "cloudiness"):
            value = _number(source.get(key))
            if value is not None:
                return _clamp_float(value, 0.0, 100.0)
    return None


def _irradiance_to_w_m2(value: float, unit: Any) -> float:
    unit_text = str(unit or "").lower()
    if "kw" in unit_text:
        return value * 1000.0
    return value


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _climate_for_ac(
    state: dict[str, Any],
    ac_id: int,
    ac: dict[str, Any],
    indoor: dict[str, Any],
    weather: WeatherSignal,
) -> ClimateSignal:
    group_temperatures = _group_temperatures_for_ac(state, ac_id, ac, active_only=True)
    source = "airtouch_active_zones" if group_temperatures else None
    if not group_temperatures:
        group_temperatures = _group_temperatures_for_ac(state, ac_id, ac, active_only=False)
        source = "airtouch_zones" if group_temperatures else None
    indoor_temperature = _average(group_temperatures)
    if indoor_temperature is None:
        indoor_temperature = _number((ac.get("status") or {}).get("sensor_temp"))
        source = "airtouch_ac" if indoor_temperature is not None else None
    if indoor_temperature is None:
        indoor_temperature = _number(indoor.get("temperature"))
        source = "home_assistant_indoor" if indoor_temperature is not None else None
        if indoor_temperature is not None:
            indoor_temperature = _temperature_to_c(indoor_temperature, indoor.get("temperature_unit") or "C")
    humidity = _number(indoor.get("humidity"))
    humidity_source = "home_assistant_indoor" if humidity is not None else None
    if humidity is None:
        humidity = weather.humidity
        humidity_source = "weather" if humidity is not None else None
    return ClimateSignal(
        indoor_temperature=indoor_temperature,
        indoor_source=source,
        humidity=humidity,
        humidity_source=humidity_source,
    )


def _group_temperatures_for_ac(state: dict[str, Any], ac_id: int, ac: dict[str, Any], *, active_only: bool) -> list[float]:
    temperatures: list[float] = []
    for _group_id, group in _groups_for_ac(state, ac_id, ac):
        status = group.get("status") or {}
        if active_only and status.get("power_name") not in {"on", "turbo"}:
            continue
        value = _number(status.get("temperature"))
        if value is not None:
            temperatures.append(value)
    return temperatures


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _indoor_allows_relax(indoor_temperature: float | None, target: int, cooling: bool) -> bool:
    if indoor_temperature is None:
        return True
    if cooling:
        return indoor_temperature <= target + 1.0
    return indoor_temperature >= target - 1.0


def _indoor_allows_auto_off(indoor_temperature: float | None, setpoint: float, cooling: bool) -> bool:
    if indoor_temperature is None:
        return True
    if cooling:
        return indoor_temperature <= setpoint + 0.5
    return indoor_temperature >= setpoint - 0.5


def _forecast_allows_auto_off(forecast_temperatures: tuple[float, ...], setpoint: float, cooling: bool) -> bool:
    if not forecast_temperatures:
        return True
    near_term = forecast_temperatures[:6]
    if cooling:
        return min(near_term) <= setpoint
    return max(near_term) >= setpoint


def _clamp_setpoint(target: int, ac: dict[str, Any]) -> int:
    settings = ac.get("settings") or {}
    minimum = _number(settings.get("min_setpoint"))
    maximum = _number(settings.get("max_setpoint"))
    if minimum is not None:
        target = max(target, int(minimum))
    if maximum is not None:
        target = min(target, int(maximum))
    return target


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


def _compressor_groups_from_zone_map(state: dict[str, Any]) -> tuple[tuple[int, ...], ...]:
    zones_by_ac: dict[int, set[int]] = {}
    for ac_id, ac in _iter_acs(state):
        base = ac.get("base") or {}
        start = base.get("group_start")
        count = base.get("group_count")
        if not isinstance(start, int) or not isinstance(count, int) or count <= 0:
            continue
        zones_by_ac[ac_id] = set(range(start, start + count))
    if len(zones_by_ac) < 2:
        return ()

    parent = {ac_id: ac_id for ac_id in zones_by_ac}

    def find(ac_id: int) -> int:
        while parent[ac_id] != ac_id:
            parent[ac_id] = parent[parent[ac_id]]
            ac_id = parent[ac_id]
        return ac_id

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    entries = sorted(zones_by_ac.items())
    for index, (left_id, left_zones) in enumerate(entries):
        for right_id, right_zones in entries[index + 1:]:
            if left_zones.intersection(right_zones):
                union(left_id, right_id)

    groups: dict[int, list[int]] = {}
    for ac_id in zones_by_ac:
        groups.setdefault(find(ac_id), []).append(ac_id)
    return tuple(tuple(sorted(members)) for members in groups.values() if len(members) >= 2)


def _validated_control_zones(value: Any) -> tuple[int, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        raise ValueError("control_zones must be a list or comma-separated string")
    zones = []
    for item in items:
        try:
            zone = int(item)
        except (TypeError, ValueError) as exc:
            raise ValueError("control_zones must contain integer zone ids") from exc
        if zone < 0:
            raise ValueError("control_zones must contain non-negative zone ids")
        zones.append(zone)
    return tuple(sorted(set(zones)))


def _validated_compressor_groups(value: Any) -> tuple[tuple[int, ...], ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        groups = []
        for group_text in value.split(";"):
            members = [item.strip() for item in group_text.split(",") if item.strip()]
            if members:
                groups.append(members)
    elif isinstance(value, (list, tuple)):
        groups = list(value)
    else:
        raise ValueError("compressor_groups must be a list of lists or semicolon-separated string")
    result: list[tuple[int, ...]] = []
    seen: set[int] = set()
    for group in groups:
        if isinstance(group, str):
            items = [item.strip() for item in group.split(",") if item.strip()]
        elif isinstance(group, (list, tuple, set)):
            items = list(group)
        else:
            raise ValueError("compressor_groups must contain lists of AC ids")
        members = []
        for item in items:
            try:
                ac_id = int(item)
            except (TypeError, ValueError) as exc:
                raise ValueError("compressor_groups must contain integer AC ids") from exc
            if ac_id < 0:
                raise ValueError("compressor_groups must contain non-negative AC ids")
            if ac_id in seen:
                raise ValueError("an AC can only belong to one compressor group")
            members.append(ac_id)
            seen.add(ac_id)
        group_tuple = tuple(sorted(set(members)))
        if len(group_tuple) >= 2:
            result.append(group_tuple)
    return tuple(result)


def _zone_id(value: Any) -> int:
    try:
        zone = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("zone must be an integer") from exc
    if zone < 0:
        raise ValueError("zone must be non-negative")
    return zone


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
