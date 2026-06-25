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
from airtouch4.service.adaptive import AdaptiveConfig
from airtouch4.service.api import create_app
from airtouch4.service.controller import RuntimeController, RuntimeControllerConfig
from airtouch4.service.error_resolver import RemoteErrorResolverConfig
from airtouch4.service.ha_client import HomeAssistantApiConfig
from airtouch4.service.mqtt import MqttConfig
from airtouch4.session.touchscreen import parse_hex_payload
from airtouch4.payloads.common import encode_internal_temperature


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", default="local_serial", choices=("local_serial", "tcp_serial"))
    parser.add_argument("--port", help="Serial port for the USB-RS485 bridge, for example COM3 or /dev/ttyUSB0.")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--tcp-host", default="127.0.0.1", help="TCP serial bridge host when --transport tcp_serial is used.")
    parser.add_argument("--tcp-port", type=int, default=6638, help="TCP serial bridge port when --transport tcp_serial is used.")
    parser.add_argument("--reconnect-interval", type=float, default=5.0, help="Seconds to wait before reconnecting after transport errors.")
    parser.add_argument("--protocol", default="auto", choices=("auto", "at4", "at5"), help="AirTouch protocol profile. AT4 is implemented; AT5 is detected but not yet live-control capable.")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP bind host. Default: 0.0.0.0.")
    parser.add_argument("--http-port", type=int, default=8099, help="HTTP bind port. Default matches HA ingress convention.")
    parser.add_argument("--bus-log", type=Path, help="Optional raw RX/TX/init JSONL log.")
    parser.add_argument("--detect-seconds", type=float, default=3.0)
    parser.add_argument("--heartbeat-interval", type=float, default=30.0)
    parser.add_argument("--touchpad-temperature", type=float, default=25.0)
    parser.add_argument("--heartbeat-payload", default="")
    parser.add_argument("--source-address", default="auto", help="Preferred touchpad source address: auto, 0x90, or 0x91.")
    parser.add_argument("--force-source-address", action="store_true")
    parser.add_argument("--ui-theme", default="system", choices=("system", "light", "dark"))
    parser.add_argument("--weather-entity", default="")
    parser.add_argument("--forecast-weather-entity", default="")
    parser.add_argument("--indoor-temperature-entity", default="")
    parser.add_argument("--indoor-humidity-entity", default="")
    parser.add_argument("--solar-irradiance-entity", default="")
    parser.add_argument("--cloud-cover-entity", default="")
    parser.add_argument("--weather-poll-interval", type=float, default=60.0)
    parser.add_argument("--adaptive-mode", default="off", choices=("off", "recommend", "auto_off", "adaptive"))
    parser.add_argument("--adaptive-cool-diff", type=int, default=4)
    parser.add_argument("--adaptive-cool-comfort-temp", type=int, default=24)
    parser.add_argument("--adaptive-heat-diff", type=int, default=4)
    parser.add_argument("--adaptive-heat-comfort-temp", type=int, default=20)
    parser.add_argument("--adaptive-check-interval", type=float, default=60.0)
    parser.add_argument("--adaptive-command-cooldown", type=float, default=300.0)
    parser.add_argument("--adaptive-learning-mode", default="off", choices=("off", "control"))
    parser.add_argument("--adaptive-mpc-horizon-hours", type=int, default=6)
    parser.add_argument("--adaptive-compressor-min-run-time", type=float, default=0.0)
    parser.add_argument("--adaptive-compressor-min-off-time", type=float, default=0.0)
    parser.add_argument("--adaptive-compressor-groups", default="")
    parser.add_argument("--adaptive-config-path", type=Path, default=Path("/data/adaptive_config.json"))
    parser.add_argument("--adaptive-learning-path", type=Path, default=Path("/data/adaptive_learning.json"))
    parser.add_argument("--mqtt-enabled", action="store_true")
    parser.add_argument("--mqtt-host", default="", help="MQTT broker host. Blank defaults to the HA Mosquitto add-on host core-mosquitto.")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--mqtt-username", default="")
    parser.add_argument("--mqtt-password", default="")
    parser.add_argument("--mqtt-discovery", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--mqtt-discovery-prefix", default="homeassistant")
    parser.add_argument("--mqtt-topic-prefix", default="airtouch4")
    parser.add_argument("--mqtt-publish-interval", type=float, default=10.0)
    parser.add_argument("--remote-error-resolution", action="store_true")
    parser.add_argument("--remote-error-cache", type=Path)
    parser.add_argument("--remote-error-cache-days", type=float, default=2.0)
    parser.add_argument("--remote-error-device-id", default="")
    parser.add_argument("--remote-error-serial", default="")
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

    heartbeat_payload = (
        parse_hex_payload(args.heartbeat_payload)
        if args.heartbeat_payload.strip()
        else bytes((0x00, encode_internal_temperature(args.touchpad_temperature), 0x00))
    )

    runtime_config = RuntimeConfig(
        active=True,
        detect_seconds=args.detect_seconds,
        heartbeat_interval=args.heartbeat_interval,
        heartbeat_payload=heartbeat_payload,
        source_address=parse_source_address(args.source_address),
        auto_address=True,
        force_source_address=args.force_source_address,
        init_transactions=True,
        protocol=args.protocol,
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
            ui_theme=args.ui_theme,
            weather=HomeAssistantApiConfig(
                weather_entity=args.weather_entity,
                forecast_weather_entity=args.forecast_weather_entity,
                indoor_temperature_entity=args.indoor_temperature_entity,
                indoor_humidity_entity=args.indoor_humidity_entity,
                solar_irradiance_entity=args.solar_irradiance_entity,
                cloud_cover_entity=args.cloud_cover_entity,
            ),
            weather_poll_interval=args.weather_poll_interval,
            adaptive=AdaptiveConfig(
                mode=args.adaptive_mode,
                cool_diff=args.adaptive_cool_diff,
                cool_comfort_temp=args.adaptive_cool_comfort_temp,
                heat_diff=args.adaptive_heat_diff,
                heat_comfort_temp=args.adaptive_heat_comfort_temp,
                check_interval=args.adaptive_check_interval,
                command_cooldown=args.adaptive_command_cooldown,
                learning_mode=args.adaptive_learning_mode,
                mpc_horizon_hours=args.adaptive_mpc_horizon_hours,
                compressor_min_run_time=args.adaptive_compressor_min_run_time,
                compressor_min_off_time=args.adaptive_compressor_min_off_time,
                compressor_groups=args.adaptive_compressor_groups,
            ),
            adaptive_config_path=args.adaptive_config_path,
            adaptive_learning_path=args.adaptive_learning_path,
            mqtt=MqttConfig(
                enabled=args.mqtt_enabled,
                host=args.mqtt_host,
                port=args.mqtt_port,
                username=args.mqtt_username,
                password=args.mqtt_password,
                discovery=args.mqtt_discovery,
                discovery_prefix=args.mqtt_discovery_prefix,
                topic_prefix=args.mqtt_topic_prefix,
                publish_interval=args.mqtt_publish_interval,
            ),
            error_resolver=RemoteErrorResolverConfig(
                enabled=args.remote_error_resolution,
                cache_path=args.remote_error_cache,
                cache_ttl_seconds=max(1.0, args.remote_error_cache_days) * 86400.0,
                device_id=args.remote_error_device_id,
                serial_number=args.remote_error_serial,
            ),
        )
    )
    uvicorn.run(create_app(controller), host=args.host, port=args.http_port, log_level=args.log_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
