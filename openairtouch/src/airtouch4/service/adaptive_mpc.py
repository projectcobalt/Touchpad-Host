"""AirTouch-native EKF learning, MPC planning, and analytics helpers."""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from .adaptive_model import AdaptiveRoom, AdaptiveSnapshot


MODE_IDLE = "idle"
MODE_HEATING = "heating"
MODE_COOLING = "cooling"
PLAN_DT_MINUTES = 5.0
MIN_IDLE_SAMPLES = 60
MIN_ACTIVE_SAMPLES = 20
MPC_STD_THRESHOLD = 0.5
NORMAL_MIN_PASSIVE_SAMPLES = 60
NORMAL_MIN_ACTIVE_SAMPLES = 20
NORMAL_MIN_EKF_UPDATES = 3
LEARNING_OBSERVATION_INTERVAL_SECONDS = 3 * 60
TELEMETRY_UNKNOWN_CONFIDENCE_FACTOR = 0.5
TELEMETRY_DISAGREE_CONFIDENCE_FACTOR = 0.45


@dataclass(frozen=True)
class MpcProposal:
    target: int
    source: str
    confidence: float
    predicted_temperatures: list[float]
    reason: str
    action: str = MODE_IDLE
    power_fraction: float = 0.0
    zone_power_fractions: dict[int, float] = field(default_factory=dict)
    projected_runtime_hours: float = 0.0
    zone_projected_runtime_hours: dict[int, float] = field(default_factory=dict)
    runtime_forecast: RuntimeForecast | None = None


@dataclass(frozen=True)
class RuntimeForecast:
    horizon_hours: int
    step_minutes: float
    runtime_minutes: float
    runtime_fraction: float
    zone_runtime_minutes: dict[int, float] = field(default_factory=dict)
    zone_runtime_fraction: dict[int, float] = field(default_factory=dict)
    action_windows: list[dict[str, Any]] = field(default_factory=list)
    series: list[dict[str, Any]] = field(default_factory=list)
    quality: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MpcInputs:
    horizon_hours: int
    outside_temperature: float | None = None
    outside_forecast: tuple[float, ...] = ()
    outside_forecast_step_minutes: float = 60.0
    humidity: float | None = None
    humidity_assist_threshold: float = 60.0
    q_solar: float = 0.0
    target_policy: str = "global_setpoint"
    comfort_weight: int = 70
    input_quality: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MpcPlan:
    actions: list[str]
    temperatures: list[float]
    power_fractions: list[float]

    @property
    def current_action(self) -> str:
        return self.actions[0] if self.actions else MODE_IDLE

    @property
    def current_power_fraction(self) -> float:
        return self.power_fractions[0] if self.power_fractions else 0.0


