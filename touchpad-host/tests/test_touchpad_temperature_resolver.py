from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.resolve_touchpad_temperature import heartbeat_payload_for_temperature, resolve_payload


class TouchpadTemperatureResolverTests(unittest.TestCase):
    def test_encodes_fallback_temperature(self) -> None:
        payload, source = resolve_payload(sensor="", fallback=25.0, raw_payload="")

        self.assertEqual(payload, "00 8C 00")
        self.assertEqual(source, "fallback=25")

    def test_raw_payload_override_wins(self) -> None:
        payload, source = resolve_payload(sensor="sensor.room", fallback=25.0, raw_payload="00 EA 00")

        self.assertEqual(payload, "00 EA 00")
        self.assertEqual(source, "raw override")

    def test_sensor_value_is_used_when_available(self) -> None:
        with patch("scripts.resolve_touchpad_temperature.read_sensor_state", return_value=23.0):
            payload, source = resolve_payload(sensor="sensor.room", fallback=25.0, raw_payload="")

        self.assertEqual(payload, "00 78 00")
        self.assertEqual(source, "sensor.room=23")

    def test_sensor_failure_falls_back(self) -> None:
        with patch("scripts.resolve_touchpad_temperature.read_sensor_state", side_effect=RuntimeError("missing")):
            payload, source = resolve_payload(sensor="sensor.room", fallback=30.0, raw_payload="")

        self.assertEqual(payload, "00 BE 00")
        self.assertEqual(source, "fallback=30")

    def test_direct_encoder_examples(self) -> None:
        self.assertEqual(heartbeat_payload_for_temperature(37), "00 EA 00")


if __name__ == "__main__":
    unittest.main()
