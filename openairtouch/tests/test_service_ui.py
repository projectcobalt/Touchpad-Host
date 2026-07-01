import unittest

from airtouch4.service.ui import INDEX_HTML


class ServiceUiTests(unittest.TestCase):
    def test_adaptive_ui_exposes_control_strategy(self) -> None:
        for fragment in (
            'id="adaptive-control-strategy"',
            '<option value="weather">Environment</option>',
            '<option value="zone">Zone</option>',
            '<option value="hybrid">Hybrid</option>',
            'control_strategy: $("adaptive-control-strategy").value',
            'setValue("adaptive-control-strategy", current.control_strategy || "weather")',
            'metric("Strategy", strategyText)',
            'function strategyLabel(value)',
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, INDEX_HTML)

    def test_adaptive_ui_exposes_air_quality_thresholds(self) -> None:
        for fragment in (
            'id="adaptive-dry-humidity-threshold"',
            'id="adaptive-co2-ventilation-threshold"',
            'setValue("adaptive-dry-humidity-threshold", current.dry_humidity_threshold ?? 70)',
            'setValue("adaptive-co2-ventilation-threshold", current.co2_ventilation_threshold_ppm ?? 1000)',
            'dry_humidity_threshold: Number($("adaptive-dry-humidity-threshold").value)',
            'co2_ventilation_threshold_ppm: Number($("adaptive-co2-ventilation-threshold").value)',
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, INDEX_HTML)

    def test_adaptive_ui_exposes_outside_air_zone_picker(self) -> None:
        for fragment in (
            "Outside Air Zones",
            'id="adaptive-outside-air-zones"',
            "data-adaptive-outside-air-zone",
            "outside_air_zones: Array.from(document.querySelectorAll(\"[data-adaptive-outside-air-zone]\"))",
            'metric("Outside Air Zones", `${outsideAirZones.size} Selected`)',
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, INDEX_HTML)

    def test_adaptive_ui_does_not_offer_legacy_learning_mode_selector(self) -> None:
        self.assertNotIn('id="adaptive-mpc-control"', INDEX_HTML)
        self.assertNotIn('learning_mode: $("adaptive-mpc-control").value', INDEX_HTML)

    def test_adaptive_ui_surfaces_projected_runtime(self) -> None:
        self.assertIn("projected_runtime_hours", INDEX_HTML)
        self.assertIn("planRunText", INDEX_HTML)
        self.assertIn("Run 0h", INDEX_HTML)

    def test_ui_uses_websocket_live_updates_with_slow_poll_fallback(self) -> None:
        for fragment in (
            "function wsPath()",
            "new WebSocket(wsPath())",
            "handleLiveMessage(JSON.parse(event.data))",
            'message.type === "events"',
            "if (!liveSocketConnected) refresh();",
            "setInterval(() => refresh(), 30000);",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, INDEX_HTML)

        self.assertNotIn("setInterval(() => refresh(), 1500);", INDEX_HTML)

    def test_spill_config_checkbox_uses_saved_config_not_live_open_state(self) -> None:
        self.assertIn("const configured = !!group.spill_configured;", INDEX_HTML)
        self.assertIn('const spillState = status.spill_on ? "Open" : (configured ? "Configured" : "Live");', INDEX_HTML)
        self.assertNotIn("const configured = group.spill_configured || status.spill_on;", INDEX_HTML)

    def test_damper_mode_sensor_zone_can_resume_temp_control(self) -> None:
        self.assertIn("const resumeTempControlButton = !sensorControl && status.has_sensor === true", INDEX_HTML)
        self.assertIn('data-action="group-setpoint"', INDEX_HTML)
        self.assertIn('>Temp</button>', INDEX_HTML)


if __name__ == "__main__":
    unittest.main()
