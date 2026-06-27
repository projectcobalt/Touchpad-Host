from __future__ import annotations

import unittest

from airtouch4.state import AirTouchState


class AirTouchStateTests(unittest.TestCase):
    def test_sensor_view_exposes_explicit_zone_mapping(self) -> None:
        state = AirTouchState()
        state.acs = {
            0: {"base": {"group_start": 0, "group_count": 2, "name": "Downstairs"}},
            1: {"base": {"group_start": 2, "group_count": 2, "name": "Upstairs"}},
        }
        state.groups = {
            0: {
                "name": "Living",
                "grouping": {"thermostat": 2, "zone_start": 0, "zone_count": 1},
                "status": {"has_sensor": True},
            },
            2: {
                "name": "Bedroom",
                "grouping": {"thermostat": 2, "zone_start": 2, "zone_count": 1},
                "status": {"has_sensor": True},
            },
        }
        state.sensors = {
            2: {
                "kind": "rf",
                "sensor_name": "rf_sensor_2",
                "temperature": 22.5,
                "listed": True,
                "present": True,
            }
        }

        row = state.sensor_view()[0]

        self.assertEqual(row["mapped_groups"], ["Living", "Bedroom"])
        self.assertEqual(row["mapped_group_ids"], [0, 2])
        self.assertEqual(row["mapped_zones"], [
            {
                "group_id": 0,
                "zone_id": 0,
                "zone_number": 1,
                "name": "Living",
                "source": "grouping.thermostat",
                "ac_id": 0,
                "damper_zone_start": 0,
                "damper_zone_count": 1,
            },
            {
                "group_id": 2,
                "zone_id": 2,
                "zone_number": 3,
                "name": "Bedroom",
                "source": "grouping.thermostat",
                "ac_id": 1,
                "damper_zone_start": 2,
                "damper_zone_count": 1,
            },
        ])

    def test_sensor_view_can_fall_back_to_status_sensor(self) -> None:
        state = AirTouchState()
        state.groups = {
            1: {
                "name": "Office",
                "status": {"sensor": 4, "has_sensor": True},
            }
        }
        state.sensors = {4: {"kind": "rf", "sensor_name": "rf_sensor_4"}}

        row = state.sensor_view()[0]

        self.assertEqual(row["mapped_group_ids"], [1])
        self.assertEqual(row["mapped_zones"], [
            {
                "group_id": 1,
                "zone_id": 1,
                "zone_number": 2,
                "name": "Office",
                "source": "group_status.sensor",
            }
        ])

    def test_supply_air_rows_have_empty_zone_mapping_fields(self) -> None:
        state = AirTouchState()
        state.system["supply_air"] = [{"ac": 0, "status": "ok", "temperature": 12.5}]

        row = state.sensor_view()[0]

        self.assertEqual(row["kind"], "supply_air")
        self.assertEqual(row["mapped_groups"], [])
        self.assertEqual(row["mapped_group_ids"], [])
        self.assertEqual(row["mapped_zones"], [])


if __name__ == "__main__":
    unittest.main()
