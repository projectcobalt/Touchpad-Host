#!/usr/bin/with-contenv bash
set -euo pipefail

CONFIG_PATH=/data/options.json

config() {
    python3 - "${CONFIG_PATH}" "$1" "$2" <<'PY'
import json
import sys

path, key, default = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
except FileNotFoundError:
    data = {}
value = data.get(key, default)
if isinstance(value, bool):
    print("true" if value else "false")
else:
    print(value)
PY
}

TRANSPORT="$(config transport local_serial)"
SERIAL_PORT="$(config serial_port /dev/ttyUSB0)"
BAUDRATE="$(config baudrate 115200)"
TCP_HOST="$(config tcp_host 127.0.0.1)"
TCP_PORT="$(config tcp_port 6638)"
RECONNECT_INTERVAL="$(config reconnect_interval 5.0)"
SOURCE_ADDRESS="$(config source_address auto)"
FORCE_SOURCE_ADDRESS="$(config force_source_address false)"
DETECT_SECONDS="$(config detect_seconds 3.0)"
HEARTBEAT_INTERVAL="$(config heartbeat_interval 30.0)"
HEARTBEAT_PAYLOAD="$(config heartbeat_payload "00 EA 00")"
BUS_LOG="$(config bus_log true)"
LOG_LEVEL="$(config log_level info)"

case "${TRANSPORT}" in
    local_serial|tcp_serial)
        ;;
    *)
        echo "Invalid transport: ${TRANSPORT}" >&2
        exit 2
        ;;
esac

if [[ "${TRANSPORT}" == "local_serial" && -z "${SERIAL_PORT}" ]]; then
    echo "serial_port is required when transport is local_serial" >&2
    exit 2
fi

if [[ "${TRANSPORT}" == "tcp_serial" && ( -z "${TCP_HOST}" || -z "${TCP_PORT}" ) ]]; then
    echo "tcp_host and tcp_port are required when transport is tcp_serial" >&2
    exit 2
fi

ARGS=(
    "--transport" "${TRANSPORT}"
    "--port" "${SERIAL_PORT}"
    "--baud" "${BAUDRATE}"
    "--tcp-host" "${TCP_HOST}"
    "--tcp-port" "${TCP_PORT}"
    "--reconnect-interval" "${RECONNECT_INTERVAL}"
    "--host" "0.0.0.0"
    "--http-port" "8099"
    "--source-address" "${SOURCE_ADDRESS}"
    "--detect-seconds" "${DETECT_SECONDS}"
    "--heartbeat-interval" "${HEARTBEAT_INTERVAL}"
    "--heartbeat-payload" "${HEARTBEAT_PAYLOAD}"
    "--log-level" "${LOG_LEVEL}"
)

if [[ "${FORCE_SOURCE_ADDRESS}" == "true" ]]; then
    ARGS+=("--force-source-address")
fi

if [[ "${BUS_LOG}" == "true" ]]; then
    mkdir -p /data/logs
    ARGS+=("--bus-log" "/data/logs/airtouch-bus.jsonl")
fi

export PYTHONPATH=/opt/airtouch4/src

echo "Starting AirTouch 4 touchpad host with ${TRANSPORT}"
exec /opt/airtouch4/venv/bin/python /opt/airtouch4/scripts/airtouch_service.py "${ARGS[@]}"
