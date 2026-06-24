from __future__ import annotations

import unittest

from airtouch4.commands import (
    CommandBuildError,
    active_favourite_command,
    ac_timer_command,
    datetime_command,
    favourite_command,
    group_power_command,
    raw_command,
    service_command,
    set_ac_status,
    set_active_favourite,
    set_datetime,
    set_favourite,
    set_group_name,
    set_group_percentage,
    set_group_power,
    set_group_setpoint,
    set_group_turbo,
    set_grouping,
    set_parameters,
    set_pair_sensor,
    set_preference_full,
    set_sensor_temperature,
    set_service,
    set_spill,
    set_timer,
)
from airtouch4.payloads import decode_mainboard_payload


class CommandBuilderTests(unittest.TestCase):
    def test_group_control_builders_decode_back(self) -> None:
        self.assertEqual(set_group_power(4, True).hex(" ").upper(), "44 93 00 00")
        self.assertEqual(set_group_power(4, False, sensor_control=False, value=65).hex(" ").upper(), "04 41 00 00")
        self.assertEqual(set_group_percentage(4, 65).hex(" ").upper(), "84 41 00 00")
        self.assertEqual(set_group_setpoint(4, 24).hex(" ").upper(), "84 94 00 00")
        self.assertEqual(set_group_turbo(4).hex(" ").upper(), "C4 93 00 00")

        decoded = decode_mainboard_payload(0x20, set_group_setpoint(4, 24))

        self.assertEqual(decoded["group"], 4)
        self.assertEqual(decoded["power_name"], "value_change")
        self.assertTrue(decoded["sensor_control"])
        self.assertEqual(decoded["setpoint"], 24)

    def test_group_power_command_spec(self) -> None:
        spec = group_power_command(1, True)

        self.assertEqual(spec.command, 0x20)
        self.assertEqual(spec.payload, bytes.fromhex("41 93 00 00"))

    def test_ac_status_builder_decodes_back(self) -> None:
        payload = set_ac_status(0, power_on=True, mode=4, fan=3, setpoint=22)

        self.assertEqual(payload.hex(" ").upper(), "C0 43 12 00")
        decoded = decode_mainboard_payload(0x22, payload)
        self.assertEqual(decoded["power_name"], "on")
        self.assertEqual(decoded["mode"], 4)
        self.assertEqual(decoded["fan"], 3)
        self.assertEqual(decoded["setpoint"], 22)

    def test_config_builders(self) -> None:
        self.assertEqual(set_group_name(2, "Office").hex(" ").upper(), "02 4F 66 66 69 63 65 00 00")
        self.assertEqual(set_grouping(2, zone_start=2, zone_count=1, min_percent=10, thermostat=0xFF).hex(" ").upper(), "02 02 0A FF")
        self.assertEqual(set_spill([1, 0, 0, 0], [5]).hex(" ").upper(), "01 00 00 00 20 00")
        self.assertEqual(set_pair_sensor(True), b"\x80")
        self.assertEqual(set_sensor_temperature(0x90, 0xEA).hex(" ").upper(), "90 EA")

    def test_datetime_builder(self) -> None:
        self.assertEqual(set_datetime(year=2026, month=6, day=13, weekday=6, hour=9, minute=55, second=1).hex(" ").upper(), "00 1A 06 0D 06 09 37 01")
        self.assertEqual(datetime_command(year=2026, month=6, day=13, weekday=6, hour=9, minute=55, second=1).command, 0x40)

    def test_favourite_and_service_builders(self) -> None:
        self.assertEqual(set_active_favourite(2), b"\x02")
        self.assertEqual(active_favourite_command(2).command, 0x30)
        self.assertEqual(set_favourite(0, "Day", [0, 4]).hex(" ").upper(), "80 44 61 79 00 00 00 00 00 11 00")
        self.assertEqual(favourite_command(0, "Day", [0, 4]).command, 0x32)
        self.assertEqual(set_service("Bw Air", "0411 046 349")[:22].hex(" ").upper(), "42 77 20 41 69 72 00 00 00 00 30 34 31 31 20 30 34 36 20 33 34 39")
        self.assertEqual(len(set_service("Bw Air", "0411 046 349")), 30)
        self.assertEqual(service_command("Bw Air", "0411 046 349").command, 0x6A)

    def test_apk_service_page_builders_decode_back(self) -> None:
        parameters = set_parameters(
            6,
            damper_rpm=45,
            touchpad_1_location=1,
            touchpad_2_location=2,
            ac_button_blocked=True,
            show_outside_temp=True,
            lock_to_temp_control=True,
            show_control_sensor=True,
        )
        decoded_parameters = decode_mainboard_payload(0x60, parameters)
        self.assertEqual(parameters.hex(" ").upper(), "05 2D 01 02 87")
        self.assertEqual(decoded_parameters["group_count"], 6)
        self.assertTrue(decoded_parameters["ac_button_blocked"])
        self.assertTrue(decoded_parameters["show_control_sensor"])

        preference = set_preference_full(
            "Home",
            show_ac_errors=True,
            show_outside_temp=True,
            show_control_sensor=True,
            use_fahrenheit=True,
            location=3,
            screensaver_enabled=True,
            screensaver_timeout=15,
        )
        decoded_preference = decode_mainboard_payload(0x54, preference)
        self.assertEqual(preference[16:].hex(" ").upper(), "3C 83 8F")
        self.assertTrue(decoded_preference["show_ac_errors"])
        self.assertEqual(decoded_preference["location"], 3)
        self.assertEqual(decoded_preference["screensaver_timeout"], 15)

        service = set_service(
            "Dealer",
            "12345",
            show_service_due=True,
            service_due_locked=True,
            filter_clean_due=True,
            maintenance_due=True,
            months=6,
            days=365,
            runtime_hours=123456,
        )
        decoded_service = decode_mainboard_payload(0x6A, service)
        self.assertEqual(service[22:].hex(" ").upper(), "87 06 01 6D 00 01 E2 40")
        self.assertTrue(decoded_service["show_service_due"])
        self.assertTrue(decoded_service["maintenance_due"])
        self.assertEqual(decoded_service["days"], 365)
        self.assertEqual(decoded_service["runtime_hours"], 123456)

    def test_timer_and_raw_command_builders(self) -> None:
        self.assertEqual(set_timer(None, None).hex(" ").upper(), "80 00")
        self.assertEqual(set_timer(9, 30).hex(" ").upper(), "09 1E")
        self.assertEqual(ac_timer_command(0, hour=9, minute=30).payload.hex(" ").upper(), "00 09 1E")
        self.assertEqual(raw_command(0x3C, b"\x01\x02").payload, b"\x01\x02")

    def test_rejects_out_of_range(self) -> None:
        with self.assertRaises(CommandBuildError):
            set_group_percentage(20, 50)
        with self.assertRaises(CommandBuildError):
            set_group_setpoint(1, 99)
        with self.assertRaises(CommandBuildError):
            set_active_favourite(8)


if __name__ == "__main__":
    unittest.main()
