# AirTouch 4 Touchpad Host

This add-on runs the Python AirTouch 4 internal RS485 touchpad host. It is an
experimental replacement for the original touchpad-side protocol process and
talks to the main board through a USB-RS485 bridge or a serial-over-TCP bridge.

## Required Hardware

- AirTouch 4 main board.
- USB-RS485 bridge connected to the touchpad bus, either attached directly to
  Home Assistant or exposed through a TCP serial bridge.
- Home Assistant OS or Supervised install with the serial device visible to the
  Supervisor.

## Installation

Add this repository to the Home Assistant add-on store, install **AirTouch 4
Touchpad Host**, configure the transport, then start the add-on. The default
configuration uses the current lab TCP serial bridge at `192.168.30.56:6638`.
Change `transport` to `local_serial` and set `serial_port` to the HA device path
when the USB-RS485 adapter is plugged directly into the Home Assistant host.

## Configuration

- `transport`: `local_serial` for a USB-RS485 bridge attached to Home
  Assistant, or `tcp_serial` for a serial-over-TCP bridge.
- `serial_port`: USB-RS485 device, usually `/dev/ttyUSB0` or `/dev/ttyACM0`.
- `baudrate`: AirTouch bus speed. The current decoded system uses `115200`.
- `tcp_host`: serial-over-TCP bridge host when `transport` is `tcp_serial`.
- `tcp_port`: serial-over-TCP bridge port when `transport` is `tcp_serial`.
- `reconnect_interval`: delay before retrying a failed serial or TCP
  connection. The web UI remains available while the runtime reconnects.
- `source_address`: `auto` is recommended. The host asks for existing touchpad
  presence and chooses the free touchpad address before initialising.
- `force_source_address`: lab override only. Leave this off when an original
  touchpad might still be connected.
- `detect_seconds`: address-discovery listening window before the fresh boot
  init sequence.
- `heartbeat_interval`: touchpad heartbeat interval in seconds.
- `heartbeat_payload`: raw heartbeat payload. The default matches the decoded
  touchpad temperature heartbeat.
- `bus_log`: write raw runtime bus traffic to `/data/logs/airtouch-bus.jsonl`.

## Web UI and API

Ingress opens the current API surface. The first UI is intentionally sparse
until the protocol runtime is stable.

- `/api/health`
- `/api/state`
- `/api/events`
- `/api/command`
- `/ws`