@dataclass
class RCModel:
    """First-order room thermal model using normalized heat/cool rates."""

    alpha: float = 0.15
    beta_heat: float = 3.0
    beta_cool: float = 4.0
    beta_solar: float = 0.5
    beta_occupancy: float = 0.2

    def predict(
        self,
        room_temp: float,
        outdoor_temp: float,
        mode: str,
        dt_minutes: float,
        *,
        power_fraction: float = 1.0,
        q_solar: float = 0.0,
        q_occupancy: float = 0.0,
    ) -> float:
        dt_hours = max(0.0, dt_minutes) / 60.0
        if dt_hours <= 0:
            return room_temp
        u = self.beta_solar * q_solar + self.beta_occupancy * q_occupancy
        if mode == MODE_HEATING:
            u += self.beta_heat * power_fraction
        elif mode == MODE_COOLING:
            u -= self.beta_cool * power_fraction
        if abs(self.alpha) < 0.01:
            result = room_temp + ((outdoor_temp - room_temp) * self.alpha + u) * dt_hours
        else:
            decay = math.exp(-self.alpha * dt_hours)
            equilibrium = outdoor_temp + (u / self.alpha)
            result = equilibrium + (room_temp - equilibrium) * decay
        return max(0.0, min(50.0, result))

    def to_dict(self) -> dict[str, float]:
        return {
            "alpha": self.alpha,
            "beta_heat": self.beta_heat,
            "beta_cool": self.beta_cool,
            "beta_solar": self.beta_solar,
            "beta_occupancy": self.beta_occupancy,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RCModel:
        return cls(
            alpha=_clamp(_number(data.get("alpha")) or cls.alpha, 0.005, 2.0),
            beta_heat=_clamp(_number(data.get("beta_heat")) or cls.beta_heat, 0.1, 200.0),
            beta_cool=_clamp(_number(data.get("beta_cool")) or cls.beta_cool, 0.1, 300.0),
            beta_solar=_clamp(_number(data.get("beta_solar")) or cls.beta_solar, 0.0, 50.0),
            beta_occupancy=_clamp(_number(data.get("beta_occupancy")) or cls.beta_occupancy, 0.0, 20.0),
        )


@dataclass
class ThermalEKF:
    """Extended Kalman filter for [T, alpha, beta_h, beta_c, beta_s, beta_o]."""

    x: list[float] = field(default_factory=lambda: [20.0, 0.15, 3.0, 4.0, 0.5, 0.2])
    p: list[list[float]] = field(default_factory=lambda: [
        [0.5, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 0.5, 0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 50.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 50.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 25.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.0, 10.0],
    ])
    updates: int = 0
    idle_samples: int = 0
    heating_samples: int = 0
    cooling_samples: int = 0
    initialized: bool = False

    @property
    def model(self) -> RCModel:
        return RCModel(
            alpha=self.x[1],
            beta_heat=self.x[2],
            beta_cool=self.x[3],
            beta_solar=self.x[4],
            beta_occupancy=self.x[5],
        )

    @property
    def confidence(self) -> float:
        if self.updates < 3:
            return 0.0
        idle = min(self.idle_samples / MIN_IDLE_SAMPLES, 1.0)
        active_count = max(self.heating_samples, self.cooling_samples)
        active = min(active_count / MIN_ACTIVE_SAMPLES, 1.0)
        std = self.prediction_std(MODE_IDLE, self.x[0], self.x[0], PLAN_DT_MINUTES)
        accuracy = 0.0 if std >= MPC_STD_THRESHOLD else 1.0 - (std / MPC_STD_THRESHOLD)
        return round((0.25 * idle) + (0.35 * active) + (0.4 * accuracy), 3)

    def update(
        self,
        measured_temp: float,
        outdoor_temp: float,
        mode: str,
        dt_minutes: float,
        *,
        power_fraction: float = 1.0,
        q_solar: float = 0.0,
        q_occupancy: float = 0.0,
    ) -> None:
        if dt_minutes < 1.0:
            self.x[0] = measured_temp
            self.initialized = True
            return
        if not self.initialized:
            self.x[0] = measured_temp
            self.initialized = True
            return
        self._predict(outdoor_temp, mode, dt_minutes, power_fraction, q_solar, q_occupancy)
        self._measurement_update(measured_temp)
        self._clamp()
        self.updates += 1
        if mode == MODE_HEATING:
            self.heating_samples += 1
        elif mode == MODE_COOLING:
            self.cooling_samples += 1
        else:
            self.idle_samples += 1

    def prediction_std(
        self,
        mode: str,
        room_temp: float,
        outdoor_temp: float,
        dt_minutes: float,
        *,
        power_fraction: float = 1.0,
        q_solar: float = 0.0,
        q_occupancy: float = 0.0,
    ) -> float:
        f = self._jacobian(room_temp, outdoor_temp, mode, dt_minutes, power_fraction, q_solar, q_occupancy)
        fp = [sum(f[k] * self.p[k][j] for k in range(6)) for j in range(6)]
        var = sum(fp[j] * f[j] for j in range(6)) + 0.01
        return math.sqrt(max(0.0, var))

    def _predict(
        self,
        outdoor_temp: float,
        mode: str,
        dt_minutes: float,
        power_fraction: float,
        q_solar: float,
        q_occupancy: float,
    ) -> None:
        f = self._jacobian(self.x[0], outdoor_temp, mode, dt_minutes, power_fraction, q_solar, q_occupancy)
        predicted_temp = self.model.predict(
            self.x[0],
            outdoor_temp,
            mode,
            dt_minutes,
            power_fraction=power_fraction,
            q_solar=q_solar,
            q_occupancy=q_occupancy,
        )
        fp = [[f[i] * self.p[i][j] if i == 0 else (self.p[i][j] if i == j else 0.0) for j in range(6)] for i in range(6)]
        p_new = [[0.0] * 6 for _ in range(6)]
        for i in range(6):
            for j in range(6):
                if i == 0 and j == 0:
                    p_new[i][j] = sum(fp[0][k] * f[k] for k in range(6)) + 0.01
                elif i == j:
                    noise = [0.01, 0.0005, 0.005 if mode == MODE_HEATING else 0.0, 0.005 if mode == MODE_COOLING else 0.0, 0.002 if q_solar > 0 else 0.0, 0.002 if q_occupancy > 0 else 0.0][i]
                    p_new[i][j] = max(1e-9, self.p[i][j] + noise)
                else:
                    p_new[i][j] = self.p[i][j]
        self.x[0] = predicted_temp
        self.p = p_new

    def _measurement_update(self, measured_temp: float) -> None:
        r = 0.04
        innovation = measured_temp - self.x[0]
        s = self.p[0][0] + r
        if s <= 1e-12:
            self.x[0] = measured_temp
            return
        if abs(innovation) / math.sqrt(s) > 4.0:
            r *= 100.0
            s = self.p[0][0] + r
        k = [self.p[i][0] / s for i in range(6)]
        for i in range(6):
            self.x[i] += k[i] * innovation
        p_new = [[self.p[i][j] - k[i] * self.p[0][j] for j in range(6)] for i in range(6)]
        for i in range(6):
            p_new[i][i] = max(1e-9, p_new[i][i] + k[i] * r * k[i])
        self.p = p_new

    def _jacobian(
        self,
        room_temp: float,
        outdoor_temp: float,
        mode: str,
        dt_minutes: float,
        power_fraction: float,
        q_solar: float,
        q_occupancy: float,
    ) -> list[float]:
        dt_h = max(0.0, dt_minutes) / 60.0
        alpha = max(0.005, self.x[1])
        decay = math.exp(-alpha * dt_h)
        one_minus = 1.0 - decay
        u = self._mode_u(mode, power_fraction, q_solar, q_occupancy)
        row = [0.0] * 6
        row[0] = decay
        row[1] = -(u / (alpha * alpha)) * one_minus - (room_temp - outdoor_temp - u / alpha) * dt_h * decay
        if mode == MODE_HEATING:
            row[2] = power_fraction * one_minus / alpha
        elif mode == MODE_COOLING:
            row[3] = -power_fraction * one_minus / alpha
        row[4] = q_solar * one_minus / alpha
        row[5] = q_occupancy * one_minus / alpha
        return row

    def _mode_u(self, mode: str, power_fraction: float, q_solar: float, q_occupancy: float) -> float:
        u = self.x[4] * q_solar + self.x[5] * q_occupancy
        if mode == MODE_HEATING:
            u += self.x[2] * power_fraction
        elif mode == MODE_COOLING:
            u -= self.x[3] * power_fraction
        return u

    def _clamp(self) -> None:
        bounds = [(0.0, 50.0), (0.005, 2.0), (0.1, 200.0), (0.1, 300.0), (0.0, 50.0), (0.0, 20.0)]
        for index, (lo, hi) in enumerate(bounds):
            self.x[index] = _clamp(self.x[index], lo, hi)

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": list(self.x),
            "p": [list(row) for row in self.p],
            "updates": self.updates,
            "idle_samples": self.idle_samples,
            "heating_samples": self.heating_samples,
            "cooling_samples": self.cooling_samples,
            "initialized": self.initialized,
        }

    def boost_covariance(self, factor: float = 2.5, floor_fraction: float = 0.3) -> None:
        initial = [0.5, 0.5, 50.0, 50.0, 25.0, 10.0]
        for i in range(6):
            for j in range(6):
                boosted = self.p[i][j] * factor
                if i == j:
                    boosted = max(boosted, initial[i] * floor_fraction)
                self.p[i][j] = boosted
        for i in range(6):
            for j in range(i + 1, 6):
                avg = (self.p[i][j] + self.p[j][i]) / 2.0
                self.p[i][j] = avg
                self.p[j][i] = avg
        for i in range(6):
            self.p[i][i] = max(self.p[i][i], 1e-10)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ThermalEKF:
        ekf = cls()
        if isinstance(data.get("x"), list) and len(data["x"]) == 6:
            ekf.x = [float(value) for value in data["x"]]
        if isinstance(data.get("p"), list) and len(data["p"]) == 6:
            ekf.p = [[float(value) for value in row[:6]] for row in data["p"][:6]]
        ekf.updates = int(data.get("updates") or 0)
        ekf.idle_samples = int(data.get("idle_samples") or 0)
        ekf.heating_samples = int(data.get("heating_samples") or 0)
        ekf.cooling_samples = int(data.get("cooling_samples") or 0)
        ekf.initialized = bool(data.get("initialized", ekf.updates > 0))
        ekf._clamp()
        return ekf


