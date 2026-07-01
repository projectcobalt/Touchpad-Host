from __future__ import annotations

import json
import os
import unittest
from datetime import datetime
from unittest.mock import patch

from airtouch4.service.ha_client import HomeAssistantApiClient, HomeAssistantApiConfig, _now_forecast_entry


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class HomeAssistantApiClientTests(unittest.TestCase):
    def test_current_weather_forecast_anchor_uses_aware_now(self) -> None:
        before = datetime.now().astimezone()

        entry = _now_forecast_entry({"temperature": 19.3, "state": "partlycloudy", "humidity": 60})

        self.assertIsNotNone(entry)
        assert entry is not None
        parsed = datetime.fromisoformat(entry["datetime"])
        self.assertIsNotNone(parsed.tzinfo)
        self.assertLess(abs((parsed - before).total_seconds()), 5)
        self.assertEqual(entry["source"], "current_weather")
        self.assertEqual(entry["temperature"], 19.3)
        self.assertEqual(entry["humidity"], 60.0)

    @patch.dict(os.environ, {"SUPERVISOR_TOKEN": "test-token"})
    @patch("airtouch4.service.ha_client.urlopen")
    def test_home_assistant_timezone_is_cached(self, urlopen_mock) -> None:
        urlopen_mock.return_value = FakeResponse({"time_zone": "Australia/Brisbane"})
        client = HomeAssistantApiClient(HomeAssistantApiConfig())

        self.assertEqual(client.home_assistant_timezone(), "Australia/Brisbane")
        self.assertEqual(client.home_assistant_timezone(), "Australia/Brisbane")

        self.assertEqual(urlopen_mock.call_count, 1)

    @patch.dict(os.environ, {"SUPERVISOR_TOKEN": "test-token"})
    @patch("airtouch4.service.ha_client.urlopen")
    def test_ac_telemetry_snapshot_normalizes_optional_entities(self, urlopen_mock) -> None:
        urlopen_mock.side_effect = [
            FakeResponse({"state": "1.2", "attributes": {"unit_of_measurement": "kW", "friendly_name": "AC Power"}}),
            FakeResponse({"state": "On", "attributes": {"friendly_name": "Compressor Status"}}),
            FakeResponse({"state": "42", "attributes": {"unit_of_measurement": "Hz", "friendly_name": "Run Frequency"}}),
            FakeResponse({"state": "75.2", "attributes": {"unit_of_measurement": "°F", "friendly_name": "Return Air"}}),
            FakeResponse({"state": "12", "attributes": {"unit_of_measurement": "°C", "friendly_name": "Supply Air"}}),
        ]
        client = HomeAssistantApiClient(
            HomeAssistantApiConfig(
                ac_power_entity="sensor.ac_power",
                ac_running_entity="sensor.ac_running",
                ac_frequency_entity="sensor.ac_frequency",
                ac_return_air_temp_entity="sensor.return_air",
                ac_supply_air_temp_entity="sensor.supply_air",
            )
        )

        snapshot = client.ac_telemetry_snapshot()

        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot["power_w"], 1200)
        self.assertTrue(snapshot["running"])
        self.assertEqual(snapshot["frequency_hz"], 42)
        self.assertAlmostEqual(snapshot["return_air_temperature_c"], 24.0, places=1)
        self.assertEqual(snapshot["supply_air_temperature_c"], 12)
        self.assertAlmostEqual(snapshot["supply_return_delta_c"], -12.0, places=1)
        self.assertIn("electrical_power", snapshot["evidence"])
        self.assertIn("supply_air_temperature", snapshot["evidence"])

    @patch.dict(os.environ, {"SUPERVISOR_TOKEN": "test-token"})
    @patch("airtouch4.service.ha_client.urlopen")
    def test_indoor_snapshot_includes_optional_co2_entity(self, urlopen_mock) -> None:
        urlopen_mock.side_effect = [
            FakeResponse({"state": "22.4", "attributes": {"unit_of_measurement": "Â°C", "friendly_name": "Indoor Temp"}}),
            FakeResponse({"state": "51", "attributes": {"unit_of_measurement": "%", "friendly_name": "Indoor Humidity"}}),
            FakeResponse({"state": "1180", "attributes": {"unit_of_measurement": "ppm", "friendly_name": "Indoor CO2"}}),
        ]
        client = HomeAssistantApiClient(
            HomeAssistantApiConfig(
                indoor_temperature_entity="sensor.indoor_temp",
                indoor_humidity_entity="sensor.indoor_humidity",
                indoor_co2_entity="sensor.indoor_co2",
            )
        )

        snapshot = client.indoor_snapshot()

        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot["temperature"], 22.4)
        self.assertEqual(snapshot["humidity"], 51)
        self.assertEqual(snapshot["co2_ppm"], 1180)
        self.assertEqual(snapshot["co2_unit"], "ppm")
        self.assertEqual(snapshot["co2_name"], "Indoor CO2")


if __name__ == "__main__":
    unittest.main()
