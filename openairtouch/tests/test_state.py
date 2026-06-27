from __future__ import annotations

import unittest

from airtouch4.state import AirTouchState


class AirTouchStateTests(unittest.TestCase):
    def test_sensor_view_resolves_group_local_rf_sensor_slots(self) -> None:
        state = AirTouchState()
        state.system["group_count"] = 3
        state.acs = {
            0: {"base": {"group_start": 0, "group_count": 3, "name": "Downstairs"}},
        }
        state.groups = {
            0: {
                "name": "Living",
                "grouping": {"thermostat": 0, "zone_start": 0, "zone_count": 1},
                "status": {"has_sensor": True},
            },
            1: {
                "name": "Bedroom",
                "grouping": {"thermostat": 0, "zone_start": 1, "zone_count": 1},
                "status": {"has_sensor": True},
            },
            2: {
                "name": "Spill",
                "grouping": {"thermostat": 0, "zone_start": 2, "zone_count": 1},
                "status": {"has_sensor": False},
            },
        }
        state.sensors = {
            0: {"kind": "rf", "sensor_name": "rf_sensor_0", "temperature": 21.0},
            2: {"kind": "rf", "sensor_name": "rf_sensor_2", "temperature": 20.0},
        }

        rows = {row["id"]: row for row in state.sensor_view()}

        self.assertEqual(rows[0]["mapping_status"], "resolved")
        self.assertEqual(rows[0]["resolved_group_id"], 0)
        self.assertEqual(rows[0]["mapped_group_ids"], [0])
        self.assertEqual(rows[0]["mapped_zones"], [
            {
                "group_id": 0,
                "zone_id": 0,
                "zone_number": 1,
                "name": "Living",
                "source": "grouping.sensor_slot",
                "sensor_id": 0,
                "sensor_kind": "rf",
                "sensor_slot": 1,
                "ac_id": 0,
                "damper_zone_start": 0,
                "damper_zone_count": 1,
            }
        ])
        self.assertEqual(rows[2]["mapping_status"], "resolved")
        self.assertEqual(rows[2]["resolved_group_id"], 1)
        self.assertEqual(rows[2]["mapped_group_ids"], [1])

    def test_snapshot_exposes_zone_backing_sensor(self) -> None:
        state = AirTouchState()
        state.system["group_count"] = 1
        state.groups = {
            0: {
                "name": "Living",
                "grouping": {"thermostat": 0, "zone_start": 0, "zone_count": 1},
                "status": {"has_sensor": True},
            },
        }

        status = state.snapshot()["active_groups"][0]["status"]

        self.assertEqual(status["sensor_id"], 0)
        self.assertEqual(status["sensor_kind"], "rf")
        self.assertEqual(status["sensor_slot"], 1)
        self.assertEqual(status["sensor_source"], "grouping.sensor_slot")
        self.assertEqual(status["sensor_mapping_status"], "resolved")

    def test_sensor_view_falls_back_to_resolved_zone_temperature(self) -> None:
        state = AirTouchState()
        state.system["group_count"] = 1
        state.groups = {
            0: {
                "name": "Living",
                "grouping": {"thermostat": 0, "zone_start": 0, "zone_count": 1},
                "status": {"has_sensor": True, "temperature": 19, "low_battery": False},
            },
        }
        state.sensors = {
            0: {"kind": "rf", "sensor_name": "rf_sensor_0", "listed": True, "present": True}
        }

        row = state.sensor_view()[0]

        self.assertEqual(row["temperature"], 19)
        self.assertFalse(row["low_battery"])
        self.assertIsNone(row["battery"])
        self.assertIsNone(row["signal"])

    def test_sensor_view_prefers_sensor_info_over_zone_temperature(self) -> None:
        state = AirTouchState()
        state.system["group_count"] = 1
        state.groups = {
            0: {
                "name": "Living",
                "grouping": {"thermostat": 0, "zone_start": 0, "zone_count": 1},
                "status": {"has_sensor": True, "temperature": 19},
            },
        }
        state.sensors = {
            0: {"kind": "rf", "sensor_name": "rf_sensor_0", "temperature": 20, "battery": 90, "signal": -70}
        }

        row = state.sensor_view()[0]

        self.assertEqual(row["temperature"], 20)
        self.assertEqual(row["battery"], 90)
        self.assertEqual(row["signal"], -70)

    def test_sensor_view_marks_multiple_explicit_owners_ambiguous(self) -> None:
        state = AirTouchState()
        state.groups = {
            1: {
                "name": "Office",
                "status": {"sensor": 4, "has_sensor": True},
            },
            2: {
                "name": "Guest",
                "status": {"sensor": 4, "has_sensor": True},
            },
        }
        state.sensors = {4: {"kind": "rf", "sensor_name": "rf_sensor_4"}}

        row = state.sensor_view()[0]

        self.assertEqual(row["mapping_status"], "ambiguous")
        self.assertIsNone(row["resolved_group_id"])
        self.assertEqual(row["mapped_group_ids"], [])
        self.assertEqual(row["mapped_zones"], [])
        self.assertEqual(row["mapping_candidate_group_ids"], [1, 2])

    def test_sensor_view_marks_unowned_rf_sensor_unmapped(self) -> None:
        state = AirTouchState()
        state.groups = {
            1: {
                "name": "Office",
                "grouping": {"thermostat": 0},
                "status": {"has_sensor": True},
            }
        }
        state.sensors = {
            2: {"kind": "rf", "sensor_name": "rf_sensor_2"},
            4: {"kind": "rf", "sensor_name": "rf_sensor_4"},
        }

        rows = {row["id"]: row for row in state.sensor_view()}

        self.assertEqual(rows[2]["mapping_status"], "resolved")
        self.assertEqual(rows[4]["mapping_status"], "unmapped")
        self.assertIsNone(rows[4]["resolved_group_id"])

    def test_supply_air_rows_have_empty_zone_mapping_fields(self) -> None:
        state = AirTouchState()
        state.system["supply_air"] = [{"ac": 0, "status": "ok", "temperature": 12.5}]

        row = state.sensor_view()[0]

        self.assertEqual(row["kind"], "supply_air")
        self.assertEqual(row["mapping_status"], "unmapped")
        self.assertIsNone(row["resolved_group_id"])
        self.assertEqual(row["mapped_groups"], [])
        self.assertEqual(row["mapped_group_ids"], [])
        self.assertEqual(row["mapped_zones"], [])


if __name__ == "__main__":
    unittest.main()
