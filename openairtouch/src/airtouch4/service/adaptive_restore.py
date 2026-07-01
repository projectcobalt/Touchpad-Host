"""Restore ledger helpers for adaptive control."""

from __future__ import annotations

from typing import Any

from ..session.queue import TransactionSpec


class AdaptiveRestoreMixin:
    def _restore_all(self, state: dict[str, Any], status: dict[str, Any], now: float) -> list[TransactionSpec]:
        specs: list[TransactionSpec] = []
        for key in list(self._restore_records):
            specs.extend(self._restore_record(state, key, status, now))
        return specs

    def _restore_ac(self, state: dict[str, Any], ac_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        specs = self._restore_ac_mode(state, ac_id, status, now)
        specs.extend(self._restore_ac_setpoint(state, ac_id, status, now))
        specs.extend(self._restore_ac_control_sensor(state, ac_id, status, now))
        ac = _indexed(state.get("acs") or {}, ac_id) or {}
        for group_id, _group in _groups_for_ac(state, ac_id, ac):
            specs.extend(self._restore_group_sensor_control(state, group_id, status, now))
            specs.extend(self._restore_group_setpoint(state, group_id, status, now))
            specs.extend(self._restore_group_percentage(state, group_id, status, now))
        return specs

    def _restore_ac_mode(self, state: dict[str, Any], ac_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"ac:{ac_id}:mode", status, now)

    def _restore_ac_setpoint(self, state: dict[str, Any], ac_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"ac:{ac_id}:setpoint", status, now)

    def _restore_ac_control_sensor(self, state: dict[str, Any], ac_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"ac:{ac_id}:control_sensor", status, now)

    def _restore_group_setpoint(self, state: dict[str, Any], group_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"group:{group_id}:setpoint", status, now)

    def _restore_group_sensor_control(self, state: dict[str, Any], group_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"group:{group_id}:sensor_control", status, now)

    def _record_restore(
        self,
        key: str,
        action: str,
        original: dict[str, Any],
        target: dict[str, Any],
        *,
        target_action: str | None = None,
    ) -> bool:
        if original == target:
            if key not in self._restore_records:
                return False
            self._restore_records.pop(key, None)
            return False
        record = self._restore_records.setdefault(key, {"action": action, "original": dict(original)})
        record["action"] = action
        record.setdefault("original", dict(original))
        record["target"] = dict(target)
        if target_action is not None:
            record["target_action"] = target_action
        else:
            record.pop("target_action", None)
        return True

    def _restore_dampers_for_ac(self, state: dict[str, Any], ac_id: int, ac: dict[str, Any], status: dict[str, Any], now: float) -> list[TransactionSpec]:
        specs: list[TransactionSpec] = []
        for group_id, _group in _groups_for_ac(state, ac_id, ac):
            specs.extend(self._restore_group_sensor_control(state, group_id, status, now))
            specs.extend(self._restore_group_percentage(state, group_id, status, now))
        return specs

    def _restore_group_percentage(self, state: dict[str, Any], group_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"group:{group_id}:percentage", status, now)

    def _restore_record(self, state: dict[str, Any], key: str, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        record = self._restore_records.get(key)
        if record is None:
            return []
        action = str(record.get("action") or "")
        target_action = str(record.get("target_action") or action)
        original = record.get("original") if isinstance(record.get("original"), dict) else {}
        target = record.get("target") if isinstance(record.get("target"), dict) else {}
        current = self._restore_current_payload(state, target_action, target)
        if current != target:
            self._restore_records.pop(key, None)
            return []
        spec = self._send_restore_action(state, action, original, status, now)
        if spec is None:
            return []
        self._restore_records.pop(key, None)
        status["actions"].append(self._restore_action_text(state, action, original))
        return [spec]

    def _restore_current_payload(self, state: dict[str, Any], action: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        if action == "ac_status":
            ac_id = _optional_int(payload.get("ac"))
            ac = _indexed(state.get("acs") or {}, ac_id) if ac_id is not None else None
            ac_status = (ac.get("status") or {}) if isinstance(ac, dict) else {}
            current: dict[str, Any] = {"ac": ac_id}
            if "mode" in payload:
                current["mode"] = _optional_int(ac_status.get("mode"))
            if "setpoint" in payload:
                setpoint = _number(ac_status.get("setpoint"))
                current["setpoint"] = int(round(setpoint)) if setpoint is not None else None
            if "power_on" in payload:
                current["power_on"] = bool(ac_status.get("power_on"))
            return current
        if action in {"group_setpoint", "group_percentage"}:
            group_id = _optional_int(payload.get("group"))
            group = _group_for_id(state, group_id) if group_id is not None else None
            group_status = (group.get("status") or {}) if isinstance(group, dict) else {}
            current = {"group": group_id}
            field = "setpoint" if action == "group_setpoint" else "percentage"
            value = _number(group_status.get(field))
            current[field] = int(round(value)) if value is not None else None
            return current
        if action == "ac_setting_new":
            ac_id = _optional_int(payload.get("ac"))
            record = _ac_setting_record_for(state, ac_id) if ac_id is not None else None
            return {
                "ac": ac_id,
                "ctrl_thermostat": _optional_int(record.get("ctrl_thermostat")) if isinstance(record, dict) else None,
            }
        return None

    def _send_restore_action(
        self,
        state: dict[str, Any],
        action: str,
        original: dict[str, Any],
        status: dict[str, Any],
        now: float,
    ) -> TransactionSpec | None:
        if action == "ac_status":
            key_suffix = "mode" if "mode" in original else "setpoint" if "setpoint" in original else "status"
            return self._send_transaction(state, action, original, f"restore:ac:{original.get('ac')}:{key_suffix}", status, now)
        if action == "group_setpoint":
            return self._send_transaction(state, action, original, f"restore:group:{original.get('group')}:setpoint", status, now)
        if action == "group_percentage":
            return self._send_transaction(state, action, original, f"restore:group:{original.get('group')}:percentage", status, now)
        if action == "ac_setting_new":
            return self._send_transaction(state, action, original, f"restore:ac:{original.get('ac')}:control_sensor", status, now)
        return None

    def _restore_action_text(self, state: dict[str, Any], action: str, original: dict[str, Any]) -> str:
        if action == "ac_status":
            ac_id = _optional_int(original.get("ac"))
            ac = _indexed(state.get("acs") or {}, ac_id) if ac_id is not None else {}
            if "mode" in original:
                return f"{_ac_name(ac_id or 0, ac or {})}: Restored Mode: {_mode_name(_optional_int(original.get('mode')))}"
            if "setpoint" in original:
                return f"{_ac_name(ac_id or 0, ac or {})}: Restored Setpoint: {original['setpoint']} C"
            return f"{_ac_name(ac_id or 0, ac or {})}: Restored AC State"
        group_id = _optional_int(original.get("group")) or 0
        group = _group_for_id(state, group_id)
        if action == "group_setpoint":
            return f"{_group_name(group_id, group)}: Restored Setpoint: {original['setpoint']} C"
        if action == "group_percentage":
            return f"{_group_name(group_id, group)}: Restored Damper: {original['percentage']}%"
        if action == "ac_setting_new":
            ac_id = _optional_int(original.get("ac")) or 0
            ac = _indexed(state.get("acs") or {}, ac_id) or {}
            return f"{_ac_name(ac_id, ac)}: Restored Control Sensor"
        return "Adaptive State Restored"




def _groups_for_ac(state: dict[str, Any], ac_id: int, ac: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    base = ac.get("base") or {}
    groups = state.get("active_groups") or state.get("groups") or {}
    start = base.get("group_start")
    count = base.get("group_count")
    result = []
    for key, value in groups.items():
        try:
            group_id = int(key)
        except (TypeError, ValueError):
            continue
        if not isinstance(value, dict):
            continue
        if isinstance(start, int) and isinstance(count, int) and not (start <= group_id < start + count):
            continue
        result.append((group_id, value))
    return sorted(result)


def _group_for_id(state: dict[str, Any], group_id: int) -> dict[str, Any]:
    group = _indexed(state.get("active_groups") or {}, group_id)
    if isinstance(group, dict):
        return group
    group = _indexed(state.get("groups") or {}, group_id)
    return group if isinstance(group, dict) else {}


def _ac_setting_record_for(state: dict[str, Any], ac_id: int | None) -> dict[str, Any] | None:
    if ac_id is None:
        return None
    ac = _indexed(state.get("acs") or {}, ac_id)
    if not isinstance(ac, dict):
        return None
    settings = ac.get("settings") or {}
    if not isinstance(settings, dict):
        return None
    return {
        "ac": ac_id,
        "hide_spill_group": bool(settings.get("hide_spill_group", False)),
        "ctrl_thermostat": int(settings.get("ctrl_thermostat", 0) or 0),
        "cool_adjust": int(settings.get("cool_adjust", 0) or 0),
        "heat_adjust": int(settings.get("heat_adjust", 0) or 0),
        "modes": dict(settings.get("modes") or {}),
        "fan_values": dict(settings.get("fan_values") or {}),
        "auto_off": bool(settings.get("auto_off", False)),
        "on_time_limit": int(settings.get("on_time_limit", 0) or 0),
        "max_setpoint": int(settings.get("max_setpoint", 30) or 30),
        "min_setpoint": int(settings.get("min_setpoint", 16) or 16),
        "selector_visibility": dict(settings.get("selector_visibility") or {}),
    }


def _ac_setting_records_from_state(state: dict[str, Any]) -> list[dict[str, Any]]:
    acs = state.get("acs") or {}
    if not isinstance(acs, dict):
        return []
    records: list[dict[str, Any]] = []
    for key in sorted(acs, key=lambda value: _optional_int(value) if _optional_int(value) is not None else 999):
        ac_id = _optional_int(key)
        record = _ac_setting_record_for(state, ac_id)
        if record is not None:
            records.append(record)
    return records


def _indexed(mapping: Any, key: int | None) -> Any:
    if key is None:
        return None
    if isinstance(mapping, dict):
        return mapping.get(key) or mapping.get(str(key))
    if isinstance(mapping, list) and 0 <= key < len(mapping):
        return mapping[key]
    return None


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _mode_name(mode: int | None) -> str:
    names = {0: "Auto", 1: "Heat", 2: "Dry", 3: "Fan", 4: "Cool"}
    return names.get(mode, "Unknown")


def _ac_name(ac_id: int, ac: dict[str, Any]) -> str:
    base = ac.get("base") or {}
    return str(base.get("name") or f"AC {ac_id + 1}")


def _group_name(group_id: int, group: dict[str, Any]) -> str:
    base = group.get("base") or {}
    return str(base.get("name") or f"Zone {group_id + 1}")