@dataclass
class ZoneThermalModel:
    """Compatibility wrapper around the EKF with training accumulation."""

    last_ts: float | None = None
    last_temperature: float | None = None
    passive_samples: int = 0
    active_samples: int = 0
    passive_drift_per_hour: float = 0.0
    active_response_per_hour: float = 0.0
    outside_coupling_per_hour: float = 0.0
    learn: bool = False
    accelerated_learning: bool = False
    last_boost_ts: float | None = None
    skipped_observations: int = 0
    last_skip_reason: str | None = None
    ekf: ThermalEKF = field(default_factory=ThermalEKF)

    @property
    def confidence(self) -> float:
        if self.ekf.updates < 3:
            return 0.0
        data_factor = self.learning_progress
        std = self._prediction_std()
        noise_floor = 0.20
        if std <= noise_floor:
            accuracy_factor = 1.0
        elif std >= MPC_STD_THRESHOLD:
            accuracy_factor = 0.0
        else:
            accuracy_factor = 1.0 - ((std - noise_floor) / (MPC_STD_THRESHOLD - noise_floor))
        return round(data_factor * (0.3 + 0.7 * accuracy_factor), 3)

    @property
    def learning_progress(self) -> float:
        requirements = self._readiness_requirements()
        passive = min(self.passive_samples / requirements["passive"], 1.0)
        active_observations = max(self.active_samples, self.ekf.heating_samples, self.ekf.cooling_samples)
        active = min(active_observations / requirements["active"], 1.0)
        ekf = min(self.ekf.updates / requirements["ekf"], 1.0)
        return round((0.35 * passive) + (0.35 * active) + (0.3 * ekf), 3)

    @property
    def mpc_ready(self) -> bool:
        return self._has_readiness_evidence()

    def mpc_ready_for(self, *, cooling: bool) -> bool:
        return self._has_readiness_evidence(cooling=cooling)

    @property
    def cooling_ready(self) -> bool:
        return self._has_readiness_evidence(cooling=True)

    @property
    def heating_ready(self) -> bool:
        return self._has_readiness_evidence(cooling=False)

    @property
    def readiness_reason(self) -> str:
        return self.readiness_reason_for()

    def readiness_reason_for(self, *, cooling: bool | None = None) -> str:
        requirements = self._readiness_requirements()
        if self.passive_samples < requirements["passive"]:
            return "passive_samples"
        active_samples = self.active_samples
        if cooling is True:
            active_samples = self.ekf.cooling_samples
        elif cooling is False:
            active_samples = self.ekf.heating_samples
        else:
            active_samples = max(self.ekf.heating_samples, self.ekf.cooling_samples, self.active_samples)
        if active_samples < requirements["active"]:
            return "cooling_samples" if cooling is True else "heating_samples" if cooling is False else "active_samples"
        if self.ekf.updates < requirements["ekf"]:
            return "ekf_updates"
        if self._prediction_std() >= MPC_STD_THRESHOLD:
            return "prediction_std"
        return "ready"

    def _readiness_requirements(self) -> dict[str, int]:
        return {
            "passive": NORMAL_MIN_PASSIVE_SAMPLES,
            "active": NORMAL_MIN_ACTIVE_SAMPLES,
            "ekf": NORMAL_MIN_EKF_UPDATES,
        }

    def _has_readiness_evidence(self, *, cooling: bool | None = None) -> bool:
        requirements = self._readiness_requirements()
        active_samples = self.active_samples
        if cooling is True:
            active_samples = self.ekf.cooling_samples
        elif cooling is False:
            active_samples = self.ekf.heating_samples
        return (
            self.passive_samples >= requirements["passive"]
            and active_samples >= requirements["active"]
            and self.ekf.updates >= requirements["ekf"]
            and self._prediction_std() < MPC_STD_THRESHOLD
        )

    def _prediction_std(self) -> float:
        return self.ekf.prediction_std(MODE_IDLE, self.ekf.x[0], self.ekf.x[0], PLAN_DT_MINUTES)

    def _observation_interval_seconds(self) -> float:
        return LEARNING_OBSERVATION_INTERVAL_SECONDS

    def boost_learning(self, *, now: float | None = None, cooldown_seconds: float = 3600.0) -> bool:
        if now is not None and self.last_boost_ts is not None and now - self.last_boost_ts < cooldown_seconds:
            return False
        self.ekf.boost_covariance()
        self.last_boost_ts = now
        return True

    def mark_skipped(self, reason: str) -> None:
        self.skipped_observations += 1
        self.last_skip_reason = reason

    def observe(
        self,
        *,
        ts: float,
        temperature: float,
        active: bool,
        cooling: bool | None,
        outside_temperature: float | None = None,
        q_solar: float = 0.0,
        q_occupancy: float = 0.0,
        learn: bool = True,
        power_fraction: float = 1.0,
    ) -> float | None:
        self.learn = self.learn or learn
        if self.last_ts is None or self.last_temperature is None:
            self.last_ts = ts
            self.last_temperature = temperature
            self.ekf.x[0] = temperature
            self.ekf.initialized = True
            return None
        elapsed_hours = (ts - self.last_ts) / 3600.0
        if elapsed_hours * 3600.0 < self._observation_interval_seconds():
            return None
        mode = MODE_IDLE
        if active and cooling is not None:
            mode = MODE_COOLING if cooling else MODE_HEATING
        predicted_temperature = self.ekf.model.predict(
            self.last_temperature,
            outside_temperature if outside_temperature is not None else self.last_temperature,
            mode,
            elapsed_hours * 60.0,
            power_fraction=power_fraction,
            q_solar=q_solar,
            q_occupancy=q_occupancy,
        )
        delta_per_hour = (temperature - self.last_temperature) / elapsed_hours
        if active and cooling is not None:
            expected = -1 if cooling else 1
            response = delta_per_hour * expected
            self.active_response_per_hour = _smooth(self.active_response_per_hour, _clamp(response, -2.0, 4.0), self.active_samples)
            self.active_samples += 1
        else:
            self.passive_drift_per_hour = _smooth(self.passive_drift_per_hour, _clamp(delta_per_hour, -2.0, 2.0), self.passive_samples)
            if outside_temperature is not None:
                gap = outside_temperature - self.last_temperature
                if abs(gap) >= 1.0:
                    self.outside_coupling_per_hour = _smooth(self.outside_coupling_per_hour, _clamp(delta_per_hour / gap, -0.3, 0.3), self.passive_samples)
            self.passive_samples += 1
        self.ekf.update(
            temperature,
            outside_temperature if outside_temperature is not None else self.last_temperature,
            mode,
            elapsed_hours * 60.0,
            power_fraction=power_fraction,
            q_solar=q_solar,
            q_occupancy=q_occupancy,
        )
        self.last_ts = ts
        self.last_temperature = temperature
        return predicted_temperature

    def predict(
        self,
        *,
        current_temperature: float,
        hours: int,
        cooling: bool,
        outside_forecast: list[float] | tuple[float, ...] = (),
    ) -> list[float]:
        blocks = max(1, hours * int(60 / PLAN_DT_MINUTES))
        outdoor = _expand_hourly(outside_forecast, blocks, current_temperature)
        plan = _optimize_plan(
            self.ekf.model,
            current_temperature,
            outdoor,
            [current_temperature] * blocks,
            [current_temperature] * blocks,
            can_heat=not cooling,
            can_cool=cooling,
        )
        hourly: list[float] = []
        step = int(60 / PLAN_DT_MINUTES)
        for hour in range(hours):
            index = min((hour + 1) * step, len(plan.temperatures) - 1)
            hourly.append(round(plan.temperatures[index], 2))
        return hourly

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_ts": self.last_ts,
            "last_temperature": self.last_temperature,
            "passive_samples": self.passive_samples,
            "active_samples": self.active_samples,
            "passive_drift_per_hour": self.passive_drift_per_hour,
            "active_response_per_hour": self.active_response_per_hour,
            "outside_coupling_per_hour": self.outside_coupling_per_hour,
            "learn": self.learn,
            "accelerated_learning": self.accelerated_learning,
            "last_boost_ts": self.last_boost_ts,
            "skipped_observations": self.skipped_observations,
            "last_skip_reason": self.last_skip_reason,
            "ekf": self.ekf.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ZoneThermalModel:
        model = cls(
            last_ts=_number(data.get("last_ts")),
            last_temperature=_number(data.get("last_temperature")),
            passive_samples=int(data.get("passive_samples") or 0),
            active_samples=int(data.get("active_samples") or 0),
            passive_drift_per_hour=float(data.get("passive_drift_per_hour") or 0.0),
            active_response_per_hour=float(data.get("active_response_per_hour") or 0.0),
            outside_coupling_per_hour=float(data.get("outside_coupling_per_hour") or 0.0),
            learn=bool(data.get("learn", False)),
            accelerated_learning=bool(data.get("accelerated_learning", False)),
            last_boost_ts=_number(data.get("last_boost_ts")),
            skipped_observations=int(data.get("skipped_observations") or 0),
            last_skip_reason=data.get("last_skip_reason") if isinstance(data.get("last_skip_reason"), str) else None,
        )
        if isinstance(data.get("ekf"), dict):
            model.ekf = ThermalEKF.from_dict(data["ekf"])
        return model


