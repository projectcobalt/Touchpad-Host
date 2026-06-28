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


if __name__ == "__main__":
    unittest.main()
