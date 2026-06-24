from __future__ import annotations

import unittest

from airtouch4.commands import (
    CommandBuildError,
    ac_base_info_command,
    ac_setting_new_command,
    ac_timer_table_command,
    active_favourite_command,
    ac_timer_command,
    datetime_command,
    favourite_command,
    group_power_command,
    raw_command,
    service_command,
    set_ac_status,
    set_ac_base_info,
    set_ac_setting_new,
    set_ac_setting_record,
    set_ac_group_counts,
    set_ac_name,
    set_ac_timer_table,
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
    set_program_define_new,
    set_preference_full,
    set_sensor_temperature,
    set_service,
    set_spill,
    set_timer,
    program_define_new_command,
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

    def test_ac_base_info_builder_decodes_back(self) -> None:
        records = [
            {"ac": 0, "group_start": 0, "group_count": 8, "brand": 0x1200, "name": "Home"},
        ]

        payload = set_ac_base_info(records, one_duct_system=True)
        decoded = decode_mainboard_payload(0x74, payload)

        self.assertEqual(payload.hex(" ").upper(), "01 01 00 80 12 00 48 6F 6D 65 00 00 00 00")
        self.assertEqual(ac_base_info_command(records, one_duct_system=True).command, 0x74)
        self.assertEqual(decoded["type"], "set_ac_base_info")
        self.assertTrue(decoded["one_duct_system"])
        self.assertEqual(decoded["records"][0]["group_count"], 8)
        self.assertEqual(decoded["records"][0]["name"], "Home")

        renamed = set_ac_name(records, 0, "Unit 1", one_duct_system=True)
        self.assertEqual(decode_mainboard_payload(0x74, renamed)["records"][0]["name"], "Unit 1")

        regrouped = set_ac_group_counts(records, [6], one_duct_system=True)
        self.assertEqual(decode_mainboard_payload(0x74, regrouped)["records"][0]["group_count"], 6)

    def test_ac_setting_new_builder_decodes_back(self) -> None:
        record = {
            "ac": 0,
            "hide_spill_group": True,
            "ctrl_thermostat": 0xFD,
            "cool_adjust": 0,
            "heat_adjust": 0,
            "modes": {"cool": True, "fan": True, "dry": True, "heat": True, "auto": True},
            "fan_values": {
                "auto": 0,
                "quiet": 15,
                "low": 1,
                "medium": 2,
                "high": 3,
                "powerful": 15,
                "turbo": 15,
            },
            "auto_off": True,
            "on_time_limit": 0,
            "max_setpoint": 30,
            "min_setpoint": 16,
            "selector_visibility": {
                "auto": True,
                "touchpad_1": True,
                "touchpad_2": True,
                "average": True,
                "economy": True,
                "groups_1_8_bitmap": 0x1F,
                "groups_9_16_bitmap": 0x00,
            },
        }

        payload = set_ac_setting_record(**record)
        decoded = decode_mainboard_payload(0x78, set_ac_setting_new([record]))

        self.assertEqual(payload.hex(" ").upper(), "80 0D FD 88 1F F0 21 F3 0F 10 1E 10 3E 1F 00")
        self.assertEqual(ac_setting_new_command([record]).command, 0x78)
        self.assertEqual(decoded["type"], "set_ac_setting_new")
        self.assertEqual(decoded["record_count"], 1)
        self.assertEqual(decoded["records"][0]["ctrl_thermostat"], 0xFD)
        self.assertTrue(decoded["records"][0]["hide_spill_group"])
        self.assertEqual(decoded["records"][0]["fan_values"]["quiet"], 15)
        self.assertTrue(decoded["records"][0]["selector_visibility"]["economy"])

    def test_timer_and_raw_command_builders(self) -> None:
        self.assertEqual(set_timer(None, None).hex(" ").upper(), "80 00")
        self.assertEqual(set_timer(9, 30).hex(" ").upper(), "09 1E")
        self.assertEqual(ac_timer_command(0, hour=9, minute=30).payload.hex(" ").upper(), "00 09 1E")
        self.assertEqual(raw_command(0x3C, b"\x01\x02").payload, b"\x01\x02")

    def test_apk_ac_timer_table_builder_decodes_back(self) -> None:
        records = [
            {
                "ac": 0,
                "on_timer": {"enabled": True, "hour": 6, "minute": 15},
                "off_timer": {"enabled": False, "hour": 22, "minute": 45},
            },
            {
                "ac": 1,
                "on_timer": {"enabled": False},
                "off_timer": {"enabled": False},
            },
        ]

        payload = set_ac_timer_table(records, ac_count=2)
        decoded = decode_mainboard_payload(0x36, payload)

        self.assertEqual(len(payload), 32)
        self.assertEqual(payload[:16].hex(" ").upper(), "06 0F 96 2D 00 00 00 00 80 00 80 00 00 00 00 00")
        self.assertEqual(ac_timer_table_command(records, ac_count=2).command, 0x36)
        self.assertEqual(decoded["type"], "set_ac_timer")
        self.assertEqual(decoded["record_count"], 4)
        self.assertEqual(decoded["records"][0]["on_timer"]["hour"], 6)
        self.assertFalse(decoded["records"][0]["off_timer"]["enabled"])

    def test_program_define_builder_decodes_back(self) -> None:
        records = [
            {
                "program": 0,
                "enabled": True,
                "days_bitmap": 0x3E,
                "name": "Weekday",
                "groups_1_8_bitmap": 0x05,
                "groups_9_16_bitmap": 0x00,
                "active_ac_bitmap": 0x01,
                "on_timer": {"enabled": True, "hour": 7, "minute": 0},
                "on_setpoint": 22,
                "off_timer": {"enabled": True, "hour": 18, "minute": 30},
            }
        ]

        payload = set_program_define_new(records, program_count=1, linked_ac=True)
        decoded = decode_mainboard_payload(0x3C, payload)

        self.assertEqual(len(payload), 260)
        self.assertEqual(payload[:36].hex(" ").upper(), "01 01 00 20 80 3E 57 65 65 6B 64 61 79 00 05 00 00 00 00 00 00 00 01 00 07 00 16 00 12 1E 00 00 00 00 00 00")
        self.assertEqual(program_define_new_command(records, program_count=1, linked_ac=True).command, 0x3C)
        self.assertEqual(decoded["type"], "set_program_define_new")
        self.assertEqual(decoded["program_count"], 1)
        self.assertTrue(decoded["linked_ac"])
        self.assertEqual(decoded["records"][0]["name"], "Weekday")
        self.assertEqual(decoded["records"][0]["on_setpoint"], 22)

    def test_rejects_out_of_range(self) -> None:
        with self.assertRaises(CommandBuildError):
            set_group_percentage(20, 50)
        with self.assertRaises(CommandBuildError):
            set_group_setpoint(1, 99)
        with self.assertRaises(CommandBuildError):
            set_active_favourite(8)


if __name__ == "__main__":
    unittest.main()