@dataclass
class CompressorTracker:
    ac_state: dict[int, bool] = field(default_factory=dict)
    state: dict[int, bool] = field(default_factory=dict)
    changed_at: dict[int, float] = field(default_factory=dict)
    groups: tuple[tuple[int, ...], ...] = ()

    def configure(self, groups: tuple[tuple[int, ...], ...]) -> None:
        self.groups = tuple(tuple(group) for group in groups)
        self._recompute_all(0.0, preserve_existing=True)

    def observe(self, ac_id: int, power_on: bool, now: float) -> None:
        self.ac_state[ac_id] = power_on
        self._recompute_group(self._group_key(ac_id), now)

    def can_power_off(
        self,
        ac_id: int,
        now: float,
        minimum_run_seconds: float,
        *,
        planned_off: set[int] | None = None,
    ) -> bool:
        key = self._group_key(ac_id)
        if self._other_members_on(ac_id, planned_off=planned_off or set()):
            return True
        if self.state.get(key) is not True:
            return True
        changed = self.changed_at.get(key)
        return changed is None or now - changed >= minimum_run_seconds

    def can_power_on(self, ac_id: int, now: float, minimum_off_seconds: float) -> bool:
        key = self._group_key(ac_id)
        if self.state.get(key) is True:
            return True
        if self.state.get(key) is not False:
            return True
        changed = self.changed_at.get(key)
        return changed is None or now - changed >= minimum_off_seconds

    def status(self, now: float) -> dict[str, Any]:
        return {
            str(key): {
                "acs": list(self._members_for_key(key)),
                "power_on": power_on,
                "seconds_since_change": None if key not in self.changed_at else round(now - self.changed_at[key], 1),
            }
            for key, power_on in sorted(self.state.items())
        }

    def _recompute_all(self, now: float, *, preserve_existing: bool = False) -> None:
        keys = {self._group_key(ac_id) for ac_id in self.ac_state}
        keys.update(range(len(self.groups)))
        for key in sorted(keys):
            self._recompute_group(key, now, preserve_existing=preserve_existing)

    def _recompute_group(self, key: int, now: float, *, preserve_existing: bool = False) -> None:
        power_on = any(self.ac_state.get(member) is True for member in self._members_for_key(key))
        previous = self.state.get(key)
        if previous is None:
            self.state[key] = power_on
            if not preserve_existing:
                self.changed_at[key] = now
            return
        if previous != power_on:
            self.state[key] = power_on
            self.changed_at[key] = now

    def _group_key(self, ac_id: int) -> int:
        for index, group in enumerate(self.groups):
            if ac_id in group:
                return index
        return len(self.groups) + ac_id

    def _members_for_key(self, key: int) -> tuple[int, ...]:
        if 0 <= key < len(self.groups):
            return self.groups[key]
        return (key - len(self.groups),)

    def _other_members_on(self, ac_id: int, *, planned_off: set[int]) -> bool:
        members = self._members_for_key(self._group_key(ac_id))
        return any(member != ac_id and member not in planned_off and self.ac_state.get(member) is True for member in members)


