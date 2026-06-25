#!/usr/bin/env python3
"""Run the Python AirTouch touchscreen-protocol host and emit state snapshots."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import TextIO

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from airtouch4.command_file import CommandFileError, load_transactions
from airtouch4.live_log import JsonlBusLogger
from airtouch4.runtime import AirTouchRuntime, RuntimeConfig, RuntimeEvent
from airtouch4.session.touchscreen import describe_packet, parse_hex_payload
from airtouch4.state import AirTouchState
from airtouch4.transport.serial import SerialConfig, SerialDependencyError, SerialRs485Transport


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="Serial port for the USB-RS485 bridge, for example COM3.")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate. Default: 115200.")
    parser.add_argument("--duration", type=float, help="Stop after this many seconds.")
    parser.add_argument("--bus-log", type=Path, help="Optional raw RX/TX/init JSONL log.")
    parser.add_argument("--state-log", type=Path, help="Optional state snapshot JSONL log.")
    parser.add_argument("--command-file", type=Path, help="Optional JSONL transactions to enqueue after init.")
    parser.add_argument("--snapshot-interval", type=float, default=10.0, help="State snapshot interval in seconds.")
    parser.add_argument("--protocol", default="auto", choices=("auto", "at4", "at5"), help="AirTouch protocol profile. AT4 is implemented; AT5 is detected but not yet live-control capable.")
    parser.add_argument("--detect-seconds", type=float, default=3.0, help="Address-detection listen window.")
    parser.add_argument("--source-address", default="auto", help="Preferred touchpad source address: auto, 0x90, or 0x91. Default: auto.")
    parser.add_argument("--force-source-address", action="store_true", help="Use --source-address even if discovery sees that address occupied.")
    parser.add_argument("--heartbeat-interval", type=float, default=30.0, help="Heartbeat interval in seconds.")
    parser.add_argument("--heartbeat-payload", default="00 EA 00", help="Heartbeat payload hex. Default: '00 EA 00'.")
    parser.add_argument("--quiet", action="store_true", help="Suppress packet/status lines.")
    return parser


class SnapshotWriter:
    def __init__(self, path: Path | None) -> None:
        self.path = path
        self._handle: TextIO | None = None

    def __enter__(self) -> "SnapshotWriter":
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = self.path.open("a", encoding="utf-8")
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def write(self, snapshot: dict, *, reason: str) -> None:
        record = {
            "event": "state",
            "reason": reason,
            "host_epoch": time.time(),
            "host_ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            **snapshot,
        }
        line = json.dumps(record, sort_keys=True, separators=(",", ":"))
        if self._handle is None:
            print(line, flush=True)
        else:
            self._handle.write(line + "\n")
            self._handle.flush()


def maybe_print(quiet: bool, line: str) -> None:
    if not quiet:
        print(line, flush=True)


def handle_runtime_event(logger: JsonlBusLogger, quiet: bool, event: RuntimeEvent) -> None:
    if event.event == "rx" and event.packet is not None:
        logger.log_rx(event.packet)
        maybe_print(quiet, "RX " + describe_packet(event.packet))
    elif event.event == "tx" and event.packet is not None and event.wire is not None:
        logger.log_tx(event.packet, event.wire)
        maybe_print(quiet, "TX " + describe_packet(event.packet))
    elif event.event == "transaction" and event.transaction is not None:
        logger.write(event.transaction.to_record())
        txn = event.transaction
        maybe_print(quiet, f"TXN {txn.event} {txn.name} {txn.detail}".strip())
    elif event.event == "status":
        logger.write({"event": "runtime_status", "message": event.message})
        maybe_print(quiet, event.message)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started = time.monotonic()
    next_snapshot = started

    try:
        with (
            SerialRs485Transport(SerialConfig(port=args.port, baudrate=args.baud)) as transport,
            JsonlBusLogger(args.bus_log) as bus_logger,
            SnapshotWriter(args.state_log) as snapshots,
        ):
            maybe_print(args.quiet, f"opened {args.port} at {args.baud}")
            runtime = AirTouchRuntime(
                transport,
                RuntimeConfig(
                    active=True,
                    detect_seconds=args.detect_seconds,
                    heartbeat_interval=args.heartbeat_interval,
                    heartbeat_payload=parse_hex_payload(args.heartbeat_payload),
                    source_address=parse_source_address(args.source_address),
                    auto_address=True,
                    force_source_address=args.force_source_address,
                    init_transactions=True,
                    protocol=args.protocol,
                ),
            )
            if args.command_file is not None:
                try:
                    runtime.enqueue(load_transactions(args.command_file))
                except CommandFileError as exc:
                    print(str(exc), file=sys.stderr)
                    return 2

            for event in runtime.start(now=started):
                handle_runtime_event(bus_logger, args.quiet, event)

            while True:
                now = time.monotonic()
                if args.duration is not None and now - started >= args.duration:
                    if runtime.transactions is not None:
                        bus_logger.write({"event": "transaction_summary", **runtime.transactions.summary()})
                    snapshots.write(runtime.snapshot(), reason="duration_exit")
                    return 0

                for event in runtime.step(now=now):
                    handle_runtime_event(bus_logger, args.quiet, event)

                if now >= next_snapshot:
                    snapshots.write(runtime.snapshot(), reason="interval")
                    next_snapshot = now + args.snapshot_interval

    except KeyboardInterrupt:
        return 130
    except SerialDependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 2


def parse_source_address(text: str) -> int | None:
    if text.lower() == "auto":
        return None
    return int(text, 0)


if __name__ == "__main__":
    raise SystemExit(main())
