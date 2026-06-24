"""Human-readable formatting for live AirTouch RS485 monitoring."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .packet import AirTouchPacket, hex_bytes
from .constants import ADDR_MOBILE, ADDR_SERVER
from .payloads import REFERENCE_DECODERS, decode_mainboard_payload

SKIPPED_TYPES = {
    "expansion_damper_status",
    "bulk_info_client",
    "group_control_client",
    "group_status_client",
    "group_status_client_request",
    "ac_control_client",
    "ac_status_client",
    "ac_status_client_request",
    "non_emulation_reference_traffic",
}


@dataclass
class MonitorStats:
    rx_count: int = 0
    tx_count: int = 0
    shown_count: int = 0
    skipped: Counter[str] = field(default_factory=Counter)
    undecoded: Counter[str] = field(default_factory=Counter)

    def observe(self, direction: str, packet: AirTouchPacket, decoded: dict[str, Any], *, shown: bool) -> None:
        if direction == "rx":
            self.rx_count += 1
        elif direction == "tx":
            self.tx_count += 1
        if shown:
            self.shown_count += 1
        key = f"0x{packet.command:02X} {packet.command_name} {packet.src_name}->{packet.dest_name} len={len(packet.payload)}"
        kind = decoded.get("type")
        if kind in SKIPPED_TYPES:
            self.skipped[key] += 1
        elif kind in {"unknown", "decode_error"}:
            self.undecoded[key] += 1

    def summary_lines(self) -> list[str]:
        lines = [f"summary rx={self.rx_count} tx={self.tx_count} shown={self.shown_count}"]
        if self.skipped:
            lines.append("skipped non-touchscreen/client/internal traffic:")
            for key, count in self.skipped.most_common(8):
                lines.append(f"  {count:4d} {key}")
        if self.undecoded:
            lines.append("undecoded touchscreen-stack traffic:")
            for key, count in self.undecoded.most_common(8):
                lines.append(f"  {count:4d} {key}")
        return lines


def should_show(decoded: dict[str, Any], *, show_skipped: bool = False) -> bool:
    kind = decoded.get("type")
    if kind in SKIPPED_TYPES:
        return show_skipped
    return True


def format_packet_line(direction: str, packet: AirTouchPacket, *, show_hex: bool = False) -> str:
    decoded = decode_live_payload(packet)
    base = f"{direction.upper()} {packet.src_name}->{packet.dest_name} #{packet.packet_id:02X} 0x{packet.command:02X} {packet.command_name}"
    detail = format_decoded_detail(decoded, packet)
    if show_hex:
        detail = f"{detail} hex={hex_bytes(packet.payload)}".strip()
    return f"{base} {detail}".rstrip()


def decode_live_payload(packet: AirTouchPacket) -> dict[str, Any]:
    """Decode only APK/internal touchscreen traffic for live emulation tools."""
    if packet.command in REFERENCE_DECODERS or packet.src in (ADDR_MOBILE, ADDR_SERVER) or packet.dest in (ADDR_MOBILE, ADDR_SERVER):
        return {
            "type": "non_emulation_reference_traffic",
            "scope": "not_touchscreen_emulation",
            "payload_len": len(packet.payload),
        }
    return decode_mainboard_payload(packet.command, packet.payload)


def format_decoded_detail(decoded: dict[str, Any], packet: AirTouchPacket) -> str:
    kind = decoded.get("type")
    if kind in SKIPPED_TYPES:
        return f"[skipped-category:{kind}] len={len(packet.payload)}"
    if kind == "unknown":
        return f"[needs-decoder] len={len(packet.payload)} {hex_bytes(packet.payload[:24])}"
    if kind == "decode_error":
        return f"[decode-error] {decoded.get('error')} len={len(packet.payload)}"
    if kind == "group_status_internal":
        return format_group_status(decoded)
    if kind == "ac_status_internal":
        return format_ac_status(decoded)
    if kind == "sensor_info":
        return format_sensor_info(decoded)
    if kind == "sensor_list":
        return f"sensors={decoded.get('sensor_addresses', [])}"
    if kind == "touchpad_temperature":
        return f"touchpad_temp={decoded.get('temperature')} raw=0x{decoded.get('temperature_raw', 0):02X}"
    if kind == "led_response":
        return f"led=0x{decoded.get('led_code', 0):02X} {decoded.get('led_name')}"
    if kind == "group_name":
        names = ", ".join(record.get("name", "") for record in decoded.get("records", [])[:6])
        return f"group_names {names}"
    if kind == "grouping":
        return f"grouping records={decoded.get('record_count')}"
    if kind == "spill":
        return f"spill_groups={decoded.get('spill_groups_one_based')}"
    if kind == "parameters":
        return f"groups={decoded.get('group_count')} device={decoded.get('device_id')} fw={decoded.get('firmware_version_raw')}"
    if kind == "preference":
        return f"system={decoded.get('system_name', '')}"
    if kind == "favourite":
        names = ", ".join(record.get("name", "") for record in decoded.get("records", []))
        return f"favourites {names}"
    if kind == "program_define_new":
        return f"programs={decoded.get('program_count')} record_len={decoded.get('record_len')}"
    if kind == "service":
        return f"service={decoded.get('company', '')} {decoded.get('phone', '')}"
    if kind == "ac_setting_new":
        return f"ac_settings records={decoded.get('record_count')}"
    if kind == "ac_base_info":
        names = ", ".join(record.get("name", "") for record in decoded.get("records", []))
        return f"ac_count={decoded.get('ac_count')} {names}"
    if kind == "datetime":
        return f"time={decoded.get('year')}-{decoded.get('month')}-{decoded.get('day')} {decoded.get('hour')}:{decoded.get('minute')}:{decoded.get('second')}"
    return f"{kind} len={len(packet.payload)}"


def format_group_status(decoded: dict[str, Any]) -> str:
    parts = []
    for record in decoded.get("records", [])[:8]:
        parts.append(
            f"g{record.get('group')}:{record.get('power_name')} "
            f"{record.get('percentage')}% sp={record.get('setpoint')} temp={record.get('temperature')}"
        )
    return " | ".join(parts)


def format_ac_status(decoded: dict[str, Any]) -> str:
    parts = []
    for record in decoded.get("records", [])[:4]:
        if not record.get("available"):
            parts.append(f"ac{record.get('ac')}:unavailable")
        else:
            parts.append(
                f"ac{record.get('ac')}:{'on' if record.get('power_on') else 'off'} "
                f"mode={record.get('mode')} fan={record.get('fan')} sp={record.get('setpoint')}"
            )
    return " | ".join(parts)


def format_sensor_info(decoded: dict[str, Any]) -> str:
    parts = []
    for record in decoded.get("records", [])[:4]:
        parts.append(
            f"{record.get('sensor_name')}:{record.get('status')} "
            f"temp={record.get('temperature')} batt={record.get('battery')} sig={record.get('signal')}"
        )
    return " | ".join(parts)