class AdaptiveMpcEngine:
    def __init__(self) -> None:
        self.zone_models: dict[int, ZoneThermalModel] = {}
        self.compressor = CompressorTracker()
        self.history: dict[int, deque[dict[str, Any]]] = {}
        self.forecasts: dict[int, list[dict[str, Any]]] = {}
        self.last_plans: dict[int, MpcProposal] = {}
        self.learning_paused_reason: str | None = None

    def observe(
        self,
        snapshot: AdaptiveSnapshot,
        *,
        now: float,
        outside_temperature: float | None = None,
        q_solar: float = 0.0,
        q_occupancy: float = 0.0,
    ) -> None:
        for device in snapshot.devices:
            self.compressor.observe(device.ac_id, device.power_on, now)
        learning_rooms_seen = False
        skipped_for_outdoor = False
        for device in snapshot.devices:
            mode = device.mode
            cooling = True if mode == 4 else False if mode == 1 else None
            for room in device.rooms:
                if room.temperature is None or not room.learn:
                    continue
                learning_rooms_seen = True
                active = device.power_on and room.active
                model = self.zone_models.setdefault(room.id, ZoneThermalModel())
                model.learn = model.learn or room.learn
                if outside_temperature is None:
                    skipped_for_outdoor = True
                    model.mark_skipped("outside_temperature_unavailable")
                    self._record(
                        room.id,
                        now,
                        room.temperature,
                        outside_temperature,
                        "skipped_outdoor",
                        source="skipped",
                        skipped=True,
                        skip_reason="outside_temperature_unavailable",
                        q_solar=q_solar,
                        estimated_power_fraction=room.power_fraction,
                    )
                    continue
                predicted = model.observe(
                    ts=now,
                    temperature=room.temperature,
                    active=active,
                    cooling=cooling,
                    outside_temperature=outside_temperature,
                    q_solar=q_solar,
                    q_occupancy=q_occupancy,
                    learn=room.learn,
                    power_fraction=room.power_fraction,
                )
                self._record(
                    room.id,
                    now,
                    room.temperature,
                    outside_temperature,
                    MODE_COOLING if active and cooling else MODE_HEATING if active and cooling is False else MODE_IDLE,
                    predicted_temperature=predicted,
                    source="airtouch_zone",
                    q_solar=q_solar,
                    estimated_power_fraction=room.power_fraction,
                )
        self.learning_paused_reason = "outside_temperature_unavailable" if learning_rooms_seen and skipped_for_outdoor else None

    def propose(
        self,
        *,
        ac_id: int,
        rooms: tuple[AdaptiveRoom, ...] | list[AdaptiveRoom],
        baseline_target: int,
        cooling: bool,
        inputs: MpcInputs,
        advisory: bool = False,
    ) -> MpcProposal | None:
        solve_started = time.perf_counter()
        controlled: list[tuple[AdaptiveRoom, ZoneThermalModel, float]] = []
        for room in rooms:
            control_allowed = room.configured_control if advisory else room.control_enabled
            if not room.active or not control_allowed:
                continue
            model = self.zone_models.get(room.id)
            if room.temperature is None or model is None:
                continue
            controlled.append((room, model, room.temperature))
        if not controlled:
            for room in rooms:
                self.forecasts.pop(room.id, None)
            return None

        confidences = [model.confidence for _room, model, _temp in controlled]
        confidence = min(confidences)
        blocks = max(1, inputs.horizon_hours * int(60 / PLAN_DT_MINUTES))
        fallback_outdoor = inputs.outside_temperature if inputs.outside_temperature is not None else controlled[0][2]
        outdoor = _expand_forecast(
            inputs.outside_forecast,
            blocks,
            fallback_outdoor,
            step_minutes=inputs.outside_forecast_step_minutes,
        )
        room_setpoint_targets = inputs.target_policy == "room_setpoint"
        heat_targets = [baseline_target] * blocks
        cool_targets = [baseline_target] * blocks
        predictions: list[list[float]] = []
        actions: list[str] = []
        fractions: list[float] = []
        zone_fractions: dict[int, float] = {}
        runtime_blocks: set[int] = set()
        zone_runtime_hours: dict[int, float] = {}
        zone_plans: dict[int, MpcPlan] = {}
        self.forecasts = {room.id: [] for room, _model, _temperature in controlled}
        optimizer_started = time.perf_counter()
        for room, model, temperature in controlled:
            room_target = _room_mpc_target(room, baseline_target, cooling, room_setpoint_targets)
            room_heat_targets = [room_target] * blocks
            room_cool_targets = [room_target] * blocks
            plan = _optimize_plan(
                model.ekf.model,
                temperature,
                outdoor,
                room_heat_targets,
                room_cool_targets,
                can_heat=not cooling,
                can_cool=cooling,
                humidity=inputs.humidity,
                humidity_assist_threshold=inputs.humidity_assist_threshold,
                q_solar=inputs.q_solar,
                comfort_weight=inputs.comfort_weight,
            )
            predictions.append(plan.temperatures[1:])
            actions.append(plan.current_action)
            fractions.append(plan.current_power_fraction)
            zone_fractions[room.id] = round(plan.current_power_fraction, 3)
            active_blocks = {index for index, action in enumerate(plan.actions) if action != MODE_IDLE}
            runtime_blocks.update(active_blocks)
            zone_runtime_hours[room.id] = round(len(active_blocks) * PLAN_DT_MINUTES / 60.0, 2)
            zone_plans[room.id] = plan
            self.forecasts[room.id] = _forecast_points(plan, outdoor)
        optimizer_duration_ms = (time.perf_counter() - optimizer_started) * 1000.0
        projected_runtime_hours = round(len(runtime_blocks) * PLAN_DT_MINUTES / 60.0, 2)
        runtime_forecast = _runtime_forecast(
            inputs=inputs,
            cooling=cooling,
            target=baseline_target,
            confidence=confidence,
            zone_plans=zone_plans,
            outdoor=outdoor,
            ready=all(model.mpc_ready_for(cooling=cooling) for _room, model, _temp in controlled),
        )
        if not runtime_forecast.quality.get("model_ready"):
            _annotate_solve_diagnostics(
                runtime_forecast,
                started=solve_started,
                optimizer_duration_ms=optimizer_duration_ms,
                horizon_blocks=blocks,
                zone_count=len(controlled),
                input_forecast_points=len(inputs.outside_forecast),
            )
            return MpcProposal(
                target=baseline_target,
                source="learning",
                confidence=confidence,
                predicted_temperatures=[],
                reason="warming_up",
                zone_power_fractions=zone_fractions,
                projected_runtime_hours=projected_runtime_hours,
                zone_projected_runtime_hours=zone_runtime_hours,
                runtime_forecast=runtime_forecast,
            )
        worst_by_block: list[float] = []
        for block in range(blocks):
            values = [prediction[block] for prediction in predictions if len(prediction) > block]
            if values:
                worst_by_block.append(max(values) if cooling else min(values))
        if not worst_by_block:
            return None
        target = _aggregate_room_target(controlled, baseline_target, cooling, room_setpoint_targets)
        if not room_setpoint_targets:
            if cooling and max(worst_by_block) <= baseline_target:
                target = baseline_target + 1
            elif not cooling and min(worst_by_block) >= baseline_target:
                target = baseline_target - 1
        hourly = [round(worst_by_block[min((hour + 1) * int(60 / PLAN_DT_MINUTES) - 1, len(worst_by_block) - 1)], 2) for hour in range(inputs.horizon_hours)]
        _annotate_solve_diagnostics(
            runtime_forecast,
            started=solve_started,
            optimizer_duration_ms=optimizer_duration_ms,
            horizon_blocks=blocks,
            zone_count=len(controlled),
            input_forecast_points=len(inputs.outside_forecast),
        )
        proposal = MpcProposal(
            target=target,
            source="zone" if room_setpoint_targets else "mpc",
            confidence=confidence,
            predicted_temperatures=hourly,
            reason="room_setpoint_demand" if room_setpoint_targets else "ekf_mpc_plan",
            action=_dominant_action(actions),
            power_fraction=round(max(fractions) if fractions else 0.0, 3),
            zone_power_fractions=zone_fractions,
            projected_runtime_hours=projected_runtime_hours,
            zone_projected_runtime_hours=zone_runtime_hours,
            runtime_forecast=runtime_forecast,
        )
        self.last_plans[ac_id] = proposal
        return proposal

    def reset_zone(self, group_id: int) -> None:
        self.zone_models.pop(group_id, None)
        self.history.pop(group_id, None)
        self.forecasts.pop(group_id, None)
        self.last_plans.clear()

    def reset_all(self) -> None:
        self.zone_models.clear()
        self.history.clear()
        self.forecasts.clear()
        self.last_plans.clear()

    def set_accelerated_learning(self, group_id: int, enabled: bool) -> None:
        now = None
        self.set_accelerated_learning_at(group_id, enabled, now=now)

    def set_accelerated_learning_at(self, group_id: int, enabled: bool, *, now: float | None) -> None:
        model = self.zone_models.setdefault(group_id, ZoneThermalModel())
        if enabled and not model.accelerated_learning:
            model.boost_learning(now=now)
        model.accelerated_learning = enabled

    def status(self, now: float) -> dict[str, Any]:
        return {
            "zones": {
                str(group_id): {
                    "learn": model.learn,
                    "accelerated_learning": model.accelerated_learning,
                    "learning_progress": model.learning_progress,
                    "readiness_reason": model.readiness_reason,
                    "cooling_readiness_reason": model.readiness_reason_for(cooling=True),
                    "heating_readiness_reason": model.readiness_reason_for(cooling=False),
                    "readiness_requirements": model._readiness_requirements(),
                    "cooling_ready": model.cooling_ready,
                    "heating_ready": model.heating_ready,
                    "idle_observations": model.ekf.idle_samples,
                    "cooling_observations": model.ekf.cooling_samples,
                    "heating_observations": model.ekf.heating_samples,
                    "skipped_observations": model.skipped_observations,
                    "last_skip_reason": model.last_skip_reason,
                    "last_boost_ts": model.last_boost_ts,
                    "passive_hours": round(model.passive_samples * LEARNING_OBSERVATION_INTERVAL_SECONDS / 3600.0, 2),
                    "active_hours": round(model.active_samples * LEARNING_OBSERVATION_INTERVAL_SECONDS / 3600.0, 2),
                    "confidence": model.confidence,
                    "mpc_ready": model.mpc_ready,
                    "passive_samples": model.passive_samples,
                    "active_samples": model.active_samples,
                    "last_temperature": model.last_temperature,
                    "last_ts": model.last_ts,
                    "passive_drift_per_hour": round(model.passive_drift_per_hour, 3),
                    "active_response_per_hour": round(model.active_response_per_hour, 3),
                    "outside_coupling_per_hour": round(model.outside_coupling_per_hour, 4),
                    "ekf_updates": model.ekf.updates,
                    "idle_samples": model.ekf.idle_samples,
                    "heating_samples": model.ekf.heating_samples,
                    "cooling_samples": model.ekf.cooling_samples,
                    "prediction_std": round(model.ekf.prediction_std(MODE_IDLE, model.ekf.x[0], model.ekf.x[0], PLAN_DT_MINUTES), 3),
                    "alpha": round(model.ekf.x[1], 4),
                    "beta_heat": round(model.ekf.x[2], 3),
                    "beta_cool": round(model.ekf.x[3], 3),
                    "beta_solar": round(model.ekf.x[4], 3),
                    "beta_occupancy": round(model.ekf.x[5], 3),
                    "covariance": {
                        "temperature": round(model.ekf.p[0][0], 4),
                        "alpha": round(model.ekf.p[1][1], 4),
                        "heat": round(model.ekf.p[2][2], 4),
                        "cool": round(model.ekf.p[3][3], 4),
                        "solar": round(model.ekf.p[4][4], 4),
                        "occupancy": round(model.ekf.p[5][5], 4),
                    },
                    "history_points": len(self.history.get(group_id, ())),
                }
                for group_id, model in sorted(self.zone_models.items())
            },
            "compressor": self.compressor.status(now),
            "learning_paused_reason": self.learning_paused_reason,
            "analytics": {
                str(group_id): [_analytics_point(point) for point in list(points)[-24:]]
                for group_id, points in sorted(self.history.items())
            },
            "forecasts": {
                str(group_id): points
                for group_id, points in sorted(self.forecasts.items())
                if points
            },
            "plans": {
                str(ac_id): {
                    "target": plan.target,
                    "source": plan.source,
                    "confidence": plan.confidence,
                    "action": plan.action,
                    "power_fraction": plan.power_fraction,
                    "projected_runtime_hours": plan.projected_runtime_hours,
                    "zone_projected_runtime_hours": {
                        str(group_id): hours
                        for group_id, hours in plan.zone_projected_runtime_hours.items()
                    },
                    "predicted_temperatures": plan.predicted_temperatures,
                    "reason": plan.reason,
                    "runtime_forecast": _runtime_forecast_status(plan.runtime_forecast),
                }
                for ac_id, plan in sorted(self.last_plans.items())
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "zones": {str(group_id): model.to_dict() for group_id, model in self.zone_models.items()},
            "history": {str(group_id): list(points) for group_id, points in self.history.items()},
        }

    def load_dict(self, payload: dict[str, Any]) -> None:
        zones = payload.get("zones") if isinstance(payload, dict) else None
        if isinstance(zones, dict):
            self.zone_models = {
                int(group_id): ZoneThermalModel.from_dict(model)
                for group_id, model in zones.items()
                if isinstance(model, dict) and _is_int(group_id)
            }
        history = payload.get("history") if isinstance(payload, dict) else None
        if isinstance(history, dict):
            self.history = {
                int(group_id): deque([row for row in rows if isinstance(row, dict)], maxlen=576)
                for group_id, rows in history.items()
                if _is_int(group_id) and isinstance(rows, list)
            }

    def _record(
        self,
        group_id: int,
        now: float,
        room_temp: float,
        outdoor_temp: float | None,
        mode: str,
        *,
        predicted_temperature: float | None = None,
        source: str | None = None,
        skipped: bool = False,
        skip_reason: str | None = None,
        q_solar: float = 0.0,
        estimated_power_fraction: float = 0.0,
    ) -> None:
        points = self.history.setdefault(group_id, deque(maxlen=576))
        point = {
            "ts": round(now, 1),
            "room_temp": round(room_temp, 2),
            "outdoor_temp": outdoor_temp,
            "mode": mode,
            "source": source,
            "skipped": skipped,
            "skip_reason": skip_reason,
            "q_solar": round(q_solar, 3),
            "estimated_power_fraction": round(estimated_power_fraction, 4),
        }
        if predicted_temperature is not None:
            point["predicted_temperature"] = round(predicted_temperature, 2)
        if points and now - float(points[-1].get("ts", 0.0)) < 60.0:
            points[-1] = point
            return
        points.append(point)


def _analytics_point(point: dict[str, Any]) -> dict[str, Any]:
    temperature = _number(point.get("temperature"))
    if temperature is None:
        temperature = _number(point.get("room_temp"))
    outdoor_temperature = _number(point.get("outdoor_temperature"))
    if outdoor_temperature is None:
        outdoor_temperature = _number(point.get("outdoor_temp"))
    result: dict[str, Any] = {
        "ts": point.get("ts"),
        "temperature": temperature,
        "outdoor_temperature": outdoor_temperature,
        "mode": point.get("mode"),
        "source": point.get("source"),
        "skipped": point.get("skipped") is True,
        "skip_reason": point.get("skip_reason"),
    }
    q_solar = _number(point.get("q_solar"))
    if q_solar is not None:
        result["q_solar"] = q_solar
    estimated_power_fraction = _number(point.get("estimated_power_fraction"))
    if estimated_power_fraction is not None:
        result["estimated_power_fraction"] = estimated_power_fraction
    predicted = _number(point.get("predicted_temperature"))
    if predicted is None:
        predicted = _number(point.get("prediction"))
    if predicted is not None:
        result["predicted_temperature"] = predicted
    return result


def _forecast_points(plan: MpcPlan, outdoor: list[float]) -> list[dict[str, Any]]:
    points = []
    for index, temperature in enumerate(plan.temperatures[1:]):
        outdoor_temperature = outdoor[index] if index < len(outdoor) else None
        point: dict[str, Any] = {
            "offset_minutes": int(round((index + 1) * PLAN_DT_MINUTES)),
            "temperature": round(temperature, 2),
            "action": plan.actions[index] if index < len(plan.actions) else MODE_IDLE,
            "power_fraction": round(plan.power_fractions[index], 3) if index < len(plan.power_fractions) else 0.0,
        }
        if outdoor_temperature is not None:
            point["outdoor_temperature"] = round(outdoor_temperature, 2)
        points.append(point)
    return points


def _runtime_forecast(
    *,
    inputs: MpcInputs,
    cooling: bool,
    target: int,
    confidence: float,
    zone_plans: dict[int, MpcPlan],
    outdoor: list[float],
    ready: bool,
) -> RuntimeForecast:
    blocks = max(1, inputs.horizon_hours * int(60 / PLAN_DT_MINUTES))
    horizon_minutes = blocks * PLAN_DT_MINUTES
    series: list[dict[str, Any]] = []
    active_blocks: list[int] = []
    zone_runtime_minutes: dict[int, float] = {}
    zone_runtime_fraction: dict[int, float] = {}
    for group_id, plan in zone_plans.items():
        active_count = sum(1 for action in plan.actions[:blocks] if action != MODE_IDLE)
        runtime_minutes = round(active_count * PLAN_DT_MINUTES, 1)
        zone_runtime_minutes[group_id] = runtime_minutes
        zone_runtime_fraction[group_id] = round(runtime_minutes / horizon_minutes, 3)
    for block in range(blocks):
        block_actions = [plan.actions[block] for plan in zone_plans.values() if len(plan.actions) > block]
        action = _dominant_action(block_actions)
        if action != MODE_IDLE:
            active_blocks.append(block)
        power_values = [plan.power_fractions[block] for plan in zone_plans.values() if len(plan.power_fractions) > block]
        temperatures = [plan.temperatures[block + 1] for plan in zone_plans.values() if len(plan.temperatures) > block + 1]
        average_temperature = sum(temperatures) / len(temperatures) if temperatures else None
        control_temperature = (max(temperatures) if cooling else min(temperatures)) if temperatures else None
        point: dict[str, Any] = {
            "offset_minutes": int(round((block + 1) * PLAN_DT_MINUTES)),
            "target": target,
            "action": action,
            "power_fraction": round(max(power_values) if power_values else 0.0, 3),
        }
        if block < len(outdoor):
            point["outside_temperature"] = round(outdoor[block], 2)
        if average_temperature is not None:
            point["average_indoor_temperature"] = round(average_temperature, 2)
        if control_temperature is not None:
            point["control_temperature"] = round(control_temperature, 2)
        series.append(point)
    runtime_minutes = round(len(active_blocks) * PLAN_DT_MINUTES, 1)
    telemetry_quality = _telemetry_forecast_quality(inputs.input_quality.get("telemetry"), series)
    quality = {
        "status": "ok" if ready else "warming_up",
        "model_ready": ready,
        "confidence": confidence,
        "input_quality": dict(inputs.input_quality),
    }
    quality.update(telemetry_quality)
    return RuntimeForecast(
        horizon_hours=inputs.horizon_hours,
        step_minutes=PLAN_DT_MINUTES,
        runtime_minutes=runtime_minutes,
        runtime_fraction=round(runtime_minutes / horizon_minutes, 3),
        zone_runtime_minutes=zone_runtime_minutes,
        zone_runtime_fraction=zone_runtime_fraction,
        action_windows=_runtime_windows(series),
        series=series,
        quality=quality,
    )


def _telemetry_forecast_quality(telemetry: Any, series: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(telemetry, dict) or not telemetry.get("available"):
        return {
            "forecast_confidence": None,
            "telemetry_agreement": "unavailable",
            "telemetry_evidence": [],
        }
    planned_action = (series[0].get("action") if series else MODE_IDLE) or MODE_IDLE
    planned_conditioning = planned_action != MODE_IDLE
    observed = telemetry.get("observed_conditioning")
    base_confidence = _number(telemetry.get("confidence")) or 0.0
    evidence = list(telemetry.get("evidence") or [])
    if observed is None:
        return {
            "forecast_confidence": round(base_confidence * TELEMETRY_UNKNOWN_CONFIDENCE_FACTOR, 3),
            "telemetry_agreement": "unknown",
            "telemetry_evidence": evidence,
        }
    agreement = observed is planned_conditioning
    return {
        "forecast_confidence": round(
            base_confidence if agreement else base_confidence * TELEMETRY_DISAGREE_CONFIDENCE_FACTOR,
            3,
        ),
        "telemetry_agreement": "agree" if agreement else "disagree",
        "telemetry_evidence": evidence,
        "telemetry_observed_conditioning": observed,
        "telemetry_planned_conditioning": planned_conditioning,
    }


def _runtime_windows(series: list[dict[str, Any]]) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    powers: list[float] = []
    for point in series:
        action = point.get("action")
        offset = int(point.get("offset_minutes") or 0)
        if action == MODE_IDLE:
            if current is not None:
                current["avg_power_fraction"] = round(sum(powers) / len(powers), 3) if powers else 0.0
                windows.append(current)
                current = None
                powers = []
            continue
        if current is None or current.get("action") != action:
            if current is not None:
                current["avg_power_fraction"] = round(sum(powers) / len(powers), 3) if powers else 0.0
                windows.append(current)
            current = {
                "start_offset_minutes": max(0, offset - int(PLAN_DT_MINUTES)),
                "end_offset_minutes": offset,
                "action": action,
            }
            powers = []
        else:
            current["end_offset_minutes"] = offset
        powers.append(float(point.get("power_fraction") or 0.0))
    if current is not None:
        current["avg_power_fraction"] = round(sum(powers) / len(powers), 3) if powers else 0.0
        windows.append(current)
    return windows


def _annotate_solve_diagnostics(
    forecast: RuntimeForecast,
    *,
    started: float,
    optimizer_duration_ms: float,
    horizon_blocks: int,
    zone_count: int,
    input_forecast_points: int,
) -> None:
    forecast.quality.update({
        "solve_duration_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "optimizer_duration_ms": round(optimizer_duration_ms, 3),
        "horizon_blocks": horizon_blocks,
        "zone_count": zone_count,
        "series_points": len(forecast.series),
        "input_forecast_points": input_forecast_points,
        "solver_status": "ok",
    })


def _runtime_forecast_status(forecast: RuntimeForecast | None) -> dict[str, Any] | None:
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
            for group_id, minutes in forecast.zone_runtime_minutes.items()
        },
        "zone_runtime_fraction": {
            str(group_id): fraction
            for group_id, fraction in forecast.zone_runtime_fraction.items()
        },
        "action_windows": forecast.action_windows,
        "series": forecast.series,
        "quality": forecast.quality,
    }


