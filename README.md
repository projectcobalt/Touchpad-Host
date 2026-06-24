# AirTouch Decoding Workspace

This workspace is split into three deliberately separate project areas.

## `touchpad-host/`

Python implementation of the AirTouch 4 internal RS485 touchpad protocol. This
is the replacement-touchscreen path: it should speak to the main board through a
USB-RS485 bridge, maintain a fresh-boot runtime model, and eventually expose the
state and controls needed by a Home Assistant app.

This folder is also an installable Home Assistant add-on. Add this repository
to the Home Assistant add-on store, install **AirTouch 4 Touchpad Host**, review
the transport options, then start it. The current defaults target the lab TCP
serial bridge at `192.168.30.56:6638`; switch `transport` to `local_serial` and
set `serial_port` when the USB-RS485 bridge is attached directly to Home
Assistant.

This area is APK-first. The local TCP/mobile libraries are useful references,
but the runtime behaviour here should be derived from the touchscreen APK and
validated against internal bus captures.

## `temperature-bridge/`

ESPHome RF temperature bridge and RF module emulator packaging. This is the
public/product-style bridge work and remains separate from the touchpad host.

The bridge and touchpad host may share protocol knowledge, but they are not the
same runtime and should not be forced into one implementation.

## `research/`

Private protocol research: captures, decoded outputs, APK decompile artifacts,
reference repos, protocol notes, and offline analysis tools.

Keep capture archaeology and one-off decoder experiments here. Promote only the
clean, runtime-relevant pieces into `touchpad-host/` or `temperature-bridge/`
when they are stable.
