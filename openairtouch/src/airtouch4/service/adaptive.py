"""Local weather-adaptive control policy inspired by the AT5 console."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone, tzinfo
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..session.queue import TransactionSpec
from .commands import CommandRequestError, build_transaction
from .adaptive_airtouch import translate_airtouch_snapshot
from .adaptive_mpc import AdaptiveMpcEngine, MpcInputs
from .adaptive_model import AdaptiveDevice


ADAPTIVE_MODES = ("off", "recommend", "adaptive")
ADAPTIVE_LEARNING_MODES = ("off", "control")
ADAPTIVE_CONTROL_STRATEGIES = ("weather", "zone", "hybrid")
TOUCHPAD_2_SENSOR = 0x91
TELEMETRY_ACTIVE_POWER_W = 300.0
TELEMETRY_IDLE_POWER_W = 120.0
TELEMETRY_ACTIVE_FREQUENCY_HZ = 1.0
TELEMETRY_ACTIVE_SUPPLY_RETURN_DELTA_C = 3.0
TELEMETRY_IDLE_SUPPLY_RETURN_DELTA_C = 1.0


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
    outside_air_zones: tuple[int, ...] = ()
    control_strategy: str = "weather"
    dry_humidity_threshold: int = 70
    co2_ventilation_threshold_ppm: int = 1000
    mpc_comfort_weight: int = 70
    hybrid_min_damper_percent: int = 10
    hybrid_max_damper_percent: int = 100
    hybrid_idle_damper_percent: int = 10


@dataclass(frozen=True)
class ClimateSignal:
    indoor_temperature: float | None = None
    indoor_source: str | None = None
    humidity: float | None = None
    humidity_source: str | None = None
    co2_ppm: float | None = None
    co2_source: str | None = None


@dataclass(frozen=True)
class WeatherSignal:
    outside_temperature: float | None = None
    forecast_temperatures: tuple[float, ...] = ()
    forecast_control_temperatures: tuple[float, ...] = ()
    forecast_step_minutes: float = 60.0
    forecast_quality: dict[str, Any] | None = None
    humidity: float | None = None


@dataclass(frozen=True)
class SolarSignal:
    q_solar: float = 0.0
    source: str = "none"
    irradiance_w_m2: float | None = None
    cloud_cover: float | None = None
    sun_elevation: float | None = None
    error: str | None = None


@dataclass(frozen=True)
class AcTelemetrySignal:
    available: bool = False
    observed_conditioning: bool | None = None
    source: str = "none"
    confidence: float = 0.0
    power_w: float | None = None
    running: bool | None = None
    frequency_hz: float | None = None
    return_air_temperature_c: float | None = None
    supply_air_temperature_c: float | None = None
    supply_return_delta_c: float | None = None
    evidence: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class AcModeIntent:
    mode: int | None
    name: str
    reason: str
    source: str
    current_mode: int | None = None
    outside_air_intent: bool = False
    ventilation_reason: str | None = None


class AdaptiveController:
    def __init__(self, config: AdaptiveConfig = AdaptiveConfig()) -> None:
        self.config = _validated_config(config)
        self._next_check = 0.0
        self._last_command: dict[str, tuple[int | bool, float]] = {}
        self._restore_records: dict[str, dict[str, Any]] = {}
        self._weather_suspensions: dict[str, dict[str, Any]] = {}
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
        if "control_strategy" in values and "learning_mode" not in values:
            data["learning_mode"] = "control" if _strategy_uses_mpc(str(data["control_strategy"]).lower()) else "off"
        self.config = _validated_config(AdaptiveConfig(**data))
        self._set_compressor_groups(self.config.compressor_groups)
        if self.config.mode != "adaptive" or self.config.control_strategy != "weather":
            self._weather_suspensions.clear()
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
            "outside_air_zones": list(self.config.outside_air_zones),
            "control_strategy": self.config.control_strategy,
            "dry_humidity_threshold": self.config.dry_humidity_threshold,
            "co2_ventilation_threshold_ppm": self.config.co2_ventilation_threshold_ppm,
            "mpc_comfort_weight": self.config.mpc_comfort_weight,
            "hybrid_min_damper_percent": self.config.hybrid_min_damper_percent,
            "hybrid_max_damper_percent": self.config.hybrid_max_damper_percent,
            "hybrid_idle_damper_percent": self.config.hybrid_idle_damper_percent,
        }

    def export_learning(self) -> dict[str, Any]:
        return {
            **self._mpc.to_dict(),
            "restore_state": self.export_restore_state(),
            "weather_state": self.export_weather_state(),
        }

    def import_learning(self, payload: dict[str, Any]) -> None:
        self._mpc.load_dict(payload)
        self.import_restore_state(payload.get("restore_state") if isinstance(payload, dict) else None)
        self.import_weather_state(payload.get("weather_state") if isinstance(payload, dict) else None)
        self._status = {**self._status, "learning": self._mpc.status(time.monotonic())}

    def export_restore_state(self) -> dict[str, Any]:
        return {"records": dict(self._restore_records)}

    def import_restore_state(self, payload: Any) -> None:
        records = payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(records, dict):
            return
        self._restore_records = {
            str(key): dict(value)
            for key, value in records.items()
            if isinstance(value, dict) and isinstance(value.get("action"), str)
        }

    def export_weather_state(self) -> dict[str, Any]:
        return {"suspensions": dict(self._weather_suspensions)}

    def import_weather_state(self, payload: Any) -> None:
        suspensions = payload.get("suspensions") if isinstance(payload, dict) else None
        if not isinstance(suspensions, dict):
            return
        self._weather_suspensions = {
            str(key): dict(value)
            for key, value in suspensions.items()
            if isinstance(value, dict) and value.get("phase") == "weather_off"
        }

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
        status = self._empty_status()
        status["config"] = self.public_config()
        if runtime_snapshot is None:
            status["note"] = "Runtime state is not available"
            self._status = self._final_status(status)
            return []
        runtime_control = _runtime_control_status(runtime_snapshot)
        status["runtime_control"] = runtime_control
        if not runtime_control["connected"]:
            status["note"] = runtime_control["reason"]
            self._status = self._final_status(status)
            return []
        if now < self._next_check:
            return []
        self._next_check = now + max(5.0, self.config.check_interval)
        weather = ((integrations.get("weather") or {}).get("state") or {}) if integrations else {}
        indoor = ((integrations.get("indoor") or {}).get("state") or {}) if integrations else {}
        weather_signal = _weather_signal(weather, integrations, horizon_hours=self.config.mpc_horizon_hours)
        solar_signal = _solar_signal(weather, integrations)
        telemetry_signal = _ac_telemetry_signal(integrations)
        state = runtime_snapshot.get("state") or {}
        self._set_compressor_groups(_compressor_groups_from_zone_map(state) or self.config.compressor_groups)
        mode = self.config.mode
        adaptive_snapshot = translate_airtouch_snapshot(
            state,
            control_zones=self.config.control_zones,
            control_active=mode == "adaptive",
        )
        self._mpc.observe(
            adaptive_snapshot,
            now=now,
            outside_temperature=weather_signal.outside_temperature,
            q_solar=solar_signal.q_solar,
        )
        outside = weather_signal.outside_temperature
        status["outside_temperature"] = outside
        status["forecast_temperatures"] = list(weather_signal.forecast_temperatures)
        status["forecast_quality"] = weather_signal.forecast_quality or {}
        status["solar"] = {
            "q_solar": solar_signal.q_solar,
            "source": solar_signal.source,
            "irradiance_w_m2": solar_signal.irradiance_w_m2,
            "cloud_cover": solar_signal.cloud_cover,
            "sun_elevation": solar_signal.sun_elevation,
        }
        if solar_signal.error is not None:
            status["errors"].append(f"Solar: {solar_signal.error}")
        status["ac_telemetry"] = _ac_telemetry_status(telemetry_signal)
        if telemetry_signal.error is not None:
            status["errors"].append(f"AC telemetry: {telemetry_signal.error}")
        if outside is None:
            status["note"] = "Outside temperature is not available"
            specs = self._restore_all(state, status, now) if self.config.mode != "off" else []
            self._status = self._final_status(status)
            return specs
        if mode == "off":
            specs = self._restore_all(state, status, now)
            self._status = self._final_status(status)
            return specs
        specs: list[TransactionSpec] = []
        planned_power_off: set[int] = set()
        for device in adaptive_snapshot.devices:
            ac_id = device.ac_id
            ac = _indexed(state.get("acs") or {}, ac_id) or {}
            has_weather_suspension = self.config.control_strategy == "weather" and self._weather_suspension(ac_id) is not None
            if not device.power_on or device.mode is None:
                if mode == "adaptive" and has_weather_suspension:
                    climate = _climate_for_ac(state, ac_id, ac, indoor, weather_signal)
                    mode_intent = self._mode_intent(device, ac, climate)
                    status["evaluations"].append({
                        "ac": ac_id,
                        "name": _ac_name(ac_id, ac),
                        "indoor_temperature": climate.indoor_temperature,
                        "indoor_source": climate.indoor_source,
                        "humidity": climate.humidity,
                        "humidity_source": climate.humidity_source,
                        "co2_ppm": climate.co2_ppm,
                        "co2_source": climate.co2_source,
                        "mode_intent": _mode_intent_status(mode_intent),
                    })
                    specs.extend(self._weather_action(state, ac_id, ac, outside, weather_signal, climate, mode_intent, status, now, planned_power_off))
                else:
                    specs.extend(self._restore_ac(state, ac_id, status, now))
                continue
            climate = _climate_for_ac(state, ac_id, ac, indoor, weather_signal)
            mode_intent = self._mode_intent(device, ac, climate)
            status["evaluations"].append({
                "ac": ac_id,
                "name": _ac_name(ac_id, ac),
                "indoor_temperature": climate.indoor_temperature,
                "indoor_source": climate.indoor_source,
                "humidity": climate.humidity,
                "humidity_source": climate.humidity_source,
                "co2_ppm": climate.co2_ppm,
                "co2_source": climate.co2_source,
                "mode_intent": _mode_intent_status(mode_intent),
            })
            if mode == "recommend":
                self._recommend_action(device, ac, outside, weather_signal, solar_signal, telemetry_signal, climate, mode_intent, status)
            elif mode == "adaptive":
                if self.config.control_strategy == "weather":
                    specs.extend(self._weather_action(state, ac_id, ac, outside, weather_signal, climate, mode_intent, status, now, planned_power_off))
                elif self.config.control_strategy == "hybrid":
                    specs.extend(self._hybrid_damper_action(state, device, ac, outside, weather_signal, solar_signal, telemetry_signal, climate, mode_intent, status, now))
                else:
                    specs.extend(self._adaptive_action(state, device, ac, outside, weather_signal, solar_signal, telemetry_signal, climate, mode_intent, status, now))
        self._status = self._final_status(status)
        return specs

    def _set_compressor_groups(self, groups: tuple[tuple[int, ...], ...]) -> None:
        groups = tuple(tuple(group) for group in groups)
        if groups == self._compressor_groups:
            return
        self._compressor_groups = groups
        self._mpc.compressor.configure(groups)

    def _recommend_action(
        self,
        device: AdaptiveDevice,
        ac: dict[str, Any],
        outside: float,
        weather: WeatherSignal,
        solar: SolarSignal,
        telemetry: AcTelemetrySignal,
        climate: ClimateSignal,
        mode_intent: AcModeIntent,
        status: dict[str, Any],
    ) -> None:
        ac_status = ac.get("status") or {}
        setpoint = _number(ac_status.get("setpoint"))
        cooling = mode_intent.mode != 1
        opportunity_cooling = _cooling_for_mode(mode_intent.current_mode, default=cooling)
        opportunity = _weather_opportunity(outside, setpoint, opportunity_cooling, weather, climate)
        target: int | None = None
        forecast_target: int | None = None
        proposal = None
        if _strategy_uses_mpc(self.config.control_strategy) and mode_intent.mode in (1, 4):
            target = self._control_target(device, ac, outside, weather, climate, cooling)
            proposal = self._mpc_proposal(device, target, cooling, outside, weather, solar, telemetry, climate, advisory=True)
        hybrid_status = None
        if self.config.control_strategy == "hybrid" and target is not None:
            controlled_rooms = tuple(room for room in device.rooms if room.active and room.configured_control and room.temperature is not None)
            hybrid_status = self._hybrid_shadow_status(controlled_rooms, target, cooling, proposal)
        status["evaluations"][-1].update({
            "target": target,
            "forecast_target": forecast_target,
            "weather_opportunity": opportunity,
            "weather_intent": self._weather_intent_status(device.ac_id, opportunity, None, {}, opportunity_cooling),
            "mode_intent": _mode_intent_status(mode_intent),
            "air_quality": self._air_quality_status(device, climate, mode_intent),
            "outside_air": self._outside_air_status(mode_intent),
            "mpc": _proposal_status(proposal),
            "hybrid": hybrid_status,
            "solar": {
                "q_solar": solar.q_solar,
                "source": solar.source,
            },
            "relaxation_allowed": opportunity["indoor_comfort_allows"] if target is None else _indoor_allows_relax(climate.indoor_temperature, target, cooling),
        })
        name = _ac_name(device.ac_id, ac)
        _append_weather_recommendations(name, opportunity, status)
        if proposal is not None:
            if proposal.source in {"mpc", "zone"}:
                status["recommendations"].append(
                    f"{name}: Recommended Target: {proposal.target} C "
                    f"(Confidence {round(proposal.confidence * 100)}%, Action {_title_text(proposal.action)})"
                )
                if hybrid_status is not None and hybrid_status["damper_percentages"]:
                    damper_text = ", ".join(
                        f"Zone {int(group_id) + 1} {percent}%"
                        for group_id, percent in sorted(hybrid_status["damper_percentages"].items(), key=lambda item: int(item[0]))
                    )
                    status["recommendations"].append(f"{name}: Damper Plan: {damper_text}")
            elif proposal.source == "learning":
                status["recommendations"].append(f"{name}: Model Learning: Waiting For Selected Control Zones")

    def _air_quality_status(self, device: AdaptiveDevice, climate: ClimateSignal, mode_intent: AcModeIntent) -> dict[str, Any]:
        humidity_high = (
            climate.humidity is not None
            and climate.humidity_source == "home_assistant_indoor"
            and climate.humidity >= self.config.dry_humidity_threshold
        )
        co2_high = climate.co2_ppm is not None and climate.co2_ppm >= self.config.co2_ventilation_threshold_ppm
        thermal_mode = mode_intent.mode in (1, 4)
        active_zone_ids = [
            int(room.id)
            for room in device.rooms
            if room.active and (room.control_enabled or room.configured_control)
        ]
        return {
            "humidity_high": humidity_high,
            "humidity": climate.humidity,
            "humidity_threshold": self.config.dry_humidity_threshold,
            "co2_high": co2_high,
            "co2_ppm": climate.co2_ppm,
            "co2_threshold_ppm": self.config.co2_ventilation_threshold_ppm,
            "thermal_mode_preferred": thermal_mode and (humidity_high or co2_high),
            "dry_recommended": mode_intent.mode == 2,
            "dry_held_reason": "thermal_demand_active" if thermal_mode and humidity_high else None,
            "fan_recommended": mode_intent.mode == 3 and mode_intent.outside_air_intent,
            "fan_held_reason": "thermal_demand_active" if thermal_mode and co2_high else None,
            "dry_zone_ids": active_zone_ids if mode_intent.mode == 2 else [],
            "outside_air_zone_ids": list(self.config.outside_air_zones) if co2_high else [],
        }

    def _weather_action(
        self,
        state: dict[str, Any],
        ac_id: int,
        ac: dict[str, Any],
        outside: float,
        weather: WeatherSignal,
        climate: ClimateSignal,
        mode_intent: AcModeIntent,
        status: dict[str, Any],
        now: float,
        planned_power_off: set[int],
    ) -> list[TransactionSpec]:
        ac_status = ac.get("status") or {}
        setpoint = _number(ac_status.get("setpoint"))
        if setpoint is None:
            return []
        cooling = _cooling_for_mode(mode_intent.current_mode, default=mode_intent.mode != 1)
        opportunity = _weather_opportunity(outside, setpoint, cooling, weather, climate)
        suspension = self._weather_suspension(ac_id)
        should_stop = opportunity["outside_favourable"]
        status["evaluations"][-1].update({
            "target": None,
            "forecast_target": None,
            "weather_opportunity": opportunity,
            "weather_intent": self._weather_intent_status(ac_id, opportunity, suspension, state, cooling),
            "mode_intent": _mode_intent_status(mode_intent),
            "mpc": None,
            "hybrid": None,
            "relaxation_allowed": opportunity["indoor_comfort_allows"],
        })
        name = _ac_name(ac_id, ac)
        if suspension is not None:
            if ac_status.get("power_on") is True:
                self._clear_weather_suspension(ac_id)
                status["recommendations"].append(f"{name}: Weather Resume Cancelled: AC Power Changed Externally")
                status["evaluations"][-1]["weather_intent"] = self._weather_intent_status(
                    ac_id,
                    opportunity,
                    None,
                    state,
                    cooling,
                    cancelled_reason="ac_power_changed_externally",
                )
                return []
            if not _has_active_zone_for_ac(state, ac_id, ac):
                self._clear_weather_suspension(ac_id)
                status["recommendations"].append(f"{name}: Weather Resume Cancelled: No Zones Are On")
                status["evaluations"][-1]["weather_intent"] = self._weather_intent_status(
                    ac_id,
                    opportunity,
                    None,
                    state,
                    cooling,
                    cancelled_reason="no_active_zones",
                )
                return []
            if opportunity["recommend_off"]:
                _append_weather_recommendations(name, opportunity, status)
                status["recommendations"].append(f"{name}: AC Paused: Outside Air Can Carry The Load")
                return []
            if not self._mpc.compressor.can_power_on(ac_id, now, self.config.compressor_min_off_time):
                status["recommendations"].append(f"{name}: Weather Resume Held By Compressor Minimum Off Time")
                return []
            spec = self._send_ac_power(state, ac_id, True, status, now, key_prefix="weather_resume")
            if spec is None:
                return []
            self._clear_weather_suspension(ac_id)
            status["actions"].append(f"{name}: AC Resumed")
            status["evaluations"][-1]["weather_intent"] = self._weather_intent_status(
                ac_id,
                opportunity,
                None,
                state,
                cooling,
                resumed=True,
            )
            return [spec]
        if not should_stop:
            return []
        _append_weather_recommendations(name, opportunity, status)
        if self.config.mode != "adaptive":
            return []
        if not self._mpc.compressor.can_power_off(
            ac_id,
            now,
            self.config.compressor_min_run_time,
            planned_off=planned_power_off,
        ):
            status["recommendations"].append(f"{name}: Weather Off Held By Compressor Minimum Run Time")
            return []
        if not opportunity["indoor_comfort_allows"]:
            status["recommendations"].append(f"{name}: Weather Off Held By Indoor Temperature")
            return []
        if not opportunity["forecast_favourable"]:
            status["recommendations"].append(f"{name}: Weather Off Held By Forecast")
            return []
        spec = self._send_ac_power(state, ac_id, False, status, now, key_prefix="weather_suspend")
        if spec is None:
            return []
        self._record_weather_suspension(ac_id, opportunity, now, cooling)
        status["actions"].append(f"{name}: Turned AC Off")
        status["evaluations"][-1]["weather_intent"] = self._weather_intent_status(
            ac_id,
            opportunity,
            self._weather_suspension(ac_id),
            state,
            cooling,
        )
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
        telemetry: AcTelemetrySignal,
        climate: ClimateSignal,
        mode_intent: AcModeIntent,
        status: dict[str, Any],
        now: float,
    ) -> list[TransactionSpec]:
        specs: list[TransactionSpec] = []
        ac_id = device.ac_id
        ac_status = ac.get("status") or {}
        cooling = mode_intent.mode != 1
        forecast_target = None
        target = self._control_target(device, ac, outside, weather, climate, cooling)
        groups = _groups_for_ac(state, ac_id, ac)
        controlled_rooms = tuple(room for room in device.rooms if room.active and room.control_enabled and room.temperature is not None)
        controlled_group_ids = {room.id for room in controlled_rooms}
        proposal = self._mpc_proposal(device, target, cooling, outside, weather, solar, telemetry, climate) if mode_intent.mode in (1, 4) else None
        if proposal is not None:
            target = _clamp_setpoint(proposal.target, ac)
        setpoint = _number(ac_status.get("setpoint"))
        name = _ac_name(ac_id, ac)
        status["evaluations"][-1].update({
            "target": target,
            "forecast_target": forecast_target,
            "mode_intent": _mode_intent_status(mode_intent),
            "air_quality": self._air_quality_status(device, climate, mode_intent),
            "outside_air": self._outside_air_status(mode_intent),
            "mpc": _proposal_status(proposal),
            "solar": {
                "q_solar": solar.q_solar,
                "source": solar.source,
            },
            "relaxation_allowed": _indoor_allows_relax(climate.indoor_temperature, target, cooling),
        })
        outside_air_specs = self._outside_air_action(state, ac_id, status, now, mode_intent)
        if not controlled_rooms:
            if not mode_intent.outside_air_intent:
                specs.extend(self._restore_ac(state, ac_id, status, now))
                specs.extend(outside_air_specs)
                return specs
            mode_spec = self._set_ac_mode(state, ac_id, mode_intent, status, now)
            if mode_spec is not None:
                specs.append(mode_spec)
                status["actions"].append(f"{name}: Mode Changed: {mode_intent.name}")
            specs.extend(self._restore_ac_setpoint(state, ac_id, status, now))
            specs.extend(outside_air_specs)
            return specs
        mode_spec = self._set_ac_mode(state, ac_id, mode_intent, status, now)
        if mode_spec is not None:
            specs.append(mode_spec)
            status["actions"].append(f"{name}: Mode Changed: {mode_intent.name}")
        if mode_intent.mode not in (1, 4):
            specs.extend(self._restore_ac_setpoint(state, ac_id, status, now))
            specs.extend(outside_air_specs)
            return specs
        specs.extend(outside_air_specs)
        if setpoint is not None and controlled_rooms and int(round(setpoint)) != target:
            spec = self._set_ac_setpoint(state, ac_id, target, status, now)
            if spec is not None:
                specs.append(spec)
                status["actions"].append(f"{name}: Setpoint Changed: {target} C")
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
            if int(round(group_setpoint)) != target:
                spec = self._set_group_setpoint(state, group_id, target, status, now)
                if spec is not None:
                    specs.append(spec)
                    status["actions"].append(f"{_group_name(group_id, group)}: Setpoint Changed: {target} C")
            else:
                specs.extend(self._restore_group_setpoint(state, group_id, status, now))
        return specs

    def _hybrid_damper_action(
        self,
        state: dict[str, Any],
        device: AdaptiveDevice,
        ac: dict[str, Any],
        outside: float,
        weather: WeatherSignal,
        solar: SolarSignal,
        telemetry: AcTelemetrySignal,
        climate: ClimateSignal,
        mode_intent: AcModeIntent,
        status: dict[str, Any],
        now: float,
    ) -> list[TransactionSpec]:
        specs: list[TransactionSpec] = []
        ac_id = device.ac_id
        ac_status = ac.get("status") or {}
        cooling = mode_intent.mode != 1
        forecast_target = None
        target = self._control_target(device, ac, outside, weather, climate, cooling)
        proposal = self._mpc_proposal(device, target, cooling, outside, weather, solar, telemetry, climate) if mode_intent.mode in (1, 4) else None
        if proposal is not None:
            target = _clamp_setpoint(proposal.target, ac)
        name = _ac_name(ac_id, ac)
        controlled_rooms = tuple(room for room in device.rooms if room.active and room.control_enabled and room.temperature is not None)
        controlled_group_ids = {room.id for room in controlled_rooms}
        control_temperature = _hybrid_control_temperature(controlled_rooms, target, cooling, proposal.power_fraction if proposal else 0.0)
        status["evaluations"][-1].update({
            "target": target,
            "forecast_target": forecast_target,
            "mode_intent": _mode_intent_status(mode_intent),
            "air_quality": self._air_quality_status(device, climate, mode_intent),
            "outside_air": self._outside_air_status(mode_intent),
            "mpc": _proposal_status(proposal),
            "hybrid": {
                "strategy": "hybrid",
                "control_temperature": control_temperature,
                "control_temperature_source": "synthetic_weighted_zone_demand" if control_temperature is not None else None,
                "damper_percentages": {},
                "touchpad_temperature_commanded": False,
                "touchpad_temperature_note": None,
            },
            "solar": {
                "q_solar": solar.q_solar,
                "source": solar.source,
            },
            "relaxation_allowed": _indoor_allows_relax(climate.indoor_temperature, target, cooling),
        })
        outside_air_specs = self._outside_air_action(state, ac_id, status, now, mode_intent)
        if mode_intent.mode not in (1, 4):
            mode_spec = self._set_ac_mode(state, ac_id, mode_intent, status, now)
            if mode_spec is not None:
                specs.append(mode_spec)
                status["actions"].append(f"{name}: Mode Changed: {mode_intent.name}")
        if mode_intent.mode not in (1, 4):
            specs.extend(self._restore_ac_setpoint(state, ac_id, status, now))
            specs.extend(self._restore_ac_control_sensor(state, ac_id, status, now))
            specs.extend(self._restore_dampers_for_ac(state, ac_id, ac, status, now))
            specs.extend(outside_air_specs)
            return specs
        if not controlled_rooms:
            status["recommendations"].append(f"{name}: Hybrid Held: No Active Controlled Temperature Zones")
            specs.extend(self._restore_ac(state, ac_id, status, now))
            specs.extend(self._restore_dampers_for_ac(state, ac_id, ac, status, now))
            specs.extend(outside_air_specs)
            return specs
        if proposal is None:
            status["recommendations"].append(f"{name}: Hybrid Waiting For Forecast Proposal")
            specs.extend(self._restore_ac_control_sensor(state, ac_id, status, now))
            specs.extend(self._restore_dampers_for_ac(state, ac_id, ac, status, now))
            specs.extend(outside_air_specs)
            return specs
        if proposal.source not in {"mpc", "zone"}:
            status["recommendations"].append(f"{name}: Model Learning: Waiting Before Damper Control")
            specs.extend(self._restore_ac_control_sensor(state, ac_id, status, now))
            specs.extend(self._restore_dampers_for_ac(state, ac_id, ac, status, now))
            specs.extend(outside_air_specs)
            return specs
        mode_spec = self._set_ac_mode(state, ac_id, mode_intent, status, now)
        if mode_spec is not None:
            specs.append(mode_spec)
            status["actions"].append(f"{name}: Mode Changed: {mode_intent.name}")
        setpoint = _number(ac_status.get("setpoint"))
        if setpoint is not None and int(round(setpoint)) != target:
            spec = self._set_ac_setpoint(state, ac_id, target, status, now)
            if spec is not None:
                specs.append(spec)
                status["actions"].append(f"{name}: Setpoint Changed: {target} C")
        else:
            specs.extend(self._restore_ac_setpoint(state, ac_id, status, now))

        control_sensor_spec = self._set_ac_control_sensor(state, ac_id, TOUCHPAD_2_SENSOR, status, now)
        if control_sensor_spec is not None:
            specs.append(control_sensor_spec)
            status["actions"].append(f"{name}: Control Sensor Changed: Touchpad 2")
        if control_temperature is not None:
            temp_spec = self._set_touchpad_temperature(state, TOUCHPAD_2_SENSOR, control_temperature, status, now)
            if temp_spec is not None:
                specs.append(temp_spec)
                commanded_temp = int(round(control_temperature))
                status["actions"].append(f"{name}: Control Temperature Updated: {commanded_temp} C")
            status["evaluations"][-1]["hybrid"]["touchpad_temperature_commanded"] = temp_spec is not None
            status["evaluations"][-1]["hybrid"]["touchpad_temperature"] = int(round(control_temperature))
            status["evaluations"][-1]["hybrid"]["touchpad_sensor"] = TOUCHPAD_2_SENSOR
        else:
            status["evaluations"][-1]["hybrid"]["touchpad_temperature_note"] = "No Controlled Zone Temperatures Available"

        groups = _groups_for_ac(state, ac_id, ac)
        for group_id, group in groups:
            if group_id not in controlled_group_ids:
                if not (mode_intent.outside_air_intent and group_id in self.config.outside_air_zones):
                    specs.extend(self._restore_group_percentage(state, group_id, status, now))
                continue
            group_status = group.get("status") or {}
            current = _number(group_status.get("percentage"))
            if current is None:
                continue
            percent = _hybrid_damper_percent(
                proposal.zone_power_fractions.get(group_id, proposal.power_fraction),
                minimum_percent=self.config.hybrid_min_damper_percent,
                maximum_percent=self.config.hybrid_max_damper_percent,
                idle_percent=self.config.hybrid_idle_damper_percent,
            )
            status["evaluations"][-1]["hybrid"]["damper_percentages"][str(group_id)] = percent
            if int(round(current)) == percent:
                continue
            spec = self._set_group_percentage(state, group_id, percent, status, now)
            if spec is not None:
                specs.append(spec)
                status["actions"].append(f"{_group_name(group_id, group)}: Damper Changed: {percent}%")
        specs.extend(outside_air_specs)
        return specs

    def _hybrid_shadow_status(
        self,
        controlled_rooms: tuple[Any, ...],
        target: int,
        cooling: bool,
        proposal: Any,
    ) -> dict[str, Any]:
        power_fraction = proposal.power_fraction if proposal is not None else 0.0
        status = {
            "strategy": "hybrid",
            "control_temperature": _hybrid_control_temperature(controlled_rooms, target, cooling, power_fraction),
            "control_temperature_source": "synthetic_weighted_zone_demand" if controlled_rooms else None,
            "damper_percentages": {},
            "touchpad_temperature_commanded": False,
            "touchpad_temperature_note": "Recommend Mode Only",
        }
        if proposal is None:
            return status
        for room in controlled_rooms:
            status["damper_percentages"][str(room.id)] = _hybrid_damper_percent(
                proposal.zone_power_fractions.get(room.id, proposal.power_fraction),
                minimum_percent=self.config.hybrid_min_damper_percent,
                maximum_percent=self.config.hybrid_max_damper_percent,
                idle_percent=self.config.hybrid_idle_damper_percent,
            )
        return status

    def _adaptive_target(self, ac: dict[str, Any], outside: float, weather: WeatherSignal, climate: ClimateSignal, cooling: bool) -> int:
        target = self._target_setpoint(outside, cooling)
        target = self._forecast_target(
            target,
            _forecast_values_for_control(weather),
            cooling,
            step_minutes=_forecast_step_for_control(weather),
        )
        target = self._humidity_adjusted_target(target, climate.humidity, cooling)
        return _clamp_setpoint(target, ac)

    def _room_demand_target(self, device: AdaptiveDevice, ac: dict[str, Any], cooling: bool) -> int:
        controlled = [
            room
            for room in device.rooms
            if room.active and (room.control_enabled or room.configured_control) and room.temperature is not None and room.setpoint is not None
        ]
        if controlled:
            setpoints = [float(room.setpoint) for room in controlled if room.setpoint is not None]
            target = min(setpoints) if cooling else max(setpoints)
            return _clamp_setpoint(int(round(target)), ac)
        setpoint = device.setpoint if device.setpoint is not None else _number((ac.get("status") or {}).get("setpoint"))
        if setpoint is None:
            setpoint = self.config.cool_comfort_temp if cooling else self.config.heat_comfort_temp
        return _clamp_setpoint(int(round(setpoint)), ac)

    def _mode_intent(self, device: AdaptiveDevice, ac: dict[str, Any], climate: ClimateSignal) -> AcModeIntent:
        current_mode = device.mode if isinstance(device.mode, int) else _optional_mode((ac.get("status") or {}).get("mode"))
        candidates = [
            room
            for room in device.rooms
            if room.active and (room.configured_control or room.control_enabled) and room.temperature is not None and room.setpoint is not None
        ]
        if not candidates:
            candidates = [
                room
                for room in device.rooms
                if room.active and room.temperature is not None and room.setpoint is not None
            ]
        demand: list[tuple[str, float]] = []
        for room in candidates:
            assert room.temperature is not None
            assert room.setpoint is not None
            delta = float(room.temperature) - float(room.setpoint)
            if delta >= 0.5:
                demand.append(("cool", delta))
            elif delta <= -0.5:
                demand.append(("heat", abs(delta)))
        outside_air_intent = climate.co2_ppm is not None and climate.co2_ppm >= self.config.co2_ventilation_threshold_ppm
        ventilation_reason = "co2_high" if outside_air_intent else None
        if demand:
            mode_name, _score = max(demand, key=lambda item: item[1])
            mode = 4 if mode_name == "cool" else 1
            return AcModeIntent(
                mode=mode,
                name=_mode_name(mode),
                reason="room_above_setpoint" if mode == 4 else "room_below_setpoint",
                source="zone_temperature",
                current_mode=current_mode,
                outside_air_intent=outside_air_intent,
                ventilation_reason=ventilation_reason,
            )
        if (
            climate.humidity is not None
            and climate.humidity_source == "home_assistant_indoor"
            and climate.humidity >= self.config.dry_humidity_threshold
        ):
            return AcModeIntent(
                mode=2,
                name=_mode_name(2),
                reason="indoor_humidity_extreme",
                source=climate.humidity_source,
                current_mode=current_mode,
                outside_air_intent=outside_air_intent,
                ventilation_reason=ventilation_reason,
            )
        if outside_air_intent:
            return AcModeIntent(
                mode=3,
                name=_mode_name(3),
                reason="co2_high",
                source=climate.co2_source or "co2",
                current_mode=current_mode,
                outside_air_intent=True,
                ventilation_reason=ventilation_reason,
            )
        return AcModeIntent(
            mode=current_mode,
            name=_mode_name(current_mode),
            reason="current_mode_held",
            source="current_mode",
            current_mode=current_mode,
            outside_air_intent=outside_air_intent,
            ventilation_reason=ventilation_reason,
        )

    def _control_target(self, device: AdaptiveDevice, ac: dict[str, Any], outside: float, weather: WeatherSignal, climate: ClimateSignal, cooling: bool) -> int:
        if self.config.control_strategy in {"zone", "hybrid"}:
            return self._room_demand_target(device, ac, cooling)
        return self._adaptive_target(ac, outside, weather, climate, cooling)

    def _mpc_proposal(
        self,
        device: AdaptiveDevice,
        baseline_target: int,
        cooling: bool,
        outside: float,
        weather: WeatherSignal,
        solar: SolarSignal,
        telemetry: AcTelemetrySignal,
        climate: ClimateSignal,
        *,
        advisory: bool = False,
    ):
        if not _strategy_uses_mpc(self.config.control_strategy):
            return None
        return self._mpc.propose(
            ac_id=device.ac_id,
            rooms=device.rooms,
            baseline_target=baseline_target,
            cooling=cooling,
            inputs=self._mpc_inputs(outside, weather, solar, telemetry, climate),
            advisory=advisory,
        )

    def _mpc_inputs(
        self,
        outside: float,
        weather: WeatherSignal,
        solar: SolarSignal,
        telemetry: AcTelemetrySignal,
        climate: ClimateSignal,
    ) -> MpcInputs:
        return MpcInputs(
            horizon_hours=self.config.mpc_horizon_hours,
            outside_temperature=outside,
            outside_forecast=_forecast_values_for_control(weather),
            outside_forecast_step_minutes=_forecast_step_for_control(weather),
            humidity=climate.humidity,
            humidity_assist_threshold=max(0, self.config.dry_humidity_threshold - 10),
            q_solar=solar.q_solar,
            target_policy="room_setpoint" if self.config.control_strategy in {"zone", "hybrid"} else "global_setpoint",
            comfort_weight=self.config.mpc_comfort_weight,
            input_quality={
                "forecast": weather.forecast_quality or {},
                "solar": {
                    "source": solar.source,
                    "error": solar.error,
                    "available": solar.source != "none",
                },
                "humidity": {
                    "source": climate.humidity_source,
                    "available": climate.humidity is not None,
                    "dry_threshold": self.config.dry_humidity_threshold,
                    "assist_threshold": max(0, self.config.dry_humidity_threshold - 10),
                },
                "co2": {
                    "source": climate.co2_source,
                    "available": climate.co2_ppm is not None,
                    "ppm": climate.co2_ppm,
                    "threshold_ppm": self.config.co2_ventilation_threshold_ppm,
                    "outside_air_intent": climate.co2_ppm is not None and climate.co2_ppm >= self.config.co2_ventilation_threshold_ppm,
                },
                "telemetry": _ac_telemetry_status(telemetry),
            },
        )

    def _target_setpoint(self, outside: float, cooling: bool) -> int:
        outside_round = round(outside)
        if cooling:
            return min(outside_round - self.config.cool_diff, self.config.cool_comfort_temp)
        return max(outside_round + self.config.heat_diff, self.config.heat_comfort_temp)

    def _forecast_target(self, current_target: int, forecast_temperatures: tuple[float, ...], cooling: bool, *, step_minutes: float = 60.0) -> int:
        if not forecast_temperatures:
            return current_target
        near_term_count = max(1, int(round((6 * 60) / max(1.0, step_minutes))))
        targets = [self._target_setpoint(temperature, cooling) for temperature in forecast_temperatures[:near_term_count]]
        if cooling:
            return min([current_target, *targets])
        return max([current_target, *targets])

    def _humidity_adjusted_target(self, target: int, humidity: float | None, cooling: bool) -> int:
        if not cooling or humidity is None:
            return target
        high_threshold = self.config.dry_humidity_threshold
        assist_threshold = max(0, high_threshold - 10)
        if humidity >= high_threshold:
            return target - 2
        if humidity >= assist_threshold:
            return target - 1
        return target

    @staticmethod
    def _needs_relax(current: float, target: int, cooling: bool) -> bool:
        return current < target if cooling else current > target

    def _restore_all(self, state: dict[str, Any], status: dict[str, Any], now: float) -> list[TransactionSpec]:
        specs: list[TransactionSpec] = []
        for key in list(self._restore_records):
            specs.extend(self._restore_record(state, key, status, now))
        return specs

    def _restore_ac(self, state: dict[str, Any], ac_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        specs = self._restore_ac_mode(state, ac_id, status, now)
        specs.extend(self._restore_ac_setpoint(state, ac_id, status, now))
        specs.extend(self._restore_ac_control_sensor(state, ac_id, status, now))
        ac = _indexed(state.get("acs") or {}, ac_id) or {}
        for group_id, _group in _groups_for_ac(state, ac_id, ac):
            specs.extend(self._restore_group_sensor_control(state, group_id, status, now))
            specs.extend(self._restore_group_setpoint(state, group_id, status, now))
            specs.extend(self._restore_group_percentage(state, group_id, status, now))
        return specs

    def _restore_ac_mode(self, state: dict[str, Any], ac_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"ac:{ac_id}:mode", status, now)

    def _restore_ac_setpoint(self, state: dict[str, Any], ac_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"ac:{ac_id}:setpoint", status, now)

    def _restore_ac_control_sensor(self, state: dict[str, Any], ac_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"ac:{ac_id}:control_sensor", status, now)

    def _restore_group_setpoint(self, state: dict[str, Any], group_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"group:{group_id}:setpoint", status, now)

    def _restore_group_sensor_control(self, state: dict[str, Any], group_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"group:{group_id}:sensor_control", status, now)

    def _outside_air_status(self, mode_intent: AcModeIntent) -> dict[str, Any]:
        return {
            "intent": mode_intent.outside_air_intent,
            "reason": mode_intent.ventilation_reason,
            "configured_zones": list(self.config.outside_air_zones),
            "commanded_percent": 100 if mode_intent.outside_air_intent and self.config.outside_air_zones else None,
        }

    def _outside_air_action(
        self,
        state: dict[str, Any],
        ac_id: int,
        status: dict[str, Any],
        now: float,
        mode_intent: AcModeIntent,
    ) -> list[TransactionSpec]:
        specs: list[TransactionSpec] = []
        zones = self.config.outside_air_zones
        if mode_intent.outside_air_intent and not zones:
            status["recommendations"].append(f"{_ac_name(ac_id, _indexed(state.get('acs') or {}, ac_id) or {})}: Outside Air Zone Not Configured")
            return specs
        for group_id in zones:
            if mode_intent.outside_air_intent:
                spec = self._set_group_percentage(state, group_id, 100, status, now)
                if spec is not None:
                    specs.append(spec)
                    status["actions"].append(f"{_group_name(group_id, _group_for_id(state, group_id))}: Outside Air Opened")
            else:
                specs.extend(self._restore_group_sensor_control(state, group_id, status, now))
                specs.extend(self._restore_group_percentage(state, group_id, status, now))
        return specs

    def _restore_dampers_for_ac(self, state: dict[str, Any], ac_id: int, ac: dict[str, Any], status: dict[str, Any], now: float) -> list[TransactionSpec]:
        specs: list[TransactionSpec] = []
        for group_id, _group in _groups_for_ac(state, ac_id, ac):
            specs.extend(self._restore_group_sensor_control(state, group_id, status, now))
            specs.extend(self._restore_group_percentage(state, group_id, status, now))
        return specs

    def _restore_group_percentage(self, state: dict[str, Any], group_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"group:{group_id}:percentage", status, now)

    def _restore_record(self, state: dict[str, Any], key: str, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        record = self._restore_records.get(key)
        if record is None:
            return []
        action = str(record.get("action") or "")
        target_action = str(record.get("target_action") or action)
        original = record.get("original") if isinstance(record.get("original"), dict) else {}
        target = record.get("target") if isinstance(record.get("target"), dict) else {}
        current = self._restore_current_payload(state, target_action, target)
        if current != target:
            self._restore_records.pop(key, None)
            return []
        spec = self._send_restore_action(state, action, original, status, now)
        if spec is None:
            return []
        self._restore_records.pop(key, None)
        status["actions"].append(self._restore_action_text(state, action, original))
        return [spec]

    def _restore_current_payload(self, state: dict[str, Any], action: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        if action == "ac_status":
            ac_id = _optional_int(payload.get("ac"))
            ac = _indexed(state.get("acs") or {}, ac_id) if ac_id is not None else None
            ac_status = (ac.get("status") or {}) if isinstance(ac, dict) else {}
            current: dict[str, Any] = {"ac": ac_id}
            if "mode" in payload:
                current["mode"] = _optional_int(ac_status.get("mode"))
            if "setpoint" in payload:
                setpoint = _number(ac_status.get("setpoint"))
                current["setpoint"] = int(round(setpoint)) if setpoint is not None else None
            if "power_on" in payload:
                current["power_on"] = bool(ac_status.get("power_on"))
            return current
        if action in {"group_setpoint", "group_percentage"}:
            group_id = _optional_int(payload.get("group"))
            group = _group_for_id(state, group_id) if group_id is not None else None
            group_status = (group.get("status") or {}) if isinstance(group, dict) else {}
            current = {"group": group_id}
            field = "setpoint" if action == "group_setpoint" else "percentage"
            value = _number(group_status.get(field))
            current[field] = int(round(value)) if value is not None else None
            return current
        if action == "ac_setting_new":
            ac_id = _optional_int(payload.get("ac"))
            record = _ac_setting_record_for(state, ac_id) if ac_id is not None else None
            return {
                "ac": ac_id,
                "ctrl_thermostat": _optional_int(record.get("ctrl_thermostat")) if isinstance(record, dict) else None,
            }
        return None

    def _send_restore_action(
        self,
        state: dict[str, Any],
        action: str,
        original: dict[str, Any],
        status: dict[str, Any],
        now: float,
    ) -> TransactionSpec | None:
        if action == "ac_status":
            key_suffix = "mode" if "mode" in original else "setpoint" if "setpoint" in original else "status"
            return self._send_transaction(state, action, original, f"restore:ac:{original.get('ac')}:{key_suffix}", status, now)
        if action == "group_setpoint":
            return self._send_transaction(state, action, original, f"restore:group:{original.get('group')}:setpoint", status, now)
        if action == "group_percentage":
            return self._send_transaction(state, action, original, f"restore:group:{original.get('group')}:percentage", status, now)
        if action == "ac_setting_new":
            return self._send_transaction(state, action, original, f"restore:ac:{original.get('ac')}:control_sensor", status, now)
        return None

    def _restore_action_text(self, state: dict[str, Any], action: str, original: dict[str, Any]) -> str:
        if action == "ac_status":
            ac_id = _optional_int(original.get("ac"))
            ac = _indexed(state.get("acs") or {}, ac_id) if ac_id is not None else {}
            if "mode" in original:
                return f"{_ac_name(ac_id or 0, ac or {})}: Restored Mode: {_mode_name(_optional_int(original.get('mode')))}"
            if "setpoint" in original:
                return f"{_ac_name(ac_id or 0, ac or {})}: Restored Setpoint: {original['setpoint']} C"
            return f"{_ac_name(ac_id or 0, ac or {})}: Restored AC State"
        group_id = _optional_int(original.get("group")) or 0
        group = _group_for_id(state, group_id)
        if action == "group_setpoint":
            return f"{_group_name(group_id, group)}: Restored Setpoint: {original['setpoint']} C"
        if action == "group_percentage":
            return f"{_group_name(group_id, group)}: Restored Damper: {original['percentage']}%"
        if action == "ac_setting_new":
            ac_id = _optional_int(original.get("ac")) or 0
            ac = _indexed(state.get("acs") or {}, ac_id) or {}
            return f"{_ac_name(ac_id, ac)}: Restored Control Sensor"
        return "Adaptive State Restored"

    def _set_ac_setpoint(self, state: dict[str, Any], ac_id: int, setpoint: int, status: dict[str, Any], now: float) -> TransactionSpec | None:
        ac = _indexed(state.get("acs") or {}, ac_id) or {}
        current = _number((ac.get("status") or {}).get("setpoint")) if isinstance(ac, dict) else None
        if current is None or int(round(current)) == setpoint:
            return None
        key = f"ac:{ac_id}:setpoint"
        payload = {"ac": ac_id, "setpoint": setpoint}
        self._record_restore(key, "ac_status", {"ac": ac_id, "setpoint": int(round(current))}, payload)
        return self._send_transaction(state, "ac_status", payload, key, status, now)

    def _set_ac_mode(self, state: dict[str, Any], ac_id: int, mode_intent: AcModeIntent, status: dict[str, Any], now: float) -> TransactionSpec | None:
        if mode_intent.mode is None or mode_intent.mode == mode_intent.current_mode:
            return None
        key = f"ac:{ac_id}:mode"
        payload = {"ac": ac_id, "mode": mode_intent.mode}
        self._record_restore(key, "ac_status", {"ac": ac_id, "mode": mode_intent.current_mode}, payload)
        return self._send_transaction(state, "ac_status", payload, key, status, now)

    def _set_ac_control_sensor(self, state: dict[str, Any], ac_id: int, sensor: int, status: dict[str, Any], now: float) -> TransactionSpec | None:
        records = _ac_setting_records_from_state(state)
        record = next((item for item in records if item.get("ac") == ac_id), None)
        if record is None:
            status["errors"].append(f"missing AC setting record for AC {ac_id + 1}")
            return None
        current = _optional_int(record.get("ctrl_thermostat"))
        if current is None or current == sensor:
            return None
        target_records = [dict(item) for item in records]
        target = next(item for item in target_records if item.get("ac") == ac_id)
        target["ctrl_thermostat"] = sensor
        payload = {"ac": ac_id, "ctrl_thermostat": sensor, "records": target_records}
        original_records = [dict(item) for item in records]
        original_payload = {"ac": ac_id, "ctrl_thermostat": current, "records": original_records}
        key = f"ac:{ac_id}:control_sensor"
        self._record_restore(key, "ac_setting_new", original_payload, {"ac": ac_id, "ctrl_thermostat": sensor})
        return self._send_transaction(state, "ac_setting_new", payload, key, status, now)

    def _set_touchpad_temperature(self, state: dict[str, Any], sensor: int, temperature: float, status: dict[str, Any], now: float) -> TransactionSpec | None:
        payload = {"sensor": sensor, "temperature": int(round(temperature))}
        return self._send_transaction(state, "sensor_temperature", payload, f"sensor:{sensor}:temperature", status, now)

    def _set_group_setpoint(self, state: dict[str, Any], group_id: int, setpoint: int, status: dict[str, Any], now: float) -> TransactionSpec | None:
        group = _group_for_id(state, group_id)
        current = _number((group.get("status") or {}).get("setpoint")) if isinstance(group, dict) else None
        if current is None or int(round(current)) == setpoint:
            return None
        key = f"group:{group_id}:setpoint"
        payload = {"group": group_id, "setpoint": setpoint}
        self._record_restore(key, "group_setpoint", {"group": group_id, "setpoint": int(round(current))}, payload)
        return self._send_transaction(state, "group_setpoint", payload, key, status, now)

    def _set_group_percentage(self, state: dict[str, Any], group_id: int, percentage: int, status: dict[str, Any], now: float) -> TransactionSpec | None:
        group = _group_for_id(state, group_id)
        group_status = (group.get("status") or {}) if isinstance(group, dict) else {}
        current = _number(group_status.get("percentage"))
        if current is None or int(round(current)) == percentage:
            return None
        payload = {"group": group_id, "percentage": percentage}
        if group_status.get("sensor_control") is True:
            setpoint = _number(group_status.get("setpoint"))
            if setpoint is None:
                return None
            key = f"group:{group_id}:sensor_control"
            self._record_restore(
                key,
                "group_setpoint",
                {"group": group_id, "setpoint": int(round(setpoint))},
                payload,
                target_action="group_percentage",
            )
        else:
            key = f"group:{group_id}:percentage"
            self._record_restore(key, "group_percentage", {"group": group_id, "percentage": int(round(current))}, payload)
        return self._send_transaction(state, "group_percentage", payload, key, status, now)

    def _weather_key(self, ac_id: int) -> str:
        return f"ac:{ac_id}"

    def _weather_suspension(self, ac_id: int) -> dict[str, Any] | None:
        record = self._weather_suspensions.get(self._weather_key(ac_id))
        return record if isinstance(record, dict) else None

    def _record_weather_suspension(self, ac_id: int, opportunity: dict[str, Any], now: float, cooling: bool) -> None:
        window_minutes = _weather_window_minutes(opportunity, cooling)
        self._weather_suspensions[self._weather_key(ac_id)] = {
            "phase": "weather_off",
            "ac": ac_id,
            "turned_off_at": round(now, 3),
            "outside_temperature": opportunity.get("outside_temperature"),
            "setpoint": opportunity.get("setpoint"),
            "mode": opportunity.get("mode"),
            "reason": opportunity.get("reason"),
            "nice_window_minutes": window_minutes,
        }

    def _clear_weather_suspension(self, ac_id: int) -> None:
        self._weather_suspensions.pop(self._weather_key(ac_id), None)

    def _weather_intent_status(
        self,
        ac_id: int,
        opportunity: dict[str, Any],
        suspension: dict[str, Any] | None,
        state: dict[str, Any],
        cooling: bool,
        *,
        cancelled_reason: str | None = None,
        resumed: bool = False,
    ) -> dict[str, Any]:
        window_minutes = _weather_window_minutes(opportunity, cooling)
        intent = "monitor"
        headline = "Weather Holding"
        summary = "Outside Air Is Not Helpful Yet."
        if resumed:
            intent = "resume"
            headline = "AC Resumed"
            summary = "Outside Air No Longer Carries The Load."
        elif cancelled_reason == "no_active_zones":
            intent = "cancelled"
            headline = "Resume Cancelled"
            summary = "No Zones Are On."
        elif cancelled_reason == "ac_power_changed_externally":
            intent = "cancelled"
            headline = "Resume Cancelled"
            summary = "AC Power Changed Externally."
        elif suspension is not None:
            intent = "paused"
            headline = "AC Paused"
            summary = "Outside Air Can Carry The Load."
        elif opportunity.get("recommend_off"):
            intent = "pause_recommended" if self.config.mode == "recommend" else "pause"
            headline = "Nice Outside"
            summary = "Outside Air Can Carry The Load."
        elif opportunity.get("outside_favourable"):
            intent = "hold"
            headline = "Outside Air Can Help"
            summary = "Waiting For Forecast Or Indoor Comfort."
        return {
            "ac": ac_id,
            "intent": intent,
            "headline": headline,
            "summary": summary,
            "reason": cancelled_reason or opportunity.get("reason"),
            "outside_temperature": opportunity.get("outside_temperature"),
            "setpoint": opportunity.get("setpoint"),
            "nice_outside": bool(opportunity.get("outside_favourable")),
            "open_windows": bool(opportunity.get("open_windows_intent")),
            "pause_recommended": bool(opportunity.get("recommend_off")),
            "pause_active": suspension is not None,
            "resume_pending": suspension is not None and not opportunity.get("recommend_off"),
            "resume_cancelled": cancelled_reason is not None,
            "nice_window_minutes": window_minutes,
            "suspension_active": suspension is not None,
            "cancelled_reason": cancelled_reason,
            "active_zones_available": _has_active_zone_for_ac(
                state,
                ac_id,
                _indexed(state.get("acs") or {}, ac_id) or {},
            ),
        }

    def _send_ac_power(
        self,
        state: dict[str, Any],
        ac_id: int,
        power_on: bool,
        status: dict[str, Any],
        now: float,
        *,
        key_prefix: str,
    ) -> TransactionSpec | None:
        return self._send_transaction(
            state,
            "ac_status",
            {"ac": ac_id, "power_on": power_on},
            f"{key_prefix}:ac:{ac_id}:power",
            status,
            now,
        )

    def _record_restore(
        self,
        key: str,
        action: str,
        original: dict[str, Any],
        target: dict[str, Any],
        *,
        target_action: str | None = None,
    ) -> bool:
        if original == target:
            if key not in self._restore_records:
                return False
            self._restore_records.pop(key, None)
            return False
        record = self._restore_records.setdefault(key, {"action": action, "original": dict(original)})
        record["action"] = action
        record.setdefault("original", dict(original))
        record["target"] = dict(target)
        if target_action is not None:
            record["target_action"] = target_action
        else:
            record.pop("target_action", None)
        return True

    def _send_transaction(
        self,
        state: dict[str, Any],
        action: str,
        payload: dict[str, Any],
        throttle_key: str,
        status: dict[str, Any],
        now: float,
    ) -> TransactionSpec | None:
        throttle_value = _command_value(payload)
        if throttle_value is not None and not self._should_send(throttle_key, throttle_value, now):
            return None
        try:
            return build_transaction(action, payload, state=state)
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
            "intents": [],
            "errors": [],
            "evaluations": [],
            "forecast_temperatures": [],
            "forecast_quality": {"status": "missing", "used_for_control": False},
            "solar": {"q_solar": 0.0, "source": "none", "irradiance_w_m2": None, "cloud_cover": None, "sun_elevation": None},
            "learning": self._mpc.status(time.monotonic()),
            "restore_state": self.export_restore_state(),
            "weather_state": self.export_weather_state(),
            "active_restore": sorted(self._restore_records),
            "active_ac": _active_ac_restore_ids(self._restore_records),
            "active_groups": _active_group_restore_ids(self._restore_records, "setpoint"),
            "active_dampers": sorted(set(_active_group_restore_ids(self._restore_records, "percentage")) | set(_active_group_restore_ids(self._restore_records, "sensor_control"))),
        }

    def _final_status(self, status: dict[str, Any]) -> dict[str, Any]:
        status["restore_state"] = self.export_restore_state()
        status["weather_state"] = self.export_weather_state()
        status["active_restore"] = sorted(self._restore_records)
        status["active_ac"] = _active_ac_restore_ids(self._restore_records)
        status["active_groups"] = _active_group_restore_ids(self._restore_records, "setpoint")
        status["active_dampers"] = sorted(set(_active_group_restore_ids(self._restore_records, "percentage")) | set(_active_group_restore_ids(self._restore_records, "sensor_control")))
        status["outside_air_zones"] = list(self.config.outside_air_zones)
        status["learning"] = self._mpc.status(time.monotonic())
        status["intents"] = [_intent_status(evaluation, status) for evaluation in status.get("evaluations", [])]
        for evaluation, intent in zip(status.get("evaluations", []), status["intents"], strict=False):
            evaluation["intent"] = intent
        return status


def _validated_config(config: AdaptiveConfig) -> AdaptiveConfig:
    mode = str(config.mode or "off").lower()
    if mode not in ADAPTIVE_MODES:
        raise ValueError(f"adaptive mode must be one of {', '.join(ADAPTIVE_MODES)}")
    learning_mode = str(config.learning_mode or "off").lower()
    if learning_mode not in ADAPTIVE_LEARNING_MODES:
        raise ValueError(f"adaptive learning mode must be one of {', '.join(ADAPTIVE_LEARNING_MODES)}")
    control_strategy = str(config.control_strategy or "weather").lower()
    if control_strategy not in ADAPTIVE_CONTROL_STRATEGIES:
        raise ValueError(f"adaptive control strategy must be one of {', '.join(ADAPTIVE_CONTROL_STRATEGIES)}")
    learning_mode = "control" if _strategy_uses_mpc(control_strategy) else "off"
    min_damper = _int_range("hybrid_min_damper_percent", config.hybrid_min_damper_percent, 0, 100)
    max_damper = _int_range("hybrid_max_damper_percent", config.hybrid_max_damper_percent, 0, 100)
    if min_damper > max_damper:
        raise ValueError("hybrid_min_damper_percent must be less than or equal to hybrid_max_damper_percent")
    return replace(
        config,
        mode=mode,
        learning_mode=learning_mode,
        control_strategy=control_strategy,
        cool_diff=_int_range("cool_diff", config.cool_diff, 0, 15),
        cool_comfort_temp=_int_range("cool_comfort_temp", config.cool_comfort_temp, 16, 32),
        heat_diff=_int_range("heat_diff", config.heat_diff, 0, 15),
        heat_comfort_temp=_int_range("heat_comfort_temp", config.heat_comfort_temp, 16, 32),
        check_interval=max(5.0, float(config.check_interval)),
        command_cooldown=max(1.0, float(config.command_cooldown)),
        mpc_horizon_hours=_int_range("mpc_horizon_hours", config.mpc_horizon_hours, 1, 24),
        mpc_comfort_weight=_int_range("mpc_comfort_weight", config.mpc_comfort_weight, 0, 100),
        dry_humidity_threshold=_int_range("dry_humidity_threshold", config.dry_humidity_threshold, 30, 100),
        co2_ventilation_threshold_ppm=_int_range("co2_ventilation_threshold_ppm", config.co2_ventilation_threshold_ppm, 400, 5000),
        compressor_min_run_time=max(0.0, float(config.compressor_min_run_time)),
        compressor_min_off_time=max(0.0, float(config.compressor_min_off_time)),
        compressor_groups=_validated_compressor_groups(config.compressor_groups),
        control_zones=_validated_control_zones(config.control_zones),
        outside_air_zones=_validated_outside_air_zones(config.outside_air_zones),
        hybrid_min_damper_percent=min_damper,
        hybrid_max_damper_percent=max_damper,
        hybrid_idle_damper_percent=_int_range("hybrid_idle_damper_percent", config.hybrid_idle_damper_percent, 0, 100),
    )


def _int_range(name: str, value: Any, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= number <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return number


def _strategy_uses_mpc(control_strategy: str) -> bool:
    return control_strategy in {"zone", "hybrid"}


def _weather_signal(weather: dict[str, Any], integrations: dict[str, Any], *, horizon_hours: int) -> WeatherSignal:
    outside_temperature = _weather_temperature_c(weather)
    forecast = _forecast_frame(weather, integrations, horizon_hours=horizon_hours, outside_temperature=outside_temperature)
    return WeatherSignal(
        outside_temperature=outside_temperature,
        forecast_temperatures=forecast["temperatures"],
        forecast_control_temperatures=forecast["control_temperatures"],
        forecast_step_minutes=forecast["step_minutes"],
        forecast_quality=forecast["quality"],
        humidity=_number(weather.get("humidity")),
    )


def _weather_temperature_c(weather: dict[str, Any]) -> float | None:
    value = _number(weather.get("temperature"))
    if value is None:
        return None
    return _temperature_to_c(value, weather.get("temperature_unit") or weather.get("unit_of_measurement") or "C")


def _forecast_values_for_control(weather: WeatherSignal) -> tuple[float, ...]:
    if weather.forecast_quality and weather.forecast_quality.get("used_for_control") is False:
        return ()
    return weather.forecast_control_temperatures or weather.forecast_temperatures


def _forecast_step_for_control(weather: WeatherSignal) -> float:
    return weather.forecast_step_minutes if weather.forecast_control_temperatures else 60.0


def _weather_opportunity(
    outside: float,
    setpoint: float | None,
    cooling: bool,
    weather: WeatherSignal,
    climate: ClimateSignal,
) -> dict[str, Any]:
    mode = "cooling" if cooling else "heating"
    outside_round = round(outside)
    outside_favourable = False
    forecast_favourable = False
    indoor_comfort_allows = False
    if setpoint is not None:
        outside_favourable = outside_round < setpoint if cooling else outside_round > setpoint
        forecast_favourable = _forecast_supports_weather_pause(
            _forecast_values_for_control(weather),
            setpoint,
            cooling,
            step_minutes=_forecast_step_for_control(weather),
        )
        indoor_comfort_allows = _indoor_allows_weather_pause(climate.indoor_temperature, setpoint, cooling)
    recommend_off = outside_favourable and forecast_favourable and indoor_comfort_allows
    reason = "outside_not_favourable"
    if recommend_off:
        reason = "outside_air_can_carry_load"
    elif outside_favourable and not forecast_favourable:
        reason = "forecast_not_favourable_enough"
    elif outside_favourable and not indoor_comfort_allows:
        reason = "indoor_comfort_not_satisfied"
    return {
        "mode": mode,
        "outside_temperature": round(outside, 2),
        "outside_rounded": outside_round,
        "setpoint": setpoint,
        "forecast_temperatures": _forecast_values_for_control(weather),
        "forecast_step_minutes": _forecast_step_for_control(weather),
        "outside_favourable": outside_favourable,
        "forecast_favourable": forecast_favourable,
        "indoor_comfort_allows": indoor_comfort_allows,
        "recommend_off": recommend_off,
        "open_windows_intent": recommend_off,
        "fan_ventilation_intent": False,
        "reason": reason,
    }


def _weather_window_minutes(opportunity: dict[str, Any], cooling: bool) -> float | None:
    setpoint = _number(opportunity.get("setpoint"))
    if setpoint is None or not opportunity.get("outside_favourable"):
        return None
    forecast = opportunity.get("forecast_temperatures")
    if not isinstance(forecast, tuple):
        return None
    step = _number(opportunity.get("forecast_step_minutes")) or 60.0
    minutes = 0.0
    for temperature in forecast:
        value = _number(temperature)
        if value is None:
            break
        if (value <= setpoint) if cooling else (value >= setpoint):
            minutes += step
            continue
        break
    return round(minutes, 1)


def _append_weather_recommendations(name: str, opportunity: dict[str, Any], status: dict[str, Any]) -> None:
    if not opportunity["outside_favourable"]:
        return
    status["recommendations"].append(
        f"{name}: Outside {opportunity['outside_rounded']} C Is Favourable Versus Setpoint {opportunity['setpoint']} C"
    )
    if opportunity["open_windows_intent"]:
        status["recommendations"].append(f"{name}: Open Windows Recommended: Outside Air Can Carry The Load")
    elif not opportunity["forecast_favourable"]:
        status["recommendations"].append(f"{name}: Weather Off Held By Forecast")
    elif not opportunity["indoor_comfort_allows"]:
        status["recommendations"].append(f"{name}: Weather Off Held By Indoor Comfort")


def _temperature_to_c(value: float, unit: Any) -> float:
    unit_name = str(unit or "C").upper()
    if "F" in unit_name:
        return (value - 32.0) * 5.0 / 9.0
    return value


def _forecast_frame(weather: dict[str, Any], integrations: dict[str, Any], *, horizon_hours: int, outside_temperature: float | None) -> dict[str, Any]:
    sources = _forecast_sources(weather, integrations)
    default_unit = weather.get("temperature_unit") or weather.get("unit_of_measurement") or "C"
    time_zone_name = _forecast_time_zone(integrations)
    naive_time_zone = _timezone_for_name(time_zone_name)
    timed_points: list[tuple[datetime, float]] = []
    untimed: list[float] = []
    entry_count = 0
    dropped_current_weather_anchor = False
    duplicate_timestamps = False
    localized_naive_datetimes = False
    for source in sources:
        entries, source_quality = _normalized_forecast_entries(source, naive_time_zone=naive_time_zone)
        dropped_current_weather_anchor = dropped_current_weather_anchor or source_quality["dropped_current_weather_anchor"]
        duplicate_timestamps = duplicate_timestamps or source_quality["duplicate_timestamps"]
        localized_naive_datetimes = localized_naive_datetimes or source_quality["localized_naive_datetimes"]
        for entry in entries:
            entry_count += 1
            ts, value, was_naive = _forecast_entry_time_temperature(entry, default_unit, naive_time_zone=naive_time_zone)
            localized_naive_datetimes = localized_naive_datetimes or was_naive
            if value is None:
                continue
            if ts is None:
                untimed.append(value)
            else:
                timed_points.append((ts, value))

    if timed_points:
        return _timed_forecast_frame(
            timed_points,
            horizon_hours=horizon_hours,
            entry_count=entry_count,
            outside_temperature=outside_temperature,
            dropped_current_weather_anchor=dropped_current_weather_anchor,
            duplicate_timestamps=duplicate_timestamps,
            localized_naive_datetimes=localized_naive_datetimes,
            time_zone_name=time_zone_name,
        )
    if untimed:
        values = tuple(untimed[:12])
        return {
            "temperatures": values,
            "control_temperatures": values,
            "step_minutes": 60.0,
            "quality": {
                "status": "untimed",
                "timed": False,
                "used_for_control": True,
                "entry_count": entry_count,
                "usable_count": len(values),
                "step_minutes": 60.0,
            },
        }
    return {
        "temperatures": (),
        "control_temperatures": (),
        "step_minutes": 60.0,
        "quality": {
            "status": "missing",
            "timed": False,
            "used_for_control": False,
            "entry_count": entry_count,
            "usable_count": 0,
            "step_minutes": 60.0,
        },
    }


def _forecast_sources(weather: dict[str, Any], integrations: dict[str, Any]) -> list[Any]:
    sources: list[Any] = [weather.get("forecast")]
    if integrations:
        forecast_state = (integrations.get("forecast") or {}).get("state")
        if isinstance(forecast_state, dict):
            sources.extend([forecast_state.get("forecast"), forecast_state.get("hourly"), forecast_state.get("daily")])
        else:
            sources.append(forecast_state)
    return sources


def _forecast_time_zone(integrations: dict[str, Any]) -> str | None:
    if not integrations:
        return None
    forecast_state = (integrations.get("forecast") or {}).get("state")
    if isinstance(forecast_state, dict):
        value = forecast_state.get("time_zone") or forecast_state.get("timezone")
        if isinstance(value, str) and value.strip():
            return value.strip()
    ha_state = (integrations.get("homeassistant") or {}).get("state")
    if isinstance(ha_state, dict):
        value = ha_state.get("time_zone") or ha_state.get("timezone")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _forecast_entries(source: Any) -> list[Any]:
    if not source:
        return []
    if isinstance(source, list):
        return list(source)
    if isinstance(source, dict):
        if _forecast_entry_datetime(source) is not None or any(key in source for key in ("temperature", "native_temperature", "templow")):
            return [source]
        return [
            {"datetime": key, "temperature": value} if not isinstance(value, dict) else {"datetime": key, **value}
            for key, value in source.items()
        ]
    return [{"temperature": source}]


def _normalized_forecast_entries(source: Any, *, naive_time_zone: tzinfo) -> tuple[list[Any], dict[str, bool]]:
    entries = _forecast_entries(source)
    quality = {
        "dropped_current_weather_anchor": False,
        "duplicate_timestamps": False,
        "localized_naive_datetimes": False,
    }
    if not entries:
        return entries, quality
    seen: set[datetime] = set()
    duplicate_timestamps: set[datetime] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        ts, was_naive = _forecast_entry_datetime_with_metadata(entry, naive_time_zone=naive_time_zone)
        quality["localized_naive_datetimes"] = quality["localized_naive_datetimes"] or was_naive
        if ts is None:
            continue
        if ts in seen:
            duplicate_timestamps.add(ts)
        seen.add(ts)
    quality["duplicate_timestamps"] = bool(duplicate_timestamps)
    first = entries[0]
    if (
        isinstance(first, dict)
        and str(first.get("source") or "").lower() == "current_weather"
    ):
        first_ts, first_was_naive = _forecast_entry_datetime_with_metadata(first, naive_time_zone=naive_time_zone)
        quality["localized_naive_datetimes"] = quality["localized_naive_datetimes"] or first_was_naive
        following_timestamps = {
            _forecast_entry_datetime(entry, naive_time_zone=naive_time_zone)
            for entry in entries[1:]
            if isinstance(entry, dict)
        }
        following_timestamps.discard(None)
        if first_ts is not None and following_timestamps:
            quality["dropped_current_weather_anchor"] = True
            return entries[1:], quality
    return entries, quality


def _forecast_entry_time_temperature(entry: Any, default_unit: Any, *, naive_time_zone: tzinfo) -> tuple[datetime | None, float | None, bool]:
    if not isinstance(entry, dict):
        value = _number(entry)
        return None, value, False
    value = _number(
        entry.get("temperature")
        if entry.get("temperature") is not None
        else entry.get("native_temperature")
        if entry.get("native_temperature") is not None
        else entry.get("templow")
    )
    ts, was_naive = _forecast_entry_datetime_with_metadata(entry, naive_time_zone=naive_time_zone)
    if value is None:
        return ts, None, was_naive
    unit = entry.get("temperature_unit") or entry.get("native_temperature_unit") or default_unit
    return ts, _temperature_to_c(value, unit), was_naive


def _forecast_entry_datetime(entry: dict[str, Any], *, naive_time_zone: tzinfo | None = None) -> datetime | None:
    parsed, _was_naive = _forecast_entry_datetime_with_metadata(entry, naive_time_zone=naive_time_zone or _local_timezone())
    return parsed


def _forecast_entry_datetime_with_metadata(entry: dict[str, Any], *, naive_time_zone: tzinfo) -> tuple[datetime | None, bool]:
    for key in ("datetime", "time", "timestamp", "start_time", "period_start"):
        parsed, was_naive = _parse_datetime(entry.get(key), naive_time_zone=naive_time_zone)
        if parsed is not None:
            return parsed, was_naive
    return None, False


def _parse_datetime(value: Any, *, naive_time_zone: tzinfo | None = None) -> tuple[datetime | None, bool]:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None, False
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None, False
    else:
        return None, False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=naive_time_zone or _local_timezone())
        return dt.astimezone(timezone.utc), True
    return dt.astimezone(timezone.utc), False


def _timed_forecast_frame(
    points: list[tuple[datetime, float]],
    *,
    horizon_hours: int,
    entry_count: int,
    outside_temperature: float | None,
    dropped_current_weather_anchor: bool,
    duplicate_timestamps: bool,
    localized_naive_datetimes: bool,
    time_zone_name: str | None,
) -> dict[str, Any]:
    ordered = sorted(points, key=lambda item: item[0])
    deduped: dict[datetime, float] = {}
    for ts, value in ordered:
        deduped[ts] = value
    ordered = sorted(deduped.items(), key=lambda item: item[0])
    now = datetime.now(timezone.utc).replace(microsecond=0)
    horizon_blocks = max(1, int(horizon_hours * 60 / 5))
    start = _floor_to_step(now, 5)
    end = start.timestamp() + (horizon_blocks * 5 * 60)
    first_ts = ordered[0][0]
    last_ts = ordered[-1][0]
    control_points = list(ordered)
    current_anchor = outside_temperature is not None
    if current_anchor:
        control_points.insert(0, (now, float(outside_temperature)))
        control_points = sorted(control_points, key=lambda item: item[0])
    base_quality = {
        "timed": True,
        "entry_count": entry_count,
        "usable_count": len(ordered),
        "step_minutes": 5.0,
        "first_datetime": first_ts.isoformat(),
        "last_datetime": last_ts.isoformat(),
        "horizon_blocks": horizon_blocks,
        "start_datetime": start.isoformat(),
        "anchor_datetime": now.isoformat() if current_anchor else None,
        "current_anchor": current_anchor,
        "dropped_current_weather_anchor": dropped_current_weather_anchor,
        "duplicate_timestamps": duplicate_timestamps,
        "localized_naive_datetimes": localized_naive_datetimes,
        "time_zone": time_zone_name,
    }
    if last_ts.timestamp() < start.timestamp() - (30 * 60):
        return {
            "temperatures": tuple(value for _ts, value in ordered[:12]),
            "control_temperatures": (),
            "step_minutes": 5.0,
            "quality": {**base_quality, "status": "stale", "used_for_control": False},
        }
    if first_ts.timestamp() > end:
        return {
            "temperatures": tuple(value for _ts, value in ordered[:12]),
            "control_temperatures": (),
            "step_minutes": 5.0,
            "quality": {**base_quality, "status": "out_of_horizon", "used_for_control": False},
        }
    blocks, sparse = _forecast_blocks(control_points, start=start, horizon_blocks=horizon_blocks)
    sampled = tuple(value for _ts, value in ordered[:12])
    return {
        "temperatures": sampled,
        "control_temperatures": tuple(blocks),
        "step_minutes": 5.0,
        "quality": {**base_quality, "status": "sparse" if sparse else "ok", "used_for_control": bool(blocks)},
    }


def _forecast_blocks(points: list[tuple[datetime, float]], *, start: datetime, horizon_blocks: int) -> tuple[list[float], bool]:
    block_values: list[float] = []
    sparse = False
    point_seconds = [(ts.timestamp(), value) for ts, value in points]
    index = 0
    for block in range(horizon_blocks):
        ts = start.timestamp() + ((block + 1) * 5 * 60)
        while index + 1 < len(point_seconds) and point_seconds[index + 1][0] <= ts:
            index += 1
        if ts <= point_seconds[0][0]:
            if point_seconds[0][0] - ts > 2 * 3600:
                sparse = True
            block_values.append(point_seconds[0][1])
            continue
        if index + 1 >= len(point_seconds):
            if ts - point_seconds[index][0] > 2 * 3600:
                sparse = True
            block_values.append(point_seconds[index][1])
            continue
        left_ts, left_value = point_seconds[index]
        right_ts, right_value = point_seconds[index + 1]
        if right_ts - left_ts > 3 * 3600:
            sparse = True
            block_values.append(left_value)
            continue
        ratio = (ts - left_ts) / max(1.0, right_ts - left_ts)
        block_values.append(left_value + ((right_value - left_value) * ratio))
    return block_values, sparse


def _floor_to_step(dt: datetime, minutes: int) -> datetime:
    step_seconds = minutes * 60
    floored = int(dt.timestamp() // step_seconds) * step_seconds
    return datetime.fromtimestamp(floored, timezone.utc)


def _local_timezone() -> tzinfo:
    local = datetime.now().astimezone().tzinfo
    return local or timezone.utc


def _timezone_for_name(name: str | None) -> tzinfo:
    if not name:
        return _local_timezone()
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return _local_timezone()


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


def _ac_telemetry_signal(integrations: dict[str, Any]) -> AcTelemetrySignal:
    pipe = (integrations.get("ac_telemetry") or {}) if integrations else {}
    error = pipe.get("error") if isinstance(pipe, dict) else None
    state = pipe.get("state") if isinstance(pipe, dict) else None
    if not isinstance(state, dict):
        return AcTelemetrySignal(error=str(error) if error else None)

    power_w = _number(state.get("power_w"))
    running = state.get("running") if isinstance(state.get("running"), bool) else None
    frequency_hz = _number(state.get("frequency_hz"))
    return_air = _number(state.get("return_air_temperature_c"))
    supply_air = _number(state.get("supply_air_temperature_c"))
    delta = _number(state.get("supply_return_delta_c"))
    if delta is None and return_air is not None and supply_air is not None:
        delta = supply_air - return_air

    evidence: list[str] = []
    raw_evidence = state.get("evidence")
    if isinstance(raw_evidence, list):
        evidence.extend(str(item) for item in raw_evidence if item)
    active_votes = 0
    inactive_votes = 0
    source = "none"
    confidence = 0.0
    if power_w is not None:
        source = "electrical_power"
        confidence = max(confidence, 0.85)
        if power_w >= TELEMETRY_ACTIVE_POWER_W:
            active_votes += 1
        elif power_w <= TELEMETRY_IDLE_POWER_W:
            inactive_votes += 1
    if running is not None:
        if source == "none":
            source = "running_state"
        confidence = max(confidence, 0.9)
        if running:
            active_votes += 1
        else:
            inactive_votes += 1
    if frequency_hz is not None:
        if source == "none":
            source = "compressor_frequency"
        confidence = max(confidence, 0.95)
        if frequency_hz > TELEMETRY_ACTIVE_FREQUENCY_HZ:
            active_votes += 1
        else:
            inactive_votes += 1
    if delta is not None:
        confidence = max(confidence, 0.65)
        abs_delta = abs(delta)
        if abs_delta >= TELEMETRY_ACTIVE_SUPPLY_RETURN_DELTA_C:
            active_votes += 1
            evidence.append("supply_return_delta")
        elif abs_delta <= TELEMETRY_IDLE_SUPPLY_RETURN_DELTA_C:
            inactive_votes += 1

    observed = None
    if active_votes or inactive_votes:
        observed = active_votes > inactive_votes
    return AcTelemetrySignal(
        available=bool(active_votes or inactive_votes or evidence),
        observed_conditioning=observed,
        source=source,
        confidence=round(confidence, 3),
        power_w=None if power_w is None else round(power_w, 3),
        running=running,
        frequency_hz=None if frequency_hz is None else round(frequency_hz, 3),
        return_air_temperature_c=None if return_air is None else round(return_air, 2),
        supply_air_temperature_c=None if supply_air is None else round(supply_air, 2),
        supply_return_delta_c=None if delta is None else round(delta, 2),
        evidence=tuple(dict.fromkeys(evidence)),
        error=str(error) if error else None,
    )


def _ac_telemetry_status(signal: AcTelemetrySignal) -> dict[str, Any]:
    return {
        "available": signal.available,
        "observed_conditioning": signal.observed_conditioning,
        "source": signal.source,
        "confidence": signal.confidence,
        "power_w": signal.power_w,
        "running": signal.running,
        "frequency_hz": signal.frequency_hz,
        "return_air_temperature_c": signal.return_air_temperature_c,
        "supply_air_temperature_c": signal.supply_air_temperature_c,
        "supply_return_delta_c": signal.supply_return_delta_c,
        "evidence": list(signal.evidence),
        "error": signal.error,
    }


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
    co2_ppm = _number(indoor.get("co2_ppm"))
    co2_source = "home_assistant_indoor" if co2_ppm is not None else None
    return ClimateSignal(
        indoor_temperature=indoor_temperature,
        indoor_source=source,
        humidity=humidity,
        humidity_source=humidity_source,
        co2_ppm=co2_ppm,
        co2_source=co2_source,
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


def _indoor_allows_weather_pause(indoor_temperature: float | None, setpoint: float, cooling: bool) -> bool:
    if indoor_temperature is None:
        return True
    if cooling:
        return indoor_temperature <= setpoint + 0.5
    return indoor_temperature >= setpoint - 0.5


def _forecast_supports_weather_pause(forecast_temperatures: tuple[float, ...], setpoint: float, cooling: bool, *, step_minutes: float = 60.0) -> bool:
    if not forecast_temperatures:
        return True
    near_term_count = max(1, int(round((6 * 60) / max(1.0, step_minutes))))
    near_term = forecast_temperatures[:near_term_count]
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


def _proposal_status(proposal: Any) -> dict[str, Any] | None:
    if proposal is None:
        return None
    return {
        "target": proposal.target,
        "source": proposal.source,
        "confidence": proposal.confidence,
        "predicted_temperatures": proposal.predicted_temperatures,
        "reason": proposal.reason,
        "action": proposal.action,
        "power_fraction": proposal.power_fraction,
        "zone_power_fractions": {str(group_id): fraction for group_id, fraction in getattr(proposal, "zone_power_fractions", {}).items()},
        "projected_runtime_hours": getattr(proposal, "projected_runtime_hours", 0.0),
        "zone_projected_runtime_hours": {
            str(group_id): hours
            for group_id, hours in getattr(proposal, "zone_projected_runtime_hours", {}).items()
        },
        "runtime_forecast": _runtime_forecast_status(getattr(proposal, "runtime_forecast", None)),
    }


def _mode_intent_status(intent: AcModeIntent) -> dict[str, Any]:
    return {
        "mode": intent.mode,
        "name": intent.name,
        "reason": intent.reason,
        "source": intent.source,
        "current_mode": intent.current_mode,
        "current_mode_name": _mode_name(intent.current_mode),
        "change_required": intent.mode is not None and intent.mode != intent.current_mode,
        "outside_air_intent": intent.outside_air_intent,
        "ventilation_reason": intent.ventilation_reason,
    }


def _intent_status(evaluation: dict[str, Any], status: dict[str, Any]) -> dict[str, Any]:
    mode = str(status.get("mode") or "off")
    config = status.get("config") or {}
    strategy = str(config.get("control_strategy") or "weather")
    name = str(evaluation.get("name") or f"AC {int(evaluation.get('ac') or 0) + 1}")
    authority = "off" if mode == "off" else ("insight" if mode == "recommend" else "control")
    commands = [action for action in status.get("actions", []) if isinstance(action, str) and action.startswith(f"{name}:")]
    target = evaluation.get("target")
    mpc = evaluation.get("mpc") or {}
    runtime = (mpc.get("runtime_forecast") or {}) if isinstance(mpc, dict) else {}
    runtime_hours = runtime.get("runtime_hours")
    confidence = mpc.get("confidence") if isinstance(mpc, dict) else None
    affected_zones = sorted(_zone_labels((mpc.get("zone_power_fractions") or {}).keys())) if isinstance(mpc, dict) else []
    mode_intent = evaluation.get("mode_intent") if isinstance(evaluation.get("mode_intent"), dict) else {}
    air_quality = evaluation.get("air_quality") if isinstance(evaluation.get("air_quality"), dict) else {}
    base = {
        "ac": evaluation.get("ac"),
        "name": name,
        "mode": mode,
        "strategy": strategy,
        "authority": authority,
        "intent": "monitor",
        "headline": "Monitoring",
        "summary": "No Adaptive Change Is Planned.",
        "reason": None,
        "confidence": confidence,
        "recommended_target": target,
        "runtime_hours": runtime_hours,
        "affected_zones": affected_zones,
        "mode_intent": mode_intent,
        "air_quality": air_quality,
        "intended_ac_mode": mode_intent.get("name"),
        "commands": commands,
    }
    opportunity = evaluation.get("weather_opportunity") or {}
    if strategy == "weather":
        return _weather_intent(base, opportunity, mode)
    if mode_intent and mode_intent.get("mode") == 2:
        zone_text = _zone_plan_text(air_quality.get("dry_zone_ids"), "Zones Would Open")
        summary = "AC Mode Intent: Dry"
        if zone_text:
            summary = f"{summary} / {zone_text}"
        return {
            **base,
            "intent": "dehumidify",
            "headline": "Dehumidification Recommended",
            "summary": summary,
            "reason": mode_intent.get("reason"),
            "confidence": 0.7,
        }
    if mode_intent and mode_intent.get("mode") == 3 and mode_intent.get("outside_air_intent"):
        zone_text = _zone_plan_text(air_quality.get("outside_air_zone_ids"), "Outside Air Zones Would Open")
        summary = "Fan And Outside Air Recommended"
        if zone_text:
            summary = f"{summary} / {zone_text}"
        return {
            **base,
            "intent": "ventilate",
            "headline": "Fresh Air Recommended",
            "summary": summary,
            "reason": mode_intent.get("reason"),
            "confidence": 0.7,
        }
    if mode_intent and mode_intent.get("change_required") and not mpc:
        summary = f"AC Mode Intent: {mode_intent.get('name')}"
        if mode_intent.get("outside_air_intent"):
            summary = f"{summary} / Outside Air Recommended"
        return {
            **base,
            "intent": "mode_change",
            "headline": f"{mode_intent.get('name')} Mode Recommended",
            "summary": summary,
            "reason": mode_intent.get("reason"),
        }
    if isinstance(mpc, dict) and mpc:
        return _forecast_intent(base, mpc, evaluation)
    if opportunity and not mpc:
        return _weather_intent(base, opportunity, mode)
    if mode == "off":
        return {**base, "intent": "off", "headline": "Adaptive Control Is Off", "summary": "No Adaptive Recommendations Or Commands Are Being Produced."}
    return base


def _weather_intent(base: dict[str, Any], opportunity: dict[str, Any], mode: str) -> dict[str, Any]:
    if not opportunity:
        return base
    setpoint = opportunity.get("setpoint")
    outside = opportunity.get("outside_rounded")
    reason = opportunity.get("reason")
    if opportunity.get("recommend_off"):
        intent = "turn_off" if mode == "adaptive" else "ventilate"
        headline = "Weather Can Carry Load" if mode == "adaptive" else "Open Windows Recommended"
        summary = f"Outside {outside} C Is Favourable Versus Setpoint {setpoint} C."
    elif opportunity.get("outside_favourable"):
        intent = "hold"
        headline = "Outside Air Is Favourable"
        summary = "Weather Off Is Held By Forecast." if reason == "forecast_not_favourable_enough" else "Weather Off Is Held By Indoor Comfort."
    else:
        intent = "monitor"
        headline = "Weather Holding"
        summary = "Outside Air Is Not Favourable Yet."
    return {
        **base,
        "intent": intent,
        "headline": headline,
        "summary": summary,
        "reason": reason,
        "confidence": 1.0 if opportunity.get("recommend_off") else None,
    }


def _forecast_intent(base: dict[str, Any], mpc: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
    source = str(mpc.get("source") or "")
    if source == "learning":
        return {
            **base,
            "intent": "learning",
            "headline": "Model Learning",
            "summary": "Waiting For More Samples Before Control.",
            "reason": mpc.get("reason"),
        }
    action = str(mpc.get("action") or "idle")
    intent = {"heating": "heat", "cooling": "cool", "idle": "hold"}.get(action, "monitor")
    headline = {"heating": "Heating Expected", "cooling": "Cooling Expected", "idle": "Holding Target"}.get(action, "Forecast Ready")
    target = mpc.get("target", base.get("recommended_target"))
    summary_parts = [f"Recommended Target: {target} C"]
    runtime_hours = base.get("runtime_hours")
    if isinstance(runtime_hours, (int, float)):
        summary_parts.append(f"Expected Runtime: {runtime_hours:.1f} H")
    hybrid = evaluation.get("hybrid") or {}
    dampers = hybrid.get("damper_percentages") if isinstance(hybrid, dict) else None
    if dampers:
        damper_text = ", ".join(f"Zone {int(group_id) + 1} {percent}%" for group_id, percent in sorted(dampers.items(), key=lambda item: int(item[0])))
        summary_parts.append(f"Damper Plan: {damper_text}")
    air_quality = evaluation.get("air_quality") if isinstance(evaluation.get("air_quality"), dict) else {}
    if air_quality.get("dry_held_reason") == "thermal_demand_active":
        summary_parts.append("Humidity High: Thermal Mode Preferred")
    if air_quality.get("fan_held_reason") == "thermal_demand_active":
        summary_parts.append("CO2 High: Outside Air Recommended")
    return {
        **base,
        "intent": intent,
        "headline": headline,
        "summary": " / ".join(summary_parts),
        "reason": mpc.get("reason"),
        "recommended_target": target,
        "confidence": mpc.get("confidence"),
    }


def _zone_plan_text(values: Any, label: str) -> str:
    labels = _zone_labels(values or [])
    if not labels:
        return ""
    return f"{label}: {', '.join(labels)}"


def _zone_labels(values: Any) -> list[str]:
    labels = []
    for value in values:
        try:
            labels.append(f"Zone {int(value) + 1}")
        except (TypeError, ValueError):
            continue
    return labels


def _title_text(value: Any) -> str:
    text = str(value or "").replace("_", " ").replace("-", " ").strip()
    return " ".join(part[:1].upper() + part[1:].lower() for part in text.split())


def _runtime_forecast_status(forecast: Any) -> dict[str, Any] | None:
    if forecast is None:
        return None
    return {
        "horizon_hours": forecast.horizon_hours,
        "step_minutes": forecast.step_minutes,
        "runtime_minutes": forecast.runtime_minutes,
        "runtime_hours": round(forecast.runtime_minutes / 60.0, 2),
        "runtime_fraction": forecast.runtime_fraction,
        "zone_runtime_minutes": {
            str(group_id): minutes
            for group_id, minutes in getattr(forecast, "zone_runtime_minutes", {}).items()
        },
        "zone_runtime_fraction": {
            str(group_id): fraction
            for group_id, fraction in getattr(forecast, "zone_runtime_fraction", {}).items()
        },
        "action_windows": list(getattr(forecast, "action_windows", [])),
        "series": list(getattr(forecast, "series", [])),
        "quality": dict(getattr(forecast, "quality", {})),
    }


def _hybrid_damper_percent(power_fraction: float, *, minimum_percent: int, maximum_percent: int, idle_percent: int) -> int:
    fraction = _number(power_fraction)
    if fraction is None or fraction <= 0.0:
        return _clamp_int(idle_percent, 0, 100)
    minimum = _percent_to_fraction(minimum_percent)
    maximum = _percent_to_fraction(maximum_percent)
    damper = minimum + (maximum - minimum) * min(1.0, fraction)
    return _fraction_to_percent(damper)


def _hybrid_control_temperature(rooms: tuple[Any, ...], target: int, cooling: bool, power_fraction: float) -> float | None:
    temperatures = [(room.temperature, max(0.05, room.power_fraction)) for room in rooms if room.temperature is not None]
    if not temperatures:
        return None
    total_weight = sum(weight for _temperature, weight in temperatures)
    average = sum(temperature * weight for temperature, weight in temperatures) / total_weight
    demand = min(1.0, max(0.0, float(power_fraction or 0.0)))
    offset = demand * 2.0
    synthetic = max(average, target + offset) if cooling else min(average, target - offset)
    return round(synthetic, 1)


def _clamp_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = minimum
    return min(max(number, minimum), maximum)


def _fraction_to_percent(value: float) -> int:
    return _clamp_int(round(float(value) * 100.0), 0, 100)


def _percent_to_fraction(value: int) -> float:
    return _clamp_int(value, 0, 100) / 100.0


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


def _has_active_zone_for_ac(state: dict[str, Any], ac_id: int, ac: dict[str, Any]) -> bool:
    return any(
        (group.get("status") or {}).get("power_name") in {"on", "turbo"}
        for _group_id, group in _groups_for_ac(state, ac_id, ac)
    )


def _group_for_id(state: dict[str, Any], group_id: int) -> dict[str, Any]:
    group = _indexed(state.get("active_groups") or {}, group_id)
    if isinstance(group, dict):
        return group
    group = _indexed(state.get("groups") or {}, group_id)
    return group if isinstance(group, dict) else {}


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
    return _validated_zone_ids("control_zones", value)


def _validated_outside_air_zones(value: Any) -> tuple[int, ...]:
    return _validated_zone_ids("outside_air_zones", value)


def _validated_zone_ids(name: str, value: Any) -> tuple[int, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        raise ValueError(f"{name} must be a list or comma-separated string")
    zones = []
    for item in items:
        try:
            zone = int(item)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must contain integer zone ids") from exc
        if zone < 0:
            raise ValueError(f"{name} must contain non-negative zone ids")
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


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_mode(value: Any) -> int | None:
    mode = _optional_int(value)
    return mode if mode in {0, 1, 2, 3, 4} else None


def _mode_name(mode: int | None) -> str:
    return {
        0: "Auto",
        1: "Heat",
        2: "Dry",
        3: "Fan",
        4: "Cool",
    }.get(mode, "Unknown")


def _cooling_for_mode(mode: int | None, *, default: bool) -> bool:
    if mode == 1:
        return False
    if mode == 4:
        return True
    return default


def _runtime_control_status(runtime_snapshot: dict[str, Any]) -> dict[str, Any]:
    runtime = runtime_snapshot.get("runtime")
    if not isinstance(runtime, dict):
        return {"connected": False, "reason": "Runtime Connection State Is Not Available"}
    connected = runtime.get("connected") is True
    return {
        "connected": connected,
        "reason": None if connected else "Runtime Is Not Connected To The Mainboard",
    }


def _command_value(payload: dict[str, Any]) -> int | bool | None:
    for key in ("mode", "setpoint", "percentage", "temperature", "ctrl_thermostat", "power_on"):
        if key in payload:
            value = payload[key]
            if isinstance(value, bool):
                return value
            parsed = _optional_int(value)
            return parsed
    return None


def _active_ac_restore_ids(records: dict[str, dict[str, Any]]) -> list[int]:
    ids: set[int] = set()
    for key in records:
        parts = key.split(":")
        if len(parts) >= 3 and parts[0] == "ac":
            value = _optional_int(parts[1])
            if value is not None:
                ids.add(value)
    return sorted(ids)


def _active_group_restore_ids(records: dict[str, dict[str, Any]], surface: str) -> list[int]:
    ids: set[int] = set()
    for key in records:
        parts = key.split(":")
        if len(parts) >= 3 and parts[0] == "group" and parts[2] == surface:
            value = _optional_int(parts[1])
            if value is not None:
                ids.add(value)
    return sorted(ids)


def _ac_setting_record_for(state: dict[str, Any], ac_id: int | None) -> dict[str, Any] | None:
    if ac_id is None:
        return None
    ac = _indexed(state.get("acs") or {}, ac_id)
    if not isinstance(ac, dict):
        return None
    settings = ac.get("settings") or {}
    if not isinstance(settings, dict):
        return None
    return {
        "ac": ac_id,
        "hide_spill_group": bool(settings.get("hide_spill_group", False)),
        "ctrl_thermostat": int(settings.get("ctrl_thermostat", 0) or 0),
        "cool_adjust": int(settings.get("cool_adjust", 0) or 0),
        "heat_adjust": int(settings.get("heat_adjust", 0) or 0),
        "modes": dict(settings.get("modes") or {}),
        "fan_values": dict(settings.get("fan_values") or {}),
        "auto_off": bool(settings.get("auto_off", False)),
        "on_time_limit": int(settings.get("on_time_limit", 0) or 0),
        "max_setpoint": int(settings.get("max_setpoint", 30) or 30),
        "min_setpoint": int(settings.get("min_setpoint", 16) or 16),
        "selector_visibility": dict(settings.get("selector_visibility") or {}),
    }


def _ac_setting_records_from_state(state: dict[str, Any]) -> list[dict[str, Any]]:
    acs = state.get("acs") or {}
    if not isinstance(acs, dict):
        return []
    records: list[dict[str, Any]] = []
    for key in sorted(acs, key=lambda value: _optional_int(value) if _optional_int(value) is not None else 999):
        ac_id = _optional_int(key)
        record = _ac_setting_record_for(state, ac_id)
        if record is not None:
            records.append(record)
    return records


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
