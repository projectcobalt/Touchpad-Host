"""Normalized live state built from decoded AirTouch main-board packets."""

from __future__ import annotations

import time
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
    console: dict[str, Any] = field(default_factory=dict)
    last_led: dict[str, Any] = field(default_factory=dict)
    last_command: int | None = None
    temperature_history_limit: int = 96

    def apply_packet(self, packet: AirTouchPacket) -> dict[str, Any]:
        decoded = decode_mainboard_payload(packet.command, packet.payload)
        self.apply_decoded(packet.command, decoded)
        self.last_command = packet.command
        return decoded

    def apply_decoded(self, command: int, decoded: dict[str, Any]) -> None:
        kind = decoded.get("type")
        if kind in {"unknown", "decode_error"}:
            return
        if kind in {"parameters", "set_parameters"}:
            self.system.update({key: value for key, value in decoded.items() if key not in {"type", "raw", "tail"}})
        elif kind == "preference":
            self.system.update({key: value for key, value in decoded.items() if key != "type"})
        elif kind in {"ac_base_info", "set_ac_base_info"}:
            self.system["ac_count"] = decoded.get("ac_count")
            self.system["one_duct_system"] = decoded.get("one_duct_system")
            for record in decoded.get("records", []):
                self._merge(self.acs, record.get("ac"), {"base": record})
        elif kind in {"ac_setting", "ac_setting_new", "set_ac_setting_new"}:
            for record in decoded.get("records", []):
                self._merge(self.acs, record.get("ac"), {"settings": record})
        elif kind == "set_ac_status_internal":
            self._merge(self.acs, decoded.get("ac"), {"last_control": decoded})
        elif kind == "ac_status_internal":
            for record in decoded.get("records", []):
                self._merge(self.acs, record.get("ac"), {"status": record})
        elif kind in {"ac_runtime_status", "ac_timer", "set_ac_timer"}:
            field_name = "runtime" if kind == "ac_runtime_status" else "timer"
            for record in decoded.get("records", []):
                self._merge(self.acs, record.get("ac"), {field_name: record})
        elif kind == "group_name":
            for record in decoded.get("records", []):
                self._merge(self.groups, record.get("group"), {"name": record.get("name"), "name_record": record})
        elif kind == "set_group_status_internal":
            self._merge(self.groups, decoded.get("group"), {"last_control": decoded})
        elif kind == "group_status_internal":
            for record in decoded.get("records", []):
                self._merge(self.groups, record.get("group"), {"status": record})
                self._remember_group_temperature(record)
        elif kind == "set_grouping":
            self._merge(self.groups, decoded.get("group"), {"grouping": decoded})
        elif kind == "grouping":
            for record in decoded.get("records", []):
                self._merge(self.groups, record.get("group"), {"grouping": record})
        elif kind in {"balance", "balance_control"}:
            self.system["balance"] = decoded
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
        elif kind == "pair_sensor":
            self.system["sensor_pairing"] = decoded
        elif kind == "set_sensor_temp":
            self._merge_sensor(decoded.get("sensor"), {
                "kind": "touchpad" if decoded.get("sensor") in (0x90, 0x91) else "rf",
                "sensor_name": SENSOR_SELECTORS.get(decoded.get("sensor"), f"sensor_addr_{decoded.get('sensor')}"),
                "temperature": decoded.get("temperature"),
                "temperature_raw": decoded.get("temperature_raw"),
                "last_temperature_write": decoded,
            })
            self.console["last_heartbeat"] = decoded
            self.console["touchpad_temperature"] = decoded.get("temperature")
        elif kind == "touchpad_temperature":
            self.console["last_heartbeat"] = decoded
            self.console["touchpad_temperature"] = decoded.get("temperature")
        elif kind == "sensor_info":
            for record in decoded.get("records", []):
                self._merge_sensor_info(record)
        elif kind in {"favourite", "set_favourite"}:
            for record in decoded.get("records", []):
                self._merge(self.favourites, record.get("favourite"), record)
        elif kind == "set_active_favourite":
            self.system["active_favourite"] = decoded.get("favourite")
        elif kind == "active_favourite":
            self.system["active_favourite"] = decoded.get("active_favourite")
            for record in decoded.get("names", []):
                self._merge(self.favourites, record.get("favourite"), {"name": record.get("name"), "name_record": record})
        elif kind in {"program_define", "program_define_new", "set_program_define_new"}:
            self.system["program_count"] = decoded.get("program_count")
            self.system["programs_linked_ac"] = decoded.get("linked_ac")
            self.system["program_record_len"] = decoded.get("record_len")
            for record in decoded.get("records", []):
                self._merge(self.programs, record.get("program"), record)
        elif kind in {"service", "set_service"}:
            self.service.update(decoded)
        elif kind in {"password_info", "set_password_info"}:
            page = decoded.get("page")
            if page is not None:
                self.password[f"page_{page}"] = decoded
        elif kind == "dialog_message":
            self.system["dialog_message"] = decoded
        elif kind == "clear_notification":
            self.system["clear_notification"] = decoded
        elif kind == "led_response":
            self.last_led = decoded
            self.console["last_led"] = decoded
            self.console["led_name"] = decoded.get("led_name")
        elif kind == "main_display_new":
            self.system["main_display"] = decoded
        elif kind == "turbo_group":
            self.system["turbo_group"] = decoded
        elif kind == "expanded":
            self.system["expanded"] = decoded
        elif kind in {"debug_info", "gateway_info"}:
            self.system[kind] = decoded

    def snapshot(self) -> dict[str, Any]:
        return {
            "system": self.system,
            "acs": self.acs,
            "groups": self.groups,
            "active_groups": self.active_groups(),
            "sensors": self.sensors,
            "sensor_view": self.sensor_view(),
            "favourites": self.favourites,
            "programs": self.programs,
            "service": self.service,
            "password": self.password,
            "console": self.console,
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

    def sensor_view(self) -> list[dict[str, Any]]:
        mapped: dict[int, list[str]] = {}
        for group_id, group in self.groups.items():
            grouping = group.get("grouping") or {}
            status = group.get("status") or {}
            sensor = grouping.get("thermostat", status.get("sensor"))
            if not isinstance(sensor, int) or sensor == 255:
                continue
            mapped.setdefault(sensor, []).append(group.get("name") or f"Zone {group_id + 1}")

        rows: list[dict[str, Any]] = []
        for sensor, data in sorted(self.sensors.items()):
            rows.append({
                "id": sensor,
                "address": f"0x{sensor:02X}" if sensor >= 0x80 else str(sensor),
                "name": data.get("sensor_name") or SENSOR_SELECTORS.get(sensor, f"rf_sensor_{sensor}"),
                "kind": data.get("kind") or ("touchpad" if sensor in (0x90, 0x91) else "rf"),
                "temperature": data.get("temperature"),
                "status": data.get("status") or ("missing" if data.get("present") is False else "listed" if data.get("listed") else "unknown"),
                "present": data.get("present"),
                "listed": data.get("listed"),
                "signal": data.get("signal"),
                "battery": data.get("battery"),
                "low_battery": data.get("low_battery"),
                "mac": data.get("mac"),
                "mapped_groups": mapped.get(sensor, []),
            })

        for supply in self.system.get("supply_air", []) or []:
            ac = supply.get("ac")
            if not isinstance(ac, int):
                continue
            rows.append({
                "id": f"supply_air_{ac}",
                "address": f"SA{ac + 1}",
                "name": f"Supply Air {ac + 1}",
                "kind": "supply_air",
                "temperature": supply.get("temperature"),
                "status": supply.get("status") or "unknown",
                "present": supply.get("status") == "ok",
                "listed": True,
                "signal": None,
                "battery": None,
                "low_battery": None,
                "mac": None,
                "mapped_groups": [],
                "ac": ac,
            })
        return rows

    def _remember_group_temperature(self, record: dict[str, Any]) -> None:
        group = record.get("group")
        temperature = record.get("temperature")
        percentage = record.get("percentage")
        if not isinstance(group, int) or not isinstance(temperature, (int, float)):
            return
        current = self.groups.setdefault(group, {})
        history = current.setdefault("temperature_history", [])
        entry = {"ts": int(time.time()), "temperature": temperature}
        if isinstance(percentage, (int, float)):
            entry["percentage"] = percentage
        if history and history[-1].get("temperature") == temperature and history[-1].get("percentage") == entry.get("percentage"):
            history[-1]["ts"] = int(time.time())
            return
        history.append(entry)
        if len(history) > self.temperature_history_limit:
            del history[:-self.temperature_history_limit]

    def active_groups(self) -> dict[int, dict[str, Any]]:
        count = self.system.get("group_count")
        if not isinstance(count, int):
            return {key: value for key, value in self.groups.items() if "status" in value}
        return {key: value for key, value in self.groups.items() if key < count}
