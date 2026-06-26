import unittest

from airtouch4.service.ui import INDEX_HTML


class ServiceUiTests(unittest.TestCase):
    def test_adaptive_ui_exposes_control_strategy(self) -> None:
        for fragment in (
            'id="adaptive-control-strategy"',
            '<option value="weather_setpoint">Weather Setpoint</option>',
            '<option value="mpc_setpoint">MPC Setpoint</option>',
            '<option value="hybrid_damper_mpc">Hybrid Damper MPC</option>',
            'control_strategy: $("adaptive-control-strategy").value',
            'setValue("adaptive-control-strategy", current.control_strategy || "weather_setpoint")',
            'metric("Strategy", strategyText)',
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


if __name__ == "__main__":
    unittest.main()