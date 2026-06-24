# APK Activity Audit

Working tracker for replacing the AirTouch 4 touchscreen-side runtime with the
Python `touchpad-host` service. This is not public product documentation. Use it
as the implementation map when deciding what to port, what to ignore, and what
still needs live validation.

Overall status: **core APK reimplementation is not finished**. Some protocol
tracks are individually done, but phase-one completion means the Python host can
parse, represent, and send every touchscreen/main-board message needed by the
factory touchpad role, excluding mobile/client, cloud/server, update, and Zimi
paths.

## Status Key

- `done`: implemented in `touchpad-host` and covered by tests or live smoke.
- `partial`: implemented enough for current UI/runtime, but still has known gaps.
- `research`: decoded or inspected, not yet needed in runtime.
- `defer`: known APK path, intentionally outside the replacement-touchscreen goal.
- `todo`: should be implemented or audited next.

## Source Boundaries

- Runtime source of truth: APK internal touchscreen/mainboard code and live RS485
  captures.
- Reference only: TCP/mobile/client code, cloud/server paths, update pathways.
- Current product target: Home Assistant add-on that talks to the main board via
  local USB-RS485 or TCP serial bridge and presents a modern local UI.

## Core APK Areas

| APK area | Key files | Status | Runtime decision |
| --- | --- | --- | --- |
| Framing and unpacking | `protocol/manager/DataPacket.java`, `DataUnpacker.java` | done | Reimplemented in `airtouch4.packet` and session RX/TX framing. |
| Command ids and constants | `Util/Constants.java` | partial | Main runtime commands mapped in `payloads/registry.py`; keep auditing expanded/debug constants as needed. |
| Payload parsing | `protocol/manager/PackageParser.java` | partial | Current touchscreen/runtime command surface is mapped in `payloads/registry.py`; capture coverage tests assert no unknown/decode-error packets for retained internal-bus captures. Continue checking rare expanded/debug service pages as they are exercised live. |
| Payload builders | `protocol/manager/DataFormattor.java` | partial | Common commands plus parameters/preference/service page writers implemented in `commands.py`; AC base info (`0x74`), AC setting (`0x78`), program define (`0x3C`), and APK-style AC timer table (`0x36`) now have state-shaped builders and service command intents. Remaining work is wiring retained factory UI controls to these intents. |
| Touchpad connection/session | `protocol/manager/TouchPadConnection.java`, `TouchPadAddressMonitor.java`, `CommMainBoard.java` | partial | Runtime fresh-boot, heartbeat, auto address, transactions implemented; continue live stability tests. |
| Service orchestration | `protocol/manager/ServiceImpl.java`, `DataChangeListener.java` | partial | Python controller/service provides equivalent runtime loop; APK failure and retry behavior still worth auditing. |
| Runtime state containers | `protocol/data/*.java` | partial | Python state model now retains AC base/settings/timers, active favourite, program count/link flags, favourites, grouping, spill, service, sensors, LED, and diagnostics used by retained pages. Continue parity audit for advanced password/pay-lock/update-adjacent state as those service pages become active. |
| Temperature heartbeat | `Util/TempSensorTool.java` | done | Touchpad temperature config and HA sensor startup bridge implemented. |
| LED behavior | `Util/LEDTool.java` | research | Basic decoded LED response exists. Need decide whether UI/runtime should emulate any LED semantics beyond status. |
| Error display | `Util/ErrorCodeTable.java`, `Util/errortable/*.java`, `MainACInfoPage.java` | done | APK-derived local display-code tables added in `airtouch4.error_codes`; optional AirTouch update-server descriptions enrich errors through a persistent local cache when enabled. |
| Main control UI flow | `ui/mainpage/MainACInfoPage.java`, `GroupListPage.java`, `HomePageActivity.java` | partial | Current UI follows AC plus zones plus programs/service shape. Service/program pages now use structured APK-derived command intents for AC setup, program definitions, AC timer table, grouping, spill, balance, sensors, parameters, and service contact writes. Continue extracting exact page behavior. |
| Logging/reporting | `Util/StateTool.java`, `ReportTool.java`, `Log.java` | research | Useful for parity and diagnostics; not a runtime dependency unless needed for troubleshooting. |
| Local serial/native bridge | `NativeSerialPort.java`, `au/com/polyaire/tools/SerialPort.java`, native libs | done | Replaced by Python serial/TCP transports. No APK native porting needed. |
| Cloud/mobile/server | `AirTouchServerConnection.java`, `ServerData.java`, voice/state report classes | defer | Outside replacement touchscreen runtime except as passive reference for protocol shape. |
| Update paths | `UpdateMonitorService.java`, `AutoUpdateTool.java`, `GatewayUpdateTool.java`, `MainBoardUpdateTool.java` | defer | Not part of HA app runtime. Do not port. |
| Zimi/app install paths | `ZimiAppTool.java`, plugin update/install UI | defer | Not part of HA app runtime. Do not port. |

## Core APK Completion Criteria

Core APK work is only done when all of these are true:

