from __future__ import annotations

from contextlib import AbstractContextManager
from collections import deque
import json
from pathlib import Path
import tempfile
import time
import unittest
from typing import Iterable

from airtouch4.packet import AirTouchPacket
from airtouch4.runtime import RuntimeConfig, RuntimeEvent
from airtouch4.service.adaptive import AdaptiveConfig
from airtouch4.service.adaptive_mpc import ZoneThermalModel
from airtouch4.service.controller import RuntimeController, RuntimeControllerConfig, _event_record
from airtouch4.service.ha_client import HomeAssistantApiConfig
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


class FakeWeatherClient:
    def __init__(self, weather_readings: Iterable[dict]) -> None:
        self.weather_readings = deque(weather_readings)

    def weather_snapshot(self) -> dict:
        if len(self.weather_readings) > 1:
            return self.weather_readings.popleft()
        return self.weather_readings[0]

    def sun_snapshot(self) -> dict:
        return {"entity_id": "sun.sun", "state": "above_horizon"}


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
        self.assertEqual(health["protocol_mode"], "auto")
        self.assertEqual(health["protocol"], "at4")
        self.assertEqual(health["protocol_name"], "AirTouch 4")
        self.assertFalse(health["protocol_mismatch"])
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

    def test_adaptive_config_updates_are_persisted_and_reloaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = f"{tmp}/adaptive_config.json"
            first = RuntimeController(RuntimeControllerConfig(port="TEST", adaptive_config_path=Path(path)))

            updated = first.update_adaptive_config({
                "mode": "adaptive",
                "learning_mode": "control",
                "mpc_horizon_hours": 8,
                "compressor_min_run_time": 600,
                "compressor_min_off_time": 300,
                "compressor_groups": [[0, 1], [2, 3]],
            })
            second = RuntimeController(
                RuntimeControllerConfig(
                    port="TEST",
                    adaptive=AdaptiveConfig(mode="off"),
                    adaptive_config_path=Path(path),
                )
            )

            persisted = json.loads(Path(path).read_text(encoding="utf-8"))
            self.assertEqual(updated["learning_mode"], "control")
            self.assertEqual(persisted["mpc_horizon_hours"], 8)
            self.assertEqual(persisted["compressor_groups"], [[0, 1], [2, 3]])
            self.assertNotIn("weather_entity", persisted)
            self.assertEqual(second.public_config()["adaptive"]["mode"], "adaptive")
            self.assertEqual(second.public_config()["adaptive"]["compressor_min_off_time"], 300.0)
            self.assertEqual(second.public_config()["adaptive"]["compressor_groups"], [[0, 1], [2, 3]])

    def test_adaptive_learning_data_can_be_reloaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "adaptive_learning.json"
            first = RuntimeController(RuntimeControllerConfig(port="TEST", adaptive_learning_path=path))
            first._adaptive._mpc.zone_models[3] = ZoneThermalModel(passive_samples=4)
            first._save_adaptive_learning_periodically()

            second = RuntimeController(RuntimeControllerConfig(port="TEST", adaptive_learning_path=path))

            self.assertIn("3", second.snapshot()["integrations"]["adaptive"]["learning"]["zones"])
            self.assertEqual(second.snapshot()["integrations"]["adaptive"]["learning"]["zones"]["3"]["passive_samples"], 4)

    def test_adaptive_model_management_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "adaptive_learning.json"
            controller = RuntimeController(RuntimeControllerConfig(port="TEST", adaptive_learning_path=path))
            controller._adaptive._mpc.zone_models[2] = ZoneThermalModel(passive_samples=4)

            accelerated = controller.manage_adaptive_learning({"action": "accelerate_zone", "zone": 2, "enabled": True})
            normal = controller.manage_adaptive_learning({"action": "accelerate_zone", "zone": 2, "enabled": False})
            controller.manage_adaptive_learning({"action": "reset_zone", "zone": 2})

            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(accelerated["zones"]["2"]["accelerated_learning"])
            self.assertFalse(normal["zones"]["2"]["accelerated_learning"])
            self.assertNotIn("2", payload["zones"])

    def test_weather_missing_temperature_surfaces_soft_error_and_recovers(self) -> None:
        controller = RuntimeController(
            RuntimeControllerConfig(
                port="TEST",
                weather=HomeAssistantApiConfig(weather_entity="weather.micro_weather_station"),
            )
        )
        controller._ha_client = FakeWeatherClient(
            [
                {"entity_id": "weather.micro_weather_station", "state": "cloudy", "temperature": None},
                {"entity_id": "weather.micro_weather_station", "state": "cloudy", "temperature": 17.1},
            ]
        )

        controller._poll_weather()
        first = controller.snapshot()["integrations"]["weather"]
        controller._next_weather_poll = 0.0
        controller._poll_weather()
        second = controller.snapshot()["integrations"]["weather"]

        self.assertEqual(first["error"], "weather.micro_weather_station has no numeric temperature")
        self.assertIsNone(second["error"])
        self.assertEqual(second["state"]["temperature"], 17.1)

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

    def test_tx_event_record_uses_wire_crc(self) -> None:
        packet = AirTouchPacket(
            dest=0x80,
            src=0x91,
            packet_id=0x22,
            command=0x26,
            payload=bytes.fromhex("00 8C 00"),
            raw_mode=True,
        )
        wire = packet.encode(stuff_raw=True)
        event = RuntimeEvent("tx", packet=packet, wire=wire)

        record = _event_record(event)

        self.assertTrue(record["crc_ok"])
        self.assertEqual(record["src"], "0x91")
        self.assertEqual(record["cmd"], "0x26")


if __name__ == "__main__":
    unittest.main()