def _optimize_plan(
    model: RCModel,
    room_temp: float,
    outdoor: list[float],
    heat_targets: list[float],
    cool_targets: list[float],
    *,
    can_heat: bool,
    can_cool: bool,
    humidity: float | None = None,
    humidity_assist_threshold: float = 60.0,
    q_solar: float = 0.0,
    comfort_weight: int = 70,
) -> MpcPlan:
    actions: list[str] = []
    temps = [room_temp]
    fractions: list[float] = []
    current = room_temp
    min_run_blocks = 2
    current_mode = MODE_IDLE
    blocks_in_mode = 0
    for index, outdoor_temp in enumerate(outdoor):
        heat_target = heat_targets[min(index, len(heat_targets) - 1)]
        cool_target = cool_targets[min(index, len(cool_targets) - 1)]
        available = [MODE_IDLE]
        if can_heat:
            available.append(MODE_HEATING)
        if can_cool:
            available.append(MODE_COOLING)
        if current_mode != MODE_IDLE and blocks_in_mode < min_run_blocks and current_mode in available:
            action = current_mode
        else:
            action = min(
                available,
                key=lambda candidate: _action_cost(
                    model,
                    candidate,
                    current,
                    outdoor[index : index + 6],
                    heat_targets[index : index + 6],
                    cool_targets[index : index + 6],
                    comfort_weight=comfort_weight,
                ),
            )
        target = cool_target if action == MODE_COOLING else heat_target
        fraction = _power_fraction(
            model,
            current,
            outdoor_temp,
            target,
            action,
            humidity=humidity,
            humidity_assist_threshold=humidity_assist_threshold,
            comfort_weight=comfort_weight,
        )
        if action == MODE_IDLE:
            fraction = 0.0
        elif fraction == 0.0:
            fraction = 1.0
        current = model.predict(current, outdoor_temp, action, PLAN_DT_MINUTES, power_fraction=fraction, q_solar=q_solar)
        temps.append(round(current, 2))
        actions.append(action)
        fractions.append(round(fraction, 3))
        if action == current_mode:
            blocks_in_mode += 1
        else:
            current_mode = action
            blocks_in_mode = 1
    return MpcPlan(actions=actions, temperatures=temps, power_fractions=fractions)


