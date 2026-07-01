"""User-facing adaptive intent/status helpers."""

from __future__ import annotations

from typing import Any


def _proposal_status(proposal: Any) -> dict[str, Any] | None:
    if proposal is None:
        return None
    return {
        "target": proposal.target,
        "source": proposal.source,
        "confidence": proposal.confidence,
        "predicted_temperatures": proposal.predicted_temperatures,
        "reason": proposal.reason,
        "action": proposal.action,
        "power_fraction": proposal.power_fraction,
        "zone_power_fractions": {str(group_id): fraction for group_id, fraction in getattr(proposal, "zone_power_fractions", {}).items()},
        "projected_runtime_hours": getattr(proposal, "projected_runtime_hours", 0.0),
        "zone_projected_runtime_hours": {
            str(group_id): hours
            for group_id, hours in getattr(proposal, "zone_projected_runtime_hours", {}).items()
        },
        "runtime_forecast": _runtime_forecast_status(getattr(proposal, "runtime_forecast", None)),
    }


def _mode_intent_status(intent: AcModeIntent) -> dict[str, Any]:
    return {
        "mode": intent.mode,
        "name": intent.name,
        "reason": intent.reason,
        "source": intent.source,
        "current_mode": intent.current_mode,
        "current_mode_name": _mode_name(intent.current_mode),
        "change_required": intent.mode is not None and intent.mode != intent.current_mode,
        "outside_air_intent": intent.outside_air_intent,
        "ventilation_reason": intent.ventilation_reason,
    }


def _intent_status(evaluation: dict[str, Any], status: dict[str, Any]) -> dict[str, Any]:
    mode = str(status.get("mode") or "off")
    config = status.get("config") or {}
    strategy = str(config.get("control_strategy") or "weather")
    name = str(evaluation.get("name") or f"AC {int(evaluation.get('ac') or 0) + 1}")
    authority = "off" if mode == "off" else ("insight" if mode == "recommend" else "control")
    commands = [action for action in status.get("actions", []) if isinstance(action, str) and action.startswith(f"{name}:")]
    target = evaluation.get("target")
    mpc = evaluation.get("mpc") or {}
    runtime = (mpc.get("runtime_forecast") or {}) if isinstance(mpc, dict) else {}
    runtime_hours = runtime.get("runtime_hours")
    confidence = mpc.get("confidence") if isinstance(mpc, dict) else None
    affected_zones = sorted(_zone_labels((mpc.get("zone_power_fractions") or {}).keys())) if isinstance(mpc, dict) else []
    mode_intent = evaluation.get("mode_intent") if isinstance(evaluation.get("mode_intent"), dict) else {}
    air_quality = evaluation.get("air_quality") if isinstance(evaluation.get("air_quality"), dict) else {}
    base = {
        "ac": evaluation.get("ac"),
        "name": name,
        "mode": mode,
        "strategy": strategy,
        "authority": authority,
        "intent": "monitor",
        "headline": "Monitoring",
        "summary": "No Adaptive Change Is Planned.",
        "reason": None,
        "confidence": confidence,
        "recommended_target": target,
        "runtime_hours": runtime_hours,
        "affected_zones": affected_zones,
        "mode_intent": mode_intent,
        "air_quality": air_quality,
        "intended_ac_mode": mode_intent.get("name"),
        "commands": commands,
    }
    opportunity = evaluation.get("weather_opportunity") or {}
    if strategy == "weather":
        return _weather_intent(base, opportunity, mode)
    if mode_intent and mode_intent.get("mode") == 2:
        zone_text = _zone_plan_text(air_quality.get("dry_zone_ids"), "Zones Would Open")
        summary = "AC Mode Intent: Dry"
        if zone_text:
            summary = f"{summary} / {zone_text}"
        return {
            **base,
            "intent": "dehumidify",
            "headline": "Dehumidification Recommended",
            "summary": summary,
            "reason": mode_intent.get("reason"),
            "confidence": 0.7,
        }
    if mode_intent and mode_intent.get("mode") == 3 and mode_intent.get("outside_air_intent"):
        zone_text = _zone_plan_text(air_quality.get("outside_air_zone_ids"), "Outside Air Zones Would Open")
        summary = "Fan And Outside Air Recommended"
        if zone_text:
            summary = f"{summary} / {zone_text}"
        return {
            **base,
            "intent": "ventilate",
            "headline": "Fresh Air Recommended",
            "summary": summary,
            "reason": mode_intent.get("reason"),
            "confidence": 0.7,
        }
    if mode_intent and mode_intent.get("change_required") and not mpc:
        summary = f"AC Mode Intent: {mode_intent.get('name')}"
        if mode_intent.get("outside_air_intent"):
            summary = f"{summary} / Outside Air Recommended"
        return {
            **base,
            "intent": "mode_change",
            "headline": f"{mode_intent.get('name')} Mode Recommended",
            "summary": summary,
            "reason": mode_intent.get("reason"),
        }
    if isinstance(mpc, dict) and mpc:
        return _forecast_intent(base, mpc, evaluation)
    if opportunity and not mpc:
        return _weather_intent(base, opportunity, mode)
    if mode == "off":
        return {**base, "intent": "off", "headline": "Adaptive Control Is Off", "summary": "No Adaptive Recommendations Or Commands Are Being Produced."}
    return base


