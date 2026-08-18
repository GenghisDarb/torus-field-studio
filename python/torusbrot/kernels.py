from __future__ import annotations

import cmath
import math
import random
import statistics
from dataclasses import dataclass, field
from typing import Any, Protocol

from .models import (
    ClassificationRules,
    DomainPack,
    FailureRecord,
    FieldPoint,
    MatchedNullPolicy,
    RunSpec,
)


class FieldKernel(Protocol):
    kernel_id: str
    schema_version: str

    def generate(self) -> list[FieldPoint]: ...


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _lerp(lower: float, upper: float, index: int, count: int) -> float:
    return lower if count <= 1 else lower + (upper - lower) * index / (count - 1)


@dataclass
class AnalyticKernel:
    specification: RunSpec
    kernel_id: str = "analytic.complex_power.cpu.v1"
    schema_version: str = "1.0.0"
    failures: list[FailureRecord] = field(default_factory=list, init=False)

    def generate(self) -> list[FieldPoint]:
        spec = self.specification
        params = spec.parameters
        power = float(params.get("power", 14))
        max_iterations = int(params.get("max_iterations", 80))
        escape_radius = float(params.get("escape_radius", 2.0))
        x_min, x_max = float(params.get("x_min", -1.35)), float(params.get("x_max", 1.35))
        y_min, y_max = float(params.get("y_min", -1.05)), float(params.get("y_max", 1.05))
        points: list[FieldPoint] = []
        for grid_y in range(spec.grid.height):
            y = _lerp(y_max, y_min, grid_y, spec.grid.height)
            for grid_x in range(spec.grid.width):
                x = _lerp(x_min, x_max, grid_x, spec.grid.width)
                z = 0j
                escaped_at: int | None = None
                trace: list[dict[str, float | int | str]] = []
                for iteration in range(max_iterations):
                    try:
                        z = z**power + complex(x, y)
                    except (OverflowError, ZeroDivisionError):
                        escaped_at = iteration + 1
                        break
                    if iteration < 12:
                        trace.append(
                            {
                                "step": iteration,
                                "stage": "orbit",
                                "magnitude": round(abs(z), 8),
                                "coherence": round(_clamp(1 - abs(z) / escape_radius), 8),
                            }
                        )
                    if abs(z) > escape_radius:
                        escaped_at = iteration + 1
                        break
                bounded = escaped_at is None
                iterations = max_iterations if bounded else escaped_at or max_iterations
                smooth = iterations / max_iterations
                points.append(
                    FieldPoint(
                        index=len(points),
                        grid_x=grid_x,
                        grid_y=grid_y,
                        x=round(x, 10),
                        y=round(y, 10),
                        classification="BOUNDED" if bounded else "ESCAPED",
                        eligible=True,
                        emerged=False,
                        separated_from_null=False,
                        closed=bounded,
                        survived=bounded,
                        escaped_from_reference=not bounded,
                        recovered=None,
                        winner_N=None,
                        T_e=None,
                        S_e=round(smooth, 8),
                        UI=round(smooth, 8),
                        NSS=0.0,
                        SEP=0.0,
                        rms_to_parent=0.0,
                        iterations=iterations,
                        parent_id="analytic-origin-z0",
                        null_policy_id="none",
                        trace=trace,
                    )
                )
        return points


