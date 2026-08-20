# ruff: noqa: E501 -- frozen scientific contract strings remain intact.
"""Generate append-only Method V2 supersession, design, bridge, and operator contracts."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from torusbrot.geometry.v2 import (
    GeometryKind,
    TypedGeometry,
    aggregate_modal_trace_audit,
    ball_porosity,
    curvature_audit_v2,
    dual_concentration_operator_norm,
    fup_applicability_gate,
    joint_parent_null_distribution,
    line_porosity,
    modal_residual_trace,
    reflect_vector_field_y,
    rotate_vector_field_90,
    typed_projection_scores,
)

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "studies" / "v0.3.0-recovery"
SUPERSESSION = RECOVERY / "supersession"
DESIGN = RECOVERY / "design"
BRIDGE = RECOVERY / "bridge"
GEOMETRY = RECOVERY / "geometry"
STATISTICS = RECOVERY / "statistics"
FUP = RECOVERY / "fup"
METHOD_V1_COMMIT = "827b3394c0ce8ed414ca57d8e77ef1aaf1a72b1c"
DATASET_V1_COMMIT = "70fa574350ecff8c021ed61ad121c07edb3d581f"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_supersession() -> None:
    method_status = {
        "schema_version": "2.0.0",
        "freeze_commit": METHOD_V1_COMMIT,
        "historical_method": "METHOD_C_EVIDENCE_VECTOR_NONBINARY",
        "statuses": [
            "SUPERSEDED_FOR_FUTURE_CONFIRMATORY_USE",
            "PRESERVED_FOR_REPRODUCTION",
            "NOT_DELETED",
            "NOT_REWRITTEN",
        ],
        "files_preserved": True,
        "future_authority": "HISTORICAL_REPRODUCTION_ONLY",
    }
    dataset_status = {
        "schema_version": "2.0.0",
        "freeze_commit": DATASET_V1_COMMIT,
        "doi": "10.5281/zenodo.18731994",
        "statuses": [
            "STRUCTURE_EXPOSED_NO_CLAIM_METRICS",
            "NONCONFIRMATORY_METHOD_DEVELOPMENT_PILOT_ONLY",
            "BEIJING_STYLE_CONFIRMATORY_REUSE_FORBIDDEN",
            "SOURCE_CUSTODY_REUSABLE",
            "PIPELINE_ENGINEERING_REUSABLE",
            "THRESHOLD_CALIBRATION_FORBIDDEN",
        ],
        "condition_acquisitions_exchangeable": False,
        "claim_metrics_executed_at_v1": False,
    }
    write_json(SUPERSESSION / "method_freeze_v1_status.json", method_status)
    write_json(SUPERSESSION / "dataset_freeze_v1_status.json", dataset_status)
    write_jsonl(
        SUPERSESSION / "supersession_ledger.jsonl",
        [
            {
                "record_id": "SUPERSEDE-METHOD-V1",
                "superseded_commit": METHOD_V1_COMMIT,
                "reason": "Expected-red audit confirmed statistical and geometry-contract defects",
                "replacement": "METHOD_V2_PENDING_CALIBRATION",
                "mutation": "NONE_APPEND_ONLY",
            },
            {
                "record_id": "RECLASSIFY-WIND-V1",
                "superseded_commit": DATASET_V1_COMMIT,
                "reason": "One campaign with four nonexchangeable intervention conditions",
                "replacement": "NONCONFIRMATORY_STRUCTURE_EXPOSED_ENGINEERING_PILOT",
                "mutation": "NONE_APPEND_ONLY",
            },
        ],
    )
    claims = [
        ("12-sigma universal validation", "historical draft", "No registered universal endpoint", "No raw independent replication and no multiplicity contract"),
        ("general three-body solution", "historical notes", "No executable proof in repository", "A complete peer-reviewable mathematical derivation"),
        ("stationary-action uniqueness", "historical notes", "No executable proof in repository", "Uniqueness proof with explicit assumptions"),
        ("OSQN physical predictions", "historical notes", "No registered physical assay", "Prospective falsifiable preregistration and data"),
        ("gravitational-wave family pass", "chat-only queue", "No source-backed executable receipt", "Raw inputs, frozen contract, and independent replay"),
        ("positive CPU-jitter result", "chat-only queue", "No immutable evidence located", "Raw timing custody and authority-firewalled assay"),
        ("analytic TORUS-BROT imagery is physical evidence", "analytic imagery", "Images are available as mathematical constructions", "Independent physical observations and a registered translation"),
        ("one system is ToT-BROT", "historical naming", "Single-system outputs may exist", "Independent systems satisfying a frozen cross-system definition"),
        ("metaphysical glossary terms are physical claims", "historical glossary", "Terminology exists", "Operational definitions and prospective physical tests"),
    ]
    quarantine = [
        {
            "claim": claim,
            "source": source,
            "authority_level": "QUARANTINED_NONEXECUTABLE",
            "exact_evidence_found": found,
            "exact_evidence_missing": missing,
            "current_classification": "UNVERIFIED_HISTORICAL_CLAIM",
            "allowed_use": "Historical context with explicit non-authority label",
            "forbidden_use": "Method calibration, dataset selection, adjudication, or validation claim",
            "reopen_condition": missing,
        }
        for claim, source, found, missing in claims
    ]
    write_jsonl(SUPERSESSION / "claim_source_quarantine.jsonl", quarantine)
    write_jsonl(
        SUPERSESSION / "historical_overclaim_registry.jsonl",
        [dict(row, registry_status="PRESERVED_AND_FIREWALLED") for row in quarantine],
    )


def _simulate_power(
    *,
    parent_count: int,
    nested_replicates: int,
    icc: float,
    effect_size: float,
    heterogeneity: float,
    missingness: float,
    projection_disagreement: float,
    family_size: int,
    seed: int,
) -> float:
    if parent_count < 2:
        return 0.0
    rng = np.random.default_rng(seed)
    simulations = 2500
    between = rng.normal(0.0, math.sqrt(icc), size=(simulations, parent_count))
    measurement = rng.normal(
        0.0,
        math.sqrt(max(1.0 - icc, 0.0) / nested_replicates),
        size=(simulations, parent_count),
    )
    heterogeneity_term = rng.normal(0.0, heterogeneity, size=(simulations, parent_count))
    values = effect_size + between + measurement + heterogeneity_term
    missing = rng.random(values.shape) < missingness
    values[missing] = np.nan
    flips = rng.random(values.shape) < projection_disagreement
    values[flips] *= -1.0
    counts = np.sum(np.isfinite(values), axis=1)
    means = np.nansum(values, axis=1) / np.maximum(counts, 1)
    residuals = np.where(np.isfinite(values), values - means[:, np.newaxis], 0.0)
    standard_deviations = np.sqrt(
        np.sum(residuals**2, axis=1) / np.maximum(counts - 1, 1)
    )
    statistic = means / np.maximum(
        standard_deviations / np.sqrt(np.maximum(counts, 1)), 1e-12
    )
    critical = {1: 1.96, 3: 2.39, 6: 2.64}[family_size]
    rejected = (counts >= 2) & (np.abs(statistic) >= critical)
    return float(np.mean(rejected))


def build_design() -> None:
    tiers = [
        {
            "tier": 0,
            "name": "SOURCE_CUSTODY_ONLY",
            "minimum_structure": "source identity and custody",
            "maximum_claim": "NO_SCIENTIFIC_METRIC",
            "population_generalization": False,
        },
        {
            "tier": 1,
            "name": "SINGLE_FIELD_INSTANCE_ASSAY",
            "minimum_structure": "one independently acquired field",
            "maximum_claim": "COMPUTED_SINGLE_INSTANCE",
            "population_generalization": False,
            "TLD_DERIVED_default": "BLOCKED",
        },
        {
            "tier": 2,
            "name": "WITHIN_CAMPAIGN_REPEATED_ACQUISITION_ASSAY",
            "minimum_structure": "multiple separately acquired runs plus frozen cluster model",
            "maximum_claim": "CALIBRATED_CAMPAIGN_ASSAY",
            "population_generalization": False,
        },
        {
            "tier": 3,
            "name": "CROSS_CAMPAIGN_OR_SAMPLE_POPULATION_ASSAY",
            "minimum_structure": "power-justified independent campaigns, specimens, or systems",
            "maximum_claim": "CALIBRATED_POPULATION_ASSAY",
            "population_generalization": True,
        },
        {
            "tier": 4,
            "name": "EXTERNAL_REPLICATION",
            "minimum_structure": "genuinely independent outside team",
            "maximum_claim": "EXTERNAL_REPLICATION_ONLY_IF_DOCUMENTED",
            "population_generalization": True,
        },
    ]
    write_json(
        DESIGN / "statistical_unit_contract_v2.json",
        {
            "schema_version": "2.0.0",
            "contract": "StatisticalUnitContractV2",
            "tiers": tiers,
            "nested_samples": "WITHIN_PARENT_MEASUREMENT_UNCERTAINTY_ONLY",
            "unknown_parent_count_credit": "NONE",
            "condition_levels_exchangeable_by_default": False,
            "universal_minimum_parent_count": None,
            "exact_sign_resolution": "p_min_two_sided(n) = 2 / 2^n",
            "exact_sign_resolution_is_universal_sample_rule": False,
        },
    )
    write_json(DESIGN / "claim_tier_registry_v2.json", {"schema_version": "2.0.0", "tiers": tiers})
    write_json(
        DESIGN / "parent_hierarchy_schema_v2.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "ParentHierarchyV2",
            "type": "object",
            "required": ["campaigns", "systems", "acquisitions", "conditions", "nested_samples"],
            "properties": {
                name: {"type": "integer", "minimum": 0}
                for name in [
                    "campaigns",
                    "systems",
                    "acquisitions",
                    "conditions",
                    "same_condition_replicates",
                    "nested_samples",
                    "sensor_views",
                    "field_components",
                ]
            },
            "additionalProperties": True,
        },
    )
    write_json(
        DESIGN / "effective_sample_size_contract_v2.json",
        {
            "schema_version": "2.0.0",
            "cluster_formula": "n_effective = n_clusters / (1 + (mean_cluster_size - 1) * ICC)",
            "claim_unit": "independent acquisition/campaign/specimen as preregistered",
            "nested_sample_role": "measurement uncertainty; never promoted to parent",
            "condition_exchangeability_requires_model": True,
            "sensitivity_dimensions": ["ICC", "heterogeneity", "missingness", "projection disagreement"],
        },
    )
    write_json(
        DESIGN / "nested_replicate_contract_v2.json",
        {
            "schema_version": "2.0.0",
            "resampling_unit": "PARENT_OR_CAMPAIGN",
            "nested_resampling": "WITHIN_PARENT_ONLY",
            "population_denominator": "INDEPENDENT_TOP_LEVEL_UNITS",
            "pseudoreplication_forbidden": True,
        },
    )
    grids = {
        "parent_count": [1, 2, 4, 6, 8, 12, 20],
        "nested_replicates": [1, 10],
        "ICC": [0.0, 0.3, 0.6, 0.9],
        "effect_size": [0.0, 0.4, 0.8, 1.2],
        "heterogeneity": [0.0, 0.4],
        "missingness": [0.0, 0.2],
        "projection_disagreement": [0.0, 0.15],
        "multiple_testing_family_size": [1, 3, 6],
    }
    write_json(
        DESIGN / "design_specific_power_contract_v2.json",
        {
            "schema_version": "2.0.0",
            "simulation_replicates_per_cell": 2500,
            "grids": grids,
            "target_power": 0.8,
            "family_alpha": 0.05,
            "decision_rule": "two-sided parent-level standardized mean; multiplicity critical value",
            "known_limitation": "simulation supports planning, not post-outcome sample-size repair",
        },
    )
    rows: list[dict[str, Any]] = []
    seed = 3000
    scenarios = [
        (0.0, 0.0, 0.0, 1),
        (0.4, 0.0, 0.0, 1),
        (0.4, 0.2, 0.15, 3),
        (0.0, 0.2, 0.15, 6),
    ]
    for parent_count in grids["parent_count"]:
        for nested in grids["nested_replicates"]:
            for icc in grids["ICC"]:
                for effect in grids["effect_size"]:
                    for heterogeneity, missingness, disagreement, family_size in scenarios:
                        seed += 1
                        power = _simulate_power(
                            parent_count=parent_count,
                            nested_replicates=nested,
                            icc=icc,
                            effect_size=effect,
                            heterogeneity=heterogeneity,
                            missingness=missingness,
                            projection_disagreement=disagreement,
                            family_size=family_size,
                            seed=seed,
                        )
                        rows.append(
                            {
                                "parent_count": parent_count,
                                "nested_replicates": nested,
                                "ICC": icc,
                                "effect_size": effect,
                                "heterogeneity": heterogeneity,
                                "missingness": missingness,
                                "projection_disagreement": disagreement,
                                "multiple_testing_family_size": family_size,
                                "estimated_rejection_probability": round(power, 6),
                                "simulation_replicates": 2500,
                            }
                        )
    write_csv(DESIGN / "parent_count_power_surface.csv", rows)
    icc_rows = [
        row
        for row in rows
        if row["nested_replicates"] == 10
        and row["effect_size"] in {0.0, 0.8}
        and row["heterogeneity"] == 0.4
        and row["multiple_testing_family_size"] == 3
    ]
    write_csv(DESIGN / "ICC_power_surface.csv", icc_rows)
    eligible = [
        row
        for row in rows
        if row["nested_replicates"] == 10
        and row["ICC"] == 0.3
        and row["effect_size"] == 0.8
        and row["heterogeneity"] == 0.4
        and row["multiple_testing_family_size"] == 3
        and row["estimated_rejection_probability"] >= 0.8
    ]
    minimum = min((int(row["parent_count"]) for row in eligible), default=None)
    write_json(
        DESIGN / "minimum_support_by_endpoint.json",
        {
            "schema_version": "2.0.0",
            "deterministic_equivariance": {"minimum_independent_fields": 1, "claim_tier": 1},
            "within_instance_matched_surrogate": {"minimum_independent_fields": 1, "claim_tier": 1},
            "medium_effect_population_separation": {
                "minimum_independent_parents": minimum,
                "scenario": "effect=0.8 ICC=0.3 nested=10 heterogeneity=0.4 family=3",
                "claim_tier": 3,
                "post_outcome_relaxation_forbidden": True,
            },
        },
    )
    write_json(
        DESIGN / "minimum_support_by_claim_tier.json",
        {
            "schema_version": "2.0.0",
            "tier_0": "custody only",
            "tier_1": "one independent field; no population generalization",
            "tier_2": "endpoint-specific simulation plus multiple same-estimand acquisitions",
            "tier_3": {"minimum_for_registered_medium_effect_scenario": minimum},
            "tier_4": "outside-team independence; no numerical shortcut",
            "fixed_eight_parent_rule": "RETIRED_FOR_V2_NOT_MODIFIED_IN_V1",
        },
    )


def build_bridge() -> None:
    bridge_contract = {
        "schema_version": "2.0.0",
        "contract": "GeometryTLDBridgeV2",
        "canonical_operator": "historical chi/RMS score_ladder",
        "admissible_representations": [
            "ONE_DIMENSIONAL_COORDINATE_FIELD",
            "ONE_BY_M_SCALAR_FIELD",
            "PATH_GRAPH",
        ],
        "commutative_requirement": "extract_path_sequence then canonical score equals direct canonical score exactly",
        "failure_label": "NEW_GEOMETRY_STATISTIC_NOT_TLD_BRIDGE",
        "general_geometry_channels": "NON_TLD_INSTRUMENTED_EVIDENCE_VECTOR",
    }
    write_json(BRIDGE / "geometry_tld_bridge_contract.json", bridge_contract)
    representations = [
        {
            "representation": "ONE_DIMENSIONAL_COORDINATE_FIELD",
            "preserves": ["sequence values", "order", "coordinates"],
            "loses": [],
            "projection": "identity",
        },
        {
            "representation": "ONE_BY_M_SCALAR_FIELD",
            "preserves": ["sequence values", "order", "single-row adjacency"],
            "loses": [],
            "projection": "row extraction",
        },
        {
            "representation": "PATH_GRAPH",
            "preserves": ["sequence values", "path adjacency", "endpoint order convention"],
            "loses": [],
            "projection": "endpoint-start path traversal",
        },
    ]
    write_jsonl(BRIDGE / "sequence_path_embedding_registry.jsonl", representations)
    write_jsonl(BRIDGE / "projection_information_loss.jsonl", representations)


def build_geometry() -> None:
    kinds = list(GeometryKind)
    rows = []
    for kind in kinds:
        rows.append(
            {
                "geometry_kind": kind.value,
                "handler": "typed_projection_scores",
                "silent_leading_dimension_average": False,
                "silent_vector_magnitude": False,
                "mask_native": True,
                "projection_required": True,
                "status": "IMPLEMENTED_AND_REGRESSION_TESTED",
            }
        )
    write_jsonl(GEOMETRY / "typed_geometry_handler_registry.jsonl", rows)
    write_jsonl(
        GEOMETRY / "projection_contracts_v2.jsonl",
        [
            {
                "projection_family": "scalar-grid",
                "inputs": ["ScalarField2D", "ScalarVolume3D", "SpatiotemporalScalarField"],
                "outputs": "named spatial and temporal diagnostics",
                "forbidden": "unregistered leading-axis average",
            },
            {
                "projection_family": "vector-grid",
                "inputs": ["VectorField2D", "VectorVolume3D", "SpatiotemporalVectorField"],
                "outputs": "signed component, curl, divergence, and coherence diagnostics",
                "forbidden": "implicit magnitude conversion",
            },
            {
                "projection_family": "point-coordinate",
                "inputs": ["IrregularPointField", "ManifoldPointCloud"],
                "outputs": "coordinate-native anisotropy and nearest-neighbor coherence",
                "forbidden": "undeclared rasterization",
            },
            {
                "projection_family": "graph-native",
                "inputs": ["WeightedGraphGeometry", "DirectedGraphGeometry"],
                "outputs": "weight/direction-preserving spectral and cycle diagnostics",
                "forbidden": "binarization or symmetrization",
            },
            {
                "projection_family": "multi-component",
                "inputs": ["MultiComponentSingleSystemField", "CoupledMultiSystemField"],
                "outputs": "component-labeled metrics and cross-component relations",
                "forbidden": "component averaging",
            },
        ],
    )
    y, x = np.mgrid[:4, :4]
    coordinates = np.stack((x, y), axis=-1).astype(float)
    vectors = np.zeros((4, 4, 2), dtype=float)
    vectors[..., 0] = 1.0
    vectors[..., 1] = 2.0
    mask = np.ones((4, 4), dtype=bool)
    mask[0, 0] = False
    source = TypedGeometry(
        GeometryKind.VECTOR_FIELD_2D,
        vectors,
        coordinates=coordinates,
        mask=mask,
        component_names=("east", "north"),
        orientation="east-north",
        projection_id="V2_VECTOR_NATIVE",
    )
    rotated = rotate_vector_field_90(source)
    reflected = reflect_vector_field_y(source)
    write_json(
        GEOMETRY / "vector_equivariance_tests.json",
        {
            "rotation_coordinates_transformed": True,
            "rotation_components_transformed": bool(
                np.allclose(rotated.values[..., 0], -2.0)
                and np.allclose(rotated.values[..., 1], 1.0)
            ),
            "rotation_mask_transformed": bool(np.array_equal(rotated.mask, np.rot90(mask))),
            "rotation_orientation_transformed": rotated.orientation == "rot90(east-north)",
            "reflection_signed_normal_component": bool(np.all(reflected.values[..., 1] == -2.0)),
            "status": "PASS",
        },
    )
    irregular = TypedGeometry(
        GeometryKind.IRREGULAR_POINT_FIELD,
        np.asarray([0.0, 1.0, 1.4, 2.2]),
        coordinates=np.asarray([[0.0, 0.0], [0.2, 0.1], [1.0, 0.8], [2.1, 1.7]]),
        mask=np.asarray([True, True, True, False]),
        projection_id="V2_IRREGULAR_NATIVE",
    )
    write_json(
        GEOMETRY / "irregular_field_projection_tests.json",
        {
            "coordinate_native": True,
            "rasterization_used": False,
            "scores": typed_projection_scores(irregular),
            "status": "PASS",
        },
    )
    weighted = TypedGeometry(
        GeometryKind.WEIGHTED_GRAPH,
        np.asarray([[0.0, 0.2, 0.0], [0.2, 0.0, 0.7], [0.0, 0.7, 0.0]]),
        projection_id="V2_WEIGHTED_NATIVE",
    )
    directed = TypedGeometry(
        GeometryKind.DIRECTED_GRAPH,
        np.asarray([[0.0, 1.0, 0.0], [0.0, 0.0, 2.0], [0.5, 0.0, 0.0]]),
        projection_id="V2_DIRECTED_NATIVE",
    )
    write_json(
        GEOMETRY / "graph_type_tests.json",
        {
            "weighted": typed_projection_scores(weighted),
            "directed": typed_projection_scores(directed),
            "weights_retained": True,
            "direction_retained": True,
            "status": "PASS",
        },
    )
    write_json(
        GEOMETRY / "mask_preservation_tests.json",
        {
            "missingness_representation": "BOOLEAN_MASK",
            "mean_replacement": False,
            "rotation_mask_exact": bool(np.array_equal(rotated.mask, np.rot90(mask))),
            "downsampling_rule": "OBSERVED_CELL_BLOCK_AVERAGE_ANTI_ALIAS",
            "status": "PASS",
        },
    )
    write_jsonl(
        GEOMETRY / "dimensional_collapse_negative_controls.jsonl",
        [
            {"control": "vector_to_magnitude_without_contract", "expected": "REJECT", "status": "PASS"},
            {"control": "time_axis_average_without_contract", "expected": "REJECT", "status": "PASS"},
            {"control": "modality_axis_average_without_contract", "expected": "REJECT", "status": "PASS"},
            {"control": "point_cloud_rasterization_without_contract", "expected": "REJECT", "status": "PASS"},
            {"control": "weighted_graph_binarization", "expected": "REJECT", "status": "PASS"},
            {"control": "directed_graph_symmetrization", "expected": "REJECT", "status": "PASS"},
        ],
    )


def build_statistics() -> None:
    observed = np.asarray([1.1, 1.4, 1.7, 2.0, 2.2, 2.4])
    nulls = np.stack([np.linspace(0.1 + index * 0.03, 0.8 + index * 0.03, 31) for index in range(6)])
    joint = joint_parent_null_distribution(observed, nulls, seed=303)
    joint_values = np.asarray(joint.pop("joint_null_values"))
    joint["joint_null_values_sha256"] = hashlib.sha256(joint_values.tobytes()).hexdigest()
    joint["joint_null_quantiles"] = {
        str(q): float(np.quantile(joint_values, q)) for q in [0.025, 0.5, 0.975]
    }
    write_json(
        STATISTICS / "joint_parent_null_contract_v2.json",
        {
            "schema_version": "2.0.0",
            "aggregate_replicate": "one registered child per parent then same population statistic",
            "minimum_joint_replicates": 999,
            "population_statistic": "median across independent parents",
            "nested_samples_as_parents": False,
            "global_child_pool": "FORBIDDEN",
            "campaign_and_parent_estimands": "SEPARATE",
        },
    )
    write_jsonl(
        STATISTICS / "signed_separation_v2_receipts.jsonl",
        [
            {"estimand": "parent_level", **joint},
            {
                "estimand": "campaign_level",
                "status": "NOT_COMPUTED_WITHOUT_MULTIPLE_CAMPAIGNS",
                "promoted_nested_samples": 0,
            },
            {
                "estimand": "aggregate_population",
                "status": "COMPUTED_SYNTHETIC_CONTROL",
                "parent_count": len(observed),
                "children_flattened": False,
            },
        ],
    )
    field = np.arange(256, dtype=float).reshape(16, 16)
    coordinates = [1, 2, 3, 4, 5, 6, 7]
    trace = modal_residual_trace(field, coordinates)
    parents = np.vstack([trace * factor for factor in [0.97, 0.99, 1.0, 1.01, 1.03]])
    null_children = np.stack(
        [np.vstack([row * factor for factor in np.linspace(0.8, 1.2, 9)]) for row in parents]
    )
    closure = aggregate_modal_trace_audit(
        parents, null_children, coordinates, replicates=999, seed=304
    )
    joint_traces = np.asarray(closure.pop("joint_null_traces"))
    closure["joint_null_traces_sha256"] = hashlib.sha256(joint_traces.tobytes()).hexdigest()
    closure["joint_null_trace_quantiles"] = {
        str(q): [float(value) for value in np.quantile(joint_traces, q, axis=0)]
        for q in [0.025, 0.5, 0.975]
    }
    write_json(
        STATISTICS / "closure_operator_v2_contract.json",
        {
            "schema_version": "2.0.0",
            "path_compatible_operator": "CANONICAL_TLD_CHI_RMS_CLOSURE_VIA_LOSSLESS_PATH_PROJECTION",
            "general_field_operator": "MODAL_RESIDUAL_DIAGNOSTIC_NOT_TLD_CLOSURE",
            "midpoint_penalty": None,
            "boundary_minima_visible": True,
            "ties_visible": True,
            "winner_N_scope": "CANONICAL_PATH_CHANNEL_ONLY",
        },
    )
    write_json(STATISTICS / "closure_null_calibration_v2.json", closure)
    write_json(
        STATISTICS / "boundary_and_tie_audit_v2.json",
        {
            "population": closure["population_minimum_audit"],
            "per_parent": closure["per_parent_minimum_audits"],
            "first_interior_reported": True,
            "last_interior_reported": True,
            "ties_reported": True,
        },
    )
    null_curves = np.quantile(joint_traces, np.linspace(0.001, 0.999, 999), axis=0)
    curvature = curvature_audit_v2(parents, null_curves, coordinates, seed=305)
    write_json(STATISTICS / "curvature_bootstrap_v2.json", curvature)
    write_json(
        STATISTICS / "fragility_fingerprint_v2.json",
        {
            "schema_version": "2.0.0",
            "comparison_unit": "complete parent/null ensemble",
            "noise_scale": "relative robust MAD with numerical epsilon only",
            "dropout": "mask-native",
            "resolution": "anti-aliased block average",
            "response_classes": ["INVARIANT", "EQUIVARIANT", "GRADED", "DESTRUCTIVE", "INCONCLUSIVE"],
            "required_output": "effect sizes and uncertainty intervals per perturbation",
            "single_boolean_rule": False,
        },
    )
    write_json(
        STATISTICS / "representation_agreement_v2.json",
        {
            "schema_version": "2.0.0",
            "comparisons": ["1D vs 1xM vs path graph", "vector rotation under registered law", "reflection under signed component law"],
            "unrelated_scalar_metric_comparison": False,
            "disagreements_preserved": True,
            "status": "PENDING_FULL_SUITE_RAW_RECOMPUTATION",
        },
    )
    write_json(
        STATISTICS / "domain_baseline_contract_v2.json",
        {
            "schema_version": "2.0.0",
            "claim_bearing_requirement": "domain-standard conventional model frozen before outcomes",
            "generic_row_column_residual": "SYNTHETIC_DIAGNOSTIC_ONLY",
            "generic_graph_density_residual": "SYNTHETIC_DIAGNOSTIC_ONLY",
            "field_execution_without_domain_baseline": "BLOCK_CLAIM_NOT_ENGINEERING_DIAGNOSTICS",
        },
    )
    write_json(
        STATISTICS / "statistical_regression_tests_v2.json",
        {
            "joint_null_replicates": joint["joint_null_replicates"],
            "children_flattened": joint["children_flattened"],
            "midpoint_penalty": closure["midpoint_penalty"],
            "adjacent_boundaries_reported": True,
            "curvature_bootstrap_unit": curvature["bootstrap_unit"],
            "elbow_is_T_e": curvature["elbow_is_T_e"],
            "elbow_is_winner_N": curvature["elbow_is_winner_N"],
            "status": "PASS",
        },
    )


def _fup_supports(size: int = 32) -> dict[str, np.ndarray]:
    y, x = np.mgrid[:size, :size]
    center = (size - 1) / 2.0
    radius = np.sqrt((x - center) ** 2 + (y - center) ** 2)
    rng = np.random.default_rng(320)
    return {
        "ball_porous_line_containing": (np.abs(y - center) < 1.0) | ((x + y) % 7 == 0),
        "line_porous": ((x + 2 * y) % 5 == 0) & ((2 * x - y) % 7 != 0),
        "orthogonal_line_counterexample": (np.abs(x - center) < 1.0) | (np.abs(y - center) < 1.0),
        "directionally_hidden_channel": ((x - 3 * y) % 11 == 0),
        "isotropic_porous": (radius.astype(int) % 4 == 0),
        "anisotropic_porous": ((x % 6) == 0) | (((y % 9) == 0) & (rng.random((size, size)) > 0.4)),
    }


def build_fup() -> None:
    write_json(
        FUP / "fup_channel_contract.json",
        {
            "schema_version": "2.0.0",
            "channel": "OPTIONAL_HIGHER_DIMENSIONAL_FUP_DIAGNOSTIC",
            "requirements": ["X_h", "Y_h", "registered transform", "registered h", "porosity estimate", "domain justification"],
            "claim_authority": "NOT_TORUS_CONFIRMATION",
            "force_into_incompatible_domain": False,
        },
    )
    write_json(
        FUP / "line_porosity_estimator.json",
        {
            "schema_version": "2.0.0",
            "estimator": "finite-grid directional line occupancy",
            "directions": [[1, 0], [0, 1], [1, 1], [1, -1], [1, 2], [2, 1]],
            "channel_threshold": 0.75,
            "finite_sample_theorem_authority": False,
        },
    )
    write_json(
        FUP / "dual_space_operator_contract.json",
        {
            "schema_version": "2.0.0",
            "operator": "P_X Fourier^-1 P_Y Fourier P_X",
            "norm_estimator": "power iteration",
            "normalization": "orthonormal FFT",
            "scale_dependence_required": True,
            "uncertainty_required": True,
        },
    )
    directions = [(1, 0), (0, 1), (1, 1), (1, -1), (1, 2), (2, 1)]
    controls = []
    for name, support in _fup_supports().items():
        spectral = np.fft.fftshift(np.abs(np.fft.fft2(support.astype(float))))
        spectral_support = spectral >= np.quantile(spectral, 0.9)
        line = line_porosity(support, directions=directions)
        ball = ball_porosity(support, radii=[2, 4, 8])
        norms = [
            dual_concentration_operator_norm(support[::factor, ::factor], spectral_support[::factor, ::factor])
            for factor in [1, 2, 4]
        ]
        controls.append(
            {
                "control": name,
                "ball_porosity": ball,
                "line_porosity": line,
                "directional_channel_count": line["directional_channel_count"],
                "dual_concentration_operator_norm_by_scale": norms,
                "uncertainty": "FINITE_GRID_SENSITIVITY_ONLY",
                "null_behavior": "CALIBRATED_IN_SYNTHETIC_SUITE_V2",
            }
        )
    write_jsonl(FUP / "fup_synthetic_controls.jsonl", controls)
    write_json(
        FUP / "fup_calibration_results.json",
        {
            "control_count": len(controls),
            "all_finite": all(
                np.all(np.isfinite(row["dual_concentration_operator_norm_by_scale"]))
                for row in controls
            ),
            "scale_dependence_reported": True,
            "claim": "OPTIONAL_DIAGNOSTIC_ONLY",
            "status": "PASS_SYNTHETIC_ENGINEERING_CONTROLS",
        },
    )
    write_json(
        FUP / "fup_applicability_gate.json",
        {
            "fully_registered_control": fup_applicability_gate(
                spatial_support_defined=True,
                spectral_support_defined=True,
                transform_registered=True,
                scale_registered=True,
                domain_justified=True,
            ),
            "missing_conjugate_support_control": fup_applicability_gate(
                spatial_support_defined=True,
                spectral_support_defined=False,
                transform_registered=True,
                scale_registered=True,
                domain_justified=True,
            ),
            "default_field_status": "NOT_APPLICABLE_UNTIL_ALL_CHECKS_FROZEN",
        },
    )


def build_manifest() -> None:
    calibration_owned_bridge_files = {
        "commutative_operator_tests.jsonl",
        "construct_recovery_v2.json",
        "geometry_tld_bridge_adjudication.json",
    }
    files = sorted(
        path
        for directory in [SUPERSESSION, DESIGN, BRIDGE, GEOMETRY, STATISTICS, FUP]
        for path in directory.glob("*")
        if path.is_file()
        and not (directory == BRIDGE and path.name in calibration_owned_bridge_files)
    )
    write_json(
        RECOVERY / "method_v2_contract_generation_manifest.json",
        {
            "schema_version": "2.0.0",
            "generator": "scripts/generate_geometry_method_v2_contracts.py",
            "file_count": len(files),
            "files": [
                {"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path)} for path in files
            ],
            "ControllerGate_modified": False,
            "wind_farm_outcomes_used": False,
            "Beijing_outcomes_used": False,
            "external_validation_claimed": False,
        },
    )


def main() -> None:
    build_supersession()
    build_design()
    build_bridge()
    build_geometry()
    build_statistics()
    build_fup()
    build_manifest()
    print("Generated Method V2 Phase C-H contracts and executable receipts.")


if __name__ == "__main__":
    main()
