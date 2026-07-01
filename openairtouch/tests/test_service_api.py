from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
import unittest
from typing import Any

import uvicorn
import websockets

from airtouch4.service.api import create_app


class FakeController:
    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._version = 0
        self._events: list[dict[str, Any]] = []

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def health(self) -> dict[str, Any]:
        return {"ok": True, "status": "running"}

    def snapshot(self) -> dict[str, Any]:
        return {
            "controller": {"status": "running", "config": {"transport": "tcp_serial"}},
            "runtime": {"runtime": {"connected": True, "boot_complete": True}, "state": {"acs": {}, "groups": {}}},
            "integrations": {},
        }

    def recent_events(self) -> list[dict[str, Any]]:
        with self._condition:
            return list(self._events)

    def change_version(self) -> int:
        with self._condition:
            return self._version

    def wait_for_change(self, version: int, timeout: float = 30.0) -> int:
        with self._condition:
            if self._version <= version:
                self._condition.wait(timeout)
            return self._version

    def push_event(self, event: dict[str, Any]) -> None:
        with self._condition:
            self._events.append(event)
            self._version += 1
            self._condition.notify_all()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_port(port: int) -> None:
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"server did not open port {port}")


class ServiceApiTests(unittest.TestCase):
    def test_websocket_sends_initial_state_then_batched_events_and_state(self) -> None:
        controller = FakeController()
        port = _free_port()
        server = uvicorn.Server(
            uvicorn.Config(create_app(controller), host="127.0.0.1", port=port, log_level="warning")
        )
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        _wait_for_port(port)

        async def run_client() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
            async with websockets.connect(f"ws://127.0.0.1:{port}/ws") as websocket:
                hello = json.loads(await asyncio.wait_for(websocket.recv(), timeout=5.0))
                controller.push_event({"event": "status", "message": "ready", "state_changed": True})
                controller.push_event({"event": "rx", "message": "frame", "state_changed": True})
                events = json.loads(await asyncio.wait_for(websocket.recv(), timeout=5.0))
                state = json.loads(await asyncio.wait_for(websocket.recv(), timeout=5.0))
                return hello, events, state

        try:
            hello, events, state = asyncio.run(run_client())
        finally:
            server.should_exit = True
            thread.join(timeout=5.0)

        self.assertEqual(hello["type"], "hello")
        self.assertEqual(hello["health"]["status"], "running")
        self.assertEqual(hello["events"], [])
        self.assertEqual(events["type"], "events")
        self.assertEqual([event["message"] for event in events["events"]], ["ready", "frame"])
        self.assertEqual(state["type"], "state")
        self.assertEqual([event["message"] for event in state["events"]], ["ready", "frame"])


if __name__ == "__main__":
    unittest.main()
