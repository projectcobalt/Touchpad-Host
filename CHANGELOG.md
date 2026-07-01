# Changelog

## 0.6.1 - 2026-07-02

- Keep saved spill-zone configuration separate from live spill-open status in the service UI and clear stale spill configuration flags when new spill data arrives.

## 0.6.0 - 2026-07-01

- Replace deprecated FastAPI startup/shutdown event hooks with an application lifespan handler.
- Split adaptive control into focused signal, intent, restore, and strategy layers while preserving the existing control behavior and test coverage.

## 0.5.0 - 2026-07-01

- Feed adaptive room power-fraction estimates into the thermal prediction and EKF learning path instead of using full-power active observations for every zone.

## 0.4.0 - 2026-06-28

- Fix Home Assistant forecast ingestion to treat naive forecast timestamps as HA-local time, preserve the HA timezone on forecast snapshots, and use the current outside temperature as a live interpolation anchor.
- Drop the bridge-prepended current-weather row from forecast samples when real timestamped forecast entries are present, avoiding duplicate/current-hour forecast distortion in MPC control inputs.

## 0.3.3 - 2026-06-28

- Refresh listed sensor-info records after startup and keep resolved RF sensor rows populated with zone temperature while RF battery/signal telemetry is warming up.

## 0.3.2 - 2026-06-28

- Resolve group-local RF sensor slots to concrete sensor addresses in `/api/state`, exposing one-to-one sensor owner fields and zone-side `sensor_id` metadata for Home Assistant device placement.

## 0.3.1 - 2026-06-28

- Expose explicit sensor-to-zone mapping fields in `/api/state` sensor rows so Home Assistant integrations can attach RF sensors to the correct zone without address heuristics.

## 0.2.8 - 2026-06-27

- Add time-aware adaptive forecast ingestion for Home Assistant-style timestamped forecasts, including sorted UTC alignment, 5-minute control grids, and quality metadata.
- Separate MPC input parameters into a structured input object so forecast, solar, humidity, and quality metadata can evolve without expanding the solver call signature.
- Expose adaptive runtime forecast diagnostics, including expected AC runtime over the MPC horizon, per-zone runtime, action windows, forecast series points, and solver timing metrics.