def _action_cost(
    model: RCModel,
    action: str,
    room_temp: float,
    outdoor: list[float],
    heat_targets: list[float],
    cool_targets: list[float],
    *,
    comfort_weight: int = 70,
) -> float:
    comfort_cost, energy_cost, _approach_rate = _mpc_tuning(comfort_weight)
    temp = room_temp
    total = 0.0
    for index, outdoor_temp in enumerate(outdoor or [room_temp]):
        heat_target = heat_targets[min(index, len(heat_targets) - 1)] if heat_targets else room_temp
        cool_target = cool_targets[min(index, len(cool_targets) - 1)] if cool_targets else room_temp
        fraction = 1.0 if action != MODE_IDLE and index < 2 else 0.0
        mode = action if index < 2 else MODE_IDLE
        temp = model.predict(temp, outdoor_temp, mode, PLAN_DT_MINUTES, power_fraction=fraction)
        if temp < heat_target:
            total += comfort_cost * (heat_target - temp) ** 2
        elif temp > cool_target:
            total += comfort_cost * (temp - cool_target) ** 2
        if mode != MODE_IDLE:
            total += energy_cost * fraction
    return total


def _power_fraction(
    model: RCModel,
    room_temp: float,
    outdoor_temp: float,
    target: float,
    action: str,
    *,
    humidity: float | None = None,
    humidity_assist_threshold: float = 60.0,
    comfort_weight: int = 70,
) -> float:
    if action == MODE_IDLE:
        return 0.0
    _comfort_cost, energy_cost, approach_rate = _mpc_tuning(comfort_weight)
    target = room_temp + approach_rate * (target - room_temp)
    full = model.predict(room_temp, outdoor_temp, action, PLAN_DT_MINUTES, power_fraction=1.0)
    idle = model.predict(room_temp, outdoor_temp, MODE_IDLE, PLAN_DT_MINUTES, power_fraction=0.0)
    span = full - idle
    if abs(span) < 0.01:
        return 1.0
    fraction = (target - idle) / span
    if fraction > 0:
        fraction = max(0.0, fraction - 0.02 * energy_cost)
    if action == MODE_COOLING and humidity is not None and humidity >= humidity_assist_threshold:
        fraction = max(fraction, 0.35)
    return _clamp(fraction, 0.0, 1.0)


