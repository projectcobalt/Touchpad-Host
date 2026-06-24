from __future__ import annotations

from contextlib import AbstractContextManager
from collections import deque
import time
import unittest
from typing import Iterable

from airtouch4.packet import AirTouchPacket
from airtouch4.runtime import RuntimeConfig
from airtouch4.service.controller import RuntimeController, RuntimeControllerConfig
from airtouch4.session.queue import TransactionSpec
from airtouch4.transport import TcpSerialTransport


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


class FakeTransportContext(AbstractContextManager[FakeTransport]):
    def __init__(self, transport: FakeTransport) -> None:
        self.transport = transport

    def __enter__(self) -> FakeTransport:
        return self.transport

    def __exit__(self, *_exc: object) -> None:
        return None


def wire_packet(command: int, payload: bytes = b"", *, src: int = 0x80, dest: int = 0x90) -> bytes:
    return AirTouchPacket(dest=dest, src=src, packet_id=1, command=command, payload=payload, raw_mode=True).encode(stuff_raw=True)


class RuntimeControllerTests(unittest.TestCase):
    def test_controller_starts_runtime_and_reports_health(self) -> None:
        transport = FakeTransport()
        controller = RuntimeController(
            RuntimeControllerConfig(
                port="TEST",
                runtime=RuntimeConfig(active=True, detect_seconds=0.0, init_transactions=False),
                loop_sleep=0.001,
            ),
            transport_factory=lambda: FakeTransportContext(transport),
        )

        controller.start()
        time.sleep(0.05)
        health = controller.health()
        controller.stop()

        self.assertEqual(health["status"], "running")
        self.assertTrue(health["address_assigned"])
        self.assertTrue(transport.writes)

    def test_enqueue_command_reaches_runtime_queue(self) -> None:
        transport = FakeTransport()
        controller = RuntimeController(
            RuntimeControllerConfig(
                port="TEST",
                runtime=RuntimeConfig(active=True, detect_seconds=0.0, init_transactions=False, heartbeat_interval=999.0),
                loop_sleep=0.001,
            ),
            transport_factory=lambda: FakeTransportContext(transport),
        )

        controller.start()
        initial_writes = len(transport.writes)
        controller.enqueue(TransactionSpec(0x20, bytes.fromhex("41 00"), expected_commands=(0x21,), name="test"))
        deadline = time.monotonic() + 0.2
        while len(transport.writes) <= initial_writes and time.monotonic() < deadline:
            time.sleep(0.005)
        transport.reads.append(wire_packet(0x21, bytes.fromhex("01 32 56 80 CC 00")))
        time.sleep(0.05)
        events = controller.recent_events()
        controller.stop()

        transaction_events = [event for event in events if event["event"] == "transaction"]
        self.assertTrue(any(event["transaction"]["transaction_event"] == "complete" for event in transaction_events))

    def test_default_transport_factory_can_select_tcp_serial(self) -> None:
        controller = RuntimeController(
            RuntimeControllerConfig(
                port="",
                transport="tcp_serial",
                tcp_host="192.0.2.1",
                tcp_port=8899,
            )
        )

        transport = controller._default_transport_factory()

        self.assertIsInstance(transport, TcpSerialTransport)

    def test_transport_error_keeps_controller_alive_for_reconnect(self) -> None:
        def failing_factory() -> AbstractContextManager[FakeTransport]:
            raise TimeoutError("bridge unavailable")

        controller = RuntimeController(
            RuntimeControllerConfig(
                port="TEST",
                runtime=RuntimeConfig(active=True, detect_seconds=0.0, init_transactions=False),
                reconnect_interval=0.1,
            ),
            transport_factory=failing_factory,
        )

        controller.start()
        deadline = time.monotonic() + 0.5
        health = controller.health()
        while health["status"] != "reconnecting" and time.monotonic() < deadline:
            time.sleep(0.01)
            health = controller.health()
        controller.stop()

        self.assertEqual(health["status"], "reconnecting")
        self.assertIn("TimeoutError", health["error"])
        self.assertTrue(controller.recent_events())


if __name__ == "__main__":
    unittest.main()
