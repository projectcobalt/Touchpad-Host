from __future__ import annotations

import unittest

from airtouch4.packet import parse_packet
from airtouch4.session.touchscreen import TouchscreenSession, parse_command_list, parse_hex_payload


class TouchscreenSessionTests(unittest.TestCase):
    def test_build_heartbeat(self) -> None:
        session = TouchscreenSession(next_packet_id=0xB3, heartbeat_payload=bytes.fromhex("00 CC 00"))
        packet, wire = session.build_heartbeat()

        self.assertEqual(packet.command, 0x26)
        self.assertEqual(packet.dest, 0x80)
        self.assertEqual(packet.src, 0x90)
        self.assertEqual(packet.packet_id, 0xB3)
        self.assertEqual(wire.hex(" ").upper(), "55 55 55 AA 80 90 B3 26 00 03 00 CC 00 D3 B2")

    def test_build_sync_requests_advance_sequence(self) -> None:
        session = TouchscreenSession(next_packet_id=1, sync_commands=(0x61, 0x75))
        requests = session.build_sync_requests()

        self.assertEqual([packet.command for packet, _wire in requests], [0x61, 0x75])
        self.assertEqual([packet.packet_id for packet, _wire in requests], [1, 2])
        self.assertEqual(session.next_packet_id, 3)

    def test_choose_available_address(self) -> None:
        session = TouchscreenSession(auto_address=True)
        session.seen_touchpad_addresses.add(1)

        self.assertEqual(session.choose_available_address(), 0x91)

    def test_choose_preferred_address_only_when_free(self) -> None:
        session = TouchscreenSession()
        session.seen_touchpad_addresses.add(1)

        self.assertEqual(session.choose_available_address(0x90), 0x91)
        self.assertEqual(session.src, 0x91)

    def test_choose_address_returns_none_when_both_slots_seen(self) -> None:
        session = TouchscreenSession()
        session.seen_touchpad_addresses.update({1, 2})

        self.assertIsNone(session.choose_available_address())

    def test_feed_rx_extracts_packets(self) -> None:
        session = TouchscreenSession()
        _packet, wire = session.build_heartbeat()
        packets = session.feed_rx(b"noise" + wire[:8])

        self.assertEqual(packets, [])
        packets = session.feed_rx(wire[8:])

        self.assertEqual(len(packets), 1)
        self.assertEqual(parse_packet(wire).command, packets[0].command)

    def test_parse_helpers(self) -> None:
        self.assertEqual(parse_hex_payload("00 EA 00"), bytes.fromhex("00 EA 00"))
        self.assertEqual(parse_command_list("0x61, 117,0x79"), (0x61, 117, 0x79))


if __name__ == "__main__":
    unittest.main()
