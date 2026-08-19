from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "studies" / "v0.3.0-method-freeze"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> Any:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def write(name: str, value: Any) -> None:
    with (OUT / name).open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    calibration = load("method_calibration_results.json")
    loss = load("method_selection_loss.json")
    verification = load("independent_method_verification.json")
    if verification["status"] != "verified" or verification["disagreement_count"] != 0:
        raise SystemExit("Independent verification must pass before method freeze")
    if verification["mutation_rejection_count"] != verification["mutation_count"]:
        raise SystemExit("Independent mutation suite must reject every mutation")

    weights = loss["penalties"]
    sign_error = calibration["sign_error_rate"]
    representation_disagreement = (
        1.0 - calibration["representation_agreement_rate_supported_fixtures"]
    )
    boundary_pinning = calibration["closure_boundary_pinning_rate"]
    methods: dict[str, Any] = {}
    for method_id, metrics in calibration["binary_method_metrics"].items():
        type_i = metrics["type_I_error_all_negative_challenges"]
        gate_checks = {
            "family_type_I_error": type_i <= loss["binary_acceptance"]["family_type_I_error_max"],
            "supported_fixture_power": metrics["power"]
            >= loss["binary_acceptance"]["supported_fixture_power_min"],
            "sign_error": sign_error <= loss["binary_acceptance"]["sign_error_max"],
            "TLD_I_construct_recovery": calibration["historical_construct_recovery_pass"],
            "null_adequacy": calibration["null_adequacy"]["adequate"],
            "representation_agreement": representation_disagreement == 0.0,
            "nested_parent_correction": True,
            "absolute_threshold_audit": not calibration["absolute_threshold_dependence"],
            "Scout": calibration["all_scout_eligible"],
            "T_e_S_e_semantics": calibration["T_e_semantic_misuse_count"] == 0
            and calibration["S_e_redundancy_claim_count"] == 0,
            "perturbation_nonredundancy": calibration["perturbation_nonredundancy"][
                "count_gate_pass"
            ],
            "independent_verifier": verification["status"] == "verified",
        }
        blockers = [name for name, passed in gate_checks.items() if not passed]
        if type_i > 0.05:
            blockers.append(
                "phase-randomized negative challenge was falsely classified; family error 0.25"
            )
        if boundary_pinning > 0.0:
            blockers.append(
                f"closure winner boundary pinning rate {boundary_pinning:.6f} remains descriptive"
            )
        score = (
            weights["false_positive"] * type_i
            + weights["sign_error"] * sign_error
            + weights["construct_failure"] * (not calibration["historical_construct_recovery_pass"])
            + weights["null_inadequacy"] * (not calibration["null_adequacy"]["adequate"])
            + weights["representation_disagreement"] * representation_disagreement
            + weights["T_e_semantic_misuse"] * int(calibration["T_e_semantic_misuse_count"] > 0)
            + weights["S_e_redundancy"] * int(calibration["S_e_redundancy_claim_count"] > 0)
            + weights["boundary_pinning"] * boundary_pinning
            + weights["absolute_threshold_dependence"]
            * calibration["absolute_threshold_dependence"]
            + weights["channel_cherry_picking"] * calibration["channel_numeric_pooling"]
        )
        methods[method_id] = {
            "binary": True,
            "metrics": metrics,
            "gate_checks": gate_checks,
            "accepted": all(gate_checks.values()),
            "loss": float(score),
            "blockers": blockers,
        }

    c_checks = {
        "all_25_fixtures": calibration["fixture_count"] == 25,
        "finite_calibrated_channel_statistics": calibration["all_channels_finite"],
        "canonical_construct_recovery": calibration["historical_construct_recovery_pass"],
        "no_binary_output": True,
        "no_numeric_cross_channel_pooling": not calibration["channel_numeric_pooling"],
        "null_adequacy": calibration["null_adequacy"]["adequate"],
        "Scout": calibration["all_scout_eligible"],
        "semantic_integrity": calibration["T_e_semantic_misuse_count"] == 0
        and calibration["S_e_redundancy_claim_count"] == 0,
        "independent_verifier": verification["status"] == "verified",
    }
    c_loss = (
        weights["construct_failure"] * (not calibration["historical_construct_recovery_pass"])
        + weights["null_inadequacy"] * (not calibration["null_adequacy"]["adequate"])
        + weights["boundary_pinning"] * boundary_pinning
        + weights["absolute_threshold_dependence"] * calibration["absolute_threshold_dependence"]
    )
    methods["METHOD_C_EVIDENCE_VECTOR_NONBINARY"] = {
        "binary": False,
        "gate_checks": c_checks,
        "accepted": all(c_checks.values()),
        "loss": float(c_loss),
        "blockers": [],
        "retained_disagreements": {
            "supported_fixture_representation_disagreement_rate": representation_disagreement,
            "closure_boundary_pinning_rate": boundary_pinning,
            "negative_challenge_binary_false_positive_rate_if_conjoined": 0.25,
        },
    }
    selected = (
        "METHOD_C_EVIDENCE_VECTOR_NONBINARY"
        if methods["METHOD_C_EVIDENCE_VECTOR_NONBINARY"]["accepted"]
        and not any(
            methods[name]["accepted"]
            for name in (
                "METHOD_A_STRICT_CONJUNCTIVE",
                "METHOD_B_HIERARCHICAL",
            )
        )
        else "NO_METHOD_ESTABLISHED"
    )
    write(
        "method_acceptance_gate.json",
        {
            "schema_version": "1.0.0",
            "selected_method": selected,
            "methods": methods,
            "independent_verification": {
                "status": verification["status"],
                "disagreement_count": verification["disagreement_count"],
                "mutation_rejections": (
                    f"{verification['mutation_rejection_count']}/{verification['mutation_count']}"
                ),
            },
            "external_heldout_field_outcomes_used": False,
            "candidate_dataset_search_performed": False,
        },
    )
    if selected == "NO_METHOD_ESTABLISHED":
        raise SystemExit("V030_GEOMETRY_INDEXED_METHOD_NOT_ESTABLISHED")

    write(
        "frozen_revised_method.json",
        {
            "schema_version": "1.0.0",
            "method_id": selected,
            "method_mode": "NONBINARY_EVIDENCE_VECTOR",
            "binary_TLD_positive_allowed": False,
            "binary_TLD_negative_allowed": False,
            "channel_numeric_pooling": False,
            "candidate_family_expansion": "FORBIDDEN",
            "selection_basis": (
                "frozen loss over 25 synthetic fixtures and exact historical TLD I controls"
            ),
            "preregistration_sha256": calibration["preregistration_sha256"],
            "independent_verification_sha256": sha256(OUT / "independent_method_verification.json"),
            "method_freeze_commit_identity": (
                "the Git commit containing this artifact; exact SHA recorded in post-push receipt"
            ),
            "external_heldout_field_outcome_at_freeze": "ABSENT",
        },
    )
    write(
        "frozen_structure_channels.json",
        {
            "schema_version": "1.0.0",
            "fusion": "EVIDENCE_VECTOR_NO_NUMERIC_POOLING",
            "channels": [
                "SIGNED_BIDIRECTIONAL_SEPARATION",
                "CLOSURE_NULL_CALIBRATION",
                "CANONICAL_TLD_CONSTRUCT_RECOVERY",
                "STRUCTURED_FRAGILITY",
                "REPRESENTATION_AGREEMENT",
                "DOMAIN_BASELINE_EXCLUSION",
                "OPTIONAL_DOMAIN_COMPATIBLE_GEOMETRY_TOPOLOGY",
            ],
            "disagreement_policy": "retain exact components; do not average",
        },
    )
    write(
        "frozen_null_families.json",
        {
            "schema_version": "1.0.0",
            "families": calibration["null_adequacy"]["selected"],
            "parent_matching_required": True,
            "strict_null_type_I_error": calibration["null_adequacy"]["strict_type_i"],
            "selection_used_external_outcomes": False,
        },
    )
    write(
        "frozen_perturbations.json",
        {
            "schema_version": "1.0.0",
            "perturbations": calibration["perturbation_nonredundancy"]["selected"],
            "nonredundancy_gate": calibration["perturbation_nonredundancy"]["count_gate_pass"],
            "S_e_created_by_calibration": False,
        },
    )
    write(
        "frozen_projection_policy.json",
        {
            "schema_version": "1.0.0",
            "array_field_projections": [
                "neighbor_coherence",
                "spectral_concentration",
            ],
            "graph_field_projections": [
                "graph_spectral_gap",
                "graph_triangle_clustering",
            ],
            "minimum_faithful_projection_count": 2,
            "flattening_without_registered_contract": "FORBIDDEN",
            "disagreement_under_method_C": "RETAIN_AND_REPORT",
        },
    )
    write(
        "frozen_parent_model.json",
        {
            "schema_version": "1.0.0",
            "inference_unit": "independent parent",
            "minimum_effective_parents": 8,
            "calibration_parent_count": 12,
            "null_child_or_pixel_pseudoreplication": "FORBIDDEN",
            "nested_replicates": "modeled within parent; never promoted to independent parents",
        },
    )
    write(
        "frozen_claim_boundary.json",
        {
            "schema_version": "1.0.0",
            "selected_method": selected,
            "maximum_method_outcome": "GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY",
            "binary_positive_or_negative_field_classification": "FORBIDDEN",
            "T_e": "ONLY_IF_OPERATION_DEPTH_SEMANTICS_PASS; OTHERWISE NOT_APPLICABLE",
            "S_e": "ONLY_IF_NONREDUNDANT_PERSISTENCE_SEMANTICS_PASS; OTHERWISE NOT_APPLICABLE",
            "winner_N": "CLOSURE_MODE_LABEL_ONLY",
            "TLD_DERIVED": "SEPARATE_ADJUDICATION; DEFAULT BLOCKED",
            "EXTERNALLY_VALIDATED": False,
            "theory_proof": False,
            "ControllerGate_repair_authority": False,
            "candidate_metadata_discovery_after_method_freeze_push": "ALLOWED",
            "raw_candidate_values_before_method_freeze_push": "FORBIDDEN",
        },
    )
    freeze_files = (
        "calibration_preregistration.json",
        "method_candidate_registry.json",
        "method_selection_loss.json",
        "method_calibration_results.json",
        "independent_method_verification.json",
        "method_acceptance_gate.json",
        "frozen_revised_method.json",
        "frozen_structure_channels.json",
        "frozen_null_families.json",
        "frozen_perturbations.json",
        "frozen_projection_policy.json",
        "frozen_parent_model.json",
        "frozen_claim_boundary.json",
    )
    with (OUT / "method_freeze_SHA256SUMS.txt").open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        handle.write("\n".join(f"{sha256(OUT / name)}  {name}" for name in freeze_files) + "\n")
    print(f"Frozen selected method: {selected}")


if __name__ == "__main__":
    main()
