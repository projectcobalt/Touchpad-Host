"""Normalized live state built from decoded AirTouch main-board packets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .packet import AirTouchPacket
from .payloads import decode_mainboard_payload
from .payloads.common import SENSOR_SELECTORS


@dataclass
class AirTouchState:
    system: dict[str, Any] = field(default_factory=dict)
    acs: dict[int, dict[str, Any]] = field(default_factory=dict)
    groups: dict[int, dict[str, Any]] = field(default_factory=dict)
    sensors: dict[int, dict[str, Any]] = field(default_factory=dict)
    favourites: dict[int, dict[str, Any]] = field(default_factory=dict)
    programs: dict[int, dict[str, Any]] = field(default_factory=dict)
    service: dict[str, Any] = field(default_factory=dict)
    password: dict[str, Any] = field(default_factory=dict)
    last_led: dict[str, Any] = field(default_factory=dict)
    last_command: int | None = None

    def apply_packet(self, packet: AirTouchPacket) -> dict[str, Any]:
        decoded = decode_mainboard_payload(packet.command, packet.payload)
        self.apply_decoded(packet.command, decoded)
        self.last_command = packet.command
        return decoded

    def apply_decoded(self, command: int, decoded: dict[str, Any]) -> None:
        kind = decoded.get("type")
        if kind in {"unknown", "decode_error"}:
            return
        if kind == "parameters":
            self.system.update(decoded)
        elif kind == "preference":
            self.system.update({key: value for key, value in decoded.items() if key != "type"})
        elif kind == "ac_base_info":
            self.system["ac_count"] = decoded.get("ac_count")
            self.system["one_duct_system"] = decoded.get("one_duct_system")
            for record in decoded.get("records", []):
                self._merge(self.acs, record.get("ac"), {"base": record})
        elif kind == "ac_setting_new":
            for record in decoded.get("records", []):
                self._merge(self.acs, record.get("ac"), {"settings": record})
        elif kind == "ac_status_internal":
            for record in decoded.get("records", []):
                self._merge(self.acs, record.get("ac"), {"status": record})
        elif kind in {"ac_runtime_status", "ac_timer"}:
            field_name = "runtime" if kind == "ac_runtime_status" else "timer"
            for record in decoded.get("records", []):
                self._merge(self.acs, record.get("ac"), {field_name: record})
        elif kind == "group_name":
            for record in decoded.get("records", []):
                self._merge(self.groups, record.get("group"), {"name": record.get("name"), "name_record": record})
        elif kind == "group_status_internal":
            for record in decoded.get("records", []):
                self._merge(self.groups, record.get("group"), {"status": record})
        elif kind == "grouping":
            for record in decoded.get("records", []):
                self._merge(self.groups, record.get("group"), {"grouping": record})
        elif kind == "spill":
            self.system["spill"] = decoded
            for group in decoded.get("spill_groups_zero_based", []):
                self._merge(self.groups, group, {"spill_configured": True})
        elif kind == "sensor_list":
            self.system["sensor_list"] = decoded
            listed = set(decoded.get("sensor_addresses", []))
            touchpads = set(decoded.get("touchpad_addresses", []))
            self.system["sensor_addresses"] = sorted(listed)
            self.system["supply_air"] = decoded.get("supply_air", [])
            for sensor, data in self.sensors.items():
                data["listed"] = sensor in listed
                if sensor not in listed:
                    data["present"] = False
            for sensor in listed:
                self._merge_sensor(sensor, {
                    "listed": True,
                    "present": True,
                    "kind": "touchpad" if sensor in touchpads else "rf",
                    "sensor_name": SENSOR_SELECTORS.get(sensor, f"rf_sensor_{sensor}"),
                })
        elif kind == "sensor_info":
            for record in decoded.get("records", []):
                self._merge_sensor_info(record)
        elif kind == "favourite":
            for record in decoded.get("records", []):
                self._merge(self.favourites, record.get("favourite"), record)
        elif kind == "program_define_new":
            self.system["program_count"] = decoded.get("program_count")
            for record in decoded.get("records", []):
                self._merge(self.programs, record.get("program"), record)
        elif kind == "service":
            self.service.update(decoded)
        elif kind == "password_info":
            page = decoded.get("page")
            if page is not None:
                self.password[f"page_{page}"] = decoded
        elif kind == "led_response":
            self.last_led = decoded
        elif kind == "main_display_new":
            self.system["main_display"] = decoded
        elif kind == "turbo_group":
            self.system["turbo_group"] = decoded

    def snapshot(self) -> dict[str, Any]:
        return {
            "system": self.system,
            "acs": self.acs,
            "groups": self.groups,
            "active_groups": self.active_groups(),
            "sensors": self.sensors,
            "favourites": self.favourites,
            "programs": self.programs,
            "service": self.service,
            "password": self.password,
            "last_led": self.last_led,
        }

    @staticmethod
    def _merge(target: dict[int, dict[str, Any]], key: Any, values: dict[str, Any]) -> None:
        if not isinstance(key, int):
            return
        target.setdefault(key, {}).update(values)

    def _merge_sensor(self, sensor: Any, values: dict[str, Any]) -> None:
        if not isinstance(sensor, int):
            return
        self.sensors.setdefault(sensor, {}).update(values)

    def _merge_sensor_info(self, record: dict[str, Any]) -> None:
        sensor = record.get("sensor")
        if not isinstance(sensor, int):
            return
        current = self.sensors.setdefault(sensor, {})
        status = record.get("status")
        current.update({
            "info": record,
            "kind": record.get("kind"),
            "sensor_name": record.get("sensor_name"),
            "status": status,
            "temperature": record.get("temperature"),
            "temperature_raw": record.get("temperature_raw"),
            "battery": record.get("battery"),
            "low_battery": record.get("low_battery"),
            "signal": record.get("signal"),
            "signal_raw": record.get("signal_raw"),
            "mac": record.get("mac"),
            "missing": record.get("missing"),
            "lost": record.get("lost"),
        })
        if status == "missing":
            current["present"] = False
        elif status in {"ok", "lost"}:
            current["present"] = True
        current.setdefault("listed", None)

    def active_groups(self) -> dict[int, dict[str, Any]]:
        count = self.system.get("group_count")
        if not isinstance(count, int):
            return {key: value for key, value in self.groups.items() if "status" in value}
        return {key: value for key, value in self.groups.items() if key < count}