def _room_mpc_target(room: AdaptiveRoom, baseline_target: int, cooling: bool, room_setpoint_targets: bool) -> float:
    if room_setpoint_targets and room.setpoint is not None:
        return float(room.setpoint)
    return float(baseline_target)


def _aggregate_room_target(
    controlled: list[tuple[AdaptiveRoom, ZoneThermalModel, float]],
    baseline_target: int,
    cooling: bool,
    room_setpoint_targets: bool,
) -> int:
    if not room_setpoint_targets:
        return baseline_target
    setpoints = [room.setpoint for room, _model, _temperature in controlled if room.setpoint is not None]
    if not setpoints:
        return baseline_target
    target = min(setpoints) if cooling else max(setpoints)
    return int(round(target))


def _mpc_tuning(comfort_weight: int) -> tuple[float, float, float]:
    weight = int(_clamp(float(comfort_weight), 0.0, 100.0))
    comfort_cost = max(1.0, 10.0 * weight / 70.0)
    energy_cost = max(1.0, (100.0 - weight) / 30.0)
    approach_rate = min(1.0, 0.2 + 0.8 * (weight / 70.0))
    return comfort_cost, energy_cost, approach_rate


def _expand_hourly(values: list[float] | tuple[float, ...], blocks: int, fallback: float) -> list[float]:
    return _expand_forecast(values, blocks, fallback, step_minutes=60.0)


def _expand_forecast(values: list[float] | tuple[float, ...], blocks: int, fallback: float, *, step_minutes: float) -> list[float]:
    if not values:
        return [fallback] * blocks
    normalized = [float(value) for value in values]
    per_value = max(1, int(round(max(PLAN_DT_MINUTES, step_minutes) / PLAN_DT_MINUTES)))
    result: list[float] = []
    for value in normalized:
        result.extend([value] * per_value)
        if len(result) >= blocks:
            break
    while len(result) < blocks:
        result.append(result[-1] if result else fallback)
    return result[:blocks]


def _smooth(current: float, value: float, samples: int) -> float:
    weight = 1.0 / min(12, samples + 1)
    return (current * (1.0 - weight)) + (value * weight)


def _dominant_action(actions: list[str]) -> str:
    for action in (MODE_COOLING, MODE_HEATING, MODE_IDLE):
        if action in actions:
            return action
    return MODE_IDLE


def _is_int(value: Any) -> bool:
    try:
        int(value)
    except (TypeError, ValueError):
        return False
    return True


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
