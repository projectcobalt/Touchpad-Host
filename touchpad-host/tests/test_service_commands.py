from __future__ import annotations

import unittest

from airtouch4.service.commands import CommandRequestError, build_transaction


class ServiceCommandTests(unittest.TestCase):
    def test_build_group_power_transaction(self) -> None:
        spec = build_transaction("group_power", {"group": 4, "on": True, "sensor_control": True, "setpoint": 24})

        self.assertEqual(spec.command, 0x20)
        self.assertEqual(spec.payload, bytes.fromhex("44 94 00 00"))
        self.assertEqual(spec.name, "group_power")

    def test_build_ac_status_transaction_with_optional_fields(self) -> None:
        spec = build_transaction("ac_status", {"ac": 0, "power_on": True, "mode": 1})

        self.assertEqual(spec.command, 0x22)
        self.assertEqual(spec.payload, bytes.fromhex("C0 17 1F 00"))

    def test_build_raw_transaction_from_hex(self) -> None:
        spec = build_transaction("raw", {"command": "0x55", "payload": "01 02"})

        self.assertEqual(spec.command, 0x55)
        self.assertEqual(spec.payload, bytes.fromhex("01 02"))

    def test_build_parameters_transaction(self) -> None:
        spec = build_transaction(
            "parameters",
            {
                "group_count": 6,
                "damper_rpm": 45,
                "touchpad_1_location": 1,
                "touchpad_2_location": 2,
                "ac_button_blocked": True,
                "show_outside_temp": True,
                "lock_to_temp_control": True,
                "show_control_sensor": True,
            },
        )

        self.assertEqual(spec.command, 0x60)
        self.assertEqual(spec.payload, bytes.fromhex("05 2D 01 02 87"))

    def test_build_structured_service_transaction(self) -> None:
        spec = build_transaction(
            "service",
            {
                "company": "Dealer",
                "phone": "12345",
                "show_service_due": True,
                "service_due_locked": True,
                "filter_clean_due": True,
                "maintenance_due": True,
                "months": 6,
                "days": 365,
                "runtime_hours": 123456,
            },
        )

        self.assertEqual(spec.command, 0x6A)
        self.assertEqual(spec.payload[22:], bytes.fromhex("87 06 01 6D 00 01 E2 40"))

    def test_build_ac_base_info_transaction(self) -> None:
        spec = build_transaction(
            "ac_base_info",
            {
                "one_duct_system": True,
                "records": [{"ac": 0, "group_start": 0, "group_count": 8, "brand": 0x1200, "name": "Home"}],
            },
        )

        self.assertEqual(spec.command, 0x74)
        self.assertEqual(spec.payload.hex(" ").upper(), "01 01 00 80 12 00 48 6F 6D 65 00 00 00 00")

    def test_build_ac_timer_table_transaction(self) -> None:
        spec = build_transaction(
            "ac_timer_table",
            {
                "ac_count": 1,
                "records": [
                    {
                        "ac": 0,
                        "on_timer": {"enabled": True, "hour": 6, "minute": 15},
                        "off_timer": {"enabled": False, "hour": 22, "minute": 45},
                    }
                ],
            },
        )

        self.assertEqual(spec.command, 0x36)
        self.assertEqual(spec.payload[:8].hex(" ").upper(), "06 0F 96 2D 00 00 00 00")

    def test_build_program_define_transaction(self) -> None:
        spec = build_transaction(
            "program_define_new",
            {
                "program_count": 1,
                "linked_ac": True,
                "records": [
                    {
                        "program": 0,
                        "enabled": True,
                        "name": "Weekday",
                        "days_bitmap": 0x3E,
                        "on_timer": {"enabled": True, "hour": 7, "minute": 0},
                        "off_timer": {"enabled": True, "hour": 18, "minute": 30},
                    }
                ],
            },
        )

        self.assertEqual(spec.command, 0x3C)
        self.assertEqual(len(spec.payload), 260)
        self.assertEqual(spec.payload[0:4].hex(" ").upper(), "01 01 00 20")

    def test_rejects_unknown_action(self) -> None:
        with self.assertRaises(CommandRequestError):
            build_transaction("bogus", {})


if __name__ == "__main__":
    unittest.main()
