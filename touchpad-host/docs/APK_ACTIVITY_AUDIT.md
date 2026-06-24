# APK Activity Audit

Working tracker for replacing the AirTouch 4 touchscreen-side runtime with the
Python `touchpad-host` service. This is not public product documentation. Use it
as the implementation map when deciding what to port, what to ignore, and what
still needs live validation.

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
| Payload parsing | `protocol/manager/PackageParser.java` | partial | Most touchscreen/runtime payloads decoded. Continue checking rare expanded commands and UI service pages. |
| Payload builders | `protocol/manager/DataFormattor.java` | partial | Common commands plus parameters/preference/service page writers implemented in `commands.py`; AC setting and program writers still need state-backed parity checks. |
| Touchpad connection/session | `protocol/manager/TouchPadConnection.java`, `TouchPadAddressMonitor.java`, `CommMainBoard.java` | partial | Runtime fresh-boot, heartbeat, auto address, transactions implemented; continue live stability tests. |
| Service orchestration | `protocol/manager/ServiceImpl.java`, `DataChangeListener.java` | partial | Python controller/service provides equivalent runtime loop; APK failure and retry behavior still worth auditing. |
| Runtime state containers | `protocol/data/*.java` | partial | Python state model exists. Need continued parity audit for every field used by service UI pages. |
| Temperature heartbeat | `Util/TempSensorTool.java` | done | Touchpad temperature config and HA sensor startup bridge implemented. |
| LED behavior | `Util/LEDTool.java` | research | Basic decoded LED response exists. Need decide whether UI/runtime should emulate any LED semantics beyond status. |
| Error display | `Util/ErrorCodeTable.java`, `Util/errortable/*.java`, `MainACInfoPage.java` | done | APK-derived local display-code tables added in `airtouch4.error_codes`; optional AirTouch update-server descriptions enrich errors through a persistent local cache when enabled. |
| Main control UI flow | `ui/mainpage/MainACInfoPage.java`, `GroupListPage.java`, `HomePageActivity.java` | partial | Current UI follows AC plus zones plus programs/service shape. Continue extracting exact page behavior. |
| Logging/reporting | `Util/StateTool.java`, `ReportTool.java`, `Log.java` | research | Useful for parity and diagnostics; not a runtime dependency unless needed for troubleshooting. |
| Local serial/native bridge | `NativeSerialPort.java`, `au/com/polyaire/tools/SerialPort.java`, native libs | done | Replaced by Python serial/TCP transports. No APK native porting needed. |
| Cloud/mobile/server | `AirTouchServerConnection.java`, `ServerData.java`, voice/state report classes | defer | Outside replacement touchscreen runtime except as passive reference for protocol shape. |
| Update paths | `UpdateMonitorService.java`, `AutoUpdateTool.java`, `GatewayUpdateTool.java`, `MainBoardUpdateTool.java` | defer | Not part of HA app runtime. Do not port. |
| Zimi/app install paths | `ZimiAppTool.java`, plugin update/install UI | defer | Not part of HA app runtime. Do not port. |

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
| Favourites/programs/timers | `payloads/ui_config.py`, service UI | partial | Read views exist; full edit workflows still need porting and live tests. |
| Service contact/password/system | `payloads/ui_config.py`, `commands.py`, service UI | partial | Contact/service flags, parameters and preference builders are in place. Password/system info UI flows still need build-out. |
| MQTT HA entities | `service/mqtt.py` | partial | Publishing exists; prior issue with Mosquitto path needs continued smoke testing. |
| Weather and indoor HA sensors | `service/ha_client.py`, `service/controller.py`, `service/ui.py` | partial | Config and display implemented locally; needs add-on review after publish. |
| Web UI layout | `service/ui.py` | partial | Three main pages established. Continue service subpage functionality. |
| Error resolution/cache | `error_codes.py`, `service/error_resolver.py`, `service/controller.py` | done | Runtime is local/APK first. Remote lookup is opt-in, non-blocking, and cached under add-on persistent storage. |
| Persistent bus logs | `service/controller.py`, `live_log.py` | done | Persistent logging off by default; app logger still records frames. |

## Immediate Next Work

1. Replace remaining UI-side generic protocol labels with Python-enriched
   APK-derived state where practical.
2. Continue APK audit of state-backed `DataFormattor.java` builders:
   AC base info (`0x74`), AC setting (`0x78`), program define (`0x3C`), and
   timer bulk (`0x36`) should be implemented from Python runtime state rather
   than hand-packed raw payloads.
3. Audit `PackageParser.java` against `payloads/*.py` and update
   `test_protocol_coverage.py` for any known runtime command still missing.
4. Continue service page build-out: sensors, grouping, spill, balance, AC setup,
   parameters, system info, diagnostics.
5. Re-run live TCP serial smoke against `192.168.30.56:6638` after each runtime
   protocol change.
6. Continue service page parity work, prioritising write actions that map to
   original factory touchpad setup screens.

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

## Evidence Paths

- APK notes: `research/apk/APK_NOTES.md`
- Decompiled APK Java: `research/apk-decompile-full/jadx/sources/com/auto/aircondition/base`
- APK resources/smali: `research/apk/apktool`
- Protocol findings: `research/docs/AIRTOUCH_PROTOCOL_FINDINGS.md`
- Capture decoder notes: `research/docs/CAPTURE_DECODER.md`
- Runtime add-on: `touchpad-host`
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
