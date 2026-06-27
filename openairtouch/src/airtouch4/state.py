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
        self._refresh_group_sensor_refs()
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
        mapped = self._sensor_zone_mappings()

        rows: list[dict[str, Any]] = []
        for sensor, data in sorted(self.sensors.items()):
            mappings = mapped.get(sensor, [])
            mapping_status = "resolved" if len(mappings) == 1 else "ambiguous" if mappings else "unmapped"
            resolved_mapping = mappings[0] if mapping_status == "resolved" else None
            fallback_status = self._status_for_mapping(resolved_mapping)
            rows.append({
                "id": sensor,
                "address": f"0x{sensor:02X}" if sensor >= 0x80 else str(sensor),
                "name": data.get("sensor_name") or SENSOR_SELECTORS.get(sensor, f"rf_sensor_{sensor}"),
                "kind": data.get("kind") or ("touchpad" if sensor in (0x90, 0x91) else "rf"),
                "temperature": _first_not_none(data.get("temperature"), fallback_status.get("temperature")),
                "status": data.get("status") or ("missing" if data.get("present") is False else "listed" if data.get("listed") else "unknown"),
                "present": data.get("present"),
                "listed": data.get("listed"),
                "signal": data.get("signal"),
                "battery": data.get("battery"),
                "low_battery": _first_not_none(data.get("low_battery"), fallback_status.get("low_battery")),
                "mac": data.get("mac"),
                "mapping_status": mapping_status,
                "resolved_group_id": None if resolved_mapping is None else resolved_mapping["group_id"],
                "resolved_zone_id": None if resolved_mapping is None else resolved_mapping["zone_id"],
                "mapped_groups": [] if resolved_mapping is None else [resolved_mapping["name"]],
                "mapped_group_ids": [] if resolved_mapping is None else [resolved_mapping["group_id"]],
                "mapped_zones": [] if resolved_mapping is None else [resolved_mapping],
                "mapping_candidate_group_ids": [mapping["group_id"] for mapping in mappings] if mapping_status == "ambiguous" else [],
                "mapping_candidates": mappings if mapping_status == "ambiguous" else [],
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
                "mapping_status": "unmapped",
                "resolved_group_id": None,
                "resolved_zone_id": None,
                "mapped_groups": [],
                "mapped_group_ids": [],
                "mapped_zones": [],
                "mapping_candidate_group_ids": [],
                "mapping_candidates": [],
                "ac": ac,
            })
        return rows

    def _status_for_mapping(self, mapping: dict[str, Any] | None) -> dict[str, Any]:
        if mapping is None:
            return {}
        group_id = mapping.get("group_id")
        if not isinstance(group_id, int):
            return {}
        group = self.groups.get(group_id) or {}
        status = group.get("status") or {}
        return status if isinstance(status, dict) else {}

    def _sensor_zone_mappings(self) -> dict[int, list[dict[str, Any]]]:
        mapped: dict[int, list[dict[str, Any]]] = {}
        for group_id, group in sorted(self.active_groups().items()):
            zone_mapping = self._zone_mapping_for_group(group_id, group)
            if zone_mapping is None:
                continue
            sensor, mapping = zone_mapping
            mapped.setdefault(sensor, []).append(mapping)
        return mapped

    def _zone_mapping_for_group(self, group_id: int, group: dict[str, Any]) -> tuple[int, dict[str, Any]] | None:
        status = group.get("status") or {}
        sensor_ref = self._sensor_ref_for_group(group_id, group)
        sensor = sensor_ref.get("sensor_id")
        if status.get("has_sensor") is not True or not isinstance(sensor, int):
            return None

        grouping = group.get("grouping") or {}
        name = group.get("name") or f"Zone {group_id + 1}"
        mapping: dict[str, Any] = {
            "group_id": group_id,
            "zone_id": group_id,
            "zone_number": group_id + 1,
            "name": name,
            "source": sensor_ref.get("source"),
            "sensor_id": sensor,
            "sensor_kind": sensor_ref.get("sensor_kind"),
        }
        if sensor_ref.get("sensor_slot") is not None:
            mapping["sensor_slot"] = sensor_ref["sensor_slot"]
        ac_id = self._ac_id_for_group(group_id)
        if ac_id is not None:
            mapping["ac_id"] = ac_id
        if isinstance(grouping.get("zone_start"), int):
            mapping["damper_zone_start"] = grouping["zone_start"]
        if isinstance(grouping.get("zone_count"), int):
            mapping["damper_zone_count"] = grouping["zone_count"]
        return sensor, mapping

    def _refresh_group_sensor_refs(self) -> None:
        for group_id, group in self.groups.items():
            status = group.get("status")
            if not isinstance(status, dict):
                continue
            sensor_ref = self._sensor_ref_for_group(group_id, group)
            status["sensor_id"] = sensor_ref.get("sensor_id")
            status["sensor_kind"] = sensor_ref.get("sensor_kind")
            status["sensor_slot"] = sensor_ref.get("sensor_slot")
            status["sensor_source"] = sensor_ref.get("source")
            status["sensor_mapping_status"] = sensor_ref["mapping_status"]

    def _sensor_ref_for_group(self, group_id: int, group: dict[str, Any]) -> dict[str, Any]:
        status = group.get("status") or {}
        if status.get("has_sensor") is not True:
            return _sensor_ref(None, None, None, None, "unmapped")

        grouping = group.get("grouping") or {}
        thermostat = grouping.get("thermostat")
        if isinstance(thermostat, int):
            if 0 <= thermostat <= 1:
                sensor_flag = grouping.get(f"has_sensor_{thermostat + 1}")
                if sensor_flag is False:
                    return _sensor_ref(None, None, None, "grouping.sensor_slot", "unmapped")
                sensor_id = (group_id * 2) + thermostat
                return _sensor_ref(sensor_id, "rf", thermostat + 1, "grouping.sensor_slot", "resolved")
            if thermostat in (0x90, 0x91):
                return _sensor_ref(thermostat, "touchpad", None, "grouping.touchpad", "resolved")
            if thermostat == 0xFF:
                return _sensor_ref(None, None, None, "grouping.auto", "unmapped")
            return _sensor_ref(None, None, None, "grouping.thermostat", "ambiguous")

        sensor = status.get("sensor")
        if isinstance(sensor, int) and sensor != 255:
            kind = "touchpad" if sensor in (0x90, 0x91) else "rf"
            return _sensor_ref(sensor, kind, None, "group_status.sensor", "resolved")
        return _sensor_ref(None, None, None, None, "unmapped")

    def _ac_id_for_group(self, group_id: int) -> int | None:
        for ac_id, ac in sorted(self.acs.items()):
            base = ac.get("base") if isinstance(ac, dict) else None
            if not isinstance(base, dict):
                continue
            start = base.get("group_start")
            count = base.get("group_count")
            if isinstance(start, int) and isinstance(count, int) and start <= group_id < start + count:
                return ac_id
        return None

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


def _sensor_ref(sensor_id: int | None, kind: str | None, slot: int | None, source: str | None, status: str) -> dict[str, Any]:
    return {
        "sensor_id": sensor_id,
        "sensor_kind": kind,
        "sensor_slot": slot,
        "source": source,
        "mapping_status": status,
    }


def _first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None
