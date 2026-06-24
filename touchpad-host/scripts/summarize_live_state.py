#!/usr/bin/env python3
"""Summarize live JSONL captures into the normalized AirTouch state shape."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from airtouch4.packet import parse_packet
from airtouch4.state import AirTouchState


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit full state JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state = AirTouchState()
    rx_count = 0
    for line in args.capture.open("r", encoding="utf-8"):
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("event") != "rx":
            continue
        raw = record.get("raw")
        if not isinstance(raw, str):
            continue
        packet = parse_packet(bytes.fromhex(raw))
        state.apply_packet(packet)
        rx_count += 1

    snapshot = state.snapshot()
    if args.json:
        print(json.dumps({"rx_packets": rx_count, "state": snapshot}, indent=2, sort_keys=True))
        return 0

    groups = snapshot["groups"]
    active_groups = snapshot["active_groups"]
    acs = snapshot["acs"]
    sensors = snapshot["sensors"]
    print(f"rx_packets: {rx_count}")
    print(f"system_name: {snapshot['system'].get('system_name', '')}")
    print(f"group_count: {snapshot['system'].get('group_count', '')}")
    print(f"acs: {sorted(acs)}")
    print(f"groups: {len(groups)} configured, {len(active_groups)} active")
    for group, data in sorted(active_groups.items())[:16]:
        status = data.get("status", {})
        grouping = data.get("grouping", {})
        print(
            f"  group {group}: {data.get('name', '')} "
            f"power={status.get('power_name', '')} pct={status.get('percentage', '')} "
            f"setpoint={status.get('setpoint', '')} thermostat={grouping.get('thermostat_name', '')}"
        )
    print(f"sensors: {sorted(sensors)}")
    print(f"favourites: {[data.get('name') for _key, data in sorted(snapshot['favourites'].items())]}")
    print(f"programs: {[data.get('name') for _key, data in sorted(snapshot['programs'].items())]}")
    print(f"service: {snapshot['service'].get('company', '')} {snapshot['service'].get('phone', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
