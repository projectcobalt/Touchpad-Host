from __future__ import annotations

import unittest

from airtouch4.service.adaptive_airtouch import translate_airtouch_snapshot


class AdaptiveAirTouchTranslatorTests(unittest.TestCase):
    def test_group_with_temperature_becomes_learning_room(self) -> None:
        snapshot = translate_airtouch_snapshot(
            {
                "acs": {0: {"base": {"name": "Home", "group_start": 0, "group_count": 1}, "status": {"power_on": True, "mode": 4}}},
                "active_groups": {0: {"name": "Lounge", "status": {"power_name": "on", "temperature": 22, "setpoint": 23}}},
            }
        )

        room = snapshot.devices[0].rooms[0]

        self.assertTrue(room.learn)
        self.assertFalse(room.configured_control)
        self.assertFalse(room.control_enabled)
        self.assertEqual(room.temperature, 22.0)

    def test_control_zone_checkbox_maps_to_configured_control(self) -> None:
        snapshot = translate_airtouch_snapshot(
            {
                "acs": {0: {"base": {"name": "Home", "group_start": 0, "group_count": 2}, "status": {"power_on": True, "mode": 4}}},
                "active_groups": {
                    0: {"name": "Lounge", "status": {"power_name": "on", "temperature": 22}},
                    1: {"name": "Bedroom", "status": {"power_name": "on", "temperature": 21}},
                },
            },
            control_zones=(1,),
            control_active=False,
        )

        rooms = {room.id: room for room in snapshot.devices[0].rooms}

        self.assertFalse(rooms[0].configured_control)
        self.assertFalse(rooms[0].control_enabled)
        self.assertTrue(rooms[1].configured_control)
        self.assertFalse(rooms[1].control_enabled)

    def test_control_zone_asserts_control_only_when_control_active(self) -> None:
        snapshot = translate_airtouch_snapshot(
            {
                "acs": {0: {"base": {"name": "Home", "group_start": 1, "group_count": 1}, "status": {"power_on": True, "mode": 4}}},
                "active_groups": {
                    1: {"name": "Bedroom", "status": {"power_name": "on", "temperature": 21}},
                },
            },
            control_zones=(1,),
            control_active=True,
        )

        rooms = {room.id: room for room in snapshot.devices[0].rooms}

        self.assertTrue(rooms[1].configured_control)
        self.assertTrue(rooms[1].control_enabled)

    def test_active_zones_get_equal_share_power_fraction_without_percentages(self) -> None:
        snapshot = translate_airtouch_snapshot(
            {
                "acs": {0: {"base": {"name": "Home", "group_start": 0, "group_count": 3}, "status": {"power_on": True, "mode": 4}}},
                "active_groups": {
                    0: {"name": "Lounge", "status": {"power_name": "on", "temperature": 22}},
                    1: {"name": "Bedroom", "status": {"power_name": "on", "temperature": 21}},
                    2: {"name": "Spare", "status": {"power_name": "off", "temperature": 23}},
                },
            }
        )

        rooms = {room.id: room for room in snapshot.devices[0].rooms}

        self.assertEqual(rooms[0].power_fraction, 0.5)
        self.assertEqual(rooms[1].power_fraction, 0.5)
        self.assertEqual(rooms[2].power_fraction, 0.0)

    def test_active_zone_power_fraction_uses_percentage_when_available(self) -> None:
        snapshot = translate_airtouch_snapshot(
            {
                "acs": {0: {"base": {"name": "Home", "group_start": 0, "group_count": 2}, "status": {"power_on": True, "mode": 4}}},
                "active_groups": {
                    0: {"name": "Lounge", "status": {"power_name": "on", "temperature": 22, "percentage": 75}},
                    1: {"name": "Bedroom", "status": {"power_name": "on", "temperature": 21, "percentage": 25}},
                },
            }
        )

        rooms = {room.id: room for room in snapshot.devices[0].rooms}

        self.assertEqual(rooms[0].power_fraction, 0.75)
        self.assertEqual(rooms[1].power_fraction, 0.25)

    def test_inactive_zone_percentage_is_still_normalized_for_diagnostics(self) -> None:
        snapshot = translate_airtouch_snapshot(
            {
                "acs": {0: {"base": {"name": "Home", "group_start": 0, "group_count": 1}, "status": {"power_on": False, "mode": 4}}},
                "active_groups": {
                    0: {"name": "Lounge", "status": {"power_name": "off", "temperature": 22, "percentage": 75}},
                },
            }
        )

        self.assertEqual(snapshot.devices[0].rooms[0].power_fraction, 0.75)


if __name__ == "__main__":
    unittest.main()
