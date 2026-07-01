"""Adaptive strategy decision helpers."""

from __future__ import annotations

from typing import Any

from ..session.queue import TransactionSpec
from .adaptive_intent import _mode_intent_status, _proposal_status, _title_text
from .adaptive_model import AdaptiveDevice
from .adaptive_signals import (
    AcTelemetrySignal,
    ClimateSignal,
    SolarSignal,
    WeatherSignal,
    _append_weather_recommendations,
    _forecast_step_for_control,
    _forecast_values_for_control,
    _indoor_allows_relax,
    _weather_opportunity,
)


TOUCHPAD_2_SENSOR = 0x91


class AdaptiveStrategyMixin:
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


def _cooling_for_mode(mode: int | None, *, default: bool) -> bool:
    if mode == 1:
        return False
    if mode == 4:
        return True
    return default


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


def _group_for_id(state: dict[str, Any], group_id: int) -> dict[str, Any]:
    group = _indexed(state.get("active_groups") or {}, group_id)
    if isinstance(group, dict):
        return group
    group = _indexed(state.get("groups") or {}, group_id)
    return group if isinstance(group, dict) else {}


def _has_active_zone_for_ac(state: dict[str, Any], ac_id: int, ac: dict[str, Any]) -> bool:
    return any(
        (group.get("status") or {}).get("power_name") in {"on", "turbo"}
        for _group_id, group in _groups_for_ac(state, ac_id, ac)
    )


def _indexed(mapping: Any, key: int | None) -> Any:
    if key is None:
        return None
    if not isinstance(mapping, dict):
        return None
    return mapping.get(key) if key in mapping else mapping.get(str(key))


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ac_name(ac_id: int, ac: dict[str, Any]) -> str:
    base = ac.get("base") or {}
    return str(base.get("name") or f"AC {ac_id + 1}")


def _group_name(group_id: int, group: dict[str, Any]) -> str:
    base = group.get("base") or {}
    return str(base.get("name") or f"Zone {group_id + 1}")
