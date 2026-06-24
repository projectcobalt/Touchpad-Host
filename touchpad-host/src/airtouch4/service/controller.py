"""Threaded controller that runs AirTouchRuntime for app/API surfaces."""

from __future__ import annotations

import queue
import threading
import time
from collections import deque
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..live_log import JsonlBusLogger
from ..runtime import AirTouchRuntime, RuntimeConfig, RuntimeEvent, TransportLike
from ..session.queue import TransactionSpec
from ..transport import SerialConfig, SerialRs485Transport, TcpSerialConfig, TcpSerialTransport

TransportFactory = Callable[[], AbstractContextManager[TransportLike]]


@dataclass(frozen=True)
class RuntimeControllerConfig:
    port: str
    baudrate: int = 115200
    transport: str = "local_serial"
    tcp_host: str = "127.0.0.1"
    tcp_port: int = 6638
    runtime: RuntimeConfig = RuntimeConfig()
    bus_log: Path | None = None
    loop_sleep: float = 0.02
    reconnect_interval: float = 5.0
    event_history: int = 200


class RuntimeController:
    """Runs the protocol runtime in a background thread."""

    def __init__(
        self,
        config: RuntimeControllerConfig,
        *,
        transport_factory: TransportFactory | None = None,
    ) -> None:
        self.config = config
        self._transport_factory = transport_factory or self._default_transport_factory
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._runtime: AirTouchRuntime | None = None
        self._events: deque[dict[str, Any]] = deque(maxlen=config.event_history)
        self._command_queue: queue.Queue[TransactionSpec] = queue.Queue()
        self._status = "stopped"
        self._error: str | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name="airtouch-runtime", daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout)

    def enqueue(self, spec: TransactionSpec) -> dict[str, Any]:
        self._command_queue.put(spec)
        return {
            "queued": True,
            "command": f"0x{spec.command:02X}",
            "name": spec.name,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            runtime_snapshot = None if self._runtime is None else self._runtime.snapshot()
            return {
                "controller": {
                    "status": self._status,
                    "error": self._error,
                    "thread_alive": self._thread is not None and self._thread.is_alive(),
                    "config": self.public_config(),
                },
                "runtime": runtime_snapshot,
            }

    def health(self) -> dict[str, Any]:
        snap = self.snapshot()
        runtime = snap["runtime"] or {}
        runtime_meta = runtime.get("runtime", {})
        return {
            "ok": snap["controller"]["status"] == "running" and snap["controller"]["error"] is None,
            "status": snap["controller"]["status"],
            "error": snap["controller"]["error"],
            "address_assigned": runtime_meta.get("address_assigned", False),
            "boot_complete": runtime_meta.get("boot_complete", False),
            "src": runtime_meta.get("src"),
            "config": snap["controller"]["config"],
        }

    def recent_events(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events)

    def public_config(self) -> dict[str, Any]:
        return {
            "transport": self.config.transport,
            "port": self.config.port,
            "baudrate": self.config.baudrate,
            "tcp_host": self.config.tcp_host,
            "tcp_port": self.config.tcp_port,
            "reconnect_interval": self.config.reconnect_interval,
            "bus_log": str(self.config.bus_log) if self.config.bus_log is not None else None,
        }

    def _run(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                self._status = "starting" if self._runtime is None else "reconnecting"
            try:
                with self._transport_factory() as transport, JsonlBusLogger(self.config.bus_log) as logger:
                    runtime = AirTouchRuntime(transport, self.config.runtime)
                    with self._lock:
                        self._runtime = runtime
                        self._status = "running"
                        self._error = None
                    for event in runtime.start():
                        self._record_event(event, logger)
                    while not self._stop.is_set():
                        self._drain_commands(runtime)
                        for event in runtime.step():
                            self._record_event(event, logger)
                        time.sleep(self.config.loop_sleep)
            except Exception as exc:  # pragma: no cover - exercised in live runs
                self._record_controller_error(exc)
                self._sleep_before_reconnect()
        with self._lock:
            self._status = "stopped"

    def _drain_commands(self, runtime: AirTouchRuntime) -> None:
        specs = []
        while True:
            try:
                specs.append(self._command_queue.get_nowait())
            except queue.Empty:
                break
        if specs:
            runtime.enqueue(specs)

    def _record_event(self, event: RuntimeEvent, logger: JsonlBusLogger) -> None:
        record = _event_record(event)
        with self._lock:
            self._events.append(record)
        if event.event == "rx" and event.packet is not None:
            logger.log_rx(event.packet)
        elif event.event == "tx" and event.packet is not None and event.wire is not None:
            logger.log_tx(event.packet, event.wire)
        elif event.event == "transaction" and event.transaction is not None:
            logger.write(event.transaction.to_record())
        elif event.event == "status":
            logger.write({"event": "runtime_status", "message": event.message})

    def _record_controller_error(self, exc: Exception) -> None:
        message = f"{type(exc).__name__}: {exc}"
        with self._lock:
            self._status = "reconnecting"
            self._error = message
            self._events.append({
                "event": "controller",
                "message": message,
                "state_changed": False,
            })

    def _sleep_before_reconnect(self) -> None:
        deadline = time.monotonic() + max(0.1, self.config.reconnect_interval)
        while not self._stop.is_set() and time.monotonic() < deadline:
            time.sleep(min(0.2, deadline - time.monotonic()))

    def _default_transport_factory(self) -> AbstractContextManager[TransportLike]:
        if self.config.transport == "local_serial":
            return SerialRs485Transport(SerialConfig(port=self.config.port, baudrate=self.config.baudrate))
        if self.config.transport == "tcp_serial":
            return TcpSerialTransport(TcpSerialConfig(host=self.config.tcp_host, port=self.config.tcp_port))
        raise ValueError(f"unsupported transport: {self.config.transport}")


def _event_record(event: RuntimeEvent) -> dict[str, Any]:
    record: dict[str, Any] = {
        "event": event.event,
        "message": event.message,
        "state_changed": event.state_changed,
    }
    if event.packet is not None:
        record.update({
            "direction": event.direction,
            "src": f"0x{event.packet.src:02X}",
            "dest": f"0x{event.packet.dest:02X}",
            "cmd": f"0x{event.packet.command:02X}",
            "cmd_name": event.packet.command_name,
            "packet_id": event.packet.packet_id,
            "len": len(event.packet.payload),
            "crc_ok": event.packet.crc_ok,
            "decoded": event.decoded,
        })
    if event.transaction is not None:
        record["transaction"] = event.transaction.to_record()
    return record
