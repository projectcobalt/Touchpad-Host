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
    solar_irradiance_entity: str = ""
    cloud_cover_entity: str = ""
    timeout: float = 3.0


class HomeAssistantApiClient:
    def __init__(self, config: HomeAssistantApiConfig) -> None:
        self.config = config

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
        if not temperature_entity and not humidity_entity:
            return None

        snapshot: dict[str, Any] = {
            "temperature_entity_id": temperature_entity,
            "humidity_entity_id": humidity_entity,
            "temperature": None,
            "humidity": None,
            "temperature_unit": "C",
            "humidity_unit": "%",
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
        return {
            "entity_id": entity_id,
            "type": "hourly",
            "forecast": forecast,
            "prepended_current": now_entry is not None,
        }

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


def _now_forecast_entry(current_weather: dict[str, Any] | None) -> dict[str, Any] | None:
    if not current_weather:
        return None
    temperature = _float_or_none(current_weather.get("temperature"))
    if temperature is None:
        return None
    entry: dict[str, Any] = {
        "datetime": datetime.now().replace(minute=0, second=0, microsecond=0).isoformat(),
        "temperature": temperature,
        "condition": current_weather.get("state"),
        "source": "current_weather",
    }
    humidity = _float_or_none(current_weather.get("humidity"))
    if humidity is not None:
        entry["humidity"] = humidity
    return entry
