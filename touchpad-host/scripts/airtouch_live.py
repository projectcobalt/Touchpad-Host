#!/usr/bin/env python3
"""Run a live AirTouch internal-bus session over a USB-RS485 adapter."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from airtouch4.live_log import JsonlBusLogger
from airtouch4.session.init import InitEvent, TouchscreenInitStateMachine
from airtouch4.session.touchscreen import (
    DEFAULT_SYNC_COMMANDS,
    TouchscreenSession,
    describe_packet,
    parse_command_list,
    parse_hex_payload,
)
from airtouch4.transport.serial import SerialConfig, SerialDependencyError, SerialRs485Transport


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="Serial port for the USB-RS485 bridge, for example COM7.")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate. Default: 115200.")
    parser.add_argument("--log", type=Path, help="Append JSONL RX/TX events to this path.")
    parser.add_argument("--duration", type=float, help="Stop after this many seconds.")
    parser.add_argument("--listen-only", action="store_true", help="Do not transmit anything. Safest first run.")
    parser.add_argument("--detect-address", action="store_true", help="Ask for touchpad presence and choose the unused 0x90/0x91 address before other TX.")
    parser.add_argument("--detect-seconds", type=float, default=3.0, help="How long to listen after address detection request.")
    parser.add_argument("--heartbeat", action="store_true", help="Send 0x26 heartbeat/temp frames every interval.")
    parser.add_argument("--heartbeat-interval", type=float, default=30.0, help="Heartbeat interval in seconds.")
    parser.add_argument("--heartbeat-payload", default="00 EA 00", help="Heartbeat payload hex. Default: '00 EA 00'.")
    parser.add_argument("--sync", action="store_true", help="Send zero-length startup sync requests once.")
    parser.add_argument("--init", action="store_true", help="Run APK-like sequential init with retry/fallback tracking.")
    parser.add_argument(
        "--sync-commands",
        default=",".join(f"0x{command:02X}" for command in DEFAULT_SYNC_COMMANDS),
        help="Comma-separated command list for --sync.",
    )
    parser.add_argument("--touchpad-addr", type=lambda value: int(value, 0), default=0x90, help="Touchpad source address.")
    parser.add_argument("--mainboard-addr", type=lambda value: int(value, 0), default=0x80, help="Main-board destination address.")
    parser.add_argument("--quiet", action="store_true", help="Do not print decoded packet lines.")
    return parser


def maybe_print(enabled: bool, line: str) -> None:
    if enabled:
        print(line, flush=True)


def log_init_events(logger: JsonlBusLogger, should_print: bool, events: list[InitEvent]) -> None:
    for event in events:
        logger.write(event.to_record())
        if event.command:
            maybe_print(
                should_print,
                (
                    f"INIT {event.event} step={event.step_index} cmd=0x{event.command:02X} "
                    f"payload={event.payload.hex(' ').upper()} {event.name} {event.detail}"
                ).strip(),
            )
        else:
            maybe_print(should_print, f"INIT {event.event} {event.detail}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    session = TouchscreenSession(
        src=args.touchpad_addr,
        dest=args.mainboard_addr,
        heartbeat_payload=parse_hex_payload(args.heartbeat_payload),
        heartbeat_interval=args.heartbeat_interval,
        sync_commands=parse_command_list(args.sync_commands),
        auto_address=args.detect_address,
    )

    started = time.monotonic()
    should_print = not args.quiet
    init = TouchscreenInitStateMachine() if args.init and not args.listen_only else None

    try:
        with SerialRs485Transport(SerialConfig(port=args.port, baudrate=args.baud)) as transport, JsonlBusLogger(args.log) as logger:
            maybe_print(should_print, f"opened {args.port} at {args.baud}; listen_only={args.listen_only}")

            if args.detect_address and not args.listen_only:
                packet, wire = session.build_touchpad_info_request()
                transport.write(wire)
                logger.log_tx(packet, wire)
                maybe_print(should_print, "TX " + describe_packet(packet))
                detect_until = time.monotonic() + args.detect_seconds
                while time.monotonic() < detect_until:
                    data = transport.read()
                    if data:
                        for rx_packet in session.feed_rx(data):
                            logger.log_rx(rx_packet)
                            maybe_print(should_print, "RX " + describe_packet(rx_packet))
                session.choose_available_address()
                maybe_print(should_print, f"using touchpad address 0x{session.src:02X}")

            if args.sync and not args.listen_only:
                for packet, wire in session.build_sync_requests():
                    transport.write(wire)
                    logger.log_tx(packet, wire)
                    maybe_print(should_print, "TX " + describe_packet(packet))
                    time.sleep(0.05)

            while True:
                if args.duration is not None and time.monotonic() - started >= args.duration:
                    if init is not None:
                        logger.write({"event": "init_summary", **init.summary()})
                    return 0

                data = transport.read()
                if data:
                    for packet in session.feed_rx(data):
                        logger.log_rx(packet)
                        maybe_print(should_print, "RX " + describe_packet(packet))
                        if init is not None:
                            log_init_events(logger, should_print, init.observe(packet))

                if args.heartbeat and not args.listen_only and session.due_heartbeat():
                    packet, wire = session.build_heartbeat()
                    transport.write(wire)
                    session.mark_heartbeat_sent()
                    logger.log_tx(packet, wire)
                    maybe_print(should_print, "TX " + describe_packet(packet))

                if init is not None:
                    events, request = init.poll(time.monotonic())
                    log_init_events(logger, should_print, events)
                    if request is not None:
                        packet, wire = session.build_packet(request.command, request.payload)
                        transport.write(wire)
                        logger.log_tx(packet, wire)
                        maybe_print(
                            should_print,
                            f"TX init step={request.step_index} attempt={request.attempt} " + describe_packet(packet),
                        )

    except KeyboardInterrupt:
        return 130
    except SerialDependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
