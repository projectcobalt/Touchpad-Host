from __future__ import annotations

import unittest

from airtouch4.service.adaptive import AdaptiveConfig, AdaptiveController
from airtouch4.service.adaptive_mpc import ZoneThermalModel


def ready_model() -> ZoneThermalModel:
    model = ZoneThermalModel(passive_samples=60, active_samples=20, learn=True)
    model.ekf.updates = 80
    model.ekf.idle_samples = 60
    model.ekf.cooling_samples = 20
    model.ekf.initialized = True
    model.ekf.p = [[0.0] * 6 for _ in range(6)]
    for index in range(6):
        model.ekf.p[index][index] = 0.001
    return model


def runtime_state(
    *,
    ac_setpoint: int = 22,
    zone_setpoint: int = 22,
    mode: int = 4,
    zone_temperature: float | None = None,
    sensor_control: bool = True,
    has_sensor: bool | None = None,
    zone_percentage: float | None = None,
) -> dict:
    zone_status = {"power_name": "on", "sensor_control": sensor_control, "setpoint": zone_setpoint}
    if has_sensor is not None:
        zone_status["has_sensor"] = has_sensor
    if zone_temperature is not None:
        zone_status["temperature"] = zone_temperature
    if zone_percentage is not None:
        zone_status["percentage"] = zone_percentage
    return {
        "state": {
            "acs": {
                0: {
                    "base": {"ac": 0, "name": "Home", "group_start": 0, "group_count": 2},
                    "settings": {"min_setpoint": 16, "max_setpoint": 30},
                    "status": {"power_on": True, "mode": mode, "setpoint": ac_setpoint},
                }
            },
            "active_groups": {
                0: {
                    "name": "Lounge",
                    "status": zone_status,
                },
                1: {
                    "name": "Spare",
                    "status": {"power_name": "off", "sensor_control": True, "setpoint": zone_setpoint},
                },
            },
            "groups": {},
        }
}


def multi_ac_runtime_state(*, ac_count: int = 2, setpoint: int = 24, mode: int = 4) -> dict:
    return {
        "state": {
            "acs": {
                ac_id: {
                    "base": {"ac": ac_id, "name": f"AC {ac_id + 1}", "group_start": ac_id, "group_count": 1},
                    "settings": {"min_setpoint": 16, "max_setpoint": 30},
                    "status": {"power_on": True, "mode": mode, "setpoint": setpoint},
                }
                for ac_id in range(ac_count)
            },
            "active_groups": {},
            "groups": {},
        }
    }


def overlapping_ac_runtime_state(*, setpoint: int = 24, mode: int = 4) -> dict:
    return {
        "state": {
            "acs": {
                ac_id: {
                    "base": {"ac": ac_id, "name": f"AC {ac_id + 1}", "group_start": 0, "group_count": 1},
                    "settings": {"min_setpoint": 16, "max_setpoint": 30},
                    "status": {"power_on": True, "mode": mode, "setpoint": setpoint},
                }
                for ac_id in range(2)
            },
            "active_groups": {},
            "groups": {},
        }
    }


def integrations(
    temp: float = 30.0,
    unit: str = "C",
    *,
    humidity: float | None = None,
    forecast: list[dict] | None = None,
    indoor_temp: float | None = None,
    indoor_humidity: float | None = None,
    solar: dict | None = None,
    solar_error: str | None = None,
    sun: dict | None = None,
) -> dict:
    weather = {"temperature": temp, "temperature_unit": unit}
    if humidity is not None:
        weather["humidity"] = humidity
    if forecast is not None:
        weather["forecast"] = forecast
    result = {"weather": {"state": weather}}
    indoor = {}
    if indoor_temp is not None:
        indoor["temperature"] = indoor_temp
        indoor["temperature_unit"] = "C"
    if indoor_humidity is not None:
        indoor["humidity"] = indoor_humidity
    if indoor:
        result["indoor"] = {"state": indoor}
    if solar is not None or solar_error is not None:
        result["solar"] = {"state": solar, "error": solar_error}
    if sun is not None:
        result["sun"] = {"state": sun}
    return result


