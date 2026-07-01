"""Local weather-adaptive control policy inspired by the AT5 console."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Any

from ..session.queue import TransactionSpec
from .commands import CommandRequestError, build_transaction
from .adaptive_airtouch import translate_airtouch_snapshot
from .adaptive_intent import _intent_status, _mode_intent_status
from .adaptive_mpc import AdaptiveMpcEngine, MpcInputs
from .adaptive_model import AdaptiveDevice
from .adaptive_restore import AdaptiveRestoreMixin
from .adaptive_strategies import AdaptiveStrategyMixin
from .adaptive_signals import (
    AcTelemetrySignal,
    ClimateSignal,
    SolarSignal,
    WeatherSignal,
    _ac_telemetry_signal,
    _ac_telemetry_status,
    _climate_for_ac,
    _forecast_step_for_control,
    _forecast_values_for_control,
    _solar_signal,
    _weather_signal,
    _weather_window_minutes,
)


ADAPTIVE_MODES = ("off", "recommend", "adaptive")
ADAPTIVE_LEARNING_MODES = ("off", "control")
ADAPTIVE_CONTROL_STRATEGIES = ("weather", "zone", "hybrid")
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
class AcModeIntent:
    mode: int | None
    name: str
    reason: str
    source: str
    current_mode: int | None = None
    outside_air_intent: bool = False
    ventilation_reason: str | None = None


class AdaptiveController(AdaptiveStrategyMixin, AdaptiveRestoreMixin):
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
