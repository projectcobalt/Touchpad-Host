from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from airtouch4.service.adaptive import AdaptiveConfig, AdaptiveController
from airtouch4.service.adaptive_model import AdaptiveDevice, AdaptiveRoom, AdaptiveSnapshot
from airtouch4.service.adaptive_mpc import AdaptiveMpcEngine, MpcInputs, ZoneThermalModel


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


def ready_heating_model() -> ZoneThermalModel:
    model = ready_model()
    model.ekf.heating_samples = 20
    model.ekf.cooling_samples = 0
    return model


def runtime_state(
    *,
    ac_setpoint: int = 22,
    zone_setpoint: int = 22,
    mode: int = 4,
    power_on: bool = True,
    zone_power_name: str = "on",
    zone_temperature: float | None = None,
    sensor_control: bool = True,
    has_sensor: bool | None = None,
    zone_percentage: float | None = None,
    ctrl_thermostat: int = 0,
) -> dict:
    zone_status = {"power_name": zone_power_name, "sensor_control": sensor_control, "setpoint": zone_setpoint}
    if has_sensor is not None:
        zone_status["has_sensor"] = has_sensor
    if zone_temperature is not None:
        zone_status["temperature"] = zone_temperature
    if zone_percentage is not None:
        zone_status["percentage"] = zone_percentage
    return {
        "runtime": {
            "active": True,
            "connected": True,
            "boot_complete": True,
            "address_assigned": True,
            "protocol_mismatch": False,
        },
        "state": {
            "acs": {
                0: {
                    "base": {"ac": 0, "name": "Home", "group_start": 0, "group_count": 2},
                    "settings": {"min_setpoint": 16, "max_setpoint": 30, "ctrl_thermostat": ctrl_thermostat},
                    "status": {"power_on": power_on, "mode": mode, "setpoint": ac_setpoint},
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
        "runtime": {
            "active": True,
            "connected": True,
            "boot_complete": True,
            "address_assigned": True,
            "protocol_mismatch": False,
        },
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
        "runtime": {
            "active": True,
            "connected": True,
            "boot_complete": True,
            "address_assigned": True,
            "protocol_mismatch": False,
        },
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
    forecast_time_zone: str | None = None,
    indoor_temp: float | None = None,
    indoor_humidity: float | None = None,
    indoor_co2: float | None = None,
    solar: dict | None = None,
    solar_error: str | None = None,
    ac_telemetry: dict | None = None,
    ac_telemetry_error: str | None = None,
    sun: dict | None = None,
) -> dict:
    weather = {"temperature": temp, "temperature_unit": unit}
    if humidity is not None:
        weather["humidity"] = humidity
    if forecast is not None:
        if forecast_time_zone is None:
            weather["forecast"] = forecast
        else:
            result_forecast = {"forecast": forecast, "time_zone": forecast_time_zone}
    result = {"weather": {"state": weather}}
    if forecast is not None and forecast_time_zone is not None:
        result["forecast"] = {"state": result_forecast}
    indoor = {}
    if indoor_temp is not None:
        indoor["temperature"] = indoor_temp
        indoor["temperature_unit"] = "C"
    if indoor_humidity is not None:
        indoor["humidity"] = indoor_humidity
    if indoor_co2 is not None:
        indoor["co2_ppm"] = indoor_co2
    if indoor:
        result["indoor"] = {"state": indoor}
    if solar is not None or solar_error is not None:
        result["solar"] = {"state": solar, "error": solar_error}
    if ac_telemetry is not None or ac_telemetry_error is not None:
        result["ac_telemetry"] = {"state": ac_telemetry, "error": ac_telemetry_error}
    if sun is not None:
        result["sun"] = {"state": sun}
    return result


def _mpc_snapshot(*, power_fraction: float, temperature: float) -> AdaptiveSnapshot:
    return AdaptiveSnapshot(
        devices=(
            AdaptiveDevice(
                ac_id=0,
                name="Home",
                mode=4,
                power_on=True,
                setpoint=22,
                min_setpoint=16,
                max_setpoint=30,
                rooms=(
                    AdaptiveRoom(
                        id=0,
                        name="Lounge",
                        ac_id=0,
                        temperature=temperature,
                        setpoint=22,
                        active=True,
                        learn=True,
                        configured_control=False,
                        control_enabled=False,
                        power_fraction=power_fraction,
                    ),
                ),
            ),
        )
    )


class AdaptiveControllerTests(unittest.TestCase):
    def test_recommend_mode_reports_without_command(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="recommend"))

        specs = controller.evaluate(runtime_state(ac_setpoint=24), integrations(20), now=1.0)

        self.assertEqual(specs, [])
        self.assertTrue(controller.status()["recommendations"])

    def test_weather_strategy_sends_power_off_when_weather_is_favourable_in_adaptive_mode(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="weather", check_interval=5, command_cooldown=1))

        specs = controller.evaluate(runtime_state(ac_setpoint=24), integrations(20), now=1.0)

        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0].command, 0x22)
        self.assertEqual(specs[0].payload.hex(" ").upper(), "80 87 1F 00")
        self.assertIn("ac:0", controller.export_weather_state()["suspensions"])
        self.assertTrue(controller.status()["evaluations"][0]["weather_intent"]["pause_active"])

    def test_weather_strategy_resumes_from_own_suspension_when_outside_stops_helping(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="weather", check_interval=5, command_cooldown=1))

        first = controller.evaluate(runtime_state(ac_setpoint=24), integrations(20), now=1.0)
        second = controller.evaluate(runtime_state(ac_setpoint=24, power_on=False), integrations(28), now=10.0)

        self.assertEqual(first[0].payload.hex(" ").upper(), "80 87 1F 00")
        self.assertEqual([spec.payload.hex(" ").upper() for spec in second], ["C0 87 1F 00"])
        self.assertEqual(controller.export_weather_state(), {"suspensions": {}})
        self.assertEqual(controller.status()["evaluations"][0]["weather_intent"]["intent"], "resume")

    def test_weather_resume_is_cancelled_when_all_zones_are_off(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="weather", check_interval=5, command_cooldown=1))

        controller.evaluate(runtime_state(ac_setpoint=24), integrations(20), now=1.0)
        specs = controller.evaluate(
            runtime_state(ac_setpoint=24, power_on=False, zone_power_name="off", zone_temperature=22),
            integrations(28),
            now=10.0,
        )

        self.assertEqual(specs, [])
        self.assertEqual(controller.export_weather_state(), {"suspensions": {}})
        self.assertEqual(controller.status()["evaluations"][0]["weather_intent"]["cancelled_reason"], "no_active_zones")

    def test_weather_strategy_respects_configured_compressor_minimum_run_time(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(mode="adaptive", control_strategy="weather", command_cooldown=1, compressor_min_run_time=600)
        )

        specs = controller.evaluate(runtime_state(ac_setpoint=24), integrations(20), now=1.0)

        self.assertEqual(specs, [])
        self.assertIn("Weather Off Held By Compressor Minimum Run Time", " ".join(controller.status()["recommendations"]))

    def test_shared_compressor_allows_member_off_when_another_member_keeps_running(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="adaptive",
                control_strategy="weather",
                command_cooldown=1,
                compressor_min_run_time=600,
                compressor_groups=((0, 1),),
            )
        )

        specs = controller.evaluate(multi_ac_runtime_state(ac_count=2), integrations(20), now=1.0)

        self.assertEqual(len(specs), 1)
        self.assertIn("AC 2: Weather Off Held By Compressor Minimum Run Time", controller.status()["recommendations"])
        compressor = controller.status()["learning"]["compressor"]["0"]
        self.assertEqual(compressor["acs"], [0, 1])
        self.assertTrue(compressor["power_on"])

    def test_shared_compressor_is_derived_from_overlapping_ac_zone_ranges(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(mode="adaptive", control_strategy="weather", command_cooldown=1, compressor_min_run_time=600)
        )

        specs = controller.evaluate(overlapping_ac_runtime_state(), integrations(20), now=1.0)

        self.assertEqual(len(specs), 1)
        self.assertIn("AC 2: Weather Off Held By Compressor Minimum Run Time", controller.status()["recommendations"])
        compressor = controller.status()["learning"]["compressor"]["0"]
        self.assertEqual(compressor["acs"], [0, 1])
        self.assertTrue(compressor["power_on"])

    def test_independent_compressors_each_respect_minimum_run_time(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(mode="adaptive", control_strategy="weather", command_cooldown=1, compressor_min_run_time=600)
        )

        specs = controller.evaluate(multi_ac_runtime_state(ac_count=2), integrations(20), now=1.0)

        self.assertEqual(specs, [])
        compressor = controller.status()["learning"]["compressor"]
        self.assertEqual(sorted(item["acs"] for item in compressor.values()), [[0], [1]])

    def test_zone_strategy_sets_ac_to_room_target_when_below_room_setpoint(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="zone", command_cooldown=1, control_zones=(0,)))

        specs = controller.evaluate(runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=20), integrations(30), now=1.0)

        self.assertEqual([spec.command for spec in specs], [0x22, 0x22])
        self.assertEqual(specs[0].payload.hex(" ").upper(), "00 17 1F 00")
        self.assertEqual(specs[1].payload.hex(" ").upper(), "00 87 12 00")
        self.assertEqual(controller.status()["evaluations"][0]["target"], 22)
        self.assertEqual(controller.status()["actions"], ["Home: Mode Changed: Heat", "Home: Setpoint Changed: 22 C"])

    def test_restore_state_records_only_when_target_differs_and_persists(self) -> None:
        unchanged_controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="zone", command_cooldown=1, control_zones=(0,)))

        unchanged = unchanged_controller.evaluate(runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=25), integrations(30), now=1.0)

        self.assertEqual(unchanged, [])
        self.assertEqual(unchanged_controller.export_restore_state(), {"records": {}})

        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="zone", command_cooldown=1, control_zones=(0,)))
        changed = controller.evaluate(runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=25), integrations(30), now=1.0)
        restore_state = controller.export_restore_state()

        self.assertEqual([spec.payload.hex(" ").upper() for spec in changed], ["00 87 12 00"])
        self.assertEqual(restore_state["records"]["ac:0:setpoint"]["original"], {"ac": 0, "setpoint": 20})
        self.assertEqual(restore_state["records"]["ac:0:setpoint"]["target"], {"ac": 0, "setpoint": 22})

        reloaded = AdaptiveController(AdaptiveConfig(mode="off", control_strategy="zone", command_cooldown=1, control_zones=(0,)))
        reloaded.import_learning(controller.export_learning())

        self.assertEqual(reloaded.export_restore_state(), restore_state)

    def test_restore_state_restores_after_restart_when_target_is_still_active(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="zone", command_cooldown=1, control_zones=(0,)))
        controller.evaluate(runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=25), integrations(30), now=1.0)

        reloaded = AdaptiveController(AdaptiveConfig(mode="off", control_strategy="zone", command_cooldown=1, control_zones=(0,)))
        reloaded.import_learning(controller.export_learning())
        specs = reloaded.evaluate(runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=25), integrations(30), now=10.0)

        self.assertEqual([spec.payload.hex(" ").upper() for spec in specs], ["00 87 10 00"])
        self.assertEqual(reloaded.export_restore_state(), {"records": {}})

    def test_runtime_must_be_connected_before_adaptive_commands_or_restore(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="zone", command_cooldown=1, control_zones=(0,)))
        controller.evaluate(runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=25), integrations(30), now=1.0)

        disconnected = runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=25)
        disconnected["runtime"]["connected"] = False
        specs = controller.evaluate(disconnected, integrations(30), now=10.0)

        self.assertEqual(specs, [])
        self.assertEqual(controller.status()["note"], "Runtime Is Not Connected To The Mainboard")
        self.assertFalse(controller.status()["runtime_control"]["connected"])
        self.assertIn("ac:0:setpoint", controller.export_restore_state()["records"])

    def test_invalid_learning_mode_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "adaptive learning mode"):
            AdaptiveController(AdaptiveConfig(mode="adaptive", learning_mode="learn", command_cooldown=1, control_zones=(0,)))

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

    def test_zone_strategy_uses_mpc_proposal_through_adaptive_authority(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(mode="adaptive", control_strategy="zone", command_cooldown=1, control_zones=(0,))
        )
        controller._mpc.zone_models[0] = ready_heating_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=20),
            integrations(30),
            now=1.0,
        )

        self.assertEqual([spec.command for spec in specs], [0x22, 0x22])
        self.assertEqual(specs[0].payload.hex(" ").upper(), "00 17 1F 00")
        self.assertEqual(specs[1].payload.hex(" ").upper(), "00 87 12 00")
        self.assertEqual(controller.status()["evaluations"][0]["target"], 22)
        self.assertEqual(controller.status()["evaluations"][0]["mpc"]["target"], 22)
        self.assertEqual(controller.status()["evaluations"][0]["mpc"]["source"], "zone")

    def test_recommend_mode_reports_mpc_proposal_without_asserting_control(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(mode="recommend", control_strategy="zone", command_cooldown=1, control_zones=(0,))
        )
        controller._mpc.zone_models[0] = ready_heating_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20),
            integrations(30),
            now=1.0,
        )

        self.assertEqual(specs, [])
        self.assertEqual(controller.status()["evaluations"][0]["mpc"]["target"], 22)
        self.assertEqual(controller.status()["evaluations"][0]["mpc"]["source"], "zone")
        self.assertIn("projected_runtime_hours", controller.status()["evaluations"][0]["mpc"])
        status = controller.status()
        self.assertIn("Recommended Target: 22 C", " ".join(status["recommendations"]))
        self.assertEqual(status["intents"][0]["headline"], "Heating Expected")
        self.assertEqual(status["intents"][0]["summary"], "Recommended Target: 22 C / Expected Runtime: 0.3 H")

    def test_weather_strategy_reports_open_windows_intent_without_setpoint_target(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="recommend", control_strategy="weather", command_cooldown=1))

        specs = controller.evaluate(
            runtime_state(ac_setpoint=24, zone_setpoint=24, zone_temperature=23.5),
            integrations(20, forecast=[{"temperature": 20}, {"temperature": 21}]),
            now=1.0,
        )

        self.assertEqual(specs, [])
        evaluation = controller.status()["evaluations"][0]
        opportunity = evaluation["weather_opportunity"]
        self.assertIsNone(evaluation["target"])
        self.assertIsNone(evaluation["forecast_target"])
        self.assertIsNone(evaluation["mpc"])
        self.assertTrue(opportunity["outside_favourable"])
        self.assertTrue(opportunity["recommend_off"])
        self.assertTrue(opportunity["open_windows_intent"])
        status = controller.status()
        self.assertIn("Open Windows Recommended", " / ".join(status["recommendations"]))
        self.assertEqual(status["intents"][0]["headline"], "Open Windows Recommended")
        self.assertEqual(status["intents"][0]["intent"], "ventilate")

    def test_zone_strategy_uses_room_setpoint_not_weather_target(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="recommend",
                control_strategy="zone",
                command_cooldown=1,
                control_zones=(0,),
            )
        )
        controller._mpc.zone_models[0] = ready_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=24, zone_setpoint=22, zone_temperature=25),
            integrations(31, forecast=[{"temperature": 31}, {"temperature": 30}]),
            now=1.0,
        )

        self.assertEqual(specs, [])
        evaluation = controller.status()["evaluations"][0]
        self.assertEqual(evaluation["target"], 22)
        self.assertIsNone(evaluation["forecast_target"])
        self.assertFalse(evaluation["weather_opportunity"]["outside_favourable"])
        self.assertEqual(evaluation["mpc"]["target"], 22)
        self.assertEqual(evaluation["mpc"]["source"], "zone")
        self.assertEqual(evaluation["mpc"]["runtime_forecast"]["series"][0]["outside_temperature"], 31)

    def test_recommend_mode_reports_hybrid_shadow_mpc_plan_without_commands(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="recommend",
                learning_mode="control",
                command_cooldown=1,
                control_zones=(0,),
                control_strategy="hybrid",
                hybrid_idle_damper_percent=10,
            )
        )
        controller._mpc.zone_models[0] = ready_heating_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20, sensor_control=False, zone_percentage=25),
            integrations(30),
            now=1.0,
        )

        self.assertEqual(specs, [])
        evaluation = controller.status()["evaluations"][0]
        self.assertEqual(evaluation["mpc"]["source"], "zone")
        self.assertEqual(evaluation["mpc"]["target"], 22)
        self.assertEqual(evaluation["mpc"]["zone_power_fractions"], {"0": 1.0})
        self.assertIn("projected_runtime_hours", evaluation["mpc"])
        self.assertEqual(evaluation["hybrid"]["strategy"], "hybrid")
        self.assertEqual(evaluation["hybrid"]["damper_percentages"], {"0": 100})
        self.assertFalse(evaluation["hybrid"]["touchpad_temperature_commanded"])
        status = controller.status()
        self.assertIn("Damper Plan: Zone 1 100%", " / ".join(status["recommendations"]))
        self.assertEqual(status["intents"][0]["summary"], "Recommended Target: 22 C / Expected Runtime: 0.3 H / Damper Plan: Zone 1 100%")

    def test_recommend_mode_reports_hybrid_shadow_while_models_warm(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="recommend",
                learning_mode="control",
                command_cooldown=1,
                control_zones=(0,),
                control_strategy="hybrid",
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
        self.assertEqual(evaluation["hybrid"]["damper_percentages"], {"0": 100})
        status = controller.status()
        self.assertIn("Model Learning: Waiting For Selected Control Zones", " / ".join(status["recommendations"]))
        self.assertEqual(status["intents"][0]["headline"], "Model Learning")

    def test_recommend_hybrid_reports_air_quality_preview_without_hybrid_plan_for_dry(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="recommend",
                command_cooldown=1,
                control_zones=(0,),
                control_strategy="hybrid",
            )
        )
        controller._mpc.zone_models[0] = ready_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=22, sensor_control=False, zone_percentage=25),
            integrations(30, indoor_humidity=75),
            now=1.0,
        )

        self.assertEqual(specs, [])
        evaluation = controller.status()["evaluations"][0]
        self.assertEqual(evaluation["mode_intent"]["mode"], 2)
        self.assertTrue(evaluation["air_quality"]["dry_recommended"])
        self.assertEqual(evaluation["air_quality"]["dry_zone_ids"], [0])
        self.assertIsNone(evaluation["mpc"])
        self.assertIsNone(evaluation["hybrid"])
        self.assertEqual(controller.status()["intents"][0]["summary"], "AC Mode Intent: Dry / Zones Would Open: Zone 1")

    def test_recommend_hybrid_reports_air_quality_preview_without_hybrid_plan_for_fan(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="recommend",
                command_cooldown=1,
                control_zones=(0,),
                outside_air_zones=(1,),
                control_strategy="hybrid",
            )
        )
        controller._mpc.zone_models[0] = ready_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=22, sensor_control=False, zone_percentage=25),
            integrations(30, indoor_co2=1250),
            now=1.0,
        )

        self.assertEqual(specs, [])
        evaluation = controller.status()["evaluations"][0]
        self.assertEqual(evaluation["mode_intent"]["mode"], 3)
        self.assertTrue(evaluation["air_quality"]["fan_recommended"])
        self.assertEqual(evaluation["air_quality"]["outside_air_zone_ids"], [1])
        self.assertIsNone(evaluation["mpc"])
        self.assertIsNone(evaluation["hybrid"])
        self.assertEqual(
            controller.status()["intents"][0]["summary"],
            "Fan And Outside Air Recommended / Outside Air Zones Would Open: Zone 2",
        )

    def test_recommend_hybrid_keeps_thermal_plan_when_air_quality_is_high(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="recommend",
                command_cooldown=1,
                control_zones=(0,),
                outside_air_zones=(1,),
                control_strategy="hybrid",
                hybrid_idle_damper_percent=10,
            )
        )
        controller._mpc.zone_models[0] = ready_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=25, sensor_control=False, zone_percentage=25),
            integrations(30, indoor_humidity=75, indoor_co2=1250),
            now=1.0,
        )

        self.assertEqual(specs, [])
        evaluation = controller.status()["evaluations"][0]
        self.assertEqual(evaluation["mode_intent"]["mode"], 4)
        self.assertTrue(evaluation["mode_intent"]["outside_air_intent"])
        self.assertEqual(evaluation["air_quality"]["dry_held_reason"], "thermal_demand_active")
        self.assertEqual(evaluation["air_quality"]["fan_held_reason"], "thermal_demand_active")
        self.assertEqual(evaluation["mpc"]["source"], "zone")
        self.assertEqual(evaluation["hybrid"]["strategy"], "hybrid")
        summary = controller.status()["intents"][0]["summary"]
        self.assertIn("Damper Plan: Zone 1", summary)
        self.assertIn("Humidity High: Thermal Mode Preferred", summary)
        self.assertIn("CO2 High: Outside Air Recommended", summary)

    def test_recommend_mode_does_not_report_mpc_without_configured_control_zone(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="recommend", control_strategy="zone", command_cooldown=1))
        controller._mpc.zone_models[0] = ready_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=20),
            integrations(30),
            now=1.0,
        )

        self.assertEqual(specs, [])
        self.assertIsNone(controller.status()["evaluations"][0]["mpc"])

    def test_control_mode_does_not_assert_without_zone_control_flag(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="zone", command_cooldown=1))
        controller._mpc.zone_models[0] = ready_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=20, sensor_control=False),
            integrations(30),
            now=1.0,
        )

        self.assertEqual(specs, [])
        self.assertIn("0", controller.status()["learning"]["zones"])
        self.assertIsNone(controller.status()["evaluations"][0]["mpc"])

    def test_control_zone_flag_not_airtouch_sensor_control_allows_assertion(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(mode="adaptive", control_strategy="zone", command_cooldown=1, control_zones=(0,))
        )
        controller._mpc.zone_models[0] = ready_heating_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=20, sensor_control=False),
            integrations(30),
            now=1.0,
        )

        self.assertEqual([spec.command for spec in specs], [0x22, 0x22])
        self.assertEqual(controller.status()["evaluations"][0]["mpc"]["target"], 22)
        self.assertEqual(controller.status()["evaluations"][0]["mpc"]["source"], "zone")

    def test_hybrid_damper_strategy_uses_mpc_fraction_for_control_zone(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="adaptive",
                learning_mode="control",
                command_cooldown=1,
                control_zones=(0,),
                control_strategy="hybrid",
                hybrid_idle_damper_percent=10,
            )
        )
        controller._mpc.zone_models[0] = ready_heating_model()

        specs = controller.evaluate(
            runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=20, sensor_control=False, zone_percentage=25),
            integrations(30),
            now=1.0,
        )

        self.assertEqual([spec.command for spec in specs], [0x22, 0x22, 0x78, 0x72, 0x20])
        self.assertEqual(specs[0].payload.hex(" ").upper(), "00 17 1F 00")
        self.assertEqual(specs[1].payload.hex(" ").upper(), "00 87 12 00")
        self.assertEqual(specs[2].payload.hex(" ").upper(), "00 0D 91 88 00 00 00 00 00 00 1E 10 00 00 00")
        self.assertEqual(specs[3].payload.hex(" ").upper(), "91 14")
        self.assertEqual(specs[4].payload.hex(" ").upper(), "80 64 00 00")
        evaluation = controller.status()["evaluations"][0]
        self.assertEqual(evaluation["mpc"]["source"], "zone")
        self.assertEqual(evaluation["hybrid"]["strategy"], "hybrid")
        self.assertEqual(evaluation["hybrid"]["damper_percentages"], {"0": 100})
        self.assertTrue(evaluation["hybrid"]["touchpad_temperature_commanded"])
        self.assertEqual(evaluation["hybrid"]["touchpad_sensor"], 0x91)
        self.assertEqual(evaluation["hybrid"]["touchpad_temperature"], 20)

    def test_hybrid_damper_strategy_restores_damper_when_disabled(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="adaptive",
                learning_mode="control",
                command_cooldown=1,
                control_zones=(0,),
                control_strategy="hybrid",
                hybrid_idle_damper_percent=10,
            )
        )
        controller._mpc.zone_models[0] = ready_heating_model()

        first = controller.evaluate(
            runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=20, sensor_control=False, zone_percentage=25),
            integrations(30),
            now=1.0,
        )
        controller.update_config({"mode": "off"})
        second = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, mode=1, zone_temperature=20, sensor_control=False, zone_percentage=100),
            integrations(30),
            now=10.0,
        )

        self.assertEqual(first[-1].payload.hex(" ").upper(), "80 64 00 00")
        self.assertEqual([spec.payload.hex(" ").upper() for spec in second], ["00 47 1F 00", "00 87 10 00", "80 19 00 00"])
        self.assertEqual(controller.status()["active_dampers"], [])

    def test_hybrid_restores_ac_control_sensor_when_disabled(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="adaptive",
                learning_mode="control",
                command_cooldown=1,
                control_zones=(0,),
                control_strategy="hybrid",
                hybrid_idle_damper_percent=10,
            )
        )
        controller._mpc.zone_models[0] = ready_heating_model()

        controller.evaluate(
            runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=20, sensor_control=False, zone_percentage=25, ctrl_thermostat=0),
            integrations(30),
            now=1.0,
        )
        restore = controller.export_restore_state()["records"]
        controller.update_config({"mode": "off"})
        second = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, mode=1, zone_temperature=20, sensor_control=False, zone_percentage=100, ctrl_thermostat=0x91),
            integrations(30),
            now=10.0,
        )

        self.assertIn("ac:0:control_sensor", restore)
        self.assertEqual(restore["ac:0:control_sensor"]["action"], "ac_setting_new")
        self.assertEqual(restore["ac:0:control_sensor"]["target"], {"ac": 0, "ctrl_thermostat": 0x91})
        self.assertEqual([spec.command for spec in second], [0x22, 0x22, 0x78, 0x20])
        self.assertEqual(second[2].payload.hex(" ").upper(), "00 0D 00 88 00 00 00 00 00 00 1E 10 00 00 00")
        self.assertEqual(controller.status()["active_ac"], [])

    def test_hybrid_restores_sensor_control_instead_of_stale_damper_for_sensor_zone(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="adaptive",
                learning_mode="control",
                command_cooldown=1,
                control_zones=(0,),
                control_strategy="hybrid",
                hybrid_idle_damper_percent=10,
            )
        )
        controller._mpc.zone_models[0] = ready_heating_model()

        first = controller.evaluate(
            runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=20, sensor_control=True, zone_percentage=25),
            integrations(30),
            now=1.0,
        )
        restore = controller.export_restore_state()["records"]
        controller.update_config({"mode": "off"})
        second = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, mode=1, zone_temperature=20, sensor_control=False, zone_percentage=100),
            integrations(30),
            now=10.0,
        )

        self.assertEqual(first[-1].payload.hex(" ").upper(), "80 64 00 00")
        self.assertIn("group:0:sensor_control", restore)
        self.assertNotIn("group:0:percentage", restore)
        self.assertEqual(restore["group:0:sensor_control"]["action"], "group_setpoint")
        self.assertEqual(restore["group:0:sensor_control"]["target_action"], "group_percentage")
        self.assertEqual([spec.payload.hex(" ").upper() for spec in second], ["00 47 1F 00", "00 87 10 00", "80 92 00 00"])
        self.assertEqual(controller.status()["active_dampers"], [])

    def test_hybrid_damper_bounds_are_integer_percentages(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                control_strategy="hybrid",
                hybrid_min_damper_percent=20,
                hybrid_max_damper_percent=80,
                hybrid_idle_damper_percent=5,
            )
        )

        self.assertEqual(controller.public_config()["hybrid_min_damper_percent"], 20)
        self.assertEqual(controller.public_config()["hybrid_max_damper_percent"], 80)
        self.assertEqual(controller.public_config()["hybrid_idle_damper_percent"], 5)
        with self.assertRaisesRegex(ValueError, "hybrid_max_damper_percent must be between 0 and 100"):
            AdaptiveController(AdaptiveConfig(control_strategy="hybrid", hybrid_max_damper_percent=101))

    def test_control_strategy_save_overrides_stale_learning_mode(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", learning_mode="control", command_cooldown=1))

        public = controller.update_config({"control_strategy": "weather"})

        self.assertEqual(public["control_strategy"], "weather")
        self.assertEqual(public["learning_mode"], "off")

    def test_outside_air_zones_are_runtime_adaptive_config(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(outside_air_zones=(2, 1, 1)))

        self.assertEqual(controller.public_config()["outside_air_zones"], [1, 2])
        public = controller.update_config({"outside_air_zones": "3, 2"})

        self.assertEqual(public["outside_air_zones"], [2, 3])

    def test_co2_intent_opens_configured_outside_air_zone(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="adaptive",
                control_strategy="zone",
                command_cooldown=1,
                outside_air_zones=(0,),
            )
        )

        specs = controller.evaluate(
            runtime_state(
                ac_setpoint=22,
                zone_setpoint=22,
                zone_temperature=22,
                sensor_control=False,
                zone_percentage=25,
            ),
            integrations(30, indoor_co2=1250),
            now=1.0,
        )

        payloads = [spec.payload.hex(" ").upper() for spec in specs]
        self.assertIn("80 64 00 00", payloads)
        evaluation = controller.status()["evaluations"][0]
        self.assertEqual(evaluation["outside_air"]["configured_zones"], [0])
        self.assertEqual(evaluation["outside_air"]["commanded_percent"], 100)
        self.assertIn("Lounge: Outside Air Opened", controller.status()["actions"])

    def test_legacy_weather_setpoint_strategy_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "adaptive control strategy"):
            AdaptiveController(AdaptiveConfig(control_strategy="weather_setpoint"))

    def test_accelerated_learning_is_flag_not_confidence(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(mode="adaptive", control_strategy="zone", command_cooldown=1, control_zones=(0,))
        )
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
        self.assertEqual([spec.payload.hex(" ").upper() for spec in specs], ["00 17 1F 00"])

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
        controller = AdaptiveController(
            AdaptiveConfig(mode="adaptive", control_strategy="zone", command_cooldown=1, control_zones=(0,))
        )

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
            AdaptiveConfig(mode="adaptive", control_strategy="zone", command_cooldown=1, control_zones=(0,))
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

    def test_mpc_proposal_accepts_separated_forecast_inputs(self) -> None:
        engine = AdaptiveMpcEngine()
        engine.zone_models[0] = ready_model()
        room = AdaptiveRoom(
            id=0,
            name="Zone 1",
            ac_id=0,
            temperature=25,
            setpoint=24,
            active=True,
            learn=True,
            configured_control=True,
            control_enabled=True,
        )

        proposal = engine.propose(
            ac_id=0,
            rooms=(room,),
            baseline_target=24,
            cooling=True,
            inputs=MpcInputs(
                horizon_hours=1,
                outside_temperature=31,
                outside_forecast=(31, 30, 29),
                outside_forecast_step_minutes=5,
                humidity=65,
                q_solar=0.4,
                input_quality={
                    "forecast": {"status": "ok", "used_for_control": True},
                    "telemetry": {
                        "available": True,
                        "observed_conditioning": True,
                        "confidence": 0.95,
                        "evidence": ["electrical_power", "compressor_frequency"],
                    },
                },
            ),
        )

        self.assertIsNotNone(proposal)
        assert proposal is not None
        self.assertIsNotNone(proposal.runtime_forecast)
        assert proposal.runtime_forecast is not None
        self.assertEqual(proposal.runtime_forecast.horizon_hours, 1)
        self.assertEqual(proposal.runtime_forecast.step_minutes, 5.0)
        self.assertEqual(len(proposal.runtime_forecast.series), 12)
        self.assertEqual(proposal.runtime_forecast.series[0]["outside_temperature"], 31)
        self.assertGreaterEqual(proposal.runtime_forecast.runtime_minutes, 0.0)
        self.assertGreaterEqual(proposal.runtime_forecast.quality["solve_duration_ms"], 0.0)
        self.assertGreaterEqual(proposal.runtime_forecast.quality["optimizer_duration_ms"], 0.0)
        self.assertEqual(proposal.runtime_forecast.quality["horizon_blocks"], 12)
        self.assertEqual(proposal.runtime_forecast.quality["zone_count"], 1)
        self.assertEqual(proposal.runtime_forecast.quality["series_points"], 12)
        self.assertEqual(proposal.runtime_forecast.quality["input_forecast_points"], 3)
        self.assertEqual(proposal.runtime_forecast.quality["solver_status"], "ok")
        self.assertEqual(proposal.runtime_forecast.quality["telemetry_agreement"], "agree")
        self.assertEqual(proposal.runtime_forecast.quality["forecast_confidence"], 0.95)
        self.assertEqual(engine.forecasts[0][0]["outdoor_temperature"], 31)
        self.assertEqual(engine.forecasts[0][1]["outdoor_temperature"], 30)
        self.assertEqual(engine.forecasts[0][2]["outdoor_temperature"], 29)

    def test_runtime_forecast_discounts_unknown_or_disagreeing_telemetry(self) -> None:
        engine = AdaptiveMpcEngine()
        engine.zone_models[0] = ready_model()
        room = AdaptiveRoom(
            id=0,
            name="Zone 1",
            ac_id=0,
            temperature=25,
            setpoint=24,
            active=True,
            learn=True,
            configured_control=True,
            control_enabled=True,
        )

        unknown = engine.propose(
            ac_id=0,
            rooms=(room,),
            baseline_target=24,
            cooling=True,
            inputs=MpcInputs(
                horizon_hours=1,
                outside_temperature=31,
                input_quality={"telemetry": {"available": True, "observed_conditioning": None, "confidence": 0.8}},
            ),
        )
        disagree = engine.propose(
            ac_id=0,
            rooms=(room,),
            baseline_target=24,
            cooling=True,
            inputs=MpcInputs(
                horizon_hours=1,
                outside_temperature=31,
                input_quality={"telemetry": {"available": True, "observed_conditioning": False, "confidence": 0.8}},
            ),
        )

        self.assertIsNotNone(unknown)
        self.assertIsNotNone(disagree)
        assert unknown is not None
        assert disagree is not None
        assert unknown.runtime_forecast is not None
        assert disagree.runtime_forecast is not None
        self.assertEqual(unknown.runtime_forecast.quality["telemetry_agreement"], "unknown")
        self.assertEqual(unknown.runtime_forecast.quality["forecast_confidence"], 0.4)
        self.assertEqual(disagree.runtime_forecast.quality["telemetry_agreement"], "disagree")
        self.assertEqual(disagree.runtime_forecast.quality["forecast_confidence"], 0.36)

    def test_mpc_comfort_weight_relaxes_power_fraction(self) -> None:
        engine = AdaptiveMpcEngine()
        engine.zone_models[0] = ready_model()
        room = AdaptiveRoom(
            id=0,
            name="Zone 1",
            ac_id=0,
            temperature=26,
            setpoint=22,
            active=True,
            learn=True,
            configured_control=True,
            control_enabled=True,
        )

        comfort = engine.propose(
            ac_id=0,
            rooms=(room,),
            baseline_target=22,
            cooling=True,
            inputs=MpcInputs(horizon_hours=1, outside_temperature=31, comfort_weight=70),
        )
        relaxed = engine.propose(
            ac_id=0,
            rooms=(room,),
            baseline_target=22,
            cooling=True,
            inputs=MpcInputs(horizon_hours=1, outside_temperature=31, comfort_weight=20),
        )

        self.assertIsNotNone(comfort)
        self.assertIsNotNone(relaxed)
        assert comfort is not None
        assert relaxed is not None
        self.assertLessEqual(relaxed.power_fraction, comfort.power_fraction)

    def test_runtime_forecast_is_exposed_in_adaptive_status(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="recommend", control_strategy="zone", control_zones=(0,)))
        controller._mpc.zone_models[0] = ready_model()

        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=25),
            integrations(31, forecast=[{"temperature": 31}, {"temperature": 30}]),
            now=1.0,
        )

        runtime = controller.status()["evaluations"][0]["mpc"]["runtime_forecast"]
        self.assertEqual(runtime["horizon_hours"], 6)
        self.assertEqual(runtime["step_minutes"], 5.0)
        self.assertIn("runtime_hours", runtime)
        self.assertIn("action_windows", runtime)
        self.assertEqual(len(runtime["series"]), 72)
        self.assertIn("average_indoor_temperature", runtime["series"][0])
        self.assertEqual(runtime["quality"]["status"], "ok")
        self.assertGreaterEqual(runtime["quality"]["solve_duration_ms"], 0.0)
        self.assertEqual(runtime["quality"]["horizon_blocks"], 72)

    def test_ac_telemetry_is_exposed_as_forecast_confidence_evidence(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="recommend", control_strategy="zone", control_zones=(0,)))
        controller._mpc.zone_models[0] = ready_model()

        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=25),
            integrations(
                31,
                forecast=[{"temperature": 31}, {"temperature": 30}],
                ac_telemetry={
                    "power_w": 1200,
                    "running": True,
                    "frequency_hz": 42,
                    "return_air_temperature_c": 24,
                    "supply_air_temperature_c": 12,
                    "evidence": ["electrical_power", "compressor_frequency"],
                },
            ),
            now=1.0,
        )

        status = controller.status()
        telemetry = status["ac_telemetry"]
        runtime = status["evaluations"][0]["mpc"]["runtime_forecast"]
        self.assertTrue(telemetry["observed_conditioning"])
        self.assertEqual(telemetry["source"], "electrical_power")
        self.assertEqual(telemetry["supply_return_delta_c"], -12)
        self.assertEqual(runtime["quality"]["telemetry_agreement"], "agree")
        self.assertEqual(runtime["quality"]["forecast_confidence"], 0.95)

    def test_adaptive_mode_uses_fahrenheit_weather_source(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="zone", command_cooldown=1, control_zones=(0,)))

        specs = controller.evaluate(runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=20), integrations(86, "°F"), now=1.0)

        self.assertEqual(len(specs), 2)

    def test_repeated_adaptive_command_is_cooled_down(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="zone", check_interval=5, command_cooldown=300, control_zones=(0,)))

        first = controller.evaluate(runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=20), integrations(30), now=1.0)
        second = controller.evaluate(runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=20), integrations(30), now=10.0)

        self.assertTrue(first)
        self.assertEqual(second, [])

    def test_adaptive_mode_holds_when_indoor_temperature_is_uncomfortable(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="zone", command_cooldown=1, control_zones=(0,)))

        specs = controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=27),
            integrations(30),
            now=1.0,
        )

        self.assertEqual(specs, [])
        self.assertFalse(controller.status()["evaluations"][0]["relaxation_allowed"])

    def test_humidity_compensation_is_optional_and_tightens_cooling_target(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="zone", command_cooldown=1, control_zones=(0,)))

        specs = controller.evaluate(
            runtime_state(ac_setpoint=20, zone_setpoint=21, zone_temperature=20),
            integrations(30, indoor_humidity=70),
            now=1.0,
        )

        self.assertEqual([spec.command for spec in specs], [0x22, 0x22])
        self.assertEqual(specs[0].payload.hex(" ").upper(), "00 17 1F 00")
        self.assertEqual(specs[1].payload.hex(" ").upper(), "00 87 11 00")

    def test_dry_mode_intent_requires_indoor_humidity_sensor(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="recommend", control_strategy="zone", command_cooldown=1, control_zones=(0,)))

        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=22),
            integrations(30, humidity=75),
            now=1.0,
        )

        mode_intent = controller.status()["evaluations"][0]["mode_intent"]
        self.assertNotEqual(mode_intent["mode"], 2)

        controller = AdaptiveController(AdaptiveConfig(mode="recommend", control_strategy="zone", command_cooldown=1, control_zones=(0,)))
        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=22),
            integrations(30, indoor_humidity=75),
            now=1.0,
        )

        mode_intent = controller.status()["evaluations"][0]["mode_intent"]
        self.assertEqual(mode_intent["mode"], 2)
        self.assertEqual(mode_intent["source"], "home_assistant_indoor")

    def test_dry_mode_intent_uses_configured_humidity_threshold(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(mode="recommend", control_strategy="zone", command_cooldown=1, control_zones=(0,), dry_humidity_threshold=80)
        )

        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=22),
            integrations(30, indoor_humidity=75),
            now=1.0,
        )

        self.assertNotEqual(controller.status()["evaluations"][0]["mode_intent"]["mode"], 2)

        controller = AdaptiveController(
            AdaptiveConfig(mode="recommend", control_strategy="zone", command_cooldown=1, control_zones=(0,), dry_humidity_threshold=80)
        )
        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=22),
            integrations(30, indoor_humidity=80),
            now=1.0,
        )

        self.assertEqual(controller.status()["evaluations"][-1]["mode_intent"]["mode"], 2)
        self.assertEqual(controller.public_config()["dry_humidity_threshold"], 80)

    def test_co2_mode_intent_recommends_fan_and_outside_air_when_temperature_is_comfortable(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="recommend", control_strategy="zone", command_cooldown=1, control_zones=(0,)))

        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=22),
            integrations(30, indoor_co2=1250),
            now=1.0,
        )

        mode_intent = controller.status()["evaluations"][-1]["mode_intent"]
        self.assertEqual(mode_intent["mode"], 3)
        self.assertTrue(mode_intent["outside_air_intent"])
        self.assertEqual(mode_intent["ventilation_reason"], "co2_high")
        self.assertEqual(controller.status()["intents"][0]["headline"], "Fresh Air Recommended")

    def test_co2_mode_intent_uses_configured_threshold(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(mode="recommend", control_strategy="zone", command_cooldown=1, control_zones=(0,), co2_ventilation_threshold_ppm=1400)
        )

        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=22),
            integrations(30, indoor_co2=1250),
            now=1.0,
        )

        mode_intent = controller.status()["evaluations"][0]["mode_intent"]
        self.assertFalse(mode_intent["outside_air_intent"])

        controller = AdaptiveController(
            AdaptiveConfig(mode="recommend", control_strategy="zone", command_cooldown=1, control_zones=(0,), co2_ventilation_threshold_ppm=1400)
        )
        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=22),
            integrations(30, indoor_co2=1450),
            now=1.0,
        )

        mode_intent = controller.status()["evaluations"][-1]["mode_intent"]
        self.assertEqual(mode_intent["mode"], 3)
        self.assertTrue(mode_intent["outside_air_intent"])
        self.assertEqual(controller.public_config()["co2_ventilation_threshold_ppm"], 1400)

    def test_co2_adds_outside_air_intent_to_heat_or_cool_mode(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="recommend", control_strategy="zone", command_cooldown=1, control_zones=(0,)))

        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22, zone_temperature=25),
            integrations(30, indoor_co2=1250),
            now=1.0,
        )

        mode_intent = controller.status()["evaluations"][0]["mode_intent"]
        self.assertEqual(mode_intent["mode"], 4)
        self.assertTrue(mode_intent["outside_air_intent"])

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
        self.assertEqual(controller.status()["forecast_quality"]["status"], "untimed")

    def test_timestamped_ha_forecast_is_sorted_and_marked_timed(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1, control_zones=(0,)))
        start = datetime.now(timezone.utc).replace(second=0, microsecond=0)

        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22),
            integrations(
                30,
                forecast=[
                    {"datetime": (start + timedelta(hours=2)).isoformat(), "temperature": 27},
                    {"datetime": start.isoformat(), "temperature": 25},
                    {"datetime": (start + timedelta(hours=1)).isoformat(), "temperature": 26},
                    {"datetime": (start + timedelta(hours=3)).isoformat(), "temperature": 28},
                    {"datetime": (start + timedelta(hours=4)).isoformat(), "temperature": 29},
                    {"datetime": (start + timedelta(hours=5)).isoformat(), "temperature": 30},
                    {"datetime": (start + timedelta(hours=6)).isoformat(), "temperature": 31},
                ],
            ),
            now=1.0,
        )

        status = controller.status()
        self.assertEqual(status["forecast_temperatures"][:3], [25, 26, 27])
        self.assertEqual(status["forecast_quality"]["status"], "ok")
        self.assertTrue(status["forecast_quality"]["timed"])
        self.assertTrue(status["forecast_quality"]["used_for_control"])
        self.assertEqual(status["forecast_quality"]["step_minutes"], 5.0)

    def test_timestamp_keyed_forecast_dict_is_accepted(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1, control_zones=(0,)))
        start = datetime.now(timezone.utc).replace(second=0, microsecond=0)

        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22),
            {
                "weather": {"state": {"temperature": 30, "temperature_unit": "C"}},
                "forecast": {
                    "state": {
                        "forecast": {
                            (start + timedelta(hours=hour)).isoformat(): {"temperature": 24 + hour}
                            for hour in range(7)
                        }
                    }
                },
            },
            now=1.0,
        )

        status = controller.status()
        self.assertEqual(status["forecast_temperatures"][:2], [24, 25])
        self.assertEqual(status["forecast_quality"]["status"], "ok")
        self.assertTrue(status["forecast_quality"]["timed"])

    def test_naive_ha_forecast_uses_local_time_and_drops_current_weather_anchor(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1, control_zones=(0,)))
        local_hour = datetime.now().astimezone().replace(minute=0, second=0, microsecond=0)
        current_weather_anchor = datetime.now().astimezone().replace(microsecond=0)

        controller.evaluate(
            runtime_state(ac_setpoint=22, zone_setpoint=22),
            integrations(
                19.3,
                forecast=[
                    {
                        "datetime": current_weather_anchor.isoformat(),
                        "temperature": 19.3,
                        "source": "current_weather",
                    },
                    {
                        "datetime": local_hour.replace(tzinfo=None).isoformat(),
                        "temperature": 20.0,
                    },
                    {
                        "datetime": (local_hour + timedelta(hours=1)).replace(tzinfo=None).isoformat(),
                        "temperature": 21.0,
                    },
                    {
                        "datetime": (local_hour + timedelta(hours=2)).replace(tzinfo=None).isoformat(),
                        "temperature": 21.0,
                    },
                    {
                        "datetime": (local_hour + timedelta(hours=3)).replace(tzinfo=None).isoformat(),
                        "temperature": 22.0,
                    },
                    {
                        "datetime": (local_hour + timedelta(hours=4)).replace(tzinfo=None).isoformat(),
                        "temperature": 22.0,
                    },
                    {
                        "datetime": (local_hour + timedelta(hours=5)).replace(tzinfo=None).isoformat(),
                        "temperature": 21.0,
                    },
                    {
                        "datetime": (local_hour + timedelta(hours=6)).replace(tzinfo=None).isoformat(),
                        "temperature": 20.0,
                    },
                ],
                forecast_time_zone="Australia/Brisbane",
            ),
            now=1.0,
        )

        status = controller.status()
        quality = status["forecast_quality"]
        self.assertEqual(status["forecast_temperatures"][:3], [20.0, 21.0, 21.0])
        self.assertEqual(quality["status"], "ok")
        self.assertTrue(quality["used_for_control"])
        self.assertTrue(quality["localized_naive_datetimes"])
        self.assertFalse(quality["duplicate_timestamps"])
        self.assertTrue(quality["dropped_current_weather_anchor"])
        self.assertTrue(quality["current_anchor"])
        self.assertEqual(quality["time_zone"], "Australia/Brisbane")
        self.assertLess(quality["anchor_datetime"], quality["last_datetime"])

    def test_stale_timestamped_forecast_is_not_used_for_weather_power_off_gate(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="weather", command_cooldown=1))
        old = datetime.now(timezone.utc) - timedelta(hours=3)

        specs = controller.evaluate(
            runtime_state(ac_setpoint=24),
            integrations(20, forecast=[{"datetime": old.isoformat(), "temperature": 35}]),
            now=1.0,
        )

        self.assertEqual(len(specs), 1)
        self.assertEqual(controller.status()["forecast_quality"]["status"], "stale")
        self.assertFalse(controller.status()["forecast_quality"]["used_for_control"])

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

    def test_single_active_zone_power_fraction_is_full_share(self) -> None:
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

    def test_observed_power_fraction_scales_ekf_prediction_path(self) -> None:
        full = AdaptiveMpcEngine()
        limited = AdaptiveMpcEngine()

        full.observe(_mpc_snapshot(power_fraction=1.0, temperature=24.0), now=1.0, outside_temperature=30.0)
        full.observe(_mpc_snapshot(power_fraction=1.0, temperature=23.5), now=181.0, outside_temperature=30.0)
        limited.observe(_mpc_snapshot(power_fraction=0.25, temperature=24.0), now=1.0, outside_temperature=30.0)
        limited.observe(_mpc_snapshot(power_fraction=0.25, temperature=23.5), now=181.0, outside_temperature=30.0)

        full_point = full.status(now=181.0)["analytics"]["0"][-1]
        limited_point = limited.status(now=181.0)["analytics"]["0"][-1]
        self.assertEqual(full_point["estimated_power_fraction"], 1.0)
        self.assertEqual(limited_point["estimated_power_fraction"], 0.25)
        self.assertLess(full_point["predicted_temperature"], limited_point["predicted_temperature"])

    def test_mode_specific_readiness_reason_names_missing_mode_samples(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", command_cooldown=1))
        controller._mpc.zone_models[0] = ready_model()

        zone = controller._mpc.status(now=1.0)["zones"]["0"]

        self.assertEqual(zone["heating_readiness_reason"], "heating_samples")
        self.assertEqual(zone["cooling_readiness_reason"], "ready")


if __name__ == "__main__":
    unittest.main()
