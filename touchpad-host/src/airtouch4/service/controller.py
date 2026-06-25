"""Threaded controller that runs AirTouchRuntime for app/API surfaces."""

from __future__ import annotations

import queue
import threading
import time
import logging
from collections import deque
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..live_log import JsonlBusLogger
from ..packet import PacketParseError, parse_packet
from ..runtime import AirTouchRuntime, RuntimeConfig, RuntimeEvent, TransportLike
from ..session.queue import TransactionSpec
from ..transport import SerialConfig, SerialRs485Transport, TcpSerialConfig, TcpSerialTransport
from .error_resolver import RemoteErrorResolver, RemoteErrorResolverConfig
from .ha_client import HomeAssistantApiClient, HomeAssistantApiConfig
from .mqtt import MqttConfig, MqttStatePublisher

TransportFactory = Callable[[], AbstractContextManager[TransportLike]]
LOG = logging.getLogger("uvicorn.error")


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
    ui_theme: str = "system"
    weather: HomeAssistantApiConfig = HomeAssistantApiConfig()
    weather_poll_interval: float = 60.0
    mqtt: MqttConfig = MqttConfig()
    error_resolver: RemoteErrorResolverConfig = RemoteErrorResolverConfig()


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
        self._weather: dict[str, Any] | None = None
        self._weather_error: str | None = None
        self._indoor: dict[str, Any] | None = None
        self._indoor_error: str | None = None
        self._next_weather_poll = 0.0
        self._next_mqtt_publish = 0.0
        self._ha_client = HomeAssistantApiClient(config.weather)
        self._mqtt = MqttStatePublisher(config.mqtt)
        self._error_resolver = RemoteErrorResolver(config.error_resolver)

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
            if runtime_snapshot is not None:
                _add_error_displays(runtime_snapshot, self._error_resolver)
            return {
                "controller": {
                    "status": self._status,
                    "error": self._error,
                    "thread_alive": self._thread is not None and self._thread.is_alive(),
                    "config": self.public_config(),
                },
                "runtime": runtime_snapshot,
                "integrations": {
                    "weather": {
                        "entity_id": self.config.weather.weather_entity,
                        "state": self._weather,
                        "error": self._weather_error,
                    },
                    "indoor": {
                        "temperature_entity_id": self.config.weather.indoor_temperature_entity,
                        "humidity_entity_id": self.config.weather.indoor_humidity_entity,
                        "state": self._indoor,
                        "error": self._indoor_error,
                    },
                    "mqtt": self._mqtt.status(),
                    "error_resolver": self._error_resolver.status(),
                },
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
            "ui_theme": self.config.ui_theme,
            "weather_entity": self.config.weather.weather_entity,
            "indoor_temperature_entity": self.config.weather.indoor_temperature_entity,
            "indoor_humidity_entity": self.config.weather.indoor_humidity_entity,
            "weather_poll_interval": self.config.weather_poll_interval,
            "mqtt_enabled": self.config.mqtt.enabled,
            "mqtt_host": self.config.mqtt.broker_host if self.config.mqtt.enabled else "",
            "mqtt_port": self.config.mqtt.broker_port,
            "mqtt_discovery": self.config.mqtt.discovery,
            "mqtt_discovery_prefix": self.config.mqtt.discovery_prefix,
            "mqtt_topic_prefix": self.config.mqtt.topic_prefix,
            "mqtt_publish_interval": self.config.mqtt.publish_interval,
            "remote_error_resolution": self.config.error_resolver.enabled,
            "remote_error_cache": (
                str(self.config.error_resolver.cache_path)
                if self.config.error_resolver.cache_path is not None
                else None
            ),
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
                        self._poll_weather()
                        self._publish_mqtt()
                        time.sleep(self.config.loop_sleep)
            except Exception as exc:  # pragma: no cover - exercised in live runs
                self._record_controller_error(exc)
                self._sleep_before_reconnect()
        with self._lock:
            self._status = "stopped"
        self._mqtt.stop()
        self._error_resolver.stop()

    def _drain_commands(self, runtime: AirTouchRuntime) -> None:
        specs = []
        while True:
            try:
                specs.append(self._command_queue.get_nowait())
            except queue.Empty:
                break
        if specs:
            runtime.enqueue(specs)

    def _record_event(self, event: RuntimeEvent, bus_logger: JsonlBusLogger) -> None:
        record = _event_record(event)
        with self._lock:
            self._events.append(record)
        if event.event == "rx" and event.packet is not None:
            bus_logger.log_rx(event.packet)
            LOG.info(_frame_log_line("rx", event))
        elif event.event == "tx" and event.packet is not None and event.wire is not None:
            bus_logger.log_tx(event.packet, event.wire)
            LOG.info(_frame_log_line("tx", event))
        elif event.event == "transaction" and event.transaction is not None:
            bus_logger.write(event.transaction.to_record())
        elif event.event == "status":
            bus_logger.write({"event": "runtime_status", "message": event.message})
            LOG.info("runtime status %s", event.message)

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

    def _poll_weather(self) -> None:
        weather_entity = self.config.weather.weather_entity.strip()
        indoor_configured = (
            bool(self.config.weather.indoor_temperature_entity.strip())
            or bool(self.config.weather.indoor_humidity_entity.strip())
        )
        if not weather_entity and not indoor_configured:
            return
        now = time.monotonic()
        if now < self._next_weather_poll:
            return
        self._next_weather_poll = now + max(10.0, self.config.weather_poll_interval)
        if weather_entity:
            try:
                weather = self._ha_client.weather_snapshot()
                with self._lock:
                    self._weather = weather
                    self._weather_error = None
            except Exception as exc:  # pragma: no cover - live HA API path
                with self._lock:
                    self._weather_error = f"{type(exc).__name__}: {exc}"
        else:
            with self._lock:
                self._weather = None
                self._weather_error = None
        if indoor_configured:
            try:
                indoor = self._ha_client.indoor_snapshot()
                with self._lock:
                    self._indoor = indoor
                    self._indoor_error = None
            except Exception as exc:  # pragma: no cover - live HA API path
                with self._lock:
                    self._indoor_error = f"{type(exc).__name__}: {exc}"
        else:
            with self._lock:
                self._indoor = None
                self._indoor_error = None

    def _publish_mqtt(self) -> None:
        if not self.config.mqtt.enabled:
            return
        now = time.monotonic()
        if now < self._next_mqtt_publish:
            return
        self._next_mqtt_publish = now + max(2.0, self.config.mqtt.publish_interval)
        self._mqtt.publish(self.snapshot())

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
    packet = _event_packet_for_log(event)
    if packet is not None:
        record.update({
            "direction": event.direction,
            "src": f"0x{packet.src:02X}",
            "dest": f"0x{packet.dest:02X}",
            "cmd": f"0x{packet.command:02X}",
            "cmd_name": packet.command_name,
            "packet_id": packet.packet_id,
            "len": len(packet.payload),
            "crc_ok": packet.crc_ok,
            "decoded": event.decoded,
        })
    if event.transaction is not None:
        record["transaction"] = event.transaction.to_record()
    return record


def _add_error_displays(runtime_snapshot: dict[str, Any], resolver: RemoteErrorResolver) -> None:
    state = runtime_snapshot.get("state") or {}
    for ac in (state.get("acs") or {}).values():
        if not isinstance(ac, dict):
            continue
        status = ac.get("status") or {}
        base = ac.get("base") or {}
        if not isinstance(status, dict) or not isinstance(base, dict):
            continue
        error = resolver.describe(base.get("brand"), status.get("error_code"))
        if error is not None:
            status["error_display"] = error


def _frame_log_line(direction: str, event: RuntimeEvent) -> str:
    packet = _event_packet_for_log(event)
    if packet is None:
        return f"bus {direction} packet=none"
    return (
        f"bus {direction} "
        f"src=0x{packet.src:02X} dest=0x{packet.dest:02X} "
        f"cmd=0x{packet.command:02X} {packet.command_name} "
        f"id={packet.packet_id} len={len(packet.payload)} crc_ok={packet.crc_ok} "
        f"payload={packet.payload.hex(' ').upper()}"
    )


def _event_packet_for_log(event: RuntimeEvent) -> Any:
    if event.event == "tx" and event.wire is not None:
        try:
            return parse_packet(event.wire)
        except PacketParseError:
            return event.packet
    return event.packet
