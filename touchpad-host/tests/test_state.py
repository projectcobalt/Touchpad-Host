from __future__ import annotations

import unittest

from airtouch4.commands import set_program_define_new
from airtouch4.packet import AirTouchPacket
from airtouch4.state import AirTouchState


def packet(command: int, payload_hex: str) -> AirTouchPacket:
    return AirTouchPacket(dest=0x91, src=0x80, packet_id=1, command=command, payload=bytes.fromhex(payload_hex))


class AirTouchStateTests(unittest.TestCase):
    def test_applies_core_init_state(self) -> None:
        state = AirTouchState()

        state.apply_packet(packet(0x61, "05 64 FF FF 04 11 37 19 27 10 00 11 00 00 00"))
        state.apply_packet(packet(0x53, "00 4C 6F 75 6E 67 65 00 00"))
        state.apply_packet(packet(0x21, "00 E4 13 80 67 10"))
        state.apply_packet(packet(0x67, "00 00 0A 00 13"))
        state.apply_packet(packet(0x69, "01 00 00 00 20 00"))
        state.apply_packet(packet(0x71, "01 53 00 00 00 03 FF FF FF FF"))

        self.assertEqual(state.system["group_count"], 6)
        self.assertEqual(state.groups[0]["name"], "Lounge")
        self.assertEqual(state.groups[0]["status"]["setpoint"], 23)
        self.assertEqual(state.groups[0]["grouping"]["min_percent"], 10)
        self.assertTrue(state.groups[5]["spill_configured"])
        self.assertIn(0x90, state.sensors)
        self.assertIn(0x91, state.sensors)
        self.assertTrue(state.sensors[0x90]["listed"])
        self.assertTrue(state.sensors[0x91]["present"])
        self.assertEqual(state.sensors[1]["sensor_name"], "rf_sensor_1")
        self.assertEqual(list(state.active_groups()), [0, 5])

    def test_applies_ac_and_ui_state(self) -> None:
        state = AirTouchState()

        state.apply_packet(packet(0x75, "01 01 00 60 12 00 48 6F 6D 65 00 00 00 00"))
        state.apply_packet(packet(0x23, "00 00 13 00 FF 02 FF FE"))
        state.apply_packet(packet(0x33, "00 44 61 79 00 00 00 00 00 11 00"))
        state.apply_packet(packet(0x31, "00 44 61 79 00 00 00 00 00"))
        state.apply_packet(AirTouchPacket(dest=0x91, src=0x80, packet_id=1, command=0x3D, payload=set_program_define_new([{
            "program": 0,
            "enabled": True,
            "name": "Weekday",
            "days_bitmap": 0x3E,
            "on_timer": {"enabled": True, "hour": 7, "minute": 0},
            "off_timer": {"enabled": True, "hour": 18, "minute": 30},
        }], program_count=1, linked_ac=True)))
        state.apply_packet(packet(0x6B, "42 77 20 41 69 72 00 00 00 00 30 34 31 31 20 30 34 36 20 33 34 39 01 05 09 C1 00 00 00 00"))
        state.apply_packet(packet(0x27, "16"))

        self.assertEqual(state.acs[0]["base"]["name"], "Home")
        self.assertEqual(state.acs[0]["base"]["group_start"], 0)
        self.assertEqual(state.acs[0]["base"]["group_count"], 6)
        self.assertEqual(state.acs[0]["status"]["setpoint"], 23)
        self.assertEqual(state.favourites[0]["name"], "Day")
        self.assertEqual(state.system["active_favourite"], 0)
        self.assertEqual(state.system["program_count"], 1)
        self.assertTrue(state.system["programs_linked_ac"])
        self.assertEqual(state.programs[0]["name"], "Weekday")
        self.assertEqual(state.service["company"], "Bw Air")
        self.assertEqual(state.last_led["led_code"], 0x16)

    def test_sensor_list_replaces_current_listing_and_info_updates_health(self) -> None:
        state = AirTouchState()

        state.apply_packet(packet(0x71, "01 53 00 00 00 03 FF FF FF FF"))
        state.apply_packet(packet(
            0x73,
            "06 E4 64 45 01 02 03 04 05 06 07 08"
            "04 E4 64 FF 11 12 13 14 15 16 17 18"
            "90 EA 00 FF 21 22 23 24 25 26 27 28",
        ))

        self.assertTrue(state.sensors[6]["listed"])
        self.assertTrue(state.sensors[6]["present"])
        self.assertEqual(state.sensors[6]["status"], "ok")
        self.assertEqual(state.sensors[6]["temperature"], 33)
        self.assertEqual(state.sensors[6]["signal"], -69)
        self.assertFalse(state.sensors[4]["present"])
        self.assertEqual(state.sensors[4]["status"], "missing")
        self.assertIsNone(state.sensors[4]["temperature"])
        self.assertEqual(state.sensors[0x90]["kind"], "touchpad")
        self.assertEqual(state.sensors[0x90]["temperature"], 37)

        state.apply_packet(packet(0x71, "01 53 00 00 00 01 FF FF FF FF"))

        self.assertTrue(state.sensors[0x90]["listed"])
        self.assertFalse(state.sensors[0x91]["listed"])
        self.assertFalse(state.sensors[0x91]["present"])


if __name__ == "__main__":
    unittest.main()
