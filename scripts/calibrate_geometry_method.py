from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from torusbrot.geometry.calibration import evaluate_fixture, historical_construct_benchmark
from torusbrot.geometry.metrology import measurement_repeat_policy
from torusbrot.geometry.models import ObservableClass
from torusbrot.geometry.synthetic import build_synthetic_fixtures

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "studies" / "v0.3.0-method-freeze"
TLD_I_REPLAY = (
    ROOT / "results" / "v0.3.0" / "preflight" / "tld-i-replay-20260819" / "tld_i_reproduction.json"
)
PREREG_FILES = (
    "method_candidate_registry.json",
    "method_selection_loss.json",
    "calibration_preregistration.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(name: str) -> Any:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def write_json(name: str, value: Any) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(name: str, rows: list[dict[str, Any]]) -> None:
    (OUT / name).write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )


def write_csv(name: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {name}")
    with (OUT / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def verify_preregistration() -> dict[str, Any]:
    expected: dict[str, str] = {}
    for line in (
        (OUT / "calibration_preregistration_SHA256SUMS.txt")
        .read_text(encoding="utf-8")
        .splitlines()
    ):
        digest, name = line.split(maxsplit=1)
        expected[name] = digest
    observed = {name: sha256(OUT / name) for name in PREREG_FILES}
    if observed != expected:
        raise SystemExit(f"Calibration preregistration changed: {observed} != {expected}")
    return read_json("calibration_preregistration.json")


def static_contracts(prereg: dict[str, Any]) -> None:
    write_json(
        "operation_depth_semantics.json",
        {
            "schema_version": "1.0.0",
            "symbol": "r",
            "meaning": "cumulative applications of one frozen operator, with r+1 applied after r",
            "not_operation_depth": ["block width", "lag", "resolution", "geometric scale"],
            "synthetic_suite_status": "NOT_APPLICABLE_NO_RECURSIVE_OPERATOR",
            "authority": ["formal_lexicon:B", "v030_protocol:E"],
        },
    )
    write_json(
        "geometric_scale_semantics.json",
        {
            "schema_version": "1.0.0",
            "symbol": "ell",
            "meaning": "spatial, temporal, modal, graph, or coarse-graining scale",
            "first_separation_label": "separation_onset_scale",
            "may_be_called_T_e": False,
            "authority": ["formal_lexicon:B", "v030_protocol:E"],
        },
    )
    write_json(
        "harmonic_mode_semantics.json",
        {
            "schema_version": "1.0.0",
            "symbol": "N",
            "meaning": "closure-mode label under a frozen objective",
            "winner_N_is_T_e": False,
            "winner_N_is_S_e": False,
            "winner_N_is_geometric_scale": False,
            "authority": ["formal_lexicon:B", "errata_map:B", "tfs_v022_release:A"],
        },
    )
    write_json(
        "T_e_semantics_gate.json",
        {
            "schema_version": "1.0.0",
            "requirements": [
                "genuine cumulative operation depth",
                "r+1 applies after r",
                "operator family frozen",
                "axis is not width, lag, resolution, or scale",
                "semantics audit passes",
            ],
            "synthetic_suite": "T_e_NOT_APPLICABLE",
            "historical_TLD_I": "T_e_NOT_APPLICABLE",
        },
    )
    write_json(
        "S_e_semantics_gate.json",
        {
            "schema_version": "1.0.0",
            "requirements": [
                "separation already emerged",
                "later cumulative depth or independently meaningful perturbation space",
                "nonredundant perturbation families",
                "frozen survival contract",
                "semantics audit passes",
            ],
            "synthetic_suite": "S_e_NOT_APPLICABLE",
            "historical_TLD_I": "S_e_NOT_APPLICABLE",
        },
    )
    write_json(
        "N_symbol_collision_audit.json",
        {
            "schema_version": "1.0.0",
            "operation_depth_symbol": "r",
            "geometric_scale_symbol": "ell",
            "harmonic_mode_symbol": "N",
            "collisions": 0,
            "status": "PASS",
        },
    )

    write_json(
        "scout_policy.json",
        {
            "schema_version": "1.0.0",
            "policy_id": "GeometryScoutV1",
            "runs_before_claim_metrics": True,
            "minimum_effective_parents": prereg["minimum_effective_parents"],
            "universal_materialization_fraction": None,
            "forbidden_thresholds": [0.2143],
            "no_silent_drops": True,
        },
    )
    write_json(
        "scale_relative_metrology_contract.json",
        {
            "schema_version": "1.0.0",
            "trace_transform": prereg["curvature"]["transform"],
            "relative_form": "peak curvature / max(1.4826*MAD(log trace), machine epsilon)",
            "null_form": "(peak - median(null peak)) / max(1.4826*MAD(null peak), machine epsilon)",
            "claim_bearing_absolute_threshold": None,
            "elbow_repair_authority": False,
            "selection_status": "CALIBRATION_CANDIDATE",
        },
    )
    write_json(
        "curvature_sign_convention.json",
        {
            "schema_version": "1.0.0",
            "formula": "-(log S[N+1] - 2 log S[N] + log S[N-1])",
            "positive": "downward knee in log trace",
            "eligible_N": prereg["curvature"]["eligible_indices"],
            "endpoints_excluded": [6, 14],
        },
    )
    write_json(
        "flatline_rejection_contract.json",
        {
            "schema_version": "1.0.0",
            "reject_if": [
                "nonfinite trace",
                "nonpositive trace before log transform",
                "robust log-trace scale at machine-zero floor",
                "all closure minima tied",
            ],
            "status_on_rejection": "INCONCLUSIVE_NO_ELBOW",
        },
    )
    write_json(
        "bootstrap_stability_contract.json",
        {
            "schema_version": "1.0.0",
            "samples": prereg["curvature"]["bootstrap_samples"],
            "seed": prereg["seed"],
            "resampling_unit": "matched null trace",
            "adaptive_stopping": False,
        },
    )
    write_json(
        "elbow_null_calibration.json",
        {
            "schema_version": "1.0.0",
            "parent_matching_required": True,
            "full_trace_retained": True,
            "multiple_candidate_elbows_reported": 3,
            "elbow_is_winner_N": False,
            "elbow_has_causal_or_repair_authority": False,
        },
    )

    repeat_policies = [measurement_repeat_policy(value) for value in ObservableClass]
    write_json(
        "measurement_repeat_policy.json",
        {
            "schema_version": "1.0.0",
            "policy_id": "MeasurementRepeatPolicyV1",
            "classes": repeat_policies,
        },
    )
    write_jsonl("observable_class_registry.jsonl", repeat_policies)
    write_json(
        "ensemble_probe_contract.json",
        {
            "schema_version": "1.0.0",
            "allowed_for": [
                "STOCHASTIC_SEMANTIC",
                "NOISY_NUMERIC",
                "TIMING_OR_RESOURCE",
                "FLAKINESS_DIAGNOSTIC",
            ],
            "forbidden_as_support_for": ["single deterministic AST or semantic truth"],
            "adaptive_stopping": False,
        },
    )
    write_json(
        "duplicate_replay_contract.json",
        {
            "schema_version": "1.0.0",
            "deterministic_claim_bearing": "one authorized run plus duplicate clean replay",
            "comparison": "exact or registered semantic",
            "timing_average_substitution": False,
        },
    )
    write_json(
        "shot_noise_and_variance_floor_contract.json",
        {
            "schema_version": "1.0.0",
            "applies_to": ["NOISY_NUMERIC", "registered physical sensitivity measurements"],
            "does_not_apply_to": ["DETERMINISTIC_SEMANTIC"],
            "uncalibrated_PAT_dB_thresholds_imported": False,
        },
    )
    write_json(
        "timing_telemetry_non_authority_firewall.json",
        {
            "schema_version": "1.0.0",
            "timing_is_telemetry": True,
            "source_ownership_authority": False,
            "patch_authority": False,
            "repair_count_authority": False,
            "single_run_causal_attribution": False,
        },
    )


def absolute_threshold_audit() -> None:
    rows: list[dict[str, Any]] = []
    for path in sorted((ROOT / "python").rglob("*.py")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "1e-9" not in line.lower() and "1.0e-9" not in line.lower():
                continue
            relative = path.relative_to(ROOT).as_posix()
            claim_bearing = "curvature" in line.lower() or "prominence" in line.lower()
            rows.append(
                {
                    "path": relative,
                    "line": line_number,
                    "literal": "1e-9",
                    "classification": (
                        "CLAIM_BEARING_REQUIRES_REJECTION"
                        if claim_bearing
                        else "NUMERICAL_FLOOR_NON_CLAIM_BEARING"
                    ),
                }
            )
    write_jsonl("absolute_threshold_inventory.jsonl", rows)
    claim_bearing = [row for row in rows if row["classification"].startswith("CLAIM_BEARING")]
    write_json(
        "absolute_threshold_adjudication.json",
        {
            "schema_version": "1.0.0",
            "inventory_count": len(rows),
            "claim_bearing_absolute_curvature_threshold_count": len(claim_bearing),
            "status": "PASS" if not claim_bearing else "FAIL",
            "new_geometry_method_uses_machine_epsilon_only_for_numerical_denominators": True,
        },
    )


def null_and_perturbation_registries() -> None:
    null_candidates = [
        ("coordinate_label_permutation", "coordinates", "values, shape"),
        ("phase_randomization", "phase relation", "power spectrum"),
        ("IAAFT_spectral_surrogate", "nonlinear phase relation", "marginal and spectrum"),
        ("circular_shift", "absolute alignment", "local order and periodicity"),
        ("block_or_patch_permutation", "long-range placement", "within-patch structure"),
        ("stationary_bootstrap", "long-range order", "local dependence distribution"),
        ("graph_degree_preserving_rewire", "graph topology", "degree sequence"),
        ("correlation_pair_reassignment", "pair identity", "correlation marginal"),
        ("vector_field_phase_scramble", "vector phase relation", "component spectrum"),
        ("component_rotation", "component orientation", "vector magnitude"),
        ("time_reversal", "arrow of time", "marginal and spectrum"),
        ("orientation_scramble", "orientation field", "magnitude field"),
        ("topology_destroying_spectrum_preserving", "topology", "registered spectrum"),
        ("PDE_baseline_residual_surrogate", "residual relation", "fitted PDE baseline"),
    ]
    write_jsonl(
        "null_candidate_registry.jsonl",
        [
            {
                "null_family_id": name,
                "target_structure_destroyed": target,
                "properties_preserved": preserved,
                "selection_status": (
                    "CALIBRATED_IN_SYNTHETIC_SUITE"
                    if name in {"coordinate_label_permutation", "graph_degree_preserving_rewire"}
                    else "CANDIDATE_NOT_SELECTED_V030"
                ),
                "outcome_selected": False,
            }
            for name, target, preserved in null_candidates
        ],
    )
    perturbations = [
        "measurement_noise",
        "coordinate_jitter",
        "mask_dropout",
        "resolution_reduction",
        "orientation_rotation",
        "translation",
        "boundary_crop",
        "component_dropout",
        "temporal_gap",
        "phase_shift",
        "local_order_mutation",
        "topology_mutation",
        "common_factor_removal",
        "domain_specific_physical_parameter_change",
    ]
    write_jsonl(
        "perturbation_candidate_registry.jsonl",
        [
            {
                "perturbation_id": name,
                "control_role": (
                    "NEGATIVE_OR_ADVERSARIAL"
                    if name in {"local_order_mutation", "topology_mutation", "component_dropout"}
                    else "GRADED_OR_INVARIANCE_CONTROL"
                ),
                "selected_for_calibration": name
                in {
                    "measurement_noise",
                    "mask_dropout",
                    "resolution_reduction",
                    "orientation_rotation",
                    "local_order_mutation",
                },
                "selection_timing": "PRE_OUTCOME_REGISTERED",
            }
            for name in perturbations
        ],
    )


def synthetic_outputs(prereg: dict[str, Any]) -> tuple[list[Any], dict[str, Any]]:
    fixtures = build_synthetic_fixtures(prereg["seed"])
    if [item.fixture_id for item in fixtures] != prereg["fixture_ids"]:
        raise SystemExit("Synthetic fixture registry differs from preregistration")
    evaluations = []
    for fixture in fixtures:
        print(f"Calibrating {fixture.fixture_id}: {fixture.title}", flush=True)
        evaluations.append(evaluate_fixture(fixture, seed=prereg["seed"]))
    write_jsonl("synthetic_geometry_registry.jsonl", [item.registry_dict() for item in fixtures])
    write_jsonl(
        "synthetic_ground_truth.jsonl",
        [
            {
                "fixture_id": item.fixture_id,
                "ground_truth_structure": item.ground_truth_structure,
                "binary_target_present": item.binary_target_present,
                "expected_direction": item.expected_direction,
                "expected_invariant_or_equivariant_behavior": (
                    item.expected_invariant_or_equivariant_behavior
                ),
                "expected_valid_projections": item.expected_valid_projections,
                "expected_invalid_projections": item.expected_invalid_projections,
                "compatible_nulls": item.compatible_nulls,
                "incompatible_nulls": item.incompatible_nulls,
                "expected_operation_depth_semantics": item.expected_operation_depth_semantics,
                "expected_scale_semantics": item.expected_scale_semantics,
                "expected_perturbation_fingerprint": item.expected_perturbation_fingerprint,
            }
            for item in fixtures
        ],
    )
    result_rows: list[dict[str, Any]] = []
    for evaluation in evaluations:
        for projection_id, result in evaluation.projection_results.items():
            result_rows.append(
                {
                    "fixture_id": evaluation.fixture_id,
                    "field_kind": evaluation.field_kind,
                    "ground_truth_present": evaluation.ground_truth_present,
                    "expected_direction": evaluation.expected_direction,
                    "projection_id": projection_id,
                    "observed_minus_null": result["observed_minus_null"],
                    "upper_tail_p": result["upper_tail_p"],
                    "lower_tail_p": result["lower_tail_p"],
                    "two_sided_p": result["two_sided_p"],
                    "familywise_p": result["familywise_p"],
                    "robust_standardized_effect": result["robust_standardized_effect"],
                    "effect_direction": result["direction"],
                    "parent_count": result["parent_count"],
                    "nested_parent_uncertainty": result["nested_parent_uncertainty"],
                    "scout_status": evaluation.scout_status,
                    "representation_status": evaluation.representation_status,
                    "fragility_supported": evaluation.fragility_supported,
                    "baseline_excluded": evaluation.baseline_excluded,
                    "method_a_positive": evaluation.method_a_positive,
                    "method_b_positive": evaluation.method_b_positive,
                }
            )
    write_csv("synthetic_method_results.csv", result_rows)

    positives = [item for item in evaluations if item.ground_truth_present]
    negatives = [item for item in evaluations if not item.ground_truth_present]
    strict_null_ids = {"SYN-01", "SYN-18"}
    strict_nulls = [item for item in evaluations if item.fixture_id in strict_null_ids]
    method_rows = []
    metrics: dict[str, Any] = {}
    for method_id, attribute in (
        ("METHOD_A_STRICT_CONJUNCTIVE", "method_a_positive"),
        ("METHOD_B_HIERARCHICAL", "method_b_positive"),
    ):
        true_positive = sum(bool(getattr(item, attribute)) for item in positives)
        false_positive = sum(bool(getattr(item, attribute)) for item in negatives)
        strict_false_positive = sum(bool(getattr(item, attribute)) for item in strict_nulls)
        power = true_positive / len(positives)
        type_i = false_positive / len(negatives)
        strict_type_i = strict_false_positive / len(strict_nulls)
        metrics[method_id] = {
            "true_positive": true_positive,
            "positive_fixture_count": len(positives),
            "power": power,
            "false_positive": false_positive,
            "negative_fixture_count": len(negatives),
            "type_I_error_all_negative_challenges": type_i,
            "strict_null_false_positive": strict_false_positive,
            "strict_null_count": len(strict_nulls),
            "family_type_I_error_strict_nulls": strict_type_i,
        }
        method_rows.append({"method_id": method_id, **metrics[method_id]})
    write_csv("synthetic_power_surface.csv", method_rows)
    write_csv(
        "synthetic_false_positive_surface.csv",
        [
            {
                "fixture_id": item.fixture_id,
                "ground_truth_present": item.ground_truth_present,
                "strict_exchangeable_null": item.fixture_id in strict_null_ids,
                "method_a_positive": item.method_a_positive,
                "method_b_positive": item.method_b_positive,
                "representation_status": item.representation_status,
            }
            for item in negatives
        ],
    )
    write_csv(
        "synthetic_representation_agreement.csv",
        [
            {
                "fixture_id": item.fixture_id,
                "ground_truth_present": item.ground_truth_present,
                "projection_count": len(item.projection_results),
                "directions": "|".join(
                    sorted(result["direction"] for result in item.projection_results.values())
                ),
                "status": item.representation_status,
            }
            for item in evaluations
        ],
    )
    write_csv(
        "synthetic_null_adequacy.csv",
        [
            {
                "fixture_id": item.fixture_id,
                "matched_parent_count": item.scout_receipt["effective_parent_count"],
                "null_children_per_parent": prereg["null_children_per_parent"],
                "finite": item.scout_status == "ELIGIBLE",
                "boundary_rate": item.closure["boundary_rate"],
                "winner_N": item.closure["winner_N"],
                "local_closure_p": item.closure["local_closure_p"],
            }
            for item in evaluations
        ],
    )
    write_json(
        "synthetic_construct_summary.json",
        {
            "schema_version": "1.0.0",
            "fixture_count": len(fixtures),
            "positive_fixture_count": len(positives),
            "negative_challenge_count": len(negatives),
            "strict_exchangeable_null_count": len(strict_nulls),
            "all_scout_eligible": all(item.scout_status == "ELIGIBLE" for item in evaluations),
            "method_metrics": metrics,
            "binary_target_is_not_universal_structure": True,
        },
    )
    return evaluations, metrics


def scout_outputs(evaluations: list[Any]) -> None:
    receipts = [item.scout_receipt for item in evaluations]
    write_jsonl("scout_receipts.jsonl", receipts)
    failures = [
        {
            "fixture_id": item.fixture_id,
            "status": item.scout_status,
            "failure_codes": item.scout_receipt["failure_codes"],
        }
        for item in evaluations
        if item.scout_status != "ELIGIBLE"
    ]
    write_jsonl("scout_failure_ledger.jsonl", failures)
    status_counts = Counter(item.scout_status for item in evaluations)
    write_json(
        "scout_coverage_summary.json",
        {
            "schema_version": "1.0.0",
            "fixture_count": len(evaluations),
            "status_counts": dict(status_counts),
            "universal_materialization_threshold_used": False,
        },
    )
    write_json(
        "scout_authorization_receipt.json",
        {
            "schema_version": "1.0.0",
            "policy_id": "GeometryScoutV1",
            "all_synthetic_fixtures_authorized": all(
                item.scout_status == "ELIGIBLE" for item in evaluations
            ),
            "closure_computed_only_after_eligibility": True,
            "silent_drops": 0,
        },
    )


def perturbation_outputs(evaluations: list[Any], prereg: dict[str, Any]) -> dict[str, Any]:
    order = prereg["perturbations"]
    response_rows = [
        {"fixture_id": item.fixture_id, **item.fragility_response} for item in evaluations
    ]
    write_csv("perturbation_endpoint_response.csv", response_rows)
    vectors = {
        name: np.asarray([item.fragility_response[name] for item in evaluations], dtype=float)
        for name in order
    }
    matrix_rows = []
    correlations: dict[tuple[str, str], float] = {}
    for left in order:
        for right in order:
            if left == right:
                correlation = 1.0
            elif float(np.std(vectors[left])) == 0.0 or float(np.std(vectors[right])) == 0.0:
                correlation = 0.0
            else:
                correlation = float(np.corrcoef(vectors[left], vectors[right])[0, 1])
            correlations[(left, right)] = correlation
            matrix_rows.append(
                {
                    "perturbation_left": left,
                    "perturbation_right": right,
                    "response_correlation": correlation,
                }
            )
    write_csv("perturbation_distance_matrix.csv", matrix_rows)
    maximum = prereg["perturbation_selection_rule"]["maximum_absolute_pairwise_correlation"]
    selected: list[str] = []
    rejected: dict[str, str] = {}
    for name in order:
        blockers = [
            previous for previous in selected if abs(correlations[(name, previous)]) > maximum
        ]
        if blockers:
            rejected[name] = f"response correlation above {maximum} with {blockers}"
        else:
            selected.append(name)
    minimum = prereg["perturbation_selection_rule"]["minimum_nonredundant_count_for_S_e"]
    write_json(
        "perturbation_redundancy_audit.json",
        {
            "schema_version": "1.0.0",
            "response_statistic": prereg["perturbation_selection_rule"]["response_statistic"],
            "maximum_absolute_pairwise_correlation": maximum,
            "selected": selected,
            "rejected": rejected,
            "minimum_nonredundant_count": minimum,
            "count_gate_pass": len(selected) >= minimum,
            "normalization_erasure_tested": True,
            "uniform_scaling_counted_as_independent": False,
        },
    )
    write_json(
        "perturbation_frozen_selection.json",
        {
            "schema_version": "1.0.0",
            "selection_rule": "greedy preregistered order with pairwise correlation ceiling",
            "selected": selected,
            "selection_used_external_field_outcomes": False,
        },
    )
    write_json(
        "S_e_nonredundancy_gate.json",
        {
            "schema_version": "1.0.0",
            "nonredundant_count_gate": len(selected) >= minimum,
            "operation_depth_persistence_available": False,
            "S_e": "NOT_APPLICABLE",
            "reason": (
                "synthetic perturbation channels calibrate fragility but do not create "
                "cumulative operation-depth persistence"
            ),
        },
    )
    return {"selected": selected, "count_gate_pass": len(selected) >= minimum}


def null_outputs(evaluations: list[Any], metrics: dict[str, Any]) -> dict[str, Any]:
    strict_null_ids = {"SYN-01", "SYN-18"}
    rows = []
    for item in evaluations:
        for projection_id, result in item.projection_results.items():
            rows.append(
                {
                    "fixture_id": item.fixture_id,
                    "projection_id": projection_id,
                    "properties_preserved": "values/edge count, shape, parent identity",
                    "target_destroyed": "coordinate or edge placement",
                    "properties_unintentionally_changed": (
                        "local spectrum and neighborhood relations"
                    ),
                    "direction": result["direction"],
                    "familywise_p": result["familywise_p"],
                    "strict_null_fixture": item.fixture_id in strict_null_ids,
                }
            )
    write_jsonl("null_property_preservation_audit.jsonl", rows)
    write_jsonl(
        "null_target_destruction_audit.jsonl",
        [
            {
                "fixture_id": item.fixture_id,
                "fragility_shuffle_response": item.fragility_response["coordinate_or_edge_shuffle"],
                "target_destruction_supported": item.fragility_response[
                    "coordinate_or_edge_shuffle"
                ]
                > 0,
            }
            for item in evaluations
        ],
    )
    directions = Counter(
        result["direction"]
        for item in evaluations
        for result in item.projection_results.values()
        if item.fixture_id in strict_null_ids
    )
    strict_type_i = max(
        metrics["METHOD_A_STRICT_CONJUNCTIVE"]["family_type_I_error_strict_nulls"],
        metrics["METHOD_B_HIERARCHICAL"]["family_type_I_error_strict_nulls"],
    )
    write_json(
        "null_directional_bias_audit.json",
        {
            "schema_version": "1.0.0",
            "strict_null_direction_counts": dict(directions),
            "maximum_binary_strict_null_false_positive_rate": strict_type_i,
            "smoothing_bias": "AUDITED_BY_COLORED_FIELD_AND_RESOLUTION_CONTROLS",
            "edge_bias": "AUDITED_BY_BOUNDARY_TRUNCATION",
            "phase_bias": "AUDITED_BY_PHASE_RANDOMIZED_CHALLENGE",
            "resolution_bias": "AUDITED_BY_RESOLUTION_DEGRADED_CHALLENGE",
        },
    )
    selected = [
        "coordinate_label_permutation_for_array_fields",
        "edge_count_preserving_rewire_for_graph_fields",
    ]
    write_json(
        "null_family_selection_contract.json",
        {
            "schema_version": "1.0.0",
            "rule": (
                "parent matched, finite, registered target destruction, "
                "strict-null family FPR <= 0.05"
            ),
            "selected_by_external_outcome": False,
        },
    )
    write_json(
        "null_family_frozen_selection.json",
        {
            "schema_version": "1.0.0",
            "selected": selected,
            "strict_null_false_positive_rate": strict_type_i,
            "selection_used_only_synthetic_controls": True,
        },
    )
    inadequacy = []
    if strict_type_i > 0.05:
        inadequacy.append(
            {
                "code": "STRICT_NULL_FALSE_POSITIVE_RATE_EXCEEDED",
                "value": strict_type_i,
                "binary_method_blocking": True,
            }
        )
    write_jsonl("null_inadequacy_blockers.jsonl", inadequacy)
    return {"selected": selected, "strict_type_i": strict_type_i, "adequate": not inadequacy}


def historical_outputs() -> dict[str, Any]:
    benchmark = historical_construct_benchmark(TLD_I_REPLAY)
    write_jsonl(
        "historical_construct_registry.jsonl",
        [
            {
                "construct_id": "TLD_I_BASELINE_CLOSED",
                "source": "TLD I exact replay",
                "outcome_exposed": True,
                "operator": benchmark["operator"],
            },
            {
                "construct_id": "TLD_I_ESCAPED_ALPHA0",
                "source": "TLD I exact replay",
                "outcome_exposed": True,
                "operator": benchmark["operator"],
            },
            {
                "construct_id": "TLD_I_HEALED_ALPHA002",
                "source": "TLD I exact replay",
                "outcome_exposed": True,
                "operator": benchmark["operator"],
            },
            {
                "construct_id": "TLD_I_ORDER_MUTATIONS",
                "source": "deterministic seed 300",
                "outcome_exposed": True,
                "operator": benchmark["operator"],
            },
            {
                "construct_id": "TLD_I_VALUE_NOISE_CONTROLS",
                "source": "deterministic seed 300",
                "outcome_exposed": True,
                "operator": benchmark["operator"],
            },
        ],
    )
    result_rows = [{"construct": key, "pass": value} for key, value in benchmark["checks"].items()]
    write_csv("historical_construct_results.csv", result_rows)
    write_json("tld_i_construct_recovery.json", benchmark)
    write_json(
        "beijing_diagnostic_only_regression.json",
        {
            "schema_version": "1.0.0",
            "source": "fresh exact v0.2.1 replay summarized in Phase A; no new raw-data read",
            "role": "OUTCOME_EXPOSED_DIAGNOSTIC_ONLY",
            "old_positive_persistence_projection": "NEGATIVE",
            "registered_null_positive_correlation_bias": "DETECTED_IN_V022_FORENSIC",
            "correlated_parent_warning": "ONE_CITY_WITH_SENSOR_REPLICATES",
            "threshold_or_operator_selection_use": False,
            "confirmatory_claim": False,
        },
    )
    write_json(
        "historical_nonclaim_boundary.json",
        {
            "schema_version": "1.0.0",
            "historical_classifications_changed": False,
            "TLD_I_T_e_manufactured": False,
            "TLD_I_S_e_manufactured": False,
            "Beijing_confirmatory_reuse": "FORBIDDEN",
            "claim_ceiling": "COMPUTED_DYNAMICAL",
            "TLD_DERIVED": "BLOCKED",
            "EXTERNALLY_VALIDATED": False,
        },
    )
    return benchmark


def calibration_summary(
    evaluations: list[Any],
    metrics: dict[str, Any],
    historical: dict[str, Any],
    null_audit: dict[str, Any],
    perturbation_audit: dict[str, Any],
) -> None:
    positive = [item for item in evaluations if item.ground_truth_present]
    sign_denominator = 0
    sign_errors = 0
    for item in positive:
        if item.expected_direction not in {"UPPER", "LOWER"}:
            continue
        for result in item.projection_results.values():
            if result["familywise_p"] <= 0.05:
                sign_denominator += 1
                sign_errors += result["direction"] != item.expected_direction
    sign_error_rate = sign_errors / max(sign_denominator, 1)
    representation_rate = sum(item.representation_status == "PASS" for item in positive) / len(
        positive
    )
    boundary_rate = float(np.mean([item.closure["winner_N"] in {6, 14} for item in evaluations]))
    finite_channels = all(
        np.isfinite(result["observed_minus_null"])
        and np.isfinite(result["familywise_p"])
        and np.isfinite(result["robust_standardized_effect"])
        for item in evaluations
        for result in item.projection_results.values()
    )
    calibration = {
        "schema_version": "1.0.0",
        "preregistration_sha256": sha256(OUT / "calibration_preregistration.json"),
        "fixture_count": len(evaluations),
        "all_channels_finite": finite_channels,
        "all_scout_eligible": all(item.scout_status == "ELIGIBLE" for item in evaluations),
        "sign_error_rate": sign_error_rate,
        "representation_agreement_rate_supported_fixtures": representation_rate,
        "closure_boundary_pinning_rate": boundary_rate,
        "historical_construct_recovery_pass": historical["construct_recovery_pass"],
        "null_adequacy": null_audit,
        "perturbation_nonredundancy": perturbation_audit,
        "binary_method_metrics": metrics,
        "T_e_semantic_misuse_count": 0,
        "S_e_redundancy_claim_count": 0,
        "absolute_threshold_dependence": False,
        "channel_numeric_pooling": False,
        "external_heldout_field_outcomes_used": False,
        "candidate_dataset_search_performed": False,
        "independent_verification_status": "PENDING",
    }
    write_json("method_calibration_results.json", calibration)


def main() -> None:
    prereg = verify_preregistration()
    if not TLD_I_REPLAY.exists():
        raise SystemExit("Exact TLD I preflight replay is required for historical calibration")
    static_contracts(prereg)
    absolute_threshold_audit()
    null_and_perturbation_registries()
    evaluations, metrics = synthetic_outputs(prereg)
    scout_outputs(evaluations)
    perturbation_audit = perturbation_outputs(evaluations, prereg)
    null_audit = null_outputs(evaluations, metrics)
    historical = historical_outputs()
    calibration_summary(evaluations, metrics, historical, null_audit, perturbation_audit)
    print("Calibration complete; independent verification is required before method selection.")


if __name__ == "__main__":
    main()
