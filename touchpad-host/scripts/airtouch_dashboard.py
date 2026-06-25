#!/usr/bin/env python3
"""Live terminal dashboard for AirTouch RS485 state."""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from airtouch4.formatting import decode_live_payload, format_packet_line, should_show
from airtouch4.live_log import JsonlBusLogger
from airtouch4.runtime import AirTouchRuntime, RuntimeConfig, RuntimeEvent
from airtouch4.session.queue import TransactionEvent, TransactionQueue
from airtouch4.state import AirTouchState
from airtouch4.transport.serial import SerialConfig, SerialDependencyError, SerialRs485Transport


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="Serial port for the USB-RS485 bridge, for example COM3.")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--log", type=Path, help="Optional raw JSONL packet log.")
    parser.add_argument("--duration", type=float, help="Optional smoke-test duration. Omit for normal Ctrl-C operation.")
    parser.add_argument("--refresh", type=float, default=1.0, help="Dashboard refresh interval in seconds.")
    parser.add_argument("--recent", type=int, default=12, help="Number of recent visible events to show.")
    parser.add_argument("--show-skipped", action="store_true", help="Include non-touchscreen/client/internal traffic in recent events.")
    parser.add_argument("--show-hex", action="store_true", help="Append payload hex to recent event lines.")
    parser.add_argument("--passive", action="store_true", help="Sniff only. Do not emulate a fresh touchpad boot/init.")
    parser.add_argument("--protocol", default="auto", choices=("auto", "at4", "at5"), help="AirTouch protocol profile. AT4 is implemented; AT5 is detected but not yet live-control capable.")
    parser.add_argument("--detect-seconds", type=float, default=3.0, help="Address-detection listen window for active mode.")
    parser.add_argument("--source-address", default="auto", help="Preferred touchpad source address: auto, 0x90, or 0x91. Default: auto.")
    parser.add_argument("--force-source-address", action="store_true", help="Use --source-address even if discovery sees that address occupied.")
    parser.add_argument("--heartbeat-interval", type=float, default=30.0, help="Heartbeat interval in active mode.")
    return parser


def clear_screen() -> None:
    sys.stdout.write("\x1b[2J\x1b[H")


def fit(text: object, width: int) -> str:
    if text is None:
        text = ""
    value = str(text)
    if len(value) <= width:
        return value
    return value[: max(0, width - 1)] + "~"


def render_table(headers: list[str], rows: list[list[object]], widths: list[int]) -> list[str]:
    lines = []
    lines.append(" ".join(fit(header, width).ljust(width) for header, width in zip(headers, widths)))
    lines.append(" ".join("-" * width for width in widths))
    for row in rows:
        lines.append(" ".join(fit(value, width).ljust(width) for value, width in zip(row, widths)))
    return lines


def group_rows(state: AirTouchState) -> list[list[object]]:
    rows = []
    for group, data in sorted(state.active_groups().items()):
        status = data.get("status", {})
        grouping = data.get("grouping", {})
        rows.append([
            group,
            data.get("name", ""),
            status.get("power_name", ""),
            status.get("percentage", ""),
            status.get("setpoint", ""),
            status.get("temperature", ""),
            grouping.get("thermostat_name", ""),
        ])
    return rows


def ac_rows(state: AirTouchState) -> list[list[object]]:
    rows = []
    for ac, data in sorted(state.acs.items()):
        status = data.get("status", {})
        base = data.get("base", {})
        settings = data.get("settings", {})
        rows.append([
            ac,
            base.get("name", ""),
            "yes" if status.get("available") else "no",
            "on" if status.get("power_on") else "off",
            status.get("mode", ""),
            status.get("fan", ""),
            status.get("setpoint", ""),
            settings.get("min_setpoint", ""),
            settings.get("max_setpoint", ""),
        ])
    return rows


def sensor_rows(state: AirTouchState) -> list[list[object]]:
    rows = []
    for sensor, data in sorted(state.sensors.items()):
        listed = data.get("listed")
        if data.get("status"):
            status = data["status"]
        elif data.get("present"):
            status = "listed" if listed else "present"
        elif listed is False:
            status = "absent"
        else:
            status = ""
        rows.append([
            f"0x{sensor:02X}" if sensor >= 0x80 else sensor,
            data.get("sensor_name", ""),
            "yes" if listed is True else "no" if listed is False else "",
            status,
            data.get("temperature") if data.get("temperature") is not None else "",
            data.get("battery") if data.get("battery") is not None else "",
            data.get("signal") if data.get("signal") is not None else "",
        ])
    return rows


def transaction_status(transactions: TransactionQueue) -> str:
    summary = transactions.summary()
    completed = len(summary["completed"])
    failed = len(summary["failed"])
    pending = summary["pending"]
    current = summary["current"]
    total = completed + failed + pending + (1 if current is not None else 0)
    if failed:
        state = "failed"
    elif summary["idle"]:
        state = "complete"
    else:
        state = "running"
    current_name = "" if current is None else f" | current {current['name']} attempt {current['attempts']}"
    return f"Init: {state} | done {completed}/{total} | failed {failed}{current_name}"


def append_transaction_event(recent: deque[str], logger: JsonlBusLogger, event: TransactionEvent) -> None:
    logger.write(event.to_record())
    if event.event in {"request", "complete", "failed", "degraded", "finished"}:
        recent.append(f"INIT {event.event} {event.name} {event.detail}".strip())


