# Changelog

## 0.1.6

- Remove explicit root `ingress_entry`; the Supervisor default is already `/`
  and the explicit slash was producing doubled ingress URLs.
- Remove double-slash API route aliases now that the ingress root cause is fixed.

## 0.1.5

- Route bus frame log lines through Uvicorn's configured logger so they appear
  in Home Assistant add-on logs.

## 0.1.4

- Fix UI API polling under Home Assistant ingress double-slash URLs.
- Add double-slash API route aliases as a defensive fallback.
- Log RX/TX bus frames to the add-on logger.
- Default persistent JSONL bus logging to off.

## 0.1.3

- Serve the ingress UI on both `/` and `//` to tolerate Home Assistant ingress
  double-slash entry URLs.

## 0.1.2

- Rework the ingress UI around group/zone tiles as the primary surface.
- Show decoded group power, room temperature, setpoint, damper percentage,
  spill, and sensor mapping state.
- Keep AC, sensors, runtime, and activity visible as supporting panels.

## 0.1.1

- Relax add-on option schema so TCP serial installs can save an empty local
  serial port field.
- Keep mode-aware transport validation in the startup script.

## 0.1.0

- Initial experimental Home Assistant add-on package.
- AirTouch 4 internal RS485 protocol runtime.
- Local USB-RS485 and serial-over-TCP transport options.
- Automatic touchpad address discovery.
- Ingress UI with runtime, AC, group, sensor, and event status.
- Persistent bus logging option.
