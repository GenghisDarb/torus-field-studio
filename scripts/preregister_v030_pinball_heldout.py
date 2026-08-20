# ruff: noqa: E501 -- scientific contracts are intentionally explicit and reviewable.
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MATERIALIZATION = ROOT / "studies" / "v0.3.0-recovery" / "heldout" / "materialization"
OUT = ROOT / "studies" / "v0.3.0-recovery" / "heldout" / "preregistration"
SELECTION_COMMIT = "590f6ea5896d3813c3a0a673e108381a4e3d87da"
METHOD_FREEZE_COMMIT = "dcaeb72b29fc0d32b002d9b5de0809b13f2ed272"
METHOD_IMPLEMENTATION_COMMIT = "dd17f1f922dea81db474a8c52347a80580d7eead"


def canonical(value: Any, *, pretty: bool = False) -> bytes:
    options: dict[str, Any] = {"sort_keys": True, "ensure_ascii": False, "allow_nan": False}
    options.update(indent=2 if pretty else None, separators=None if pretty else (",", ":"))
    return (json.dumps(value, **options) + "\n").encode()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path)
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(name: str, value: Any) -> None:
    (OUT / name).write_bytes(canonical(value, pretty=True))


def write_jsonl(name: str, rows: list[dict[str, Any]]) -> None:
    (OUT / name).write_bytes(b"".join(canonical(row) for row in rows))