class AdaptiveControllerTests(unittest.TestCase):
    def test_recommend_mode_reports_without_command(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="recommend"))

        specs = controller.evaluate(runtime_state(ac_setpoint=24), integrations(20), now=1.0)

        self.assertEqual(specs, [])
        self.assertTrue(controller.status()["recommendations"])

    def test_auto_off_mode_sends_power_off_when_weather_is_favourable(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="auto_off", command_cooldown=1))

        specs = controller.evaluate(runtime_state(ac_setpoint=24), integrations(20), now=1.0)

        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0].command, 0x22)
        self.assertEqual(specs[0].payload.hex(" ").upper(), "80 87 1F 00")

    def test_auto_off_mode_respects_configured_compressor_minimum_run_time(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(mode="auto_off", command_cooldown=1, compressor_min_run_time=600)
        )

        specs = controller.evaluate(runtime_state(ac_setpoint=24), integrations(20), now=1.0)

        self.assertEqual(specs, [])
        self.assertIn("compressor minimum run time", " ".join(controller.status()["recommendations"]))

    def test_shared_compressor_allows_member_off_when_another_member_keeps_running(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="auto_off",
                command_cooldown=1,
                compressor_min_run_time=600,
                compressor_groups=((0, 1),),
            )
        )

        specs = controller.evaluate(multi_ac_runtime_state(ac_count=2), integrations(20), now=1.0)

        self.assertEqual(len(specs), 1)
        self.assertIn("AC 2: Auto Off held by compressor minimum run time", controller.status()["recommendations"])
        compressor = controller.status()["learning"]["compressor"]["0"]
        self.assertEqual(compressor["acs"], [0, 1])
        self.assertTrue(compressor["power_on"])

    def test_shared_compressor_is_derived_from_overlapping_ac_zone_ranges(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(mode="auto_off", command_cooldown=1, compressor_min_run_time=600)
        )

        specs = controller.evaluate(overlapping_ac_runtime_state(), integrations(20), now=1.0)

        self.assertEqual(len(specs), 1)
        self.assertIn("AC 2: Auto Off held by compressor minimum run time", controller.status()["recommendations"])
        compressor = controller.status()["learning"]["compressor"]["0"]
        self.assertEqual(compressor["acs"], [0, 1])
        self.assertTrue(compressor["power_on"])

    def test_independent_compressors_each_respect_minimum_run_time(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(mode="auto_off", command_cooldown=1, compressor_min_run_time=600)
        )

        specs = controller.evaluate(multi_ac_runtime_state(ac_count=2), integrations(20), now=1.0)

        self.assertEqual(specs, [])
        compressor = controller.status()["learning"]["compressor"]
        self.assertEqual(sorted(item["acs"] for item in compressor.values()), [[0], [1]])

    def test_adaptive_mode_relaxes_ac_and_active_temp_zone_setpoints(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1, control_zones=(0,)))

        specs = controller.evaluate(runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20), integrations(30), now=1.0)

        self.assertEqual([spec.command for spec in specs], [0x22, 0x20])
        self.assertEqual(specs[0].payload.hex(" ").upper(), "00 87 14 00")
        self.assertEqual(specs[1].payload.hex(" ").upper(), "80 94 00 00")
        self.assertEqual(controller.status()["actions"], ["Home: Setpoint 24°", "Lounge: Setpoint 24°"])

    def test_legacy_learning_mode_is_background_learning_without_control_authority(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", learning_mode="learn", command_cooldown=1, control_zones=(0,)))
        controller._mpc.zone_models[0] = ZoneThermalModel(passive_samples=12, active_samples=12)

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20),
            integrations(30),
            now=1.0,
        )

        self.assertEqual(specs[0].payload.hex(" ").upper(), "00 87 14 00")
        self.assertIsNone(controller.status()["evaluations"][0].get("mpc"))
        self.assertIn("0", controller.status()["learning"]["zones"])
        self.assertEqual(controller.public_config()["learning_mode"], "off")
        self.assertFalse(controller.public_config()["learning_control"])

    def test_temp_enabled_zone_sets_learning_true_from_status(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1))

        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20, has_sensor=True),
            integrations(30),
            now=1.0,
        )

        zone = controller.status()["learning"]["zones"]["0"]
        self.assertTrue(zone["learn"])

    def test_learning_pauses_without_outdoor_temperature(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1))

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20, has_sensor=True),
            {"weather": {"state": {}}},
            now=1.0,
        )

        learning = controller.status()["learning"]
        zone = learning["zones"]["0"]
        self.assertEqual(specs, [])
        self.assertEqual(controller.status()["note"], "Outside temperature is not available")
        self.assertEqual(learning["learning_paused_reason"], "outside_temperature_unavailable")
        self.assertTrue(zone["learn"])
        self.assertEqual(zone["skipped_observations"], 1)
        self.assertEqual(zone["last_skip_reason"], "outside_temperature_unavailable")
        self.assertEqual(zone["passive_samples"], 0)
        self.assertEqual(zone["active_samples"], 0)
        self.assertEqual(zone["ekf_updates"], 0)

    def test_status_exposes_mode_specific_mpc_readiness(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1))
        controller._mpc.zone_models[0] = ready_model()

        zone = controller._mpc.status(now=1.0)["zones"]["0"]

        self.assertTrue(zone["cooling_ready"])
        self.assertFalse(zone["heating_ready"])
        self.assertEqual(zone["idle_observations"], 60)
        self.assertEqual(zone["cooling_observations"], 20)
        self.assertEqual(zone["heating_observations"], 0)

    def test_learning_mode_control_uses_mpc_proposal_through_adaptive_authority(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", learning_mode="control", command_cooldown=1, control_zones=(0,)))
        controller._mpc.zone_models[0] = ready_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20),
            integrations(30),
            now=1.0,
        )

        self.assertEqual([spec.command for spec in specs], [0x22, 0x20])
        self.assertEqual(specs[0].payload.hex(" ").upper(), "00 87 14 00")
        self.assertEqual(specs[1].payload.hex(" ").upper(), "80 94 00 00")
        self.assertEqual(controller.status()["evaluations"][0]["mpc"]["target"], 24)
        self.assertEqual(controller.status()["evaluations"][0]["mpc"]["source"], "mpc")

    def test_recommend_mode_reports_mpc_proposal_without_asserting_control(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="recommend", learning_mode="control", command_cooldown=1, control_zones=(0,)))
        controller._mpc.zone_models[0] = ready_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20),
            integrations(30),
            now=1.0,
        )

        self.assertEqual(specs, [])
        self.assertEqual(controller.status()["evaluations"][0]["mpc"]["target"], 24)
        self.assertEqual(controller.status()["evaluations"][0]["mpc"]["source"], "mpc")
        self.assertIn("projected_runtime_hours", controller.status()["evaluations"][0]["mpc"])
        self.assertIn("MPC recommends target 24", " ".join(controller.status()["recommendations"]))

    def test_recommend_mode_reports_hybrid_shadow_mpc_plan_without_commands(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="recommend",
                learning_mode="control",
                command_cooldown=1,
                control_zones=(0,),
                control_strategy="hybrid_damper_mpc",
                hybrid_idle_damper_percent=10,
            )
        )
        controller._mpc.zone_models[0] = ready_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20, sensor_control=False, zone_percentage=25),
            integrations(30),
            now=1.0,
        )

        self.assertEqual(specs, [])
        evaluation = controller.status()["evaluations"][0]
        self.assertEqual(evaluation["mpc"]["source"], "mpc")
        self.assertEqual(evaluation["mpc"]["target"], 24)
        self.assertEqual(evaluation["mpc"]["zone_power_fractions"], {"0": 0.0})
        self.assertIn("projected_runtime_hours", evaluation["mpc"])
        self.assertEqual(evaluation["hybrid"]["strategy"], "hybrid_damper_mpc")
        self.assertEqual(evaluation["hybrid"]["damper_percentages"], {"0": 10})
        self.assertFalse(evaluation["hybrid"]["touchpad_temperature_commanded"])
        self.assertIn("Hybrid shadow dampers Zone 1 10%", " / ".join(controller.status()["recommendations"]))

    def test_recommend_mode_reports_hybrid_shadow_while_models_warm(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="recommend",
                learning_mode="control",
                command_cooldown=1,
                control_zones=(0,),
                control_strategy="hybrid_damper_mpc",
            )
        )
        controller._mpc.zone_models[0] = ZoneThermalModel(passive_samples=3, active_samples=2, learn=True)

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20, sensor_control=False, zone_percentage=25),
            integrations(30),
            now=1.0,
        )

        self.assertEqual(specs, [])
        evaluation = controller.status()["evaluations"][0]
        self.assertEqual(evaluation["mpc"]["source"], "learning")
        self.assertEqual(evaluation["hybrid"]["damper_percentages"], {"0": 10})
        self.assertIn("MPC learning is warming up", " / ".join(controller.status()["recommendations"]))

    def test_recommend_mode_does_not_report_mpc_without_configured_control_zone(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="recommend", learning_mode="control", command_cooldown=1))
        controller._mpc.zone_models[0] = ready_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20),
            integrations(30),
            now=1.0,
        )

        self.assertEqual(specs, [])
        self.assertIsNone(controller.status()["evaluations"][0]["mpc"])

    def test_control_mode_does_not_assert_without_zone_control_flag(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", learning_mode="control", command_cooldown=1))
        controller._mpc.zone_models[0] = ready_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20, sensor_control=False),
            integrations(30),
            now=1.0,
        )

        self.assertEqual(specs, [])
        self.assertIn("0", controller.status()["learning"]["zones"])
        self.assertIsNone(controller.status()["evaluations"][0]["mpc"])

    def test_control_zone_flag_not_airtouch_sensor_control_allows_assertion(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(mode="adaptive", learning_mode="control", command_cooldown=1, control_zones=(0,))
        )
        controller._mpc.zone_models[0] = ready_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20, sensor_control=False),
            integrations(30),
            now=1.0,
        )

        self.assertEqual([spec.command for spec in specs], [0x22, 0x20])
        self.assertEqual(controller.status()["evaluations"][0]["mpc"]["target"], 24)
        self.assertEqual(controller.status()["evaluations"][0]["mpc"]["source"], "mpc")

    def test_hybrid_damper_strategy_uses_mpc_fraction_for_control_zone(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="adaptive",
                learning_mode="control",
                command_cooldown=1,
                control_zones=(0,),
                control_strategy="hybrid_damper_mpc",
                hybrid_idle_damper_percent=10,
            )
        )
        controller._mpc.zone_models[0] = ready_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20, sensor_control=False, zone_percentage=25),
            integrations(30),
            now=1.0,
        )

        self.assertEqual([spec.command for spec in specs], [0x22, 0x20])
        self.assertEqual(specs[0].payload.hex(" ").upper(), "00 87 14 00")
        self.assertEqual(specs[1].payload.hex(" ").upper(), "80 0A 00 00")
        evaluation = controller.status()["evaluations"][0]
        self.assertEqual(evaluation["mpc"]["source"], "mpc")
        self.assertEqual(evaluation["hybrid"]["strategy"], "hybrid_damper_mpc")
        self.assertEqual(evaluation["hybrid"]["damper_percentages"], {"0": 10})
        self.assertFalse(evaluation["hybrid"]["touchpad_temperature_commanded"])
        self.assertIn("control_temperature", evaluation["hybrid"])

    def test_hybrid_damper_strategy_restores_damper_when_disabled(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="adaptive",
                learning_mode="control",
                command_cooldown=1,
                control_zones=(0,),
                control_strategy="hybrid_damper_mpc",
                hybrid_idle_damper_percent=10,
            )
        )
        controller._mpc.zone_models[0] = ready_model()

        first = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20, sensor_control=False, zone_percentage=25),
            integrations(30),
            now=1.0,
        )
        controller.update_config({"mode": "off"})
        second = controller.evaluate(
            runtime_state(ac_setpoint=24, zone_setpoint=22, zone_temperature=20, sensor_control=False, zone_percentage=10),
            integrations(30),
            now=10.0,
        )

        self.assertEqual(first[-1].payload.hex(" ").upper(), "80 0A 00 00")
        self.assertEqual([spec.payload.hex(" ").upper() for spec in second], ["00 87 12 00", "80 19 00 00"])
        self.assertEqual(controller.status()["active_dampers"], [])

    def test_hybrid_damper_bounds_are_integer_percentages(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                control_strategy="hybrid_damper_mpc",
                hybrid_min_damper_percent=20,
                hybrid_max_damper_percent=80,
                hybrid_idle_damper_percent=5,
            )
        )

        self.assertEqual(controller.public_config()["hybrid_min_damper_percent"], 20)
        self.assertEqual(controller.public_config()["hybrid_max_damper_percent"], 80)
        self.assertEqual(controller.public_config()["hybrid_idle_damper_percent"], 5)
        with self.assertRaisesRegex(ValueError, "hybrid_max_damper_percent must be between 0 and 100"):
            AdaptiveController(AdaptiveConfig(control_strategy="hybrid_damper_mpc", hybrid_max_damper_percent=101))

    def test_control_strategy_save_overrides_stale_learning_mode(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", learning_mode="control", command_cooldown=1))

        public = controller.update_config({"control_strategy": "weather_setpoint"})

        self.assertEqual(public["control_strategy"], "weather_setpoint")
        self.assertEqual(public["learning_mode"], "off")

    def test_accelerated_learning_is_flag_not_confidence(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", learning_mode="control", command_cooldown=1, control_zones=(0,)))
        controller._mpc.zone_models[0] = ZoneThermalModel(passive_samples=3, active_samples=2, learn=True)
        controller.manage_learning({"action": "accelerate_zone", "zone": 0, "enabled": True})

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20),
            integrations(30),
            now=1.0,
        )

        zone = controller.status()["learning"]["zones"]["0"]
        self.assertTrue(zone["accelerated_learning"])
        self.assertLess(zone["confidence"], 0.35)
        self.assertFalse(zone["mpc_ready"])
        self.assertEqual(controller.status()["evaluations"][0]["mpc"]["source"], "learning")
        self.assertEqual(specs[0].payload.hex(" ").upper(), "00 87 14 00")

    def test_learning_observations_are_spaced_like_roommind(self) -> None:
        normal = ZoneThermalModel(learn=True)
        normal.observe(ts=0, temperature=22, active=False, cooling=True, outside_temperature=30)
        normal.observe(ts=2 * 60, temperature=22.1, active=False, cooling=True, outside_temperature=30)
        normal.observe(ts=3 * 60, temperature=22.2, active=False, cooling=True, outside_temperature=30)

        accelerated = ZoneThermalModel(learn=True, accelerated_learning=True)
        accelerated.observe(ts=0, temperature=22, active=False, cooling=True, outside_temperature=30)
        accelerated.observe(ts=3 * 60, temperature=22.1, active=False, cooling=True, outside_temperature=30)

        self.assertEqual(normal.passive_samples, 1)
        self.assertEqual(accelerated.passive_samples, 1)

    def test_learning_status_hours_match_three_minute_observations(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1))
        controller._mpc.zone_models[0] = ZoneThermalModel(passive_samples=60, active_samples=20)

        zone = controller._mpc.status(now=1.0)["zones"]["0"]

        self.assertEqual(zone["passive_hours"], 3.0)
        self.assertEqual(zone["active_hours"], 1.0)

    def test_boost_learning_has_cooldown(self) -> None:
        model = ZoneThermalModel(learn=True)

        first = model.boost_learning(now=100.0, cooldown_seconds=3600.0)
        boosted = model.ekf.p[0][0]
        second = model.boost_learning(now=200.0, cooldown_seconds=3600.0)

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(model.ekf.p[0][0], boosted)

    def test_learning_analytics_status_uses_ui_facing_temperature_names(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", learning_mode="control", command_cooldown=1, control_zones=(0,)))

        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20),
            integrations(30),
            now=1.0,
        )

        point = controller.status()["learning"]["analytics"]["0"][0]
        self.assertIn("temperature", point)
        self.assertIn("outdoor_temperature", point)
        self.assertNotIn("room_temp", point)
        self.assertNotIn("outdoor_temp", point)

    def test_learning_analytics_status_exposes_zone_forecast_points(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(mode="adaptive", learning_mode="control", command_cooldown=1, control_zones=(0,))
        )
        controller._mpc.zone_models[0] = ready_model()

        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=25),
            integrations(31, forecast=[{"temperature": 31}, {"temperature": 30}]),
            now=1.0,
        )

        forecast = controller.status()["learning"]["forecasts"]["0"]
        self.assertGreater(len(forecast), 1)
        self.assertIn("offset_minutes", forecast[0])
        self.assertIn("temperature", forecast[0])
        self.assertIn("outdoor_temperature", forecast[0])

    def test_adaptive_mode_uses_fahrenheit_weather_source(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1, control_zones=(0,)))

        specs = controller.evaluate(runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20), integrations(86, "°F"), now=1.0)

        self.assertEqual(len(specs), 2)

    def test_repeated_adaptive_command_is_cooled_down(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", check_interval=5, command_cooldown=300, control_zones=(0,)))

        first = controller.evaluate(runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20), integrations(30), now=1.0)
        second = controller.evaluate(runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20), integrations(30), now=10.0)

        self.assertTrue(first)
        self.assertEqual(second, [])

    def test_adaptive_mode_holds_when_indoor_temperature_is_uncomfortable(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1, control_zones=(0,)))

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=27),
            integrations(30),
            now=1.0,
        )

        self.assertEqual(specs, [])
        self.assertFalse(controller.status()["evaluations"][0]["relaxation_allowed"])

    def test_humidity_compensation_is_optional_and_tightens_cooling_target(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1, control_zones=(0,)))

        specs = controller.evaluate(
            runtime_state(ac_setpoint=21, zone_setpoint=21, zone_temperature=20),
            integrations(30, indoor_humidity=70),
            now=1.0,
        )

        self.assertEqual([spec.command for spec in specs], [0x22, 0x20])
        self.assertEqual(specs[0].payload.hex(" ").upper(), "00 87 12 00")
        self.assertEqual(specs[1].payload.hex(" ").upper(), "80 92 00 00")

    def test_forecast_can_arrive_from_separate_integration_pipe(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1, control_zones=(0,)))

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22),
            {
                "weather": {"state": {"temperature": 30, "temperature_unit": "C"}},
                "forecast": {"state": {"hourly": [{"temperature": 25}, {"temperature": 26}]}},
            },
            now=1.0,
        )

        self.assertEqual(specs, [])
        self.assertEqual(controller.status()["forecast_temperatures"], [25, 26])

    def test_solar_irradiance_watts_is_normalized_and_recorded(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1, control_zones=(0,)))

        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20, has_sensor=True),
            integrations(30, solar={"irradiance": 640, "irradiance_unit": "W/m2"}),
            now=1.0,
        )

        status = controller.status()
        point = status["learning"]["analytics"]["0"][0]
        self.assertEqual(status["solar"]["source"], "ha_irradiance")
        self.assertAlmostEqual(status["solar"]["q_solar"], 0.64)
        self.assertEqual(point["q_solar"], 0.64)

    def test_solar_irradiance_kw_is_normalized(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1))

        controller.evaluate(
            runtime_state(zone_temperature=20, has_sensor=True),
            integrations(30, solar={"irradiance": 0.72, "irradiance_unit": "kW/m2"}),
            now=1.0,
        )

        self.assertAlmostEqual(controller.status()["solar"]["q_solar"], 0.72)
        self.assertEqual(controller.status()["solar"]["irradiance_w_m2"], 720.0)

    def test_solar_cloud_cover_is_diagnostic_and_error_surface(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1))

        controller.evaluate(
            runtime_state(zone_temperature=20, has_sensor=True),
            integrations(30, solar={"cloud_cover": 25}, solar_error="RuntimeError: could not read sensor.solar"),
            now=1.0,
        )

        status = controller.status()
        self.assertEqual(status["solar"]["source"], "cloud_cover_diagnostic")
        self.assertEqual(status["solar"]["q_solar"], 0.0)
        self.assertEqual(status["solar"]["cloud_cover"], 25)
        self.assertIn("Solar: RuntimeError: could not read sensor.solar", status["errors"])

    def test_solar_cloud_cover_uses_sun_elevation_when_available(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1))

        controller.evaluate(
            runtime_state(zone_temperature=20, has_sensor=True),
            integrations(30, solar={"cloud_cover": 25}, sun={"elevation": 30}),
            now=1.0,
        )

        status = controller.status()
        self.assertEqual(status["solar"]["source"], "sun_cloud_cover")
        self.assertAlmostEqual(status["solar"]["q_solar"], 0.375)
        self.assertEqual(status["solar"]["sun_elevation"], 30)

    def test_solar_cloud_cover_is_zero_when_sun_is_below_horizon(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1))

        controller.evaluate(
            runtime_state(zone_temperature=20, has_sensor=True),
            integrations(30, solar={"cloud_cover": 0}, sun={"elevation": -8}),
            now=1.0,
        )

        status = controller.status()
        self.assertEqual(status["solar"]["source"], "sun_cloud_cover")
        self.assertEqual(status["solar"]["q_solar"], 0.0)

    def test_no_solar_source_falls_back_to_zero(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1))

        controller.evaluate(runtime_state(zone_temperature=20, has_sensor=True), integrations(30), now=1.0)

        self.assertEqual(controller.status()["solar"]["source"], "none")
        self.assertEqual(controller.status()["solar"]["q_solar"], 0.0)

    def test_power_fraction_estimate_is_diagnostic_not_ekf_scaling(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1))

        controller.evaluate(
            runtime_state(zone_temperature=20, has_sensor=True, zone_percentage=25),
            integrations(30),
            now=1.0,
        )

        zone = controller.status()["learning"]["zones"]["0"]
        point = controller.status()["learning"]["analytics"]["0"][0]
        self.assertEqual(point["estimated_power_fraction"], 1.0)
        self.assertEqual(zone["active_response_per_hour"], 0.0)

    def test_mode_specific_readiness_reason_names_missing_mode_samples(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1))
        controller._mpc.zone_models[0] = ready_model()

        zone = controller._mpc.status(now=1.0)["zones"]["0"]

        self.assertEqual(zone["heating_readiness_reason"], "heating_samples")
        self.assertEqual(zone["cooling_readiness_reason"], "ready")


if __name__ == "__main__":
    unittest.main()
