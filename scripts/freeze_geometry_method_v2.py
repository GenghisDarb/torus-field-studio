# ruff: noqa: E501 -- frozen claim-boundary language stays unabridged.
"""Freeze the corrected Method V2 candidate family after raw verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "studies" / "v0.3.0-recovery"
FREEZE = RECOVERY / "freeze"
CALIBRATION = RECOVERY / "calibration"
VERIFICATION = RECOVERY / "verification"
BRIDGE = RECOVERY / "bridge"
GEOMETRY = RECOVERY / "geometry"
STATISTICS = RECOVERY / "statistics"
DESIGN = RECOVERY / "design"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_freeze() -> None:
    calibration = read_json(CALIBRATION / "calibration_uncertainty.json")
    summary = read_json(CALIBRATION / "synthetic_v2_summary.json")
    verification = read_json(VERIFICATION / "independent_raw_recomputation.json")
    bridge = read_json(BRIDGE / "geometry_tld_bridge_adjudication.json")
    regression = read_json(STATISTICS / "statistical_regression_tests_v2.json")
    minimum_support = read_json(DESIGN / "minimum_support_by_endpoint.json")
    binary_failures = [
        "No universal binary TLD truth was assigned to generic structured fields",
        "Family type-I upper confidence bounds do not establish the frozen 0.05 family bound",
        "Generic field channels are not predictive TLD discriminators",
    ]
    hierarchical_failures = [
        "No calibrated universal multi-channel adjudication rule exists",
        "Medium-effect population support was not established within the parent grid",
        "T_e and S_e are not calibrated for the general geometry evidence vector",
        "Claim-bearing domain baselines remain domain-specific and cannot be synthetic-generic",
    ]
    evidence_checks = {
        "typed_handler_registry_complete": len((GEOMETRY / "typed_geometry_handler_registry.jsonl").read_text(encoding="utf-8").splitlines()) == 13,
        "lossless_path_bridge_pass": bridge["status"] == "PASS_LOSSLESS_PATH_CHANNEL_ONLY",
        "historical_construct_recovery_pass": bool(summary["historical_construct_recovery"]),
        "raw_independent_recomputation_pass": verification["status"] == "PASS",
        "unexplained_disagreements_zero": verification["unexplained_disagreement_count"] == 0,
        "representation_disagreements_zero": verification["representation_disagreement_count"] == 0,
        "scientific_mutations_rejected": verification["mutations_rejected"] >= 45 and verification["mutations_rejected"] == verification["mutation_count"],
        "joint_parent_null": regression["children_flattened"] is False and regression["joint_null_replicates"] >= 999,
        "midpoint_penalty_absent": regression["midpoint_penalty"] is None,
        "curvature_semantic_firewall": regression["elbow_is_T_e"] is False and regression["elbow_is_winner_N"] is False,
        "outcome_exposed_calibration_absent": calibration["wind_farm_outcomes_used"] is False and calibration["Beijing_use"] == "NONE_IN_METHOD_SELECTION",
        "external_validation_not_claimed": calibration["external_validation"] is False,
    }
    evidence_pass = all(evidence_checks.values())
    candidates = {
        "schema_version": "2.0.0",
        "candidates": [
            {"method_id": "METHOD_V2_A_CALIBRATED_BINARY", "accepted": False, "mode": "PREDICTIVE_BINARY", "failures": binary_failures},
            {"method_id": "METHOD_V2_B_HIERARCHICAL_MULTI_CHANNEL", "accepted": False, "mode": "HIERARCHICAL_PREDICTIVE", "failures": hierarchical_failures},
            {"method_id": "METHOD_V2_C_EVIDENCE_VECTOR", "accepted": evidence_pass, "mode": "INSTRUMENTED_EVIDENCE_VECTOR", "failures": [] if evidence_pass else [key for key, value in evidence_checks.items() if not value]},
            {"method_id": "NO_METHOD_ESTABLISHED", "accepted": False, "mode": "STOP", "failures": ["Evidence-vector instrumentation passed"] if evidence_pass else []},
        ],
    }
    write_json(FREEZE / "method_v2_candidate_registry.json", candidates)
    write_json(
        FREEZE / "method_v2_selection_loss.json",
        {
            "schema_version": "2.0.0",
            "loss_order": [
                "unsupported predictive claim",
                "family error uncertainty",
                "sign/representation error",
                "null inadequacy",
                "semantic collision",
                "instrumentation incompleteness",
            ],
            "candidate_losses": {
                "METHOD_V2_A_CALIBRATED_BINARY": len(binary_failures),
                "METHOD_V2_B_HIERARCHICAL_MULTI_CHANNEL": len(hierarchical_failures),
                "METHOD_V2_C_EVIDENCE_VECTOR": sum(not value for value in evidence_checks.values()),
                "NO_METHOD_ESTABLISHED": 1 if evidence_pass else 0,
            },
            "selected": "METHOD_V2_C_EVIDENCE_VECTOR" if evidence_pass else "NO_METHOD_ESTABLISHED",
        },
    )
    write_json(
        FREEZE / "method_v2_acceptance_gate.json",
        {
            "schema_version": "2.0.0",
            "evidence_vector_checks": evidence_checks,
            "evidence_vector_pass": evidence_pass,
            "binary_pass": False,
            "binary_failures": binary_failures,
            "hierarchical_pass": False,
            "hierarchical_failures": hierarchical_failures,
            "method_established": evidence_pass,
        },
    )
    if not evidence_pass:
        raise RuntimeError("V030_METHOD_V2_NOT_ESTABLISHED")
    write_json(
        FREEZE / "frozen_method_v2.json",
        {
            "schema_version": "2.0.0",
            "method_id": "METHOD_V2_C_EVIDENCE_VECTOR",
            "required_name": "INSTRUMENTED_EVIDENCE_VECTOR",
            "status": "ESTABLISHED_FOR_INSTRUMENTED_NONPREDICTIVE_USE",
            "predictive_TLD_discriminator": False,
            "binary_positive_negative_authority": False,
            "TLD_bridge_authority": "LOSSLESS_SEQUENCE_PATH_CHANNEL_ONLY",
            "general_geometry_authority": "NAMED_NONPOOLED_EVIDENCE_CHANNELS",
            "TLD_DERIVED_default": "BLOCKED",
            "EXTERNALLY_VALIDATED": False,
            "T_e": "NOT_APPLICABLE_UNLESS_SEPARATELY_CALIBRATED_AND_PREREGISTERED",
            "S_e": "NOT_APPLICABLE_UNLESS_SEPARATELY_CALIBRATED_AND_PREREGISTERED",
            "winner_N": "CANONICAL_PATH_CLOSURE_LABEL_ONLY_WHERE_APPLICABLE",
            "geometric_scale_symbol": "ell",
            "forbidden_names": ["predictive TLD discriminator", "ToT-BROT", "TORUS confirmation", "external validation"],
        },
    )
    write_json(
        FREEZE / "frozen_parent_design_policy_v2.json",
        {
            "schema_version": "2.0.0",
            "policy": "DESIGN_AND_ENDPOINT_SPECIFIC",
            "universal_minimum_parent_count": None,
            "old_v1_eight_parent_gate": "PRESERVED_UNMODIFIED_HISTORICAL_ONLY",
            "tiers": read_json(DESIGN / "statistical_unit_contract_v2.json")["tiers"],
            "medium_effect_population_support": minimum_support["medium_effect_population_separation"],
            "single_instance_execution": "TIER_1_DESCRIPTIVE_WITH_MATCHED_SURROGATES_NO_POPULATION_GENERALIZATION",
            "nested_samples": "MEASUREMENT_UNCERTAINTY_ONLY",
            "condition_exchangeability_default": False,
            "unknown_hierarchy_credit": "NONE",
        },
    )
    write_json(
        FREEZE / "frozen_nulls_v2.json",
        {
            "schema_version": "2.0.0",
            "parent_matching_required": True,
            "joint_aggregate_replicates_minimum": 999,
            "aggregate_rule": "draw one registered child per parent and recompute same population statistic",
            "global_child_pool": "FORBIDDEN",
            "cluster_dependence": "EXPLICIT_DESIGN_INPUT",
            "irregular_geometry_null_bias_required": True,
            "source_specific_nulls_frozen_before_claim_metrics": True,
        },
    )
    projections = [json.loads(line) for line in (GEOMETRY / "typed_geometry_handler_registry.jsonl").read_text(encoding="utf-8").splitlines() if line]
    write_json(
        FREEZE / "frozen_projections_v2.json",
        {
            "schema_version": "2.0.0",
            "typed_handler_count": len(projections),
            "handlers": projections,
            "silent_scalarization": "FORBIDDEN",
            "silent_dimensional_average": "FORBIDDEN",
            "mask_native": True,
            "vector_transform_law": "COORDINATES_COMPONENTS_MASK_ORIENTATION",
        },
    )
    write_json(
        FREEZE / "frozen_perturbations_v2.json",
        {
            "schema_version": "2.0.0",
            "required_response_classes": ["INVARIANT", "EQUIVARIANT", "GRADED", "DESTRUCTIVE", "INCONCLUSIVE"],
            "relative_noise": "ROBUST_SCALE_NO_ABSOLUTE_UNIT_FLOOR",
            "dropout": "MASK_NATIVE",
            "resolution": "ANTI_ALIASED_BLOCK_AVERAGE",
            "ensemble_uncertainty_required": True,
            "single_boolean_fragility": False,
        },
    )
    write_json(
        FREEZE / "frozen_operation_depths_v2.json",
        {
            "schema_version": "2.0.0",
            "general_geometry_operation_depths": [],
            "post_freeze_depth_addition": "FORBIDDEN",
            "T_e_definition": "first preregistered operation depth where observed/null separation emerges",
            "T_e_current_general_geometry_status": "NOT_APPLICABLE",
            "elbow_is_T_e": False,
        },
    )
    write_json(
        FREEZE / "frozen_scale_registry_v2.json",
        {
            "schema_version": "2.0.0",
            "geometric_scale_symbol": "ell",
            "S_e_definition": "registered persistence/nonredundancy endpoint only",
            "S_e_is_geometric_scale": False,
            "general_geometry_S_e_status": "NOT_APPLICABLE",
            "unit_provenance_uncertainty_required": True,
        },
    )
    write_json(
        FREEZE / "frozen_claim_boundary_v2.json",
        {
            "schema_version": "2.0.0",
            "maximum_method_claim": "INSTRUMENTED_EVIDENCE_VECTOR",
            "allowed": ["typed finite channel outputs", "within-instance matched-surrogate evidence", "deterministic invariant/equivariant checks", "source-specific geometry descriptions"],
            "forbidden": ["predictive TLD discrimination", "binary TLD positive/negative from the general vector", "population generalization without design-specific support", "T_e from elbow", "S_e from geometric scale", "winner_N as time or physical scale", "TORUS confirmation", "ToT-BROT from one system", "external validation"],
            "TLD_DERIVED": "BLOCKED_BY_DEFAULT",
            "EXTERNALLY_VALIDATED": False,
            "wind_farm_role": "NONCONFIRMATORY_STRUCTURE_EXPOSED_ENGINEERING_PILOT_ONLY",
        },
    )
    names = [
        "method_v2_candidate_registry.json",
        "method_v2_selection_loss.json",
        "method_v2_acceptance_gate.json",
        "frozen_method_v2.json",
        "frozen_parent_design_policy_v2.json",
        "frozen_nulls_v2.json",
        "frozen_projections_v2.json",
        "frozen_perturbations_v2.json",
        "frozen_operation_depths_v2.json",
        "frozen_scale_registry_v2.json",
        "frozen_claim_boundary_v2.json",
    ]
    with (FREEZE / "method_v2_SHA256SUMS.txt").open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        handle.write(
            "".join(f"{sha256(FREEZE / name)}  {name}\n" for name in sorted(names))
        )
    print("Frozen METHOD_V2_C_EVIDENCE_VECTOR as INSTRUMENTED_EVIDENCE_VECTOR.")


if __name__ == "__main__":
    build_freeze()
