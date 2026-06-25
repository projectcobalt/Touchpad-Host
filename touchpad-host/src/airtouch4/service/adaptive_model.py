"""Normalized adaptive-control model shared by translators and MPC core."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdaptiveRoom:
    id: int
    name: str
    ac_id: int
    temperature: float | None
    setpoint: float | None
    active: bool
    learn: bool
    control_enabled: bool
    power_fraction: float = 0.0


@dataclass(frozen=True)
class AdaptiveDevice:
    ac_id: int
    name: str
    mode: int | None
    power_on: bool
    setpoint: float | None
    min_setpoint: float | None
    max_setpoint: float | None
    rooms: tuple[AdaptiveRoom, ...]


@dataclass(frozen=True)
class AdaptiveSnapshot:
    devices: tuple[AdaptiveDevice, ...]
