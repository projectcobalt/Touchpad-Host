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
PROTOCOL="$(config protocol auto)"
SOURCE_ADDRESS="$(config source_address auto)"
FORCE_SOURCE_ADDRESS="$(config force_source_address false)"
DETECT_SECONDS="$(config detect_seconds 3.0)"
HEARTBEAT_INTERVAL="$(config heartbeat_interval 30.0)"
TOUCHPAD_TEMPERATURE_SENSOR="$(config touchpad_temperature_sensor "")"
TOUCHPAD_TEMPERATURE="$(config touchpad_temperature 25.0)"
HEARTBEAT_PAYLOAD="$(config heartbeat_payload "")"
BUS_LOG="$(config bus_log true)"
UI_THEME="$(config ui_theme system)"
WEATHER_ENTITY="$(config weather_entity "")"
FORECAST_WEATHER_ENTITY="$(config forecast_weather_entity "")"
INDOOR_TEMPERATURE_ENTITY="$(config indoor_temperature_entity "")"
INDOOR_HUMIDITY_ENTITY="$(config indoor_humidity_entity "")"
SOLAR_IRRADIANCE_ENTITY="$(config solar_irradiance_entity "")"
CLOUD_COVER_ENTITY="$(config cloud_cover_entity "")"
WEATHER_POLL_INTERVAL="$(config weather_poll_interval 60.0)"
MQTT_ENABLED="$(config mqtt_enabled false)"
MQTT_HOST="$(config mqtt_host "")"
MQTT_PORT="$(config mqtt_port 1883)"
MQTT_USERNAME="$(config mqtt_username "")"
MQTT_PASSWORD="$(config mqtt_password "")"
MQTT_DISCOVERY="$(config mqtt_discovery true)"
MQTT_DISCOVERY_PREFIX="$(config mqtt_discovery_prefix homeassistant)"
MQTT_TOPIC_PREFIX="$(config mqtt_topic_prefix airtouch4)"
MQTT_PUBLISH_INTERVAL="$(config mqtt_publish_interval 10.0)"
REMOTE_ERROR_RESOLUTION="$(config remote_error_resolution false)"
REMOTE_ERROR_CACHE_DAYS="$(config remote_error_cache_days 2.0)"
REMOTE_ERROR_DEVICE_ID="$(config remote_error_device_id "")"
REMOTE_ERROR_SERIAL="$(config remote_error_serial "")"
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

case "${PROTOCOL}" in
    auto|at4|at5)
        ;;
    *)
        echo "Invalid protocol: ${PROTOCOL}" >&2
        exit 2
        ;;
esac

export PYTHONPATH=/opt/airtouch4/src

RESOLVED_HEARTBEAT_PAYLOAD="$(
    /opt/airtouch4/venv/bin/python /opt/airtouch4/scripts/resolve_touchpad_temperature.py \
        --sensor "${TOUCHPAD_TEMPERATURE_SENSOR}" \
        --fallback "${TOUCHPAD_TEMPERATURE}" \
        --raw-payload "${HEARTBEAT_PAYLOAD}"
)"

ARGS=(
    "--transport" "${TRANSPORT}"
    "--port" "${SERIAL_PORT}"
    "--baud" "${BAUDRATE}"
    "--tcp-host" "${TCP_HOST}"
    "--tcp-port" "${TCP_PORT}"
    "--reconnect-interval" "${RECONNECT_INTERVAL}"
    "--protocol" "${PROTOCOL}"
    "--host" "0.0.0.0"
    "--http-port" "8099"
    "--source-address" "${SOURCE_ADDRESS}"
    "--detect-seconds" "${DETECT_SECONDS}"
    "--heartbeat-interval" "${HEARTBEAT_INTERVAL}"
    "--touchpad-temperature" "${TOUCHPAD_TEMPERATURE}"
    "--heartbeat-payload" "${RESOLVED_HEARTBEAT_PAYLOAD}"
    "--ui-theme" "${UI_THEME}"
    "--weather-entity" "${WEATHER_ENTITY}"
    "--forecast-weather-entity" "${FORECAST_WEATHER_ENTITY}"
    "--indoor-temperature-entity" "${INDOOR_TEMPERATURE_ENTITY}"
    "--indoor-humidity-entity" "${INDOOR_HUMIDITY_ENTITY}"
    "--solar-irradiance-entity" "${SOLAR_IRRADIANCE_ENTITY}"
    "--cloud-cover-entity" "${CLOUD_COVER_ENTITY}"
    "--weather-poll-interval" "${WEATHER_POLL_INTERVAL}"
    "--adaptive-config-path" "/data/adaptive_config.json"
    "--adaptive-learning-path" "/data/adaptive_learning.json"
    "--mqtt-host" "${MQTT_HOST}"
    "--mqtt-port" "${MQTT_PORT}"
    "--mqtt-username" "${MQTT_USERNAME}"
    "--mqtt-password" "${MQTT_PASSWORD}"
    "--mqtt-discovery-prefix" "${MQTT_DISCOVERY_PREFIX}"
    "--mqtt-topic-prefix" "${MQTT_TOPIC_PREFIX}"
    "--mqtt-publish-interval" "${MQTT_PUBLISH_INTERVAL}"
    "--remote-error-cache" "/data/error-cache.json"
    "--remote-error-cache-days" "${REMOTE_ERROR_CACHE_DAYS}"
    "--remote-error-device-id" "${REMOTE_ERROR_DEVICE_ID}"
    "--remote-error-serial" "${REMOTE_ERROR_SERIAL}"
    "--log-level" "${LOG_LEVEL}"
)

if [[ "${FORCE_SOURCE_ADDRESS}" == "true" ]]; then
    ARGS+=("--force-source-address")
fi

if [[ "${BUS_LOG}" == "true" ]]; then
    mkdir -p /data/logs
    ARGS+=("--bus-log" "/data/logs/airtouch-bus.jsonl")
fi

if [[ "${MQTT_ENABLED}" == "true" ]]; then
    ARGS+=("--mqtt-enabled")
fi

if [[ "${MQTT_DISCOVERY}" != "true" ]]; then
    ARGS+=("--no-mqtt-discovery")
fi

if [[ "${REMOTE_ERROR_RESOLUTION}" == "true" ]]; then
    ARGS+=("--remote-error-resolution")
fi

echo "Starting OpenAirtouch with ${TRANSPORT} (${PROTOCOL})"
exec /opt/airtouch4/venv/bin/python /opt/airtouch4/scripts/airtouch_service.py "${ARGS[@]}"
