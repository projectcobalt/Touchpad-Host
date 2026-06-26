"""MQTT state publishing and Home Assistant discovery."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LOG = logging.getLogger("uvicorn.error")


@dataclass(frozen=True)
class MqttConfig:
    enabled: bool = False
    host: str = ""
    port: int = 1883
    username: str = ""
    password: str = ""
    discovery: bool = True
    discovery_prefix: str = "homeassistant"
    topic_prefix: str = "airtouch4"
    client_id: str = "airtouch4-touchpad-host"
    publish_interval: float = 10.0

    @property
    def broker_host(self) -> str:
        return self.host.strip() or _env_first("MQTT_HOST", "MQTT_SERVICE_HOST") or "core-mosquitto"

    @property
    def broker_port(self) -> int:
        raw = _env_first("MQTT_PORT", "MQTT_SERVICE_PORT")
        if raw:
            try:
                return int(raw)
            except ValueError:
                return self.port
        return self.port

    @property
    def broker_username(self) -> str:
        return self.username.strip() or _env_first("MQTT_USERNAME", "MQTT_USER", "MQTT_SERVICE_USERNAME")

    @property
    def broker_password(self) -> str:
        return self.password or _env_first("MQTT_PASSWORD", "MQTT_SERVICE_PASSWORD")


class MqttStatePublisher:
    def __init__(self, config: MqttConfig) -> None:
        self.config = config
        self._client: Any = None
        self._connected = False
        self._error: str | None = None
        self._published_discovery: set[str] = set()
        self._publish_count = 0
        self._json_publish_count = 0
        self._value_publish_count = 0
        self._failed_publish_count = 0
        self._last_publish_summary: dict[str, Any] | None = None
        self._transport = ""

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.config.enabled,
            "connected": self._connected,
            "host": self.config.broker_host if self.config.enabled else "",
            "port": self.config.broker_port,
            "error": self._error,
            "publish_count": self._publish_count,
            "discovery_count": len(self._published_discovery),
            "json_publish_count": self._json_publish_count,
            "value_publish_count": self._value_publish_count,
            "failed_publish_count": self._failed_publish_count,
            "last_publish": self._last_publish_summary,
            "transport": self._transport,
        }

    def publish(self, snapshot: dict[str, Any]) -> None:
        if not self.config.enabled:
            return
        if not self._ensure_connected():
            return
        runtime = snapshot.get("runtime") or {}
        state = runtime.get("state") or {}
        discovery_before = len(self._published_discovery)
        values_before = self._value_publish_count
        self._publish_json(f"{self.config.topic_prefix}/state", snapshot)
        self._publish_availability("online")
        if self.config.discovery:
            self._publish_discovery(state)
        self._publish_entities(state)
        self._publish_count += 1
        active_groups = state.get("active_groups") or {}
        summary = {
            "acs": len(state.get("acs") or {}),
            "groups": len(state.get("groups") or {}),
            "active_groups": len(active_groups),
            "discovery_added": len(self._published_discovery) - discovery_before,
            "values_published": self._value_publish_count - values_before,
            "failed_publishes": self._failed_publish_count,
        }
        self._last_publish_summary = summary
        log = LOG.info if summary["discovery_added"] or self._publish_count == 1 else LOG.debug
        log(
            "MQTT published state topic=%s acs=%s groups=%s active_groups=%s discovery_added=%s values=%s",
            self.config.topic_prefix,
            summary["acs"],
            summary["groups"],
            summary["active_groups"],
            summary["discovery_added"],
            summary["values_published"],
        )

    def stop(self) -> None:
        if self._client is None:
            return
        try:
            self._publish_availability("offline")
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:  # pragma: no cover - defensive shutdown
            LOG.debug("MQTT shutdown failed", exc_info=True)
        finally:
            self._connected = False

    def _ensure_connected(self) -> bool:
        if self._connected:
            return True
        if os.environ.get("SUPERVISOR_TOKEN"):
            self._connected = True
            self._transport = "homeassistant_service"
            self._error = None
            LOG.info("MQTT publishing through Home Assistant mqtt.publish service")
            return True
        try:
            import paho.mqtt.client as mqtt
        except ModuleNotFoundError as exc:
            self._error = "paho-mqtt is not installed"
            LOG.warning("MQTT disabled: %s", self._error)
            return False
        try:
            client = mqtt.Client(client_id=self.config.client_id)
            username = self.config.broker_username
            if username:
                client.username_pw_set(username, self.config.broker_password or None)
            client.will_set(f"{self.config.topic_prefix}/availability", "offline", retain=True)
            client.connect(self.config.broker_host, self.config.broker_port, keepalive=30)
            client.loop_start()
            self._client = client
            self._connected = True
            self._transport = "paho"
            self._error = None
            LOG.info("MQTT connected to %s:%s", self.config.broker_host, self.config.broker_port)
            return True
        except Exception as exc:  # pragma: no cover - live network path
            self._error = f"{type(exc).__name__}: {exc}"
            self._connected = False
            LOG.warning("MQTT connection failed: %s", self._error)
            return False

    def _publish_discovery(self, state: dict[str, Any]) -> None:
        device = {
            "identifiers": ["airtouch4_touchpad_host"],
            "name": "AirTouch Touchpad Host",
            "manufacturer": "Polyaire",
            "model": "AirTouch",
        }
        for ac_id, ac in sorted((state.get("acs") or {}).items(), key=lambda item: int(item[0])):
            base = ac.get("base") or {}
            name = base.get("name") or f"AC {int(ac_id) + 1}"
            object_id = f"airtouch4_ac_{int(ac_id) + 1}"
            self._publish_sensor_discovery(device, f"{object_id}_current_temperature", f"{name} Current Temperature", f"{self.config.topic_prefix}/ac/{ac_id}/current_temperature", "temperature", "\u00b0C")
            self._publish_sensor_discovery(device, f"{object_id}_target_temperature", f"{name} Target Temperature", f"{self.config.topic_prefix}/ac/{ac_id}/target_temperature", "temperature", "\u00b0C")
            self._publish_sensor_discovery(device, f"{object_id}_mode", f"{name} Mode", f"{self.config.topic_prefix}/ac/{ac_id}/mode")
            self._publish_sensor_discovery(device, f"{object_id}_fan_mode", f"{name} Fan", f"{self.config.topic_prefix}/ac/{ac_id}/fan_mode")
        for group_id, group in sorted((state.get("active_groups") or state.get("groups") or {}).items(), key=lambda item: int(item[0])):
            status = group.get("status") or {}
            name = group.get("name") or f"Zone {int(group_id) + 1}"
            object_id = f"airtouch4_zone_{int(group_id) + 1}"
            if status.get("has_sensor"):
                self._publish_sensor_discovery(device, f"{object_id}_current_temperature", f"{name} Current Temperature", f"{self.config.topic_prefix}/zone/{group_id}/current_temperature", "temperature", "\u00b0C")
                self._publish_sensor_discovery(device, f"{object_id}_target_temperature", f"{name} Target Temperature", f"{self.config.topic_prefix}/zone/{group_id}/target_temperature", "temperature", "\u00b0C")
            self._publish_sensor_discovery(device, f"{object_id}_mode", f"{name} Mode", f"{self.config.topic_prefix}/zone/{group_id}/mode")
            self._publish_sensor_discovery(device, f"{object_id}_percentage", f"{name} Damper", f"{self.config.topic_prefix}/zone/{group_id}/percentage", None, "%")

    def _publish_sensor_discovery(
        self,
        device: dict[str, Any],
        object_id: str,
        name: str,
        state_topic: str,
        device_class: str | None = None,
        unit: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "name": name,
            "unique_id": object_id,
            "object_id": object_id,
            "device": device,
            "availability_topic": f"{self.config.topic_prefix}/availability",
            "state_topic": state_topic,
        }
        if device_class:
            payload["device_class"] = device_class
        if unit:
            payload["unit_of_measurement"] = unit
        self._publish_discovery_once("sensor", object_id, payload)

    def _publish_entities(self, state: dict[str, Any]) -> None:
        mode_names = {0: "auto", 1: "heat", 2: "dry", 3: "fan_only", 4: "cool"}
        fan_names = {0: "auto", 1: "low", 2: "medium", 3: "high"}
        for ac_id, ac in (state.get("acs") or {}).items():
            status = ac.get("status") or {}
            mode = "off" if status.get("power_on") is False else mode_names.get(status.get("mode"), "auto")
            self._publish_value(f"{self.config.topic_prefix}/ac/{ac_id}/mode", mode)
            self._publish_value(f"{self.config.topic_prefix}/ac/{ac_id}/fan_mode", fan_names.get(status.get("fan"), "auto"))
            self._publish_value(f"{self.config.topic_prefix}/ac/{ac_id}/target_temperature", status.get("setpoint"))
            self._publish_value(f"{self.config.topic_prefix}/ac/{ac_id}/current_temperature", status.get("sensor_temp"))
        for group_id, group in (state.get("active_groups") or state.get("groups") or {}).items():
            status = group.get("status") or {}
            mode = "heat_cool" if status.get("power_name") in {"on", "turbo"} else "off"
            self._publish_value(f"{self.config.topic_prefix}/zone/{group_id}/mode", mode)
            self._publish_value(f"{self.config.topic_prefix}/zone/{group_id}/target_temperature", status.get("setpoint"))
            self._publish_value(f"{self.config.topic_prefix}/zone/{group_id}/current_temperature", status.get("temperature"))
            self._publish_value(f"{self.config.topic_prefix}/zone/{group_id}/percentage", status.get("percentage"))

    def _publish_discovery_once(self, component: str, object_id: str, payload: dict[str, Any]) -> None:
        key = f"{component}/{object_id}"
        if key in self._published_discovery:
            return
        topic = f"{self.config.discovery_prefix}/{component}/{object_id}/config"
        self._publish_json(topic, payload, retain=True)
        self._published_discovery.add(key)

    def _publish_availability(self, value: str) -> None:
        self._publish_value(f"{self.config.topic_prefix}/availability", value, retain=True)

    def _publish_json(self, topic: str, payload: dict[str, Any], *, retain: bool = False) -> None:
        if self._publish_payload(topic, json.dumps(payload, separators=(",", ":"), default=str), retain=retain):
            self._json_publish_count += 1

    def _publish_value(self, topic: str, value: Any, *, retain: bool = False) -> None:
        if value is None:
            return
        if self._publish_payload(topic, str(value), retain=retain):
            self._value_publish_count += 1

    def _publish_payload(self, topic: str, payload: str, *, retain: bool = False) -> bool:
        if self._transport == "homeassistant_service":
            return self._publish_to_homeassistant(topic, payload, retain=retain)
        if self._client is not None:
            info = self._client.publish(topic, payload, qos=0, retain=retain)
            if getattr(info, "rc", 0) == 0:
                try:
                    info.wait_for_publish(timeout=2.0)
                except TypeError:
                    info.wait_for_publish()
                self._error = None
                return True
            self._failed_publish_count += 1
            self._error = f"MQTT publish failed rc={getattr(info, 'rc', 'unknown')}"
            return False
        self._failed_publish_count += 1
        self._error = "MQTT publish attempted before client was available"
        return False

    def _publish_to_homeassistant(self, topic: str, payload: str, *, retain: bool = False) -> bool:
        token = os.environ.get("SUPERVISOR_TOKEN", "")
        if not token:
            self._failed_publish_count += 1
            self._error = "SUPERVISOR_TOKEN is not available"
            return False
        body = json.dumps({
            "topic": topic,
            "payload": payload,
            "qos": 0,
            "retain": retain,
        }).encode("utf-8")
        request = Request(
            "http://supervisor/core/api/services/mqtt/publish",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=3.0) as response:
                response.read()
            self._error = None
            return True
        except (HTTPError, URLError, TimeoutError) as exc:
            self._failed_publish_count += 1
            self._error = f"Home Assistant mqtt.publish failed: {exc}"
            LOG.warning("%s", self._error)
            return False


def _env_first(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""
