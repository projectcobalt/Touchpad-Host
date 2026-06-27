# Changelog

## 0.3.1 - 2026-06-28

- Expose explicit sensor-to-zone mapping fields in `/api/state` sensor rows so Home Assistant integrations can attach RF sensors to the correct zone without address heuristics.

## 0.2.8 - 2026-06-27

- Add time-aware adaptive forecast ingestion for Home Assistant-style timestamped forecasts, including sorted UTC alignment, 5-minute control grids, and quality metadata.
- Separate MPC input parameters into a structured input object so forecast, solar, humidity, and quality metadata can evolve without expanding the solver call signature.
- Expose adaptive runtime forecast diagnostics, including expected AC runtime over the MPC horizon, per-zone runtime, action windows, forecast series points, and solver timing metrics.
