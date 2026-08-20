from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class ObservableClass(StrEnum):
    DETERMINISTIC_SEMANTIC = "DETERMINISTIC_SEMANTIC"
    STOCHASTIC_SEMANTIC = "STOCHASTIC_SEMANTIC"
    NOISY_NUMERIC = "NOISY_NUMERIC"
    TIMING_OR_RESOURCE = "TIMING_OR_RESOURCE"
    FLAKINESS_DIAGNOSTIC = "FLAKINESS_DIAGNOSTIC"
    ENVIRONMENT_DEPENDENT = "ENVIRONMENT_DEPENDENT"


class MethodId(StrEnum):
    METHOD_A = "METHOD_A_STRICT_CONJUNCTIVE"
    METHOD_B = "METHOD_B_HIERARCHICAL"
    METHOD_C = "METHOD_C_EVIDENCE_VECTOR_NONBINARY"
    NONE = "NO_METHOD_ESTABLISHED"


class ScoutStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE_DEGENERATE = "INELIGIBLE_DEGENERATE"
    INELIGIBLE_COORDINATE_AMBIGUITY = "INELIGIBLE_COORDINATE_AMBIGUITY"
    INELIGIBLE_UNIT_AMBIGUITY = "INELIGIBLE_UNIT_AMBIGUITY"
    INELIGIBLE_PARENT_SUPPORT = "INELIGIBLE_PARENT_SUPPORT"
    INELIGIBLE_NULL_INCOMPLETE = "INELIGIBLE_NULL_INCOMPLETE"
    INELIGIBLE_PROJECTION_UNJUSTIFIED = "INELIGIBLE_PROJECTION_UNJUSTIFIED"
    INELIGIBLE_OPERATION_DEPTH_NOT_APPLICABLE = "INELIGIBLE_OPERATION_DEPTH_NOT_APPLICABLE"
    INELIGIBLE_BASELINE_UNAVAILABLE = "INELIGIBLE_BASELINE_UNAVAILABLE"
    MATERIALIZATION_BLOCKED = "MATERIALIZATION_BLOCKED"


@dataclass(frozen=True)
class SeparationResult:
    observed_minus_null: float
    upper_tail_p: float
    lower_tail_p: float
    two_sided_p: float
    familywise_p: float
    robust_standardized_effect: float
    direction: str
    parent_count: int
    nested_parent_uncertainty: float
    null_pseudo_effect_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CurvatureResult:
    status: str
    sign_convention: str
    interior_indices: list[int]
    curvature: list[float]
    candidate_elbows: list[int]
    selected_elbow: int | None
    robust_trace_scale: float
    relative_prominence: float | None
    null_standardized_prominence: float | None
    bootstrap_stability: float | None
    endpoint_excluded: bool
    boundary_pinning: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScoutReceipt:
    scout_id: str
    domain_id: str
    status: ScoutStatus
    closure_authorized: bool
    checks: dict[str, bool | str]
    materialized_fraction: float
    effective_parent_count: float
    orbit_length_summary: dict[str, float] | None
    failure_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["schema_version"] = "1.0.0"
        value["status"] = self.status.value
        return value