def _weather_intent(base: dict[str, Any], opportunity: dict[str, Any], mode: str) -> dict[str, Any]:
    if not opportunity:
        return base
    setpoint = opportunity.get("setpoint")
    outside = opportunity.get("outside_rounded")
    reason = opportunity.get("reason")
    if opportunity.get("recommend_off"):
        intent = "turn_off" if mode == "adaptive" else "ventilate"
        headline = "Weather Can Carry Load" if mode == "adaptive" else "Open Windows Recommended"
        summary = f"Outside {outside} C Is Favourable Versus Setpoint {setpoint} C."
    elif opportunity.get("outside_favourable"):
        intent = "hold"
        headline = "Outside Air Is Favourable"
        summary = "Weather Off Is Held By Forecast." if reason == "forecast_not_favourable_enough" else "Weather Off Is Held By Indoor Comfort."
    else:
        intent = "monitor"
        headline = "Weather Holding"
        summary = "Outside Air Is Not Favourable Yet."
    return {
        **base,
        "intent": intent,
        "headline": headline,
        "summary": summary,
        "reason": reason,
        "confidence": 1.0 if opportunity.get("recommend_off") else None,
    }


def _forecast_intent(base: dict[str, Any], mpc: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
    source = str(mpc.get("source") or "")
    if source == "learning":
        return {
            **base,
            "intent": "learning",
            "headline": "Model Learning",
            "summary": "Waiting For More Samples Before Control.",
            "reason": mpc.get("reason"),
        }
    action = str(mpc.get("action") or "idle")
    intent = {"heating": "heat", "cooling": "cool", "idle": "hold"}.get(action, "monitor")
    headline = {"heating": "Heating Expected", "cooling": "Cooling Expected", "idle": "Holding Target"}.get(action, "Forecast Ready")
    target = mpc.get("target", base.get("recommended_target"))
    summary_parts = [f"Recommended Target: {target} C"]
    runtime_hours = base.get("runtime_hours")
    if isinstance(runtime_hours, (int, float)):
        summary_parts.append(f"Expected Runtime: {runtime_hours:.1f} H")
    hybrid = evaluation.get("hybrid") or {}
    dampers = hybrid.get("damper_percentages") if isinstance(hybrid, dict) else None
    if dampers:
        damper_text = ", ".join(f"Zone {int(group_id) + 1} {percent}%" for group_id, percent in sorted(dampers.items(), key=lambda item: int(item[0])))
        summary_parts.append(f"Damper Plan: {damper_text}")
    air_quality = evaluation.get("air_quality") if isinstance(evaluation.get("air_quality"), dict) else {}
    if air_quality.get("dry_held_reason") == "thermal_demand_active":
        summary_parts.append("Humidity High: Thermal Mode Preferred")
    if air_quality.get("fan_held_reason") == "thermal_demand_active":
        summary_parts.append("CO2 High: Outside Air Recommended")
    return {
        **base,
        "intent": intent,
        "headline": headline,
        "summary": " / ".join(summary_parts),
        "reason": mpc.get("reason"),
        "recommended_target": target,
        "confidence": mpc.get("confidence"),
    }


def _zone_plan_text(values: Any, label: str) -> str:
    labels = _zone_labels(values or [])
    if not labels:
        return ""
    return f"{label}: {', '.join(labels)}"


def _zone_labels(values: Any) -> list[str]:
    labels = []
    for value in values:
        try:
            labels.append(f"Zone {int(value) + 1}")
        except (TypeError, ValueError):
            continue
    return labels


def _title_text(value: Any) -> str:
    text = str(value or "").replace("_", " ").replace("-", " ").strip()
    return " ".join(part[:1].upper() + part[1:].lower() for part in text.split())


def _runtime_forecast_status(forecast: Any) -> dict[str, Any] | None:
    if forecast is None:
        return None
    return {
        "horizon_hours": forecast.horizon_hours,
        "step_minutes": forecast.step_minutes,
        "runtime_minutes": forecast.runtime_minutes,
        "runtime_hours": round(forecast.runtime_minutes / 60.0, 2),
        "runtime_fraction": forecast.runtime_fraction,
        "zone_runtime_minutes": {
            str(group_id): minutes
            for group_id, minutes in getattr(forecast, "zone_runtime_minutes", {}).items()
        },
        "zone_runtime_fraction": {
            str(group_id): fraction
            for group_id, fraction in getattr(forecast, "zone_runtime_fraction", {}).items()
        },
        "action_windows": list(getattr(forecast, "action_windows", [])),
        "series": list(getattr(forecast, "series", [])),
        "quality": dict(getattr(forecast, "quality", {})),
    }





def _mode_name(mode: int | None) -> str:
    names = {0: "Auto", 1: "Heat", 2: "Dry", 3: "Fan", 4: "Cool"}
    return names.get(mode, "Unknown")
