# AirTouch 4 Touchpad Host

This project is the Python reimplementation of the AirTouch 4 touchscreen-side
RS485 protocol. The goal is to replace the original Android touchpad on the
main-board bus, then build a Home Assistant-facing app on top of the protocol
daemon.

## Scope

- Parse and build the internal AirTouch frame shell:
  `55 55 [dest src seq cmd len_hi len_lo payload crc_hi crc_low]`.
- Run live over USB-RS485 or a serial bridge.
- Treat every live session like a fresh touchpad boot.
- Maintain runtime state for ACs, groups, sensors, spill/storage, programs,
  favourites, and other main-board configuration exposed by the internal bus.
- Send user-setting commands that a modern UI would need.

Phase one aims for complete parser coverage of the internal main-board and
touchpad message surface. Mobile client, cloud/server, and update pathways are
reference-only and deliberately excluded from the live host contract.

## Boundaries

- Runtime behaviour should be derived from the AirTouch touchscreen APK and
  validated with main-board bus captures.
- No Zimi/cloud/client/server/update implementation belongs here.
- No RF temperature bridge runtime belongs here.
- TCP/mobile implementations are reference material only, not the source of
  truth for emulating the touchscreen.

## Layout

- `src/airtouch4/` - protocol package and state/session implementation.
- `src/airtouch4/runtime/` - long-running protocol daemon core used by live
  tools and future app/API surfaces.
- `scripts/` - live host, monitor, dashboard, and capture utilities.
- `tests/` - protocol and state model tests for this host.
- `examples/` - small captured examples used by tests or manual inspection.

## Runtime Boundary

`AirTouchRuntime` is the application boundary for phase two. It owns serial bus
ticks, fresh-boot address detection, heartbeat, init transactions, live state,
and runtime events. Terminal tools, the future HTTP/WebSocket server, and the
Home Assistant ingress UI should all consume this runtime rather than each
reimplementing the protocol loop.

## Service API

`airtouch_service.py` runs the runtime behind an HTTP/WebSocket API suitable for
the future Home Assistant ingress app.

```powershell
$env:PYTHONPATH = "src"
python .\scripts\airtouch_service.py --port COM3 --http-port 8099
```

Initial endpoints:

- `GET /api/health` - controller/runtime health and address assignment.
- `GET /api/state` - full runtime and AirTouch state snapshot.
- `GET /api/events` - recent runtime events.
- `POST /api/command` - queue an intent-level command transaction.
- `ws://.../ws` - WebSocket stream of recent runtime events.

Example command request:

```json
{
  "action": "group_power",
  "data": {
    "group": 0,
    "on": true
  }
}
```

## Development

Install the runtime dependency:

```powershell
python -m pip install -r requirements.txt
```

Run the tests from this directory:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

The test suite includes a capture regression over the sibling `research`
captures when that directory is present. It fails if any non-excluded internal
bus packet decodes as `unknown` or `decode_error`.

Run a live read-only session:

```powershell
$env:PYTHONPATH = "src"
python .\scripts\airtouch_host.py --port COM3 --duration 60
```

Run the terminal dashboard:

```powershell
$env:PYTHONPATH = "src"
python .\scripts\airtouch_dashboard.py --port COM3
```

Address discovery is automatic by default. With an original touchpad still
connected, the runtime asks for touchpad info and chooses a free slot before
starting heartbeat or init transactions. Use `--source-address 0x91` only as a
preference, and `--force-source-address` only for deliberate lab overrides.

## Home Assistant Add-on

This folder is also the installable Home Assistant add-on. The root repository
contains `repository.yaml`, and this folder contains the add-on `config.yaml`,
`Dockerfile`, `run.sh`, and `DOCS.md`.

The add-on defaults to:

- TCP serial transport at `192.168.30.56:6638`;
- serial device `/dev/ttyUSB0`;
- ingress on internal port `8099`;
- automatic touchpad address discovery;
- UART/serial device mapping enabled;
- persistent bus logging at `/data/logs/airtouch-bus.jsonl`.

Set `transport` to `local_serial` and configure `serial_port` when the RS485
adapter is attached directly to the Home Assistant host.
