from __future__ import annotations

import unittest

from airtouch4.payloads import decode_capture_payload, decode_mainboard_payload
from airtouch4.payloads.common import encode_internal_temperature


class PayloadTests(unittest.TestCase):
    def test_decode_internal_group_status(self) -> None:
        decoded = decode_mainboard_payload(0x21, bytes.fromhex("01 32 56 80 CC 00"))

        self.assertEqual(decoded["type"], "group_status_internal")
        self.assertEqual(decoded["record_count"], 1)
        record = decoded["records"][0]
        self.assertEqual(record["group"], 1)
        self.assertEqual(record["power_name"], "off")
        self.assertTrue(record["has_sensor"])
        self.assertEqual(record["temperature"], 31)

    def test_decode_touchpad_presence(self) -> None:
        decoded = decode_mainboard_payload(0x1F, bytes.fromhex("FF 01 D0 10 41 1D 55 26 19 C9 D1 00 00 00 00 00 00 00 00 70 05 31 2E 34 2E 34"))

        self.assertEqual(decoded["expanded_name"], "touchpad_address_presence")
        self.assertEqual(decoded["address"], 1)
        self.assertEqual(decoded["software_version"], "1.4.4")

    def test_decode_heartbeat_and_led(self) -> None:
        heartbeat = decode_mainboard_payload(0x26, bytes.fromhex("00 EA 00"))
        led = decode_mainboard_payload(0x27, bytes.fromhex("16"))

        self.assertEqual(heartbeat["type"], "touchpad_temperature")
        self.assertEqual(heartbeat["temperature"], 37)
        self.assertEqual(led["type"], "led_response")
        self.assertEqual(led["led_code"], 0x16)

    def test_encode_internal_temperature_round_trips_touchpad_values(self) -> None:
        for temperature, raw in ((11, 0x24), (23, 0x78), (25, 0x8C), (30, 0xBE), (37, 0xEA)):
            self.assertEqual(encode_internal_temperature(temperature), raw)
            decoded = decode_mainboard_payload(0x26, bytes((0x00, raw, 0x00)))
            self.assertEqual(decoded["temperature"], temperature)

    def test_decode_client_group_status_request(self) -> None:
        decoded = decode_capture_payload(0x2B, b"")

        self.assertEqual(decoded["type"], "group_status_client_request")

    def test_decode_client_group_control(self) -> None:
        decoded = decode_capture_payload(0x2A, bytes.fromhex("06 90 00 00"))

        self.assertEqual(decoded["type"], "group_control_client")
        self.assertEqual(decoded["group"], 6)
        self.assertEqual(decoded["ui_zone"], 7)
        self.assertEqual(decoded["power_name"], "unchanged")
        self.assertEqual(decoded["control_method"], "damper")
        self.assertEqual(decoded["setting"], {"damper_percentage": 0})

    def test_decode_client_group_status(self) -> None:
        decoded = decode_capture_payload(0x2B, bytes.fromhex("41 32 16 80 5A 00"))

        self.assertEqual(decoded["type"], "group_status_client")
        record = decoded["records"][0]
        self.assertEqual(record["group"], 1)
        self.assertEqual(record["power_name"], "on")
        self.assertEqual(record["control_method"], "damper")
        self.assertEqual(record["temperature"], 22.0)

    def test_decode_client_ac_status(self) -> None:
        decoded = decode_capture_payload(0x2D, bytes.fromhex("41 43 16 00 5A 00 00 00"))

        self.assertEqual(decoded["type"], "ac_status_client")
        record = decoded["records"][0]
        self.assertEqual(record["ac"], 1)
        self.assertTrue(record["power_on"])
        self.assertEqual(record["mode"], 4)
        self.assertEqual(record["fan"], 3)
        self.assertEqual(record["setpoint"], 22)
        self.assertEqual(record["sensor_temp"], 22.0)

    def test_decode_init_ui_payloads(self) -> None:
        group_names = decode_mainboard_payload(
            0x53,
            bytes.fromhex("00 4C 6F 75 6E 67 65 00 00 01 4D 61 73 74 65 72 00 00"),
        )
        favourite = decode_mainboard_payload(0x33, bytes.fromhex("00 44 61 79 00 00 00 00 00 11 00"))
        password = decode_mainboard_payload(0x6D, bytes.fromhex("01 01 08 20 20 20 20 20 20 20 20"))
        service = decode_mainboard_payload(0x6B, bytes.fromhex("42 77 20 41 69 72 00 00 00 00 30 34 31 31 20 30 34 36 20 33 34 39 01 05 09 C1 00 00 00 00"))
        timer = decode_mainboard_payload(0x37, bytes.fromhex("80 00 09 1E"))

        self.assertEqual(group_names["records"][0]["name"], "Lounge")
        self.assertEqual(group_names["records"][1]["name"], "Master")
        self.assertEqual(favourite["records"][0]["name"], "Day")
        self.assertEqual(password["page"], 1)
        self.assertTrue(password["enabled"])
        self.assertEqual(service["company"], "Bw Air")
        self.assertEqual(service["phone"], "0411 046 349")
        self.assertFalse(timer["records"][0]["timer"]["enabled"])
        self.assertEqual(timer["records"][1]["timer"]["minute"], 30)

    def test_decode_sensor_list_and_info(self) -> None:
        sensor_list = decode_mainboard_payload(0x71, bytes.fromhex("80 53 00 00 00 03 FF FE E4 EA"))

        self.assertTrue(sensor_list["pairing"])
        self.assertEqual(sensor_list["rf_sensor_addresses"], [0, 1, 4, 6])
        self.assertEqual(sensor_list["touchpad_addresses"], [0x90, 0x91])
        self.assertEqual(sensor_list["sensor_count"], 6)
        self.assertEqual(sensor_list["supply_air"][0]["status"], "disabled")
        self.assertEqual(sensor_list["supply_air"][1]["status"], "error")
        self.assertEqual(sensor_list["supply_air"][2]["temperature"], 33)
        self.assertEqual(sensor_list["supply_air"][3]["temperature"], 37)

        sensor_info = decode_mainboard_payload(
            0x73,
            bytes.fromhex(
                "06 E4 64 45 01 02 03 04 05 06 07 08"
                "04 E4 64 FF 11 12 13 14 15 16 17 18"
                "90 EA 00 FF 21 22 23 24 25 26 27 28"
            ),
        )

        ok, missing, touchpad = sensor_info["records"]
        self.assertEqual(ok["status"], "ok")
        self.assertEqual(ok["temperature"], 33)
        self.assertEqual(ok["battery"], 100)
        self.assertEqual(ok["signal"], -69)
        self.assertEqual(ok["mac"], "0102030405060708")
        self.assertEqual(missing["status"], "missing")
        self.assertIsNone(missing["temperature"])
        self.assertIsNone(missing["battery"])
        self.assertIsNone(missing["mac"])
        self.assertEqual(touchpad["kind"], "touchpad")
        self.assertEqual(touchpad["status"], "ok")
        self.assertEqual(touchpad["temperature"], 37)
        self.assertIsNone(touchpad["battery"])

    def test_decode_grouping_sensor_selector_flags(self) -> None:
        decoded = decode_mainboard_payload(0x67, bytes.fromhex("08 08 00 01 01 09 09 00 FF 00"))

        group8, group9 = decoded["records"]
        self.assertEqual(group8["ui_zone"], 9)
        self.assertEqual(group8["thermostat"], 1)
        self.assertEqual(group8["thermostat_name"], "rf_sensor_1")
        self.assertEqual(group8["available_selectors"], ["rf_sensor_1"])
        self.assertTrue(group8["has_sensor_1"])
        self.assertEqual(group9["ui_zone"], 10)
        self.assertEqual(group9["thermostat_name"], "auto")
        self.assertEqual(group9["available_selectors"], [])

    def test_decode_expansion_damper_active_ui_zones(self) -> None:
        decoded = decode_mainboard_payload(
            0x24,
            bytes.fromhex("00 00 00 00 00 00 3A 98 64 00 00 00 00 00 00 00"),
        )

        self.assertEqual(decoded["expansion_damper_percentages"], [100, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(decoded["active_expansion_ui_zones"], [9])


if __name__ == "__main__":
    unittest.main()
