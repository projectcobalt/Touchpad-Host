from __future__ import annotations

from collections import deque
import unittest
from typing import Iterable

from airtouch4.packet import AirTouchPacket
from airtouch4.runtime import AirTouchRuntime, RuntimeConfig
from airtouch4.session.queue import TransactionSpec


class FakeTransport:
    def __init__(self, reads: Iterable[bytes] = ()) -> None:
        self.reads = deque(reads)
        self.writes: list[bytes] = []

    def read(self, size: int = 512) -> bytes:
        if self.reads:
            return self.reads.popleft()
        return b""

    def write(self, data: bytes | bytearray | Iterable[int]) -> int:
        wire = bytes(data)
        self.writes.append(wire)
        return len(wire)


def wire_packet(command: int, payload: bytes = b"", *, src: int = 0x80, dest: int = 0x90) -> bytes:
    return AirTouchPacket(
        dest=dest,
        src=src,
        packet_id=1,
        command=command,
        payload=payload,
        raw_mode=True,
    ).encode(stuff_raw=True)


def touchpad_info_wire(slot: int, *, src: int | None = None) -> bytes:
    payload = (
        bytes.fromhex("FF 01")
        + bytes([0xD0, 0x10, 0x41, 0x1D, 0x55, 0x26, 0x19, 0xC0 + slot])
        + bytes([0xD0 | slot])
        + bytes(8)
        + bytes([0x00, 0x03])
        + b"1.0"
    )
    return wire_packet(0x1F, payload, src=src or (0x8F + slot), dest=0x9F)


class RuntimeTests(unittest.TestCase):
    def test_active_start_sends_touchpad_presence_request(self) -> None:
        transport = FakeTransport()
        runtime = AirTouchRuntime(transport, RuntimeConfig(detect_seconds=0.0))

        events = runtime.start(now=0.0)

        self.assertEqual(events[0].event, "tx")
        self.assertEqual(events[0].packet.command, 0x1F)
        self.assertEqual(events[0].packet.dest, 0x9F)
        self.assertEqual(transport.writes[0], events[0].wire)
        self.assertTrue(runtime.boot_complete)

    def test_configured_source_address_is_used(self) -> None:
        transport = FakeTransport()
        runtime = AirTouchRuntime(
            transport,
            RuntimeConfig(detect_seconds=0.0, source_address=0x91),
        )

        events = runtime.start(now=0.0)

        self.assertEqual(events[0].packet.src, 0x91)
        self.assertEqual(runtime.snapshot()["runtime"]["src"], "0x91")

    def test_preferred_occupied_source_uses_free_slot(self) -> None:
        transport = FakeTransport([touchpad_info_wire(1)])
        runtime = AirTouchRuntime(
            transport,
            RuntimeConfig(detect_seconds=0.01, source_address=0x90),
        )

        runtime.start()

        self.assertEqual(runtime.snapshot()["runtime"]["src"], "0x91")
        self.assertTrue(runtime.address_assigned)

    def test_both_touchpad_addresses_occupied_holds_before_init(self) -> None:
        transport = FakeTransport([touchpad_info_wire(1) + touchpad_info_wire(2)])
        runtime = AirTouchRuntime(
            transport,
            RuntimeConfig(detect_seconds=0.01, source_address=None),
        )

        events = runtime.start()
        step_events = runtime.step(now=1.0)

        self.assertFalse(runtime.address_assigned)
        self.assertFalse(runtime.boot_complete)
        self.assertIn("no free touchpad address", events[-1].message)
        self.assertEqual(step_events, [])
        self.assertEqual(len(transport.writes), 1)

    def test_force_source_address_allows_occupied_slot(self) -> None:
        transport = FakeTransport([touchpad_info_wire(1)])
        runtime = AirTouchRuntime(
            transport,
            RuntimeConfig(detect_seconds=0.01, source_address=0x90, force_source_address=True),
        )

        runtime.start()

        self.assertEqual(runtime.snapshot()["runtime"]["src"], "0x90")
        self.assertTrue(runtime.address_assigned)

    def test_passive_start_does_not_write(self) -> None:
        transport = FakeTransport()
        runtime = AirTouchRuntime(transport, RuntimeConfig(active=False))

        events = runtime.start()

        self.assertEqual(events[0].message, "passive runtime started")
        self.assertEqual(transport.writes, [])
        self.assertIsNone(runtime.transactions)

    def test_step_applies_rx_state_and_completes_transaction(self) -> None:
        transport = FakeTransport([wire_packet(0x21, bytes.fromhex("01 32 56 80 CC 00"))])
        runtime = AirTouchRuntime(
            transport,
            RuntimeConfig(active=True, init_transactions=False, heartbeat_interval=999.0),
        )
        runtime.enqueue([TransactionSpec(0x20, expected_commands=(0x21,), name="group")])
        runtime.transactions.poll(0.0)

        events = runtime.step(now=0.1)

        self.assertEqual(events[0].event, "rx")
        self.assertEqual(events[0].decoded["type"], "group_status_internal")
        self.assertEqual(events[1].event, "transaction")
        self.assertEqual(events[1].transaction.event, "complete")
        self.assertEqual(runtime.state.groups[1]["status"]["temperature"], 31)

    def test_step_sends_due_heartbeat(self) -> None:
        transport = FakeTransport()
        runtime = AirTouchRuntime(
            transport,
            RuntimeConfig(active=True, init_transactions=False, heartbeat_interval=30.0),
        )
        runtime.address_assigned = True

        events = runtime.step(now=10.0)

        tx = [event for event in events if event.event == "tx"]
        self.assertEqual(len(tx), 1)
        self.assertEqual(tx[0].packet.command, 0x26)
        self.assertEqual(runtime.tx_count, 1)


if __name__ == "__main__":
    unittest.main()
