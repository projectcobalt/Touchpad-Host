"""Internal/non-touchscreen bus payloads observed during RS485 monitoring."""

from __future__ import annotations

from typing import Any

from ..packet import hex_bytes
from .common import u16be


def decode_expansion_damper_status(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "expansion_damper_status",
        "scope": "non_touchscreen",
        "raw": hex_bytes(payload),
    }
    if len(payload) >= 16:
        expansion_percentages = list(payload[8:16])
        active_ui_zones = [index + 9 for index, percentage in enumerate(expansion_percentages) if percentage > 0]
        result.update({
            "leading_bytes": hex_bytes(payload[:6]),
            "word_6": u16be(payload, 6),
            "expansion_damper_percentages": expansion_percentages,
            "active_expansion_ui_zones": active_ui_zones,
            "tail_values": expansion_percentages,
            "tail_all_100": all(byte == 100 for byte in expansion_percentages),
            "zone_mapping": "tail bytes map to zero-based groups 8-15 / UI zones 9-16",
            "note": "0x80->0x81 expansion damper/output status inferred from expansion zone captures.",
        })
    return result
