#!/usr/bin/env python3
"""Resolve the emulated touchpad heartbeat temperature before service start."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from airtouch4.payloads.common import encode_internal_temperature


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sensor", default="", help="Optional Home Assistant sensor entity ID.")
    parser.add_argument("--fallback", type=float, default=25.0, help="Fallback temperature in degrees C.")
    parser.add_argument("--raw-payload", default="", help="Optional raw heartbeat payload override.")
    parser.add_argument("--timeout", type=float, default=3.0)
    return parser


def heartbeat_payload_for_temperature(temperature: float) -> str:
    return f"00 {encode_internal_temperature(temperature):02X} 00"


def read_sensor_state(entity_id: str, *, timeout: float = 3.0) -> float:
    token = os.environ.get("SUPERVISOR_TOKEN", "")
    if not token:
        raise RuntimeError("SUPERVISOR_TOKEN is not available")
    url = f"http://supervisor/core/api/states/{quote(entity_id, safe='')}"
    request = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"could not read {entity_id}: {exc}") from exc
    state = data.get("state")
    try:
        return float(state)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{entity_id} state is not numeric: {state!r}") from exc


def resolve_payload(*, sensor: str, fallback: float, raw_payload: str, timeout: float = 3.0) -> tuple[str, str]:
    raw_payload = raw_payload.strip()
    if raw_payload:
        return raw_payload, "raw override"
    sensor = sensor.strip()
    if sensor:
        try:
            temperature = read_sensor_state(sensor, timeout=timeout)
            return heartbeat_payload_for_temperature(temperature), f"{sensor}={temperature:g}"
        except RuntimeError as exc:
            print(f"WARNING: {exc}; using fallback touchpad temperature {fallback:g}", file=sys.stderr)
    return heartbeat_payload_for_temperature(fallback), f"fallback={fallback:g}"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload, source = resolve_payload(
        sensor=args.sensor,
        fallback=args.fallback,
        raw_payload=args.raw_payload,
        timeout=args.timeout,
    )
    print(payload)
    print(f"Resolved touchpad heartbeat temperature source: {source}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
