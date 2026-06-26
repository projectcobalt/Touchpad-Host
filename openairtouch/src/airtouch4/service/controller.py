"""Threaded controller that runs AirTouchRuntime for app/API surfaces."""

from __future__ import annotations

import json
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
from .adaptive import AdaptiveConfig, AdaptiveController
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
    adaptive: AdaptiveConfig = AdaptiveConfig()
    adaptive_config_path: Path | None = None
    adaptive_learning_path: Path | None = None


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
        self._forecast: dict[str, Any] | None = None
        self._forecast_error: str | None = None
        self._indoor: dict[str, Any] | None = None
        self._indoor_error: str | None = None
        self._solar: dict[str, Any] | None = None
        self._solar_error: str | None = None
        self._sun: dict[str, Any] | None = None
        self._sun_error: str | None = None
        self._next_weather_poll = 0.0
        self._next_mqtt_publish = 0.0
        self._ha_client = HomeAssistantApiClient(config.weather)
        self._mqtt = MqttStatePublisher(config.mqtt)
        self._error_resolver = RemoteErrorResolver(config.error_resolver)
        self._adaptive_config_path = config.adaptive_config_path
        self._adaptive = AdaptiveController(_load_adaptive_config(config.adaptive, config.adaptive_config_path))
        self._adaptive_learning_path = config.adaptive_learning_path
        self._adaptive.import_learning(_load_adaptive_learning(config.adaptive_learning_path))
        self._next_adaptive_learning_save = 0.0

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
                    "forecast": {
                        "entity_id": self.config.weather.forecast_weather_entity,
                        "state": self._forecast,
                        "error": self._forecast_error,
                    },
                    "solar": {
                        "irradiance_entity_id": self.config.weather.solar_irradiance_entity,
                        "cloud_cover_entity_id": self.config.weather.cloud_cover_entity,
                        "state": self._solar,
                        "error": self._solar_error,
                    },
                    "sun": {
                        "state": self._sun,
                        "error": self._sun_error,
                    },
                    "mqtt": self._mqtt.status(),
                    "error_resolver": self._error_resolver.status(),
                    "adaptive": self._adaptive.status(),
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
            "protocol_mode": runtime_meta.get("protocol_mode"),
            "protocol": runtime_meta.get("protocol"),
            "protocol_name": runtime_meta.get("protocol_name"),
            "detected_protocol": runtime_meta.get("detected_protocol"),
            "protocol_mismatch": runtime_meta.get("protocol_mismatch", False),
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
            "protocol": self.config.runtime.protocol,
            "bus_log": str(self.config.bus_log) if self.config.bus_log is not None else None,
            "ui_theme": self.config.ui_theme,
            "weather_entity": self.config.weather.weather_entity,
            "forecast_weather_entity": self.config.weather.forecast_weather_entity,
            "indoor_temperature_entity": self.config.weather.indoor_temperature_entity,
            "indoor_humidity_entity": self.config.weather.indoor_humidity_entity,
            "solar_irradiance_entity": self.config.weather.solar_irradiance_entity,
            "cloud_cover_entity": self.config.weather.cloud_cover_entity,
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
            "adaptive": self._adaptive.public_config(),
        }

    def update_adaptive_config(self, values: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            config = self._adaptive.update_config(values)
            _save_adaptive_config(self._adaptive_config_path, config)
            return config

    def manage_adaptive_learning(self, values: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            learning = self._adaptive.manage_learning(values)
            _save_adaptive_learning(self._adaptive_learning_path, self._adaptive.export_learning())
            return learning

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
                        self._run_adaptive(runtime)
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
        forecast_entity = self.config.weather.forecast_weather_entity.strip()
        indoor_configured = (
            bool(self.config.weather.indoor_temperature_entity.strip())
            or bool(self.config.weather.indoor_humidity_entity.strip())
        )
        solar_configured = (
            bool(self.config.weather.solar_irradiance_entity.strip())
            or bool(self.config.weather.cloud_cover_entity.strip())
        )
        sun_needed = bool(weather_entity) or solar_configured
        if not weather_entity and not forecast_entity and not indoor_configured and not solar_configured:
            return
        now = time.monotonic()
        if now < self._next_weather_poll:
            return
        self._next_weather_poll = now + max(10.0, self.config.weather_poll_interval)
        if weather_entity:
            try:
                weather = self._ha_client.weather_snapshot()
                weather_error = _weather_data_quality_error(weather, weather_entity)
                with self._lock:
                    self._weather = weather
                    self._weather_error = weather_error
            except Exception as exc:  # pragma: no cover - live HA API path
                with self._lock:
                    self._weather_error = f"{type(exc).__name__}: {exc}"
        else:
            with self._lock:
                self._weather = None
                self._weather_error = None
        if forecast_entity:
            try:
                forecast = self._ha_client.hourly_forecast_snapshot(current_weather=self._weather)
                with self._lock:
                    self._forecast = forecast
                    self._forecast_error = None
            except Exception as exc:  # pragma: no cover - live HA API path
                with self._lock:
                    self._forecast_error = f"{type(exc).__name__}: {exc}"
        else:
            with self._lock:
                self._forecast = None
                self._forecast_error = None
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
        if solar_configured:
            try:
                solar = self._ha_client.solar_snapshot()
                with self._lock:
                    self._solar = solar
                    self._solar_error = None
            except Exception as exc:  # pragma: no cover - live HA API path
                with self._lock:
                    self._solar_error = f"{type(exc).__name__}: {exc}"
        else:
            with self._lock:
                self._solar = None
                self._solar_error = None
        if sun_needed:
            try:
                sun = self._ha_client.sun_snapshot()
                with self._lock:
                    self._sun = sun
                    self._sun_error = None
            except Exception as exc:  # pragma: no cover - live HA API path
                with self._lock:
                    self._sun_error = f"{type(exc).__name__}: {exc}"
        else:
            with self._lock:
                self._sun = None
                self._sun_error = None

    def _publish_mqtt(self) -> None:
        if not self.config.mqtt.enabled:
            return
        now = time.monotonic()
        if now < self._next_mqtt_publish:
            return
        self._next_mqtt_publish = now + max(2.0, self.config.mqtt.publish_interval)
        self._mqtt.publish(self.snapshot())

    def _run_adaptive(self, runtime: AirTouchRuntime) -> None:
        runtime_snapshot = runtime.snapshot()
        integrations = {
            "weather": {"state": self._weather, "error": self._weather_error},
            "indoor": {"state": self._indoor, "error": self._indoor_error},
            "forecast": {"state": self._forecast, "error": self._forecast_error},
            "solar": {"state": self._solar, "error": self._solar_error},
            "sun": {"state": self._sun, "error": self._sun_error},
        }
        specs = self._adaptive.evaluate(runtime_snapshot, integrations)
        self._save_adaptive_learning_periodically()
        if specs:
            runtime.enqueue(specs)
            with self._lock:
                for spec in specs:
                    self._events.append({
                        "event": "adaptive",
                        "message": f"queued {spec.name}",
                        "command": f"0x{spec.command:02X}",
                        "state_changed": False,
                    })

    def _save_adaptive_learning_periodically(self) -> None:
        if self._adaptive_learning_path is None:
            return
        now = time.monotonic()
        if now < self._next_adaptive_learning_save:
            return
        self._next_adaptive_learning_save = now + 60.0
        _save_adaptive_learning(self._adaptive_learning_path, self._adaptive.export_learning())

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


def _weather_data_quality_error(weather: dict[str, Any] | None, entity_id: str) -> str | None:
    if not weather:
        return None
    if _float_or_none(weather.get("temperature")) is None:
        return f"{entity_id} has no numeric temperature"
    return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _load_adaptive_config(default: AdaptiveConfig, path: Path | None) -> AdaptiveConfig:
    if path is None:
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (OSError, json.JSONDecodeError) as exc:
        LOG.warning("Could not load adaptive config from %s: %s", path, exc)
        return default
    if not isinstance(payload, dict):
        LOG.warning("Ignoring adaptive config from %s because it is not an object", path)
        return default
    fields = default.__dataclass_fields__
    data = {name: getattr(default, name) for name in fields}
    data.update({key: value for key, value in payload.items() if key in fields})
    try:
        return AdaptiveController(AdaptiveConfig(**data)).config
    except (TypeError, ValueError) as exc:
        LOG.warning("Ignoring invalid adaptive config from %s: %s", path, exc)
        return default


def _save_adaptive_config(path: Path | None, config: dict[str, Any]) -> None:
    if path is None:
        return
    allowed = AdaptiveConfig.__dataclass_fields__
    payload = {key: config[key] for key in allowed if key in config}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.tmp")
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(path)
    except OSError as exc:
        LOG.warning("Could not save adaptive config to %s: %s", path, exc)


def _load_adaptive_learning(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        LOG.warning("Could not load adaptive learning data from %s: %s", path, exc)
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_adaptive_learning(path: Path | None, payload: dict[str, Any]) -> None:
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.tmp")
        temp_path.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True), encoding="utf-8")
        temp_path.replace(path)
    except OSError as exc:
        LOG.warning("Could not save adaptive learning data to %s: %s", path, exc)
