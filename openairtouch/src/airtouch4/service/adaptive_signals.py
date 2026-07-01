"""Signal normalization helpers for adaptive control."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


TELEMETRY_ACTIVE_POWER_W = 300.0
TELEMETRY_IDLE_POWER_W = 120.0
TELEMETRY_ACTIVE_FREQUENCY_HZ = 1.0
TELEMETRY_ACTIVE_SUPPLY_RETURN_DELTA_C = 3.0
TELEMETRY_IDLE_SUPPLY_RETURN_DELTA_C = 1.0


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
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
