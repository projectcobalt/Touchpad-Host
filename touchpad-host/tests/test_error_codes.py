from __future__ import annotations

import unittest

from airtouch4.error_codes import describe_ac_error


class ErrorCodeTests(unittest.TestCase):
    def test_samsung_uses_apk_display_table(self) -> None:
        error = describe_ac_error(4608, 250)

        self.assertIsNotNone(error)
        self.assertEqual(error["brand"], "Samsung")
        self.assertEqual(error["display_code"], "EA")
        self.assertEqual(error["label"], "Samsung Code:EA")

    def test_gateway_main_module_error_keeps_apk_empty_error_text(self) -> None:
        error = describe_ac_error(4608, 65534)

        self.assertIsNotNone(error)
        self.assertEqual(error["display_code"], "FFFE")
        self.assertEqual(error["label"], "Samsung Code:FFFE")
        self.assertEqual(error["description"], "Error in the communication of the gateway with the main module.")

    def test_mhi_prefixes_e_like_apk_table(self) -> None:
        error = describe_ac_error(3840, 12)

        self.assertIsNotNone(error)
        self.assertEqual(error["brand"], "MHI")
        self.assertEqual(error["display_code"], "E12")
        self.assertEqual(error["label"], "MHI Code:E12")


if __name__ == "__main__":
    unittest.main()
