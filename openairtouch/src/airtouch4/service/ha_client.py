"""Small Home Assistant API client for add-on local reads."""

from __future__ import annotations

import json
import os
from datetime import datetime
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class HomeAssistantApiConfig:
    weather_entity: str = ""
    forecast_weather_entity: str = ""
    indoor_temperature_entity: str = ""
    indoor_humidity_entity: str = ""
    indoor_co2_entity: str = ""
    solar_irradiance_entity: str = ""
    cloud_cover_entity: str = ""
    ac_power_entity: str = ""
    ac_running_entity: str = ""
    ac_frequency_entity: str = ""
    ac_return_air_temp_entity: str = ""
    ac_supply_air_temp_entity: str = ""
    timeout: float = 3.0


class HomeAssistantApiClient:
    def __init__(self, config: HomeAssistantApiConfig) -> None:
        self.config = config
        self._time_zone: str | None = None
        self._time_zone_checked = False

    def weather_snapshot(self) -> dict[str, Any] | None:
        entity_id = self.config.weather_entity.strip()
        if not entity_id:
            return None
        state = self.read_state(entity_id)
        attrs = state.get("attributes", {})
        return {
            "entity_id": entity_id,
            "state": state.get("state"),
            "temperature": attrs.get("temperature"),
            "humidity": attrs.get("humidity"),
            "wind_speed": attrs.get("wind_speed"),
            "wind_bearing": attrs.get("wind_bearing"),
            "pressure": attrs.get("pressure"),
            "forecast": attrs.get("forecast"),
            "friendly_name": attrs.get("friendly_name"),
            "temperature_unit": attrs.get("temperature_unit"),
            "pressure_unit": attrs.get("pressure_unit"),
            "wind_speed_unit": attrs.get("wind_speed_unit"),
        }

    def indoor_snapshot(self) -> dict[str, Any] | None:
        temperature_entity = self.config.indoor_temperature_entity.strip()
        humidity_entity = self.config.indoor_humidity_entity.strip()
        co2_entity = self.config.indoor_co2_entity.strip()
        if not temperature_entity and not humidity_entity and not co2_entity:
            return None

        snapshot: dict[str, Any] = {
            "temperature_entity_id": temperature_entity,
            "humidity_entity_id": humidity_entity,
            "co2_entity_id": co2_entity,
            "temperature": None,
            "humidity": None,
            "co2_ppm": None,
            "temperature_unit": "C",
            "humidity_unit": "%",
            "co2_unit": "ppm",
        }
        if temperature_entity:
            state = self.read_state(temperature_entity)
            attrs = state.get("attributes", {})
            snapshot.update({
                "temperature": _float_or_none(state.get("state")),
                "temperature_unit": attrs.get("unit_of_measurement") or "C",
                "temperature_name": attrs.get("friendly_name"),
            })
        if humidity_entity:
            state = self.read_state(humidity_entity)
            attrs = state.get("attributes", {})
            snapshot.update({
                "humidity": _float_or_none(state.get("state")),
                "humidity_unit": attrs.get("unit_of_measurement") or "%",
                "humidity_name": attrs.get("friendly_name"),
            })
        if co2_entity:
            state = self.read_state(co2_entity)
            attrs = state.get("attributes", {})
            snapshot.update({
                "co2_ppm": _float_or_none(state.get("state")),
                "co2_unit": attrs.get("unit_of_measurement") or "ppm",
                "co2_name": attrs.get("friendly_name"),
            })
        return snapshot

    def solar_snapshot(self) -> dict[str, Any] | None:
        irradiance_entity = self.config.solar_irradiance_entity.strip()
        cloud_entity = self.config.cloud_cover_entity.strip()
        if not irradiance_entity and not cloud_entity:
            return None

        snapshot: dict[str, Any] = {
            "irradiance_entity_id": irradiance_entity,
            "cloud_cover_entity_id": cloud_entity,
            "irradiance": None,
            "irradiance_unit": "",
            "cloud_cover": None,
            "cloud_cover_unit": "%",
        }
        if irradiance_entity:
            state = self.read_state(irradiance_entity)
            attrs = state.get("attributes", {})
            snapshot.update({
                "irradiance": _float_or_none(state.get("state")),
                "irradiance_unit": attrs.get("unit_of_measurement") or "",
                "irradiance_name": attrs.get("friendly_name"),
            })
        if cloud_entity:
            state = self.read_state(cloud_entity)
            attrs = state.get("attributes", {})
            snapshot.update({
                "cloud_cover": _float_or_none(state.get("state")),
                "cloud_cover_unit": attrs.get("unit_of_measurement") or "%",
                "cloud_cover_name": attrs.get("friendly_name"),
            })
        return snapshot

    def ac_telemetry_snapshot(self) -> dict[str, Any] | None:
        entities = {
            "power": self.config.ac_power_entity.strip(),
            "running": self.config.ac_running_entity.strip(),
            "frequency": self.config.ac_frequency_entity.strip(),
            "return_air_temperature": self.config.ac_return_air_temp_entity.strip(),
            "supply_air_temperature": self.config.ac_supply_air_temp_entity.strip(),
        }
        if not any(entities.values()):
            return None

        snapshot: dict[str, Any] = {
            "configured": True,
            "entities": {key: value for key, value in entities.items() if value},
            "evidence": [],
        }
        if entities["power"]:
            state = self.read_state(entities["power"])
            attrs = state.get("attributes", {})
            power = _power_to_w(_float_or_none(state.get("state")), attrs.get("unit_of_measurement"))
            snapshot.update({
                "power_w": power,
                "power_unit": "W" if power is not None else attrs.get("unit_of_measurement"),
                "power_name": attrs.get("friendly_name"),
            })
            if power is not None:
                snapshot["evidence"].append("electrical_power")
        if entities["running"]:
            state = self.read_state(entities["running"])
            attrs = state.get("attributes", {})
            running = _running_state(state.get("state"))
            snapshot.update({
                "running": running,
                "running_state": state.get("state"),
                "running_name": attrs.get("friendly_name"),
            })
            if running is not None:
                snapshot["evidence"].append("running_state")
        if entities["frequency"]:
            state = self.read_state(entities["frequency"])
            attrs = state.get("attributes", {})
            frequency = _float_or_none(state.get("state"))
            snapshot.update({
                "frequency_hz": frequency,
                "frequency_unit": attrs.get("unit_of_measurement") or "Hz",
                "frequency_name": attrs.get("friendly_name"),
            })
            if frequency is not None:
                snapshot["evidence"].append("compressor_frequency")
        return_air = self._temperature_entity_value(entities["return_air_temperature"])
        supply_air = self._temperature_entity_value(entities["supply_air_temperature"])
        if return_air is not None:
            snapshot["return_air_temperature_c"] = return_air["temperature_c"]
            snapshot["return_air_name"] = return_air.get("name")
            snapshot["evidence"].append("return_air_temperature")
        if supply_air is not None:
            snapshot["supply_air_temperature_c"] = supply_air["temperature_c"]
            snapshot["supply_air_name"] = supply_air.get("name")
            snapshot["evidence"].append("supply_air_temperature")
        if return_air is not None and supply_air is not None:
            snapshot["supply_return_delta_c"] = round(supply_air["temperature_c"] - return_air["temperature_c"], 2)
        return snapshot

    def _temperature_entity_value(self, entity_id: str) -> dict[str, Any] | None:
        if not entity_id:
            return None
        state = self.read_state(entity_id)
        attrs = state.get("attributes", {})
        value = _float_or_none(state.get("state"))
        if value is None:
            return None
        return {
            "temperature_c": _temperature_to_c(value, attrs.get("unit_of_measurement") or "C"),
            "name": attrs.get("friendly_name"),
        }

    def sun_snapshot(self) -> dict[str, Any] | None:
        sun = self.read_state("sun.sun")
        sun_attrs = sun.get("attributes", {})
        result: dict[str, Any] = {
            "entity_id": "sun.sun",
            "state": sun.get("state"),
            "elevation": _float_or_none(sun_attrs.get("elevation")),
            "azimuth": _float_or_none(sun_attrs.get("azimuth")),
            "rising": sun_attrs.get("rising"),
        }
        try:
            zone = self.read_state("zone.home")
        except Exception:
            zone = {}
        zone_attrs = zone.get("attributes", {}) if isinstance(zone, dict) else {}
        result.update({
            "latitude": _float_or_none(zone_attrs.get("latitude")),
            "longitude": _float_or_none(zone_attrs.get("longitude")),
            "location_name": zone_attrs.get("friendly_name"),
        })
        return result

    def hourly_forecast_snapshot(self, *, current_weather: dict[str, Any] | None = None) -> dict[str, Any] | None:
        entity_id = self.config.forecast_weather_entity.strip()
        if not entity_id:
            return None
        response = self.call_service_response(
            "weather",
            "get_forecasts",
            {"entity_id": entity_id, "type": "hourly"},
        )
        forecast = list(((response.get(entity_id) or {}).get("forecast") or []))
        now_entry = _now_forecast_entry(current_weather)
        if now_entry is not None:
            forecast.insert(0, now_entry)
        result = {
            "entity_id": entity_id,
            "type": "hourly",
            "forecast": forecast,
            "prepended_current": now_entry is not None,
        }
        time_zone = self.home_assistant_timezone()
        if time_zone:
            result["time_zone"] = time_zone
        return result

    def home_assistant_timezone(self) -> str | None:
        if self._time_zone_checked:
            return self._time_zone
        self._time_zone_checked = True
        token = os.environ.get("SUPERVISOR_TOKEN", "")
        if not token:
            return None
        url = "http://supervisor/core/api/config"
        request = Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })
        try:
            with urlopen(request, timeout=self.config.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError):
            return None
        time_zone = payload.get("time_zone")
        if isinstance(time_zone, str) and time_zone.strip():
            self._time_zone = time_zone.strip()
        return self._time_zone

    def read_state(self, entity_id: str) -> dict[str, Any]:
        token = os.environ.get("SUPERVISOR_TOKEN", "")
        if not token:
            raise RuntimeError("SUPERVISOR_TOKEN is not available")
        url = f"http://supervisor/core/api/states/{quote(entity_id, safe='')}"
        request = Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })
        try:
            with urlopen(request, timeout=self.config.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"could not read {entity_id}: {exc}") from exc

    def call_service_response(self, domain: str, service: str, data: dict[str, Any]) -> dict[str, Any]:
        token = os.environ.get("SUPERVISOR_TOKEN", "")
        if not token:
            raise RuntimeError("SUPERVISOR_TOKEN is not available")
        url = f"http://supervisor/core/api/services/{quote(domain, safe='')}/{quote(service, safe='')}?return_response"
        request = Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.config.timeout) as response:
                return json.loads(response.read().decode("utf-8")).get("service_response", {})
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"could not call {domain}.{service}: {exc}") from exc


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _power_to_w(value: float | None, unit: Any) -> float | None:
    if value is None:
        return None
    unit_name = str(unit or "W").lower()
    if unit_name == "kw":
        return round(value * 1000.0, 3)
    return value


def _temperature_to_c(value: float, unit: Any) -> float:
    unit_name = str(unit or "C").upper()
    if "F" in unit_name:
        return (value - 32.0) * 5.0 / 9.0
    return value


def _running_state(value: Any) -> bool | None:
    text = str(value or "").strip().lower()
    if not text or text in {"unknown", "unavailable", "none"}:
        return None
    if text in {"on", "run", "running", "heat", "heating", "cool", "cooling", "active", "1", "true"}:
        return True
    if text in {"off", "stop", "stopped", "idle", "standby", "0", "false"}:
        return False
    return None


def _now_forecast_entry(current_weather: dict[str, Any] | None) -> dict[str, Any] | None:
    if not current_weather:
        return None
    temperature = _float_or_none(current_weather.get("temperature"))
    if temperature is None:
        return None
    entry: dict[str, Any] = {
        "datetime": datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "temperature": temperature,
        "condition": current_weather.get("state"),
        "source": "current_weather",
    }
    humidity = _float_or_none(current_weather.get("humidity"))
    if humidity is not None:
        entry["humidity"] = humidity
    return entry