- Every touchscreen/main-board runtime command observed in valid captures is
  parsed without `unknown` or `decode_error`.
- `PackageParser.java` has been audited against Python `payloads/*.py`, with
  each retained internal-bus parser either implemented, tested, or explicitly
  documented as out of runtime scope.
- `DataFormattor.java` has been audited against Python `commands.py` and
  `service/commands.py`, with each retained factory UI write action mapped to a
  structured Python builder.
- State-backed builders exist for AC base info (`0x74`), AC setting (`0x78`),
  program define (`0x3C`), and APK-style AC timer table (`0x36`), covered by
  round-trip tests.
- `protocol/data/*.java` state containers have a matching Python state field for
  every value used by the Control, Favourites/Programs, and Service UI flows.
- Touchpad boot/session behavior has been live-smoked after changes, including
  address coexistence, init sequence, heartbeat, retry/failure behavior, and
  command transaction handling.
- Service pages expose every user-facing factory touchpad configuration action
  that belongs to the replacement-touchscreen goal.
- UI labels and actions use Python-enriched APK-derived state, not loose generic
  packet labels, wherever the APK gives a real semantic name or behavior.

## Runtime Implementation Map

| Feature | Python files | Status | Notes |
| --- | --- | --- | --- |
| CRC/frame shell | `packet.py`, `session/touchscreen.py` | done | Handles standard and raw UART shell. |
| Auto touchpad address | `session/touchscreen.py`, `runtime/core.py` | partial | Coexistence logic exists; keep testing with original touchpad present. |
| Fresh boot init | `session/init.py`, `runtime/core.py` | partial | APK-style transaction boot sequence is in place. Need keep comparing against captures. |
| Transaction queue | `session/queue.py` | done | Tests cover timeout/success basics. |
| Group status/control | `payloads/internal_status.py`, `commands.py`, `service/commands.py` | partial | Core on/off/setpoint/damper path exists; verify all original UI modes. |
| AC status/control | `payloads/internal_status.py`, `commands.py` | partial | Basic power/mode/fan/setpoint exists. Error display now APK-derived. |
| Sensors | `payloads/config.py`, `state.py` | partial | Sensor list/info parsed; service table still needs UI/behavior parity. |
| Grouping/spill/balance | `payloads/config.py`, `commands.py`, service UI | partial | Decoders exist; grouping/spill/parameters builders exist; balance and factory UI flows need careful parity tests. |
| AC setup | `payloads/config.py`, `commands.py`, `service/commands.py`, service UI | partial | AC base info (`0x74`) and AC setting (`0x78`) builders round-trip through decoders and are wired to service-page controls. Needs live edit validation before calling this done. |
| Favourites/programs/timers | `payloads/ui_config.py`, `commands.py`, `service/commands.py`, service UI | partial | Program define (`0x3C`) and APK bulk AC timer (`0x36`) builders and command intents are wired to program/timer controls. Needs live edit validation before calling this done. |
| Service contact/password/system | `payloads/ui_config.py`, `commands.py`, service UI | partial | Contact/service flags, parameters and preference builders are in place. Password/system info UI flows still need build-out. |
| MQTT HA entities | `service/mqtt.py` | partial | Publishing exists; prior issue with Mosquitto path needs continued smoke testing. |
| Weather and indoor HA sensors | `service/ha_client.py`, `service/controller.py`, `service/ui.py` | partial | Config and display implemented locally; needs add-on review after publish. |
| Web UI layout | `service/ui.py`, `docs/UI_THEME_MODERNIZATION_RESEARCH.md` | partial | Three main pages established. Next visual direction is a soft HA-native technical dashboard, not a rewrite or factory-LCD clone. |
| Error resolution/cache | `error_codes.py`, `service/error_resolver.py`, `service/controller.py` | done | Runtime is local/APK first. Remote lookup is opt-in, non-blocking, and cached under add-on persistent storage. |
| Persistent bus logs | `service/controller.py`, `live_log.py` | done | Persistent logging off by default; app logger still records frames. |

## Immediate Next Work

1. Live-validate retained service-page edit actions against the real mainboard:
   AC base/settings, program define, AC timer table, grouping, spill, balance,
   pair sensor, preference, parameters, and service contact.
2. Continue `PackageParser.java` versus `payloads/*.py` audits when new rare
   expanded/debug/service-page frames appear in live runs.
3. Continue `protocol/data/*.java` versus `state.py` parity for advanced
   password/pay-lock/update-adjacent state only if those pages are retained.
4. Replace any remaining UI JSON/debug summaries with compact decoded fields
   when the APK gives a real semantic name.
5. Finish service page polish after live validation: sensors, grouping, spill,
   balance, AC setup, parameters, system info, diagnostics.
6. Re-run live TCP serial smoke against `192.168.30.56:6638` after each runtime
   protocol change.
7. Keep service page parity ahead of visual modernization: factory setup flows
   first, then softer UI styling.

## Latest Validation

- 2026-06-25: unit suite passed with 100 tests, Python source/script compile
  passed, and inline UI JavaScript syntax check passed.
