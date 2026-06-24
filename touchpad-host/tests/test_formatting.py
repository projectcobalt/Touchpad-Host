from __future__ import annotations

import unittest

from airtouch4.formatting import MonitorStats, decode_live_payload, format_packet_line, should_show
from airtouch4.packet import AirTouchPacket
from airtouch4.payloads import decode_mainboard_payload


class FormattingTests(unittest.TestCase):
    def test_expansion_damper_status_is_skipped_by_default(self) -> None:
        packet = AirTouchPacket(dest=0x81, src=0x80, packet_id=1, command=0x24, payload=bytes.fromhex("00 00 00 00 00 00 3A 98 64 64 64 64 64 64 64 64"))
        decoded = decode_mainboard_payload(packet.command, packet.payload)

        self.assertEqual(decoded["type"], "expansion_damper_status")
        self.assertEqual(decoded["expansion_damper_percentages"], [100, 100, 100, 100, 100, 100, 100, 100])
        self.assertFalse(should_show(decoded))
        self.assertTrue(should_show(decoded, show_skipped=True))

    def test_client_bulk_info_is_reference_traffic_in_live_tools(self) -> None:
        packet = AirTouchPacket(dest=0x80, src=0xB0, packet_id=1, command=0x2F, payload=bytes.fromhex("03 FF"))
        decoded = decode_live_payload(packet)

        self.assertEqual(decoded["type"], "non_emulation_reference_traffic")
        self.assertFalse(should_show(decoded))

    def test_touchscreen_status_formats_as_human_line(self) -> None:
        packet = AirTouchPacket(dest=0x9F, src=0x80, packet_id=1, command=0x21, payload=bytes.fromhex("00 E4 13 80 7C 10"))
        line = format_packet_line("rx", packet)

        self.assertIn("0x21", line)
        self.assertIn("g0:off", line)

    def test_stats_reports_skipped_not_unknown_for_resolved_families(self) -> None:
        packet = AirTouchPacket(dest=0x81, src=0x80, packet_id=1, command=0x24, payload=bytes.fromhex("00 00 00 00 00 00 3A 98 64 64 64 64 64 64 64 64"))
        decoded = decode_mainboard_payload(packet.command, packet.payload)
        stats = MonitorStats()

        stats.observe("rx", packet, decoded, shown=False)

        self.assertEqual(sum(stats.skipped.values()), 1)
        self.assertEqual(sum(stats.undecoded.values()), 0)


if __name__ == "__main__":
    unittest.main()
