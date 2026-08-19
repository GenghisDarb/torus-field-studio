from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from torusbrot.geometry.channels import (
    closure_null_calibration,
    coordinate_permutation_null,
    field_projection_scores,
    signed_bidirectional_separation,
)
from torusbrot.geometry.scout import geometry_scout
from torusbrot.geometry.synthetic import SyntheticFixture, parent_and_null_ensembles
from torusbrot.tld.scoring import materialize_ladder, score_ladder


@dataclass(frozen=True)
class FixtureEvaluation:
    fixture_id: str
    field_kind: str
    ground_truth_present: bool
    expected_direction: str
    scout_status: str
    scout_receipt: dict[str, Any]
    projection_results: dict[str, dict[str, Any]]
    representation_status: str
    closure: dict[str, Any]
    fragility_supported: bool
    fragility_response: dict[str, float]
    baseline_excluded: bool
    method_a_positive: bool
    method_b_positive: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _projection_matrix(
    parents: list[np.ndarray], nulls: list[list[np.ndarray]]
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    observed_rows = [field_projection_scores(field) for field in parents]
    keys = tuple(observed_rows[0])
    observed = {key: np.asarray([row[key] for row in observed_rows]) for key in keys}
    null_values = {
        key: np.asarray(
            [[field_projection_scores(child)[key] for child in children] for children in nulls]
        )
        for key in keys
    }
    return observed, null_values


def _resample(field: np.ndarray) -> np.ndarray:
    if field.ndim == 2:
        return (
            field[::2, ::2].repeat(2, axis=0).repeat(2, axis=1)[: field.shape[0], : field.shape[1]]
        )
    if field.ndim >= 3 and field.shape[-1] in {2, 3}:
        return (
            field[::2, ::2].repeat(2, axis=0).repeat(2, axis=1)[: field.shape[0], : field.shape[1]]
        )
    return field.copy()


def _fragility(field: np.ndarray, seed: int) -> tuple[bool, dict[str, float]]:
    rng = np.random.default_rng(seed)
    baseline = field_projection_scores(field)
    null = coordinate_permutation_null(field, rng)
    if field.ndim == 2 and field.shape[0] == field.shape[1] and np.allclose(field, field.T):
        rotated = field[np.ix_(np.arange(len(field))[::-1], np.arange(len(field))[::-1])]
    else:
        rotated = np.rot90(field, axes=(0, 1))
    scale = max(float(np.std(field)), 1.0)
    noise = field + rng.normal(scale=0.05 * scale, size=field.shape)
    missing = field.copy()
    flat = (
        missing.reshape(-1, missing.shape[-1])
        if missing.ndim >= 3 and missing.shape[-1] in {2, 3}
        else missing.reshape(-1, 1)
    )
    selected = rng.choice(len(flat), size=max(1, len(flat) // 10), replace=False)
    flat[selected] = np.mean(flat, axis=0)
    variants = {
        "measurement_noise": noise,
        "coordinate_or_edge_shuffle": null,
        "orientation_rotation": rotated,
        "mask_dropout": missing,
        "resolution_reduction": _resample(field),
    }

    def distance(candidate: np.ndarray) -> float:
        scores = field_projection_scores(candidate)
        values = []
        for key, base in baseline.items():
            values.append(abs(scores[key] - base) / max(abs(base), 0.05))
        return float(np.median(values))

    response = {name: distance(value) for name, value in variants.items()}
    supported = (
        response["coordinate_or_edge_shuffle"] > response["measurement_noise"]
        and response["coordinate_or_edge_shuffle"] > response["orientation_rotation"]
    )
    return supported, response


def _baseline_exclusion(field: np.ndarray) -> bool:
    array = np.asarray(field, dtype=np.float64)
    scores = field_projection_scores(array)
    if array.ndim == 2 and array.shape[0] == array.shape[1] and np.allclose(array, array.T):
        density = float(np.mean(array))
        residual_strength = float(np.std(array - density))
        return residual_strength > 0.25
    if array.ndim >= 3 and array.shape[-1] in {2, 3}:
        scalar = np.linalg.norm(array, axis=-1)
    else:
        scalar = np.asarray(array)
        while scalar.ndim > 2:
            scalar = np.mean(scalar, axis=0)
    if scalar.ndim == 1:
        scalar = scalar[np.newaxis, :]
    additive = (
        np.mean(scalar, axis=0, keepdims=True)
        + np.mean(scalar, axis=1, keepdims=True)
        - np.mean(scalar)
    )
    residual = scalar - additive
    residual_scores = field_projection_scores(residual)
    base_magnitude = max(max(abs(value) for value in scores.values()), 0.05)
    residual_magnitude = max(abs(value) for value in residual_scores.values())
    return bool(residual_magnitude / base_magnitude >= 0.5)


def evaluate_fixture(fixture: SyntheticFixture, *, seed: int = 300) -> FixtureEvaluation:
    parents, nulls = parent_and_null_ensembles(fixture, seed=seed)
    scout = geometry_scout(
        domain_id=fixture.fixture_id.lower(),
        parent_fields=parents,
        null_children_by_parent=nulls,
        coordinates_complete=True,
        units_resolved=True,
        orientation_known=True,
        components_registered=True,
        mask_valid=True,
        support_sufficient=True,
        minimum_parents=8,
        projection_justified=True,
        boundary_known=True,
        operation_depth_applicable=False,
        geometric_scale_applicable=True,
        baseline_available=True,
    )
    observed, null_values = _projection_matrix(parents, nulls)
    projection_results = {
        key: signed_bidirectional_separation(
            observed[key], null_values[key], family_size=len(observed)
        ).to_dict()
        for key in observed
    }
    significant = [
        result["familywise_p"] <= 0.05 and abs(result["robust_standardized_effect"]) >= 1.0
        for result in projection_results.values()
    ]
    directions = {
        result["direction"]
        for result in projection_results.values()
        if result["direction"] != "ZERO"
    }
    representation_status = (
        "PASS"
        if len(projection_results) >= 2 and all(significant) and len(directions) == 1
        else "FAIL"
    )
    closure = closure_null_calibration(parents, nulls, seed=seed)
    fragility_supported, fragility_response = _fragility(fixture.field, seed)
    baseline_excluded = _baseline_exclusion(fixture.field)
    null_adequate = all(np.all(np.isfinite(values)) for values in null_values.values())
    scout_pass = scout.status.value == "ELIGIBLE"
    signed_primary = any(significant)
    closure_support = closure["local_closure_p"] <= 0.05
    method_a = bool(
        scout_pass
        and null_adequate
        and all(significant)
        and fragility_supported
        and representation_status == "PASS"
        and baseline_excluded
    )
    method_b = bool(
        scout_pass
        and null_adequate
        and signed_primary
        and (closure_support or fragility_supported)
        and representation_status == "PASS"
        and baseline_excluded
    )
    return FixtureEvaluation(
        fixture_id=fixture.fixture_id,
        field_kind=fixture.field_kind,
        ground_truth_present=fixture.binary_target_present,
        expected_direction=fixture.expected_direction,
        scout_status=scout.status.value,
        scout_receipt=scout.to_dict(),
        projection_results=projection_results,
        representation_status=representation_status,
        closure=closure,
        fragility_supported=fragility_supported,
        fragility_response=fragility_response,
        baseline_excluded=baseline_excluded,
        method_a_positive=method_a,
        method_b_positive=method_b,
    )


def historical_construct_benchmark(tld_i_reproduction: Path) -> dict[str, Any]:
    result = json.loads(tld_i_reproduction.read_text(encoding="utf-8"))
    rows = result["input_rows"]
    omega, _ = materialize_ladder(
        [float(row["value"]) for row in rows], [float(row["sigma"]) for row in rows]
    )
    baseline = score_ladder(omega, range(7, 14))
    rng = np.random.default_rng(300)
    order_scores = [
        score_ladder(omega[rng.permutation(len(omega))], range(7, 14)) for _ in range(64)
    ]
    noise_scores = [
        score_ladder(omega + rng.normal(scale=0.005, size=len(omega)), range(7, 14))
        for _ in range(64)
    ]
    core = {float(row["alpha_heal"]): row for row in result["notebook13"]["core"]}
    alpha_zero = core[0.0]
    healed = core[0.02]
    checks = {
        "baseline_closed_at_N10": baseline.winner_N == 10,
        "baseline_margin_exact": abs(baseline.margin - result["baseline"]["window_7_13"]["margin"])
        < 1e-12,
        "escape_distinguished": float(alpha_zero["escape_rate"]) >= 0.9,
        "unhealed_return_low": float(alpha_zero["return_rate_given_escape"]) <= 0.4,
        "healed_return_high": float(healed["return_rate_given_escape"]) >= 0.95,
        "order_controls_change_closure": sum(score.winner_N != 10 for score in order_scores) >= 48,
        "value_noise_robustness": sum(score.winner_N == 10 for score in noise_scores) >= 48,
    }
    return {
        "adapter_id": "canonical-tld-i-sequence-adapter-v1",
        "operator": "canonical_TLD_I_chi_RMS_closure",
        "historical_operator_preserved": True,
        "geometry_proxy_substituted": False,
        "baseline": baseline.to_dict(),
        "order_mutation_winner_counts": {
            str(value): sum(score.winner_N == value for score in order_scores)
            for value in range(7, 14)
        },
        "value_noise_N10_fraction": float(
            np.mean([score.winner_N == 10 for score in noise_scores])
        ),
        "escaped_alpha0": {
            "escape_rate": alpha_zero["escape_rate"],
            "return_rate": alpha_zero["return_rate_given_escape"],
        },
        "healed_alpha002": {
            "escape_rate": healed["escape_rate"],
            "return_rate": healed["return_rate_given_escape"],
        },
        "checks": checks,
        "construct_recovery_pass": all(checks.values()),
        "T_e": "NOT_APPLICABLE_HISTORICAL_TLD_I",
        "S_e": "NOT_APPLICABLE_HISTORICAL_TLD_I",
        "claim_boundary_preserved": True,
    }
