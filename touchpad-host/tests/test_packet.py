from __future__ import annotations

import unittest

from airtouch4 import AirTouchPacket, build_packet, extract_packets, parse_packet


class PacketTests(unittest.TestCase):
    def test_parse_raw_temperature_heartbeat(self) -> None:
        data = bytes.fromhex("55 55 55 AA 80 90 B3 26 00 03 00 CC 00 D3 B2")
        packet = parse_packet(data)

        self.assertTrue(packet.raw_mode)
        self.assertTrue(packet.crc_ok)
        self.assertEqual(packet.dest, 0x80)
        self.assertEqual(packet.src, 0x90)
        self.assertEqual(packet.packet_id, 0xB3)
        self.assertEqual(packet.command, 0x26)
        self.assertEqual(packet.payload, bytes.fromhex("00 CC 00"))
        self.assertEqual(packet.command_name, "SET_TEMPERATURE")

    def test_build_matches_capture_frame(self) -> None:
        encoded = build_packet(
            dest=0x90,
            src=0x80,
            packet_id=0xB3,
            command=0x27,
            payload=bytes.fromhex("16"),
            raw_mode=True,
        )

        self.assertEqual(encoded.hex(" ").upper(), "55 55 55 AA 90 80 B3 27 00 01 16 F9 1B")

    def test_extract_packets_from_noisy_stream(self) -> None:
        frame = build_packet(dest=0x9F, src=0x80, packet_id=1, command=0x23, payload=b"\x00" * 8, raw_mode=True)
        packets = extract_packets(b"\x00junk" + frame + b"\x99")

        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0].stream_offset, 5)
        self.assertTrue(packets[0].crc_ok)

    def test_raw_stuffing_round_trip(self) -> None:
        packet = AirTouchPacket(dest=0x80, src=0x90, packet_id=1, command=0x26, payload=b"\x55\x55\x55\x55", raw_mode=True)
        stuffed = packet.encode(stuff_raw=True)
        parsed = parse_packet(stuffed)

        self.assertEqual(parsed.payload, packet.payload)
        self.assertTrue(parsed.crc_ok)


if __name__ == "__main__":
    unittest.main()