def main() -> None:
    custody = read_json(MATERIALIZATION / "source_custody.json")
    materialization = read_json(MATERIALIZATION / "source_materialization_receipt.json")
    pairs = read_jsonl(MATERIALIZATION / "paired_acquisition_registry.jsonl")
    structures = read_jsonl(MATERIALIZATION / "hdf5_structure_registry.jsonl")
    if custody.get("status") != "PASS" or materialization.get("status") != "PASS_STRUCTURE_ONLY":
        raise SystemExit("PINBALL_SOURCE_NOT_MATERIALIZED_FOR_PREREGISTRATION")
    if custody.get("selection_commit") != SELECTION_COMMIT or len(pairs) != 28 or len(structures) != 57:
        raise SystemExit("PINBALL_FROZEN_HIERARCHY_MISMATCH")
    if any(row.get("field_values_read") is not False for row in structures):
        raise SystemExit("PINBALL_OUTCOME_EXPOSURE_BEFORE_PREREGISTRATION")
    grid_mismatch_pairs = [
        {"pair_id": row["pair_id"], "p": row["p"]}
        for row in pairs
        if row["spatial_grid_shape_match"] is False
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    run_identity = {
        "candidate_id": "actuated_fluidic_pinball_piv",
        "source_sha256": custody["verified_sha256"],
        "selection_commit": SELECTION_COMMIT,
        "method_freeze_commit": METHOD_FREEZE_COMMIT,
        "method_implementation_commit": METHOD_IMPLEMENTATION_COMMIT,
        "pair_registry_sha256": hashlib.sha256((MATERIALIZATION / "paired_acquisition_registry.jsonl").read_bytes()).hexdigest(),
        "root_seed": 20260820,
    }
    run_id = f"pinball-heldout-{hashlib.sha256(canonical(run_identity)).hexdigest()[:16]}"
    statistical_unit = {
        "schema_version": "1.0.0",
        "primary_statistical_unit": "one paired acquisition block: one actuated PIV HDF5 acquisition and its uniquely matched immediately preceding unactuated _zero_ HDF5 acquisition",
        "paired_block_count": 28,
        "reference_reuse": "FORBIDDEN",
        "snapshot_role": "NESTED_WITHIN_ACQUISITION",
        "spatial_cell_role": "NESTED_WITHIN_SNAPSHOT_AND_ACQUISITION",
        "components_are_independent_parents": False,
        "campaign_independence": "UNKNOWN_NO_POPULATION_CREDIT",
        "system_count": 1,
    }
    claim_tier = {
        "tier": 2,
        "name": "WITHIN_CAMPAIGN_REPEATED_ACQUISITION_ASSAY",
        "maximum_claim": "CALIBRATED_WITHIN_CAMPAIGN_NONBINARY_EVIDENCE_VECTOR",
        "population_generalization": False,
        "external_replication": False,
        "TLD_DERIVED_default": "BLOCKED",
    }
    parent_hierarchy = {
        "system": "one fluidic-pinball apparatus",
        "campaign_cluster": "DEPOSIT_LEVEL_SINGLE_SYSTEM_CLUSTER",
        "campaign_count": "UNKNOWN_NO_SCORE",
        "paired_acquisition_blocks": 28,
        "acquisition_files": 56,
        "auxiliary_unpaired_acquisitions": 1,
        "auxiliary_member": "ExperimentalDataset/Case_p_m1p4_upward.h5",
        "auxiliary_claim_role": "STRUCTURAL_AUDIT_ONLY_NOT_PRIMARY_SCORED_PARENT",
        "nested_snapshots": "axis 0 of U and V, cross-checked against the frozen dataset shape and Nsnapshots attribute at execution; never promoted",
        "cross_file_cell_alignment": "FORBIDDEN",
        "spatial_grid_shape_mismatch_pairs": grid_mismatch_pairs,
        "grid_mismatch_handling": "score each acquisition on its own deposited coordinate grid, then compare acquisition-level named channels within the pair",
    }
    effective_sample = {
        "primary_pair_count": 28,
        "effective_population_parent_count": 1,
        "campaign_ICC": "NOT_IDENTIFIABLE_FROM_ONE_SYSTEM",
        "cluster_model": "all pairs remain in one deposit-level system cluster",
        "pairwise_curve_claim_only": True,
        "population_sign_test": "FORBIDDEN",
        "fixed_eight_parent_rule": "NOT_USED",
        "power_claim": "NOT_MADE_FOR_POPULATION_GENERALIZATION",
    }
    projections = [
        {
            "projection_id": "P01_REGISTERED_TEMPORAL_MEAN_VECTOR_FIELD",
            "geometry_kind": "VectorField2D",
            "inputs": ["U", "V", "X", "Y"],
            "construction": "componentwise arithmetic mean across frozen U/V axis 0 (the nested snapshot axis), then convert particle displacement to u/U_infty and v/U_infty using frozen instrument constants",
            "silent_time_average": False,
            "time_reduction_disclosed": True,
            "vector_magnitude_scalarization": False,
            "mask": "jointly finite U,V,X,Y across every included value; no fill or interpolation",
            "claim_role": "PRIMARY_WITHIN_ACQUISITION_GEOMETRY_EVIDENCE",
        },
        {
            "projection_id": "P02_REGISTERED_SPATIOTEMPORAL_VECTOR_FLUCTUATIONS",
            "geometry_kind": "SpatiotemporalVectorField",
            "inputs": ["U", "V", "X", "Y"],
            "construction": "retain the full snapshot axis after subtracting each cell's temporal component mean; convert with frozen instrument constants",
            "silent_time_average": False,
            "vector_magnitude_scalarization": False,
            "claim_role": "SECONDARY_TYPED_DESCRIPTIVE_CHANNELS_NO_NULL_THRESHOLD",
        },
    ]
    nulls = [
        {
            "null_id": "N01_PARENT_LOCAL_JOINT_SPATIAL_CELL_PERMUTATION",
            "target_projection": "P01_REGISTERED_TEMPORAL_MEAN_VECTOR_FIELD",
            "children_per_acquisition": 127,
            "joint_aggregate_replicates": 999,
            "preserved": ["acquisition", "mask", "coordinate grid", "joint U/V component pairing", "component marginals"],
            "destroyed": "alignment of the vector field with registered spatial coordinates",
            "global_child_pool": "FORBIDDEN",
            "pair_matching": "actuated and reference null children remain within their acquisition and pair",
            "seed": 20260820,
            "threshold_selection": False,
        }
    ]
    perturbations = [
        {"perturbation_id": "PERT01_ROTATE_90_WITH_COORDINATES_COMPONENTS_AND_MASK", "class": "EQUIVARIANCE", "claim_role": "REQUIRED_PASS"},
        {"perturbation_id": "PERT02_MASK_DROPOUT_5_PERCENT", "class": "MISSINGNESS_SENSITIVITY", "claim_role": "REPORT_DELTA_NO_THRESHOLD"},
        {"perturbation_id": "PERT03_RELATIVE_COMPONENT_NOISE_1_PERCENT", "class": "INSTRUMENT_SENSITIVITY", "claim_role": "REPORT_DELTA_NO_THRESHOLD"},
        {"perturbation_id": "PERT04_ANTI_ALIASED_SCALE_2X", "class": "REPRESENTATION_SENSITIVITY", "claim_role": "REPORT_DELTA_NO_THRESHOLD"},
    ]
    operation_depth = {
        "general_geometry_operation_depths": [],
        "status": "NOT_APPLICABLE_NO_FROZEN_GENERAL_GEOMETRY_OPERATION_DEPTH",
        "T_e": "NOT_APPLICABLE",
        "post_preregistration_depth_addition": "FORBIDDEN",
    }
    scales = {
        "geometric_scale_symbol": "ell",
        "views": [
            {"ell": 1, "units": "native PIV grid cell", "transform": "identity"},
            {"ell": 2, "units": "native PIV grid cells", "transform": "mask-aware anti-aliased factor-two downsample"},
            {"ell": 4, "units": "native PIV grid cells", "transform": "two successive mask-aware anti-aliased factor-two downsamples"},
        ],
        "physical_coordinate_conversion": {"resolution_m_per_px": 0.00029076921, "diameter_m": 0.03},
        "S_e": "NOT_APPLICABLE_GEOMETRIC_SCALE_IS_NOT_S_E",
    }
    closure = {
        "status": "NOT_APPLICABLE_TO_GENERAL_GEOMETRY_EVIDENCE_VECTOR",
        "modal_trace_if_rendered": "DIAGNOSTIC_ONLY_NOT_TLD_CLOSURE",
        "midpoint_penalty": None,
        "winner_N": "NOT_APPLICABLE",
    }
    endpoints = {
        "T_e": "NOT_APPLICABLE_NO_OPERATION_DEPTH_AXIS",
        "S_e": "NOT_APPLICABLE_NO_CALIBRATED_PERSISTENCE_ENDPOINT",
        "winner_N": "NOT_APPLICABLE_NO_CANONICAL_PATH_CLOSURE_AXIS",
        "geometric_scale": "ell in native PIV grid cells",
    }
    baseline = {
        "baseline_id": "B01_PAIRED_UNACTUATED_REFERENCE_FLOW",
        "reference_members": "the 28 uniquely matched _zero_ acquisitions",
        "estimator": "per acquisition median abs(v_mean)/max(abs(u_mean), registered numerical floor) on the P01 observed mask",
        "comparison": "actuated minus its immediately preceding reference, retained by p and pair",
        "numeric_pooling_with_geometry_channels": False,
        "population_generalization": False,
    }
    sensitivity = {
        "resolution_m_per_px": 0.00029076921,
        "cylinder_diameter_m": 0.03,
        "stream_velocity_m_per_s": 0.31,
        "sampling_frequency_hz": 120,
        "field_specific_uncertainty_array": "NOT_DEPOSITED_IN_EACH_HDF5_FIELD",
        "sensitivity_action": "PERT03 relative 1% component noise and exact unit-provenance disclosure",
        "absolute_noise_floor_claim": "FORBIDDEN",
    }
    missingness = {
        "mask_rule": "observed only where X,Y and every U,V snapshot required by P01 are finite",
        "NaN_as_zero": False,
        "interpolation": False,
        "mean_fill": False,
        "minimum_observed_cells": 16,
        "ineligible_acquisition_action": "preserve failure and block its pair; no selective substitution",
    }
    falsifiers = [
        {"falsifier_id": "F01_SOURCE_CUSTODY", "condition": "archive size, MD5, SHA256, inventory, or member count changes", "outcome": "GEOMETRY_INDEXED_TLD_HELDOUT_INVALIDATED_BY_PROTOCOL"},
        {"falsifier_id": "F02_PAIR_HIERARCHY", "condition": "not exactly 28 unique actuated/reference pairs or any reference reuse", "outcome": "GEOMETRY_INDEXED_TLD_HELDOUT_INVALIDATED_BY_PROTOCOL"},
        {"falsifier_id": "F03_FIELD_STRUCTURE", "condition": "U/V or X/Y shapes disagree, components absent, or coordinates nonfinite", "outcome": "GEOMETRY_INDEXED_TLD_HELDOUT_EXECUTION_BLOCKED"},
        {"falsifier_id": "F04_NULL_COMPLETENESS", "condition": "any pair lacks 127 finite acquisition-local null children", "outcome": "GEOMETRY_INDEXED_TLD_HELDOUT_EXECUTION_BLOCKED"},
        {"falsifier_id": "F05_EQUIVARIANCE", "condition": "registered 90-degree vector rotation disagrees beyond 1e-10", "outcome": "GEOMETRY_INDEXED_TLD_HELDOUT_INVALIDATED_BY_PROTOCOL"},
        {"falsifier_id": "F06_PROTOCOL_MUTATION", "condition": "projection, null, seed, pairs, channels, or scale views change after authorization", "outcome": "GEOMETRY_INDEXED_TLD_HELDOUT_INVALIDATED_BY_PROTOCOL"},
        {"falsifier_id": "F07_SELECTIVE_RERUN", "condition": "a second scored execution is attempted", "outcome": "GEOMETRY_INDEXED_TLD_HELDOUT_INVALIDATED_BY_PROTOCOL"},
    ]
    multiple_testing = {
        "binary_hypothesis_tests": 0,
        "thresholded_channels": 0,
        "familywise_claim": "NONE",
        "reporting_rule": "all frozen named channels, all 28 pair deltas, null medians/intervals, scale views, perturbations, and failures are reported without winner selection",
        "post_hoc_channel_selection": "FORBIDDEN",
    }
    claim_boundary = {
        "maximum_scientific_outcome": "GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY",
        "permitted_outcomes": ["GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY", "GEOMETRY_INDEXED_TLD_HELDOUT_EXECUTION_BLOCKED", "GEOMETRY_INDEXED_TLD_HELDOUT_INVALIDATED_BY_PROTOCOL"],
        "positive_negative_TLD_classification": "FORBIDDEN_METHOD_NOT_CALIBRATED_FOR_BINARY_DISCRIMINATION",
        "population_generalization": False,
        "causal_actuation_claim": False,
        "TLD_DERIVED": "BLOCKED",
        "EXTERNALLY_VALIDATED": False,
        "ToT_BROT": "FORBIDDEN",
        "TORUS_confirmation": "FORBIDDEN",
    }
    source_registry = {
        "candidate_id": "actuated_fluidic_pinball_piv",
        "doi": custody["doi"],
        "license": custody["license"],
        "archive_sha256": custody["verified_sha256"],
        "archive_md5": custody["verified_md5"],
        "archive_inventory_sha256": custody["archive_inventory_sha256"],
        "selection_commit": SELECTION_COMMIT,
        "candidate_substitution": "FORBIDDEN",
    }
    run_contract = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "run_identity": run_identity,
        "method_id": "METHOD_V2_C_EVIDENCE_VECTOR",
        "method_mode": "INSTRUMENTED_EVIDENCE_VECTOR",
        "scored_execution_limit": 1,
        "scored_executions_completed": 0,
        "execution_authorized": False,
        "outcome_data_used_during_preregistration": False,
    }
    documents = {
        "run_contract.json": run_contract,
        "source_registry.json": source_registry,
        "statistical_unit_contract.json": statistical_unit,
        "claim_tier.json": claim_tier,
        "parent_campaign_hierarchy.json": parent_hierarchy,
        "effective_sample_method.json": effective_sample,
        "operation_depth_registry.json": operation_depth,
        "geometric_scale_registry.json": scales,
        "closure_objective.json": closure,
        "endpoint_applicability.json": endpoints,
        "domain_baseline.json": baseline,
        "instrument_sensitivity.json": sensitivity,
        "missingness_contract.json": missingness,
        "multiple_testing.json": multiple_testing,
        "claim_boundary.json": claim_boundary,
    }
    for name, document in documents.items():
        write_json(name, document)
    write_jsonl("projection_registry.jsonl", projections)
    write_jsonl("null_registry.jsonl", nulls)
    write_jsonl("perturbation_registry.jsonl", perturbations)
    write_jsonl("falsifier_registry.jsonl", falsifiers)
    artifact_names = sorted([*documents, "projection_registry.jsonl", "null_registry.jsonl", "perturbation_registry.jsonl", "falsifier_registry.jsonl"])
    manifest = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "status": "FROZEN_PENDING_COMMIT_AND_PUSH",
        "outcome_data_used": False,
        "field_values_read": False,
        "selection_commit": SELECTION_COMMIT,
        "method_freeze_commit": METHOD_FREEZE_COMMIT,
        "artifacts": [{"name": name, "sha256": hashlib.sha256((OUT / name).read_bytes()).hexdigest()} for name in artifact_names],
    }
    write_json("preregistration_manifest.json", manifest)
    print(json.dumps({"status": manifest["status"], "run_id": run_id, "artifact_count": len(artifact_names), "pair_count": len(pairs)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
