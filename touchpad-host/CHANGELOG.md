# Changelog

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