- 2026-06-25: live TCP serial smoke against `192.168.30.56:6638` started the
  service, selected source `0x91`, reached `running` with boot complete, read
  AC count 1 and group count 8, and logged 114 RX/TX bus events including
  heartbeat/LED and group/sensor status frames.
8. Start UI modernization with token/surface refresh and app-bar/status-chip
   work before changing command layout. Preserve current data bindings.
9. Add subtle per-zone temperature trend support after the basic visual refresh:
   begin with a runtime ring buffer and tiny sparkline; defer HA recorder/history
   integration until MQTT/entity publishing is stable.

## Error Resolution Model

- Local APK tables are always the first result and cover display-code formatting
  for the known brand tables plus gateway special cases.
- Remote lookup is optional (`remote_error_resolution`) and defaults off.
- When enabled, unresolved AC errors are queued for the AirTouch update endpoint
  using configurable, blank-by-default `id` and `sn` values.
- Successful remote display/info responses are cached in `/data/error-cache.json`
  by the Home Assistant add-on and reused before another network lookup.
- Empty remote responses, including gateway `65534` and `65535`, do not replace
  local special-case text.

## UI Modernization Direction

- Reference: `docs/UI_THEME_MODERNIZATION_RESEARCH.md`.
- Keep the current architecture and inline UI while the protocol/runtime is still
  moving. Do not introduce React, Tailwind, HeroUI, or external frontend
  dependencies yet.
- Target style: HA-native soft technical dashboard. Keep factory touchpad flow
  where it matters, but do not visually clone the factory LCD.
- Implement in staged passes:
  1. Token and surface refresh: richer light/dark/system tokens, softer card
     surfaces, less border weight, better semantic status colors.
  2. Header/app bar: replace the heavy console header with a sticky surface app
     bar, compact connection/weather/indoor/fault chips, and icon-only theme
     toggle.
  3. Zone rows: keep density, add soft active/off treatment, state chips, clear
     icon-led controls, and touch-ready target sizes.
  4. Selected AC panel: make it feel like the primary thermostat controller with
     big room/setpoint values and grouped mode/fan/power controls.
  5. Service pages: apply the same token system, but keep them utilitarian and
     calmer than the daily Control surface.
- Use the Home Assistant Sections/Mushroom/Bubble/Open Dynamic Export research
  as references for rhythm, chips, cards, and restraint. Do not copy ODE's
  purple/dark palette as the dominant AirTouch theme.
- Keep UI dependencies minimal and dependency-free until the replacement
  touchpad protocol is stable and the final UI shape is clearer.

## Zone Temperature History

- Add a tiny per-zone temperature sparkline to the Control view once the token
  and zone-row refresh has landed.
- Purpose: show recent temperature drift without turning every zone into a chart
  card.
- Initial data source: in-process runtime ring buffer keyed by zone/group. This
  gives immediate live trend and avoids HA recorder dependency.
- Later option: bounded persistent add-on cache for continuity across restarts.
  HA history/recorder should wait until MQTT zone temperature entities are
  stable and clearly mapped.
- Visual rules:
  - Thin room-temperature line only by default.
  - Optional faint setpoint reference line.
  - No axes or labels inside the normal zone row.
  - Hide the sparkline when no sensor/history data exists.
  - On mobile, place the sparkline as a full-width quiet strip at the bottom of
    the zone card.
  - Keep color subtle; use stronger color only for meaningful warming/cooling or
    comfort-band deviation.

## Evidence Paths

- APK notes: `research/apk/APK_NOTES.md`
- Decompiled APK Java: `research/apk-decompile-full/jadx/sources/com/auto/aircondition/base`
- APK resources/smali: `research/apk/apktool`
- Protocol findings: `research/docs/AIRTOUCH_PROTOCOL_FINDINGS.md`
- Capture decoder notes: `research/docs/CAPTURE_DECODER.md`
- Runtime add-on: `touchpad-host`
- UI modernization research: `touchpad-host/docs/UI_THEME_MODERNIZATION_RESEARCH.md`
- Local runtime logs: `touchpad-host/logs`

## Validation Tripwires

Run after protocol/runtime changes:

```powershell
$env:PYTHONPATH='touchpad-host/src;touchpad-host'
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest discover -s touchpad-host/tests
$env:PYTHONPYCACHEPREFIX="$env:TEMP\airtouch-pycache"
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m compileall -q touchpad-host/src touchpad-host/scripts
```

Run after UI changes:

```powershell
$env:PYTHONPATH='touchpad-host/src'
@'
from pathlib import Path
from airtouch4.service.ui import INDEX_HTML
out = Path(r'C:\Users\espar\AppData\Local\Temp') / 'airtouch-ui-check.js'
start = INDEX_HTML.index('<script>') + len('<script>')
end = INDEX_HTML.index('</script>', start)
out.write_text(INDEX_HTML[start:end], encoding='utf-8')
print(out)
'@ | & "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" --check C:\Users\espar\AppData\Local\Temp\airtouch-ui-check.js
```
