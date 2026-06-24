#!/usr/bin/env python3
"""Run the AirTouch runtime as an HTTP/WebSocket service."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from airtouch4.runtime import RuntimeConfig
from airtouch4.service.api import create_app
from airtouch4.service.controller import RuntimeController, RuntimeControllerConfig
from airtouch4.session.touchscreen import parse_hex_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", default="local_serial", choices=("local_serial", "tcp_serial"))
    parser.add_argument("--port", help="Serial port for the USB-RS485 bridge, for example COM3 or /dev/ttyUSB0.")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--tcp-host", default="127.0.0.1", help="TCP serial bridge host when --transport tcp_serial is used.")
    parser.add_argument("--tcp-port", type=int, default=6638, help="TCP serial bridge port when --transport tcp_serial is used.")
    parser.add_argument("--reconnect-interval", type=float, default=5.0, help="Seconds to wait before reconnecting after transport errors.")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP bind host. Default: 0.0.0.0.")
    parser.add_argument("--http-port", type=int, default=8099, help="HTTP bind port. Default matches HA ingress convention.")
    parser.add_argument("--bus-log", type=Path, help="Optional raw RX/TX/init JSONL log.")
    parser.add_argument("--detect-seconds", type=float, default=3.0)
    parser.add_argument("--heartbeat-interval", type=float, default=30.0)
    parser.add_argument("--heartbeat-payload", default="00 EA 00")
    parser.add_argument("--source-address", default="auto", help="Preferred touchpad source address: auto, 0x90, or 0x91.")
    parser.add_argument("--force-source-address", action="store_true")
    parser.add_argument("--log-level", default="info", choices=("debug", "info", "warning", "error"))
    return parser


def parse_source_address(text: str) -> int | None:
    if text.lower() == "auto":
        return None
    return int(text, 0)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.transport == "local_serial" and not args.port:
        print("--port is required when --transport local_serial is used", file=sys.stderr)
        return 2
    try:
        import uvicorn
    except ModuleNotFoundError:
        print("uvicorn is required for the service. Install dependencies from requirements.txt", file=sys.stderr)
        return 2

    runtime_config = RuntimeConfig(
        active=True,
        detect_seconds=args.detect_seconds,
        heartbeat_interval=args.heartbeat_interval,
        heartbeat_payload=parse_hex_payload(args.heartbeat_payload),
        source_address=parse_source_address(args.source_address),
        auto_address=True,
        force_source_address=args.force_source_address,
        init_transactions=True,
    )
    controller = RuntimeController(
        RuntimeControllerConfig(
            port=args.port or "",
            baudrate=args.baud,
            transport=args.transport,
            tcp_host=args.tcp_host,
            tcp_port=args.tcp_port,
            reconnect_interval=args.reconnect_interval,
            runtime=runtime_config,
            bus_log=args.bus_log,
        )
    )
    uvicorn.run(create_app(controller), host=args.host, port=args.http_port, log_level=args.log_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
