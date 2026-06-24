#!/usr/bin/env python3
"""Stream human-readable AirTouch RS485 traffic in the terminal."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from airtouch4.formatting import MonitorStats, decode_live_payload, format_packet_line, should_show
from airtouch4.live_log import JsonlBusLogger
from airtouch4.session.touchscreen import TouchscreenSession
from airtouch4.transport.serial import SerialConfig, SerialDependencyError, SerialRs485Transport


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="Serial port for the USB-RS485 bridge, for example COM3.")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--duration", type=float, help="Stop after this many seconds.")
    parser.add_argument("--log", type=Path, help="Optional raw JSONL packet log.")
    parser.add_argument("--show-hex", action="store_true", help="Append payload hex to each line.")
    parser.add_argument("--show-skipped", action="store_true", help="Also print non-touchscreen/client/internal categories that are skipped by default.")
    parser.add_argument("--summary-interval", type=float, default=30.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    session = TouchscreenSession()
    stats = MonitorStats()
    started = time.monotonic()
    next_summary = started + args.summary_interval

    try:
        with SerialRs485Transport(SerialConfig(port=args.port, baudrate=args.baud)) as transport, JsonlBusLogger(args.log) as logger:
            print(f"monitoring {args.port} at {args.baud}", flush=True)
            while True:
                now = time.monotonic()
                if args.duration is not None and now - started >= args.duration:
                    for line in stats.summary_lines():
                        print(line, flush=True)
                    return 0

                data = transport.read()
                if data:
                    for packet in session.feed_rx(data):
                        logger.log_rx(packet)
                        decoded = decode_live_payload(packet)
                        show = should_show(decoded, show_skipped=args.show_skipped)
                        stats.observe("rx", packet, decoded, shown=show)
                        if show:
                            print(format_packet_line("rx", packet, show_hex=args.show_hex), flush=True)

                if now >= next_summary:
                    for line in stats.summary_lines():
                        print(line, flush=True)
                    next_summary = now + args.summary_interval

    except KeyboardInterrupt:
        for line in stats.summary_lines():
            print(line, flush=True)
        return 130
    except SerialDependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