def append_runtime_event(
    *,
    event: RuntimeEvent,
    recent: deque[str],
    skipped: Counter[str],
    logger: JsonlBusLogger,
    show_hex: bool,
    show_skipped: bool,
) -> None:
    if event.event == "rx" and event.packet is not None:
        logger.log_rx(event.packet)
        decoded = event.decoded or decode_live_payload(event.packet)
        if should_show(decoded, show_skipped=show_skipped):
            recent.append(format_packet_line("rx", event.packet, show_hex=show_hex))
        else:
            skipped[f"0x{event.packet.command:02X} {event.packet.command_name}"] += 1
    elif event.event == "tx" and event.packet is not None and event.wire is not None:
        logger.log_tx(event.packet, event.wire)
        recent.append(format_packet_line("tx", event.packet, show_hex=show_hex))
    elif event.event == "transaction" and event.transaction is not None:
        append_transaction_event(recent, logger, event.transaction)
    elif event.event == "status" and event.message:
        logger.write({"event": "runtime_status", "message": event.message})
        recent.append(event.message.upper() if event.message.startswith("using ") else event.message)


def render_dashboard(
    *,
    state: AirTouchState,
    started: float,
    rx_count: int,
    skipped: Counter[str],
    recent: deque[str],
    port: str,
    mode: str,
    transactions: TransactionQueue | None = None,
) -> str:
    snapshot = state.snapshot()
    system = snapshot["system"]
    uptime = int(time.monotonic() - started)
    lines = [
        f"AirTouch RS485 Live Dashboard | {port} | {mode} | uptime {uptime}s | rx {rx_count} | Ctrl-C exits",
        f"System: {system.get('system_name', '')} | active groups: {system.get('group_count', '')} | configured groups: {len(state.groups)}",
        "",
        "ACs",
    ]
    if transactions is not None:
        lines.insert(2, transaction_status(transactions))
    lines.extend(render_table(
        ["#", "name", "avail", "power", "mode", "fan", "sp", "min", "max"],
        ac_rows(state),
        [3, 10, 5, 5, 4, 4, 4, 4, 4],
    ))
    lines.extend(["", "Active Groups"])
    lines.extend(render_table(
        ["#", "name", "power", "pct", "sp", "temp", "thermostat"],
        group_rows(state),
        [3, 12, 7, 5, 4, 5, 14],
    ))
    lines.extend(["", "Sensors"])
    lines.extend(render_table(
        ["addr", "name", "list", "status", "temp", "bat", "sig"],
        sensor_rows(state),
        [6, 14, 4, 9, 5, 5, 5],
    ))
    favs = ", ".join(data.get("name", "") for _key, data in sorted(state.favourites.items()))
    programs = ", ".join(data.get("name", "") for _key, data in sorted(state.programs.items()))
    service = snapshot["service"]
    lines.extend([
        "",
        f"Favourites: {favs}",
        f"Programs: {programs}",
        f"Service: {service.get('company', '')} {service.get('phone', '')}".rstrip(),
        "",
        "Recent Bus Events",
    ])
    lines.extend(list(recent) or ["  waiting for decoded touchscreen traffic..."])
    if skipped:
        lines.extend(["", "Skipped Categories"])
        for key, count in skipped.most_common(5):
            lines.append(f"  {count:4d} {key}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    recent: deque[str] = deque(maxlen=args.recent)
    skipped: Counter[str] = Counter()
    started = time.monotonic()
    next_render = 0.0

    try:
        with SerialRs485Transport(SerialConfig(port=args.port, baudrate=args.baud)) as transport, JsonlBusLogger(args.log) as logger:
            runtime = AirTouchRuntime(
                transport,
                RuntimeConfig(
                    active=not args.passive,
                    detect_seconds=args.detect_seconds,
                    heartbeat_interval=args.heartbeat_interval,
                    source_address=parse_source_address(args.source_address),
                    auto_address=not args.passive,
                    force_source_address=args.force_source_address,
                    init_transactions=not args.passive,
                    protocol=args.protocol,
                ),
            )
            for event in runtime.start(now=started):
                append_runtime_event(
                    event=event,
                    recent=recent,
                    skipped=skipped,
                    logger=logger,
                    show_hex=args.show_hex,
                    show_skipped=args.show_skipped,
                )

            while True:
                if args.duration is not None and time.monotonic() - started >= args.duration:
                    print("\ndashboard duration ended")
                    return 0

                now = time.monotonic()
                for event in runtime.step(now=now):
                    append_runtime_event(
                        event=event,
                        recent=recent,
                        skipped=skipped,
                        logger=logger,
                        show_hex=args.show_hex,
                        show_skipped=args.show_skipped,
                    )

                if now >= next_render:
                    clear_screen()
                    print(render_dashboard(
                        state=runtime.state,
                        started=started,
                        rx_count=runtime.rx_count,
                        skipped=skipped,
                        recent=recent,
                        port=args.port,
                        mode="passive sniff" if args.passive else "fresh boot emulation",
                        transactions=runtime.transactions,
                    ), flush=True)
                    next_render = now + args.refresh

    except KeyboardInterrupt:
        print("\nexiting dashboard")
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