def cyclic_coherence(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    span = max(values) - min(values)
    if span == 0:
        return 1.0
    differences = [
        abs(values[(index + 1) % len(values)] - value) for index, value in enumerate(values)
    ]
    return _clamp(1.0 - statistics.fmean(differences) / (1.25 * span))


def similarity(values: list[float], parent: list[float]) -> float:
    scale = max(statistics.pstdev(parent), 1e-9)
    squares = ((value - reference) ** 2 for value, reference in zip(values, parent))
    rms = math.sqrt(statistics.fmean(squares))
    return math.exp(-rms / scale)


def harmonic_winner(values: list[float]) -> int | None:
    if len(values) < 4:
        return None
    centered = [value - statistics.fmean(values) for value in values]
    upper = min(12, len(values) // 2)
    scores: list[tuple[float, int]] = []
    for frequency in range(1, upper + 1):
        amplitude = abs(
            sum(
                value * cmath.exp(-2j * math.pi * frequency * index / len(values))
                for index, value in enumerate(centered)
            )
        )
        scores.append((amplitude, frequency))
    return max(scores)[1]


@dataclass
class LadderKernel:
    specification: RunSpec
    domain: DomainPack
    null_policy: MatchedNullPolicy
    kernel_id: str = "torus.local_ladder.cpu.v1"
    schema_version: str = "1.0.0"
    failures: list[FailureRecord] = field(default_factory=list, init=False)

    def _nulls(self) -> list[list[float]]:
        if self.null_policy.kind != "preserve_multiset_shuffle":
            raise ValueError(f"Unsupported null policy: {self.null_policy.kind}")
        rng = random.Random(self.null_policy.seed)
        parent = list(self.domain.ladder)
        nulls: list[list[float]] = []
        for _ in range(self.null_policy.count):
            child = parent.copy()
            rng.shuffle(child)
            nulls.append(child)
        return nulls

    @staticmethod
    def _mutate(parent: list[float], strength: float, rng: random.Random) -> list[float]:
        result = parent.copy()
        order = list(range(len(parent)))
        swaps = round(strength * len(parent) * 1.5)
        for _ in range(swaps):
            left = rng.randrange(0, len(parent))
            right = rng.randrange(0, len(parent))
            order[left], order[right] = order[right], order[left]
        for index, source in enumerate(order):
            result[index] = parent[source]
        return result

    @staticmethod
    def _relax(current: list[float], parent: list[float], anchoring: float) -> list[float]:
        next_values: list[float] = []
        for index, value in enumerate(current):
            neighborhood = (
                current[index - 1] + 2 * value + current[(index + 1) % len(current)]
            ) / 4
            target = (1 - anchoring) * neighborhood + anchoring * parent[index]
            next_values.append(0.58 * value + 0.42 * target)
        return next_values

    def _point(
        self,
        grid_x: int,
        grid_y: int,
        order_mutation: float,
        anchoring: float,
        null_mean: float,
        null_stdev: float,
    ) -> FieldPoint:
        rules: ClassificationRules = self.specification.classification_rules
        parent = list(self.domain.ladder)
        point_seed = self.specification.seed + grid_x * 73_856_093 + grid_y * 19_349_663
        current = self._mutate(parent, order_mutation, random.Random(point_seed))
        initial_similarity = similarity(current, parent)
        escaped = initial_similarity < rules.escape_threshold
        trace: list[dict[str, float | int | str]] = []
        separation_flags: list[bool] = []
        emergence: int | None = None
        recovery_step: int | None = None
        recovery_steps = int(self.specification.parameters.get("recovery_steps", 12))
        for step in range(recovery_steps + 1):
            observed = cyclic_coherence(current)
            sep = observed - null_mean
            nss = sep / null_stdev
            current_similarity = similarity(current, parent)
            separated = sep >= rules.separation_threshold and nss >= rules.nss_threshold
            separation_flags.append(separated)
            if separated and emergence is None:
                emergence = step
            if escaped and recovery_step is None and current_similarity >= rules.recovery_threshold:
                recovery_step = step
            stage = "perturbation" if step == 0 else "recovery"
            if recovery_step == step:
                stage = "healing"
            trace.append(
                {
                    "step": step,
                    "stage": stage,
                    "coherence": round(observed, 8),
                    "null_mean": round(null_mean, 8),
                    "similarity": round(current_similarity, 8),
                }
            )
            current = self._relax(current, parent, anchoring)
        final = trace[-1]
        final_coherence = float(final["coherence"])
        final_similarity = float(final["similarity"])
        final_sep = final_coherence - null_mean
        final_nss = final_sep / null_stdev
        survival = (
            statistics.fmean(1.0 if flag else 0.0 for flag in separation_flags[emergence:])
            if emergence is not None
            else 0.0
        )
        separated_final = (
            final_sep >= rules.separation_threshold and final_nss >= rules.nss_threshold
        )
        closed = final_coherence >= 0.7
        survived = survival >= rules.survival_threshold
        recovered = recovery_step is not None if escaped else None
        if recovered:
            classification = "RECOVERED"
        elif escaped and final_similarity < rules.recovery_threshold:
            classification = "ESCAPED"
        elif separated_final and survived:
            classification = "BOUNDED"
        elif not separated_final:
            classification = "NULL_LIKE"
        else:
            classification = "UNRESOLVED"
        squares = ((value - reference) ** 2 for value, reference in zip(current, parent))
        rms = math.sqrt(statistics.fmean(squares))
        return FieldPoint(
            index=grid_y * self.specification.grid.width + grid_x,
            grid_x=grid_x,
            grid_y=grid_y,
            x=round(order_mutation, 10),
            y=round(anchoring, 10),
            classification=classification,
            eligible=True,
            emerged=emergence is not None,
            separated_from_null=separated_final,
            closed=closed,
            survived=survived,
            escaped_from_reference=escaped,
            recovered=recovered,
            winner_N=harmonic_winner(current),
            T_e=emergence,
            S_e=round(survival, 8),
            UI=round(final_coherence, 8),
            NSS=round(final_nss, 8),
            SEP=round(final_sep, 8),
            rms_to_parent=round(rms, 8),
            iterations=recovery_steps,
            parent_id=self.domain.domain_id,
            null_policy_id=f"{self.null_policy.kind}:{self.null_policy.count}:{self.null_policy.seed}",
            trace=trace,
        )

    def generate(self) -> list[FieldPoint]:
        nulls = self._nulls()
        if not nulls:
            raise ValueError("The local ladder engine requires at least one matched null child")
        null_coherences = [cyclic_coherence(child) for child in nulls]
        null_mean = statistics.fmean(null_coherences)
        null_stdev = max(statistics.pstdev(null_coherences), 1e-9)
        params = self.specification.parameters
        x_min, x_max = float(params.get("x_min", 0)), float(params.get("x_max", 1))
        y_min, y_max = float(params.get("y_min", 0)), float(params.get("y_max", 1))
        points: list[FieldPoint] = []
        for grid_y in range(self.specification.grid.height):
            anchoring = _lerp(y_max, y_min, grid_y, self.specification.grid.height)
            for grid_x in range(self.specification.grid.width):
                mutation = _lerp(x_min, x_max, grid_x, self.specification.grid.width)
                try:
                    point = self._point(grid_x, grid_y, mutation, anchoring, null_mean, null_stdev)
                    metrics = (
                        point.x,
                        point.y,
                        point.S_e,
                        point.UI,
                        point.NSS,
                        point.SEP,
                        point.rms_to_parent,
                    )
                    if not all(math.isfinite(value) for value in metrics):
                        raise ArithmeticError("kernel produced a nonfinite metric")
                    points.append(point)
                except Exception as error:  # noqa: BLE001 - failures are part of the artifact
                    failure_id = f"failure-point-{grid_y:04d}-{grid_x:04d}"
                    self.failures.append(
                        FailureRecord(
                            failure_id=failure_id,
                            category="KERNEL_EXCEPTION",
                            stage="field_generation",
                            message=f"{type(error).__name__}: {error}",
                            grid_x=grid_x,
                            grid_y=grid_y,
                            coordinate={"x": mutation, "y": anchoring},
                            recoverable=False,
                        )
                    )
                    points.append(
                        FieldPoint(
                            index=grid_y * self.specification.grid.width + grid_x,
                            grid_x=grid_x,
                            grid_y=grid_y,
                            x=round(mutation, 10),
                            y=round(anchoring, 10),
                            classification="UNRESOLVED",
                            eligible=False,
                            emerged=False,
                            separated_from_null=False,
                            closed=False,
                            survived=False,
                            escaped_from_reference=False,
                            recovered=None,
                            winner_N=None,
                            T_e=None,
                            S_e=0.0,
                            UI=0.0,
                            NSS=0.0,
                            SEP=0.0,
                            rms_to_parent=0.0,
                            iterations=0,
                            parent_id=self.domain.domain_id,
                            null_policy_id=(
                                f"{self.null_policy.kind}:{self.null_policy.count}:"
                                f"{self.null_policy.seed}"
                            ),
                            trace=[
                                {
                                    "step": 0,
                                    "stage": "failure",
                                    "coherence": 0.0,
                                }
                            ],
                            failure_id=failure_id,
                        )
                    )
        return points

    def null_registry(self) -> list[dict[str, Any]]:
        return [
            {
                "null_id": f"null-{index:03d}",
                "policy": self.null_policy.kind,
                "seed": self.null_policy.seed,
                "ladder": child,
                "coherence": round(cyclic_coherence(child), 8),
            }
            for index, child in enumerate(self._nulls())
        ]
