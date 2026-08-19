# ruff: noqa: E501 -- frozen registry prose and source identifiers remain verbatim.
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
from netCDF4 import Dataset

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "external_cache" / "v0.3.0-field-18731994"
DEFAULT_PROBE = DEFAULT_SOURCE / "structure_probe.json"
DEFAULT_OUT = ROOT / "studies" / "v0.3.0-field-assay" / "materialization"
DATASET_FREEZE_COMMIT = "70fa574350ecff8c021ed61ad121c07edb3d581f"
METHOD_FREEZE_COMMIT = "827b3394c0ce8ed414ca57d8e77ef1aaf1a72b1c"


def write_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def variable(dataset: Dataset, path: str) -> Any:
    value: Any = dataset
    for part in path.strip("/").split("/"):
        value = value[part]
    return value


def finite_summary(array: np.ndarray[Any, Any]) -> dict[str, Any]:
    values = np.asarray(array, dtype=np.float64)
    finite = values[np.isfinite(values)]
    if not len(finite):
        return {
            "size": int(values.size),
            "finite_count": 0,
            "missing_count": int(values.size),
        }
    return {
        "size": int(values.size),
        "finite_count": int(len(finite)),
        "missing_count": int(values.size - len(finite)),
        "minimum": float(np.min(finite)),
        "maximum": float(np.max(finite)),
        "median": float(np.median(finite)),
    }


def load_probe(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8"))
    if result["inspection_mode"] != "STRUCTURE_AND_DOMAIN_METADATA_ONLY_NO_CLAIM_METRICS":
        raise SystemExit("Unexpected structural probe mode")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze the v0.3.0 field domain translation")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--probe", type=Path, default=DEFAULT_PROBE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    source = args.source_dir.resolve()
    probe_path = args.probe.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    probe = load_probe(probe_path)
    shutil.copyfile(probe_path, out / "netcdf_structure.json")

    matrix_rows = probe["test_matrix"]["sheets"][0]["rows"]
    structure_by_member = {row["member"]: row for row in probe["netcdf"]}
    archive_by_member = {
        row["member"]: row for row in probe["archive_inventory"] if not row["is_directory"]
    }
    expected_members = {str(row["Data_nc_file"]) for row in matrix_rows}
    if expected_members != set(structure_by_member) or expected_members != set(archive_by_member):
        raise SystemExit("Test matrix, archive, and NetCDF inventory do not agree")

    source_rows = []
    for row in probe["source_custody"]:
        source_rows.append(
            {
                "source_kind": "ZENODO_DEPOSITED_OBJECT",
                "doi": "10.5281/zenodo.18731994",
                "record_id": 18731994,
                **row,
                "verified": True,
            }
        )
    for member, row in sorted(archive_by_member.items()):
        source_rows.append(
            {
                "source_kind": "ARCHIVE_MEMBER",
                "container": "Multiple Wake.zip",
                "name": member,
                "size_bytes": row["uncompressed_size"],
                "crc32": row["crc32"],
                "sha256": row["sha256"],
                "verified": True,
            }
        )
    write_jsonl(out / "raw_source_manifest.jsonl", source_rows)

    parents = []
    nested = []
    fields = []
    coordinates = []
    coordinate_checks = []
    field_checks = []
    for row in matrix_rows:
        test_id = int(row["TEST_ID"])
        member = str(row["Data_nc_file"])
        parent_id = f"PARENT_TEST_{test_id}"
        path = source / "extracted" / member
        if sha256(path) != structure_by_member[member]["sha256"]:
            raise SystemExit(f"Extracted member hash changed: {member}")
        with Dataset(path, "r") as dataset:
            time_size = int(variable(dataset, "/Time").size)
            avg = {
                axis: np.asarray(variable(dataset, f"/LidarData/AvgPosition/{axis}")[:])
                for axis in ("x", "y", "z")
            }
            lidar_fields = {
                "R2D2_vLOS": np.asarray(variable(dataset, "/LidarData/R2D2/vLOS")[:]),
                "R2D3_vLOS": np.asarray(variable(dataset, "/LidarData/R2D3/vLOS")[:]),
                "ux": np.asarray(variable(dataset, "/LidarData/ux")[:]),
                "uy": np.asarray(variable(dataset, "/LidarData/uy")[:]),
            }
            lidar_size = int(lidar_fields["ux"].size)
            if not all(value.size == lidar_size for value in (*avg.values(), *lidar_fields.values())):
                raise SystemExit(f"Lidar arrays are not aligned: {member}")
            common_mask = np.logical_and.reduce(
                [np.isfinite(value) for value in (*avg.values(), *lidar_fields.values())]
            )
            parent_role = "DOMAIN_CONTROL_BASELINE" if test_id == 1 else "YAW_INTERVENTION"
            parents.append(
                {
                    "parent_id": parent_id,
                    "test_id": test_id,
                    "member": member,
                    "member_sha256": structure_by_member[member]["sha256"],
                    "role": parent_role,
                    "control_label": row["Testesd_CTRL"],
                    "start_time_source_text": row["Test_Start_Data_Time"],
                    "duration_seconds": row["Duration_sec"],
                    "inflow_class": row["ABL_type"],
                    "pitot_reference_m_per_s": row["Pitot_wind_speed_ms-1"],
                    "flow_measurement_type": row["Flow_Meas_Type"],
                    "flow_measurement_location": row["Flow_Meas_Loc_D_mm"],
                    "wt1_yaw_deg": row["WT1_yaw_mis_deg"],
                    "wt2_yaw_deg": row["WT2_yaw_mis_deg"],
                    "wt3_yaw_deg": row["WT3_yaw_mis_deg"],
                    "independence_basis": "separate non-overlapping 600 s acquisition and separate NetCDF member",
                    "shared_campaign_caveat": "all four runs share one facility campaign and date",
                }
            )
            nested.append(
                {
                    "parent_id": parent_id,
                    "nested_replicate_kind": "synchronized_time_sample",
                    "lidar_sample_count": lidar_size,
                    "high_frequency_time_count": time_size,
                    "common_complete_lidar_sample_count": int(np.sum(common_mask)),
                    "independent_parent": False,
                    "pooling_as_independent_parent": "FORBIDDEN",
                }
            )
            for field_id, field_path, observation_class in (
                ("R2D2_VLOS", "/LidarData/R2D2/vLOS", "RAW_OBSERVATION"),
                ("R2D3_VLOS", "/LidarData/R2D3/vLOS", "RAW_OBSERVATION"),
                ("UX", "/LidarData/ux", "SOURCE_DERIVED_OBSERVATION"),
                ("UY", "/LidarData/uy", "SOURCE_DERIVED_OBSERVATION"),
            ):
                fields.append(
                    {
                        "field_id": f"{parent_id}_{field_id}",
                        "parent_id": parent_id,
                        "netcdf_path": field_path,
                        "shape": [lidar_size],
                        "dtype": "float64",
                        "units": "m/s",
                        "unit_provenance": "cross-source alignment to TestMatrix Pitot_wind_speed_ms-1; NetCDF attribute absent",
                        "observation_class": observation_class,
                        "claim_eligible": True,
                        "missing_values_are_observations": False,
                    }
                )
            for coordinate_id, coordinate_path in (
                ("AVG_X", "/LidarData/AvgPosition/x"),
                ("AVG_Y", "/LidarData/AvgPosition/y"),
                ("AVG_Z", "/LidarData/AvgPosition/z"),
                ("R2D2_X", "/LidarData/R2D2/Position/x"),
                ("R2D2_Y", "/LidarData/R2D2/Position/y"),
                ("R2D2_Z", "/LidarData/R2D2/Position/z"),
                ("R2D3_X", "/LidarData/R2D3/Position/x"),
                ("R2D3_Y", "/LidarData/R2D3/Position/y"),
                ("R2D3_Z", "/LidarData/R2D3/Position/z"),
            ):
                coordinate = np.asarray(variable(dataset, coordinate_path)[:])
                coordinates.append(
                    {
                        "coordinate_id": f"{parent_id}_{coordinate_id}",
                        "parent_id": parent_id,
                        "netcdf_path": coordinate_path,
                        "units": "mm",
                        "unit_provenance": "cross-source alignment to TestMatrix *_Pos_*_mm and 925 mm measurement-plane label; NetCDF attribute absent",
                        "summary": finite_summary(coordinate),
                        "coordinate_role": "OBSERVED_SAMPLE_LOCATION",
                    }
                )
            coordinate_checks.append(
                {
                    "parent_id": parent_id,
                    "common_complete_count": int(np.sum(common_mask)),
                    "x": finite_summary(avg["x"]),
                    "y": finite_summary(avg["y"]),
                    "z": finite_summary(avg["z"]),
                    "planar_z_span_mm": float(np.nanmax(avg["z"]) - np.nanmin(avg["z"])),
                    "test_matrix_plane_reference_mm": 925,
                    "units_resolved": True,
                    "native_unit_attribute_present": False,
                }
            )
            field_checks.append(
                {
                    "parent_id": parent_id,
                    "aligned_shape": [lidar_size],
                    "common_complete_count": int(np.sum(common_mask)),
                    "components": {
                        name: {
                            "finite_count": int(np.sum(np.isfinite(value))),
                            "missing_count": int(value.size - np.sum(np.isfinite(value))),
                        }
                        for name, value in lidar_fields.items()
                    },
                    "all_components_nonconstant": all(
                        float(np.nanmax(value) - np.nanmin(value)) > 0.0
                        for value in lidar_fields.values()
                    ),
                }
            )

    write_jsonl(out / "field_registry.jsonl", fields)
    write_jsonl(out / "coordinate_registry.jsonl", coordinates)
    write_jsonl(out / "parent_registry.jsonl", parents)
    write_jsonl(out / "nested_replicate_registry.jsonl", nested)

    projections = [
        {
            "projection_id": "P01_SOURCE_RECONSTRUCTED_VECTOR_GRID",
            "claim_role": "PRIMARY_FAITHFUL_PROJECTION",
            "inputs": ["/LidarData/ux", "/LidarData/uy", "/LidarData/AvgPosition/{x,y,z}"],
            "observation_class": "SOURCE_DERIVED_OBSERVATION",
            "construction": "componentwise median in a fixed 250 mm Cartesian bin; no interpolation; empty cells remain missing",
            "minimum_samples_per_cell": 8,
            "vector_components_pooled_numerically": False,
            "justification": "source-provided dual-lidar reconstruction on source-provided average positions",
        },
        {
            "projection_id": "P02_DUAL_NATIVE_LOS_EVIDENCE_VECTOR",
            "claim_role": "SECONDARY_FAITHFUL_PROJECTION",
            "inputs": ["R2D2 vLOS and native Position", "R2D3 vLOS and native Position"],
            "observation_class": "RAW_OBSERVATION",
            "construction": "each lidar is binned independently at 250 mm; channel results remain separate",
            "minimum_samples_per_cell": 8,
            "modalities_pooled_numerically": False,
            "justification": "retains the two physical lines of sight without reconstruction averaging",
        },
        {
            "projection_id": "P03_OCCUPIED_CELL_GRAPH",
            "claim_role": "DIAGNOSTIC_ONLY",
            "inputs": ["occupied P01 cells"],
            "observation_class": "PROJECTION",
            "construction": "8-neighbor graph over occupied Cartesian cells",
            "justification": "audits footprint topology; it cannot support a field claim by itself",
        },
    ]
    write_jsonl(out / "projection_registry.jsonl", projections)

    nulls = [
        {
            "null_id": "N01_PARENT_LOCAL_CYCLIC_FIELD_SHIFT",
            "target_destroyed": "alignment between lidar field values and observed sample coordinates",
            "preserved": ["parent", "value marginals", "missing mask", "time order", "coordinate path"],
            "construction": "apply one registered nonzero circular offset to all field components within each parent before fixed projection",
            "children_per_parent": 127,
            "parent_pooling": "FORBIDDEN",
            "seed_policy": "preregistered deterministic SeedSequence from root seed 300",
            "bias_diagnostics_required": True,
        },
        {
            "null_id": "N02_PARENT_LOCAL_CONTIGUOUS_BLOCK_PERMUTATION",
            "target_destroyed": "large-scale field-to-geometry organization",
            "preserved": ["parent", "within-block temporal dependence", "value marginals", "missing mask", "coordinates"],
            "construction": "permute fixed 5 s synchronized blocks within parent before fixed projection",
            "children_per_parent": 127,
            "parent_pooling": "FORBIDDEN",
            "seed_policy": "preregistered deterministic SeedSequence from root seed 300",
            "bias_diagnostics_required": True,
        },
    ]
    write_jsonl(out / "null_registry.jsonl", nulls)

    perturbations = [
        {
            "perturbation_id": "PERT01_REVERSE_SAMPLE_ORDER",
            "class": "REPRESENTATION_INVARIANCE",
            "expected": "fixed spatial projection and evidence vector invariant",
        },
        {
            "perturbation_id": "PERT02_REFLECT_Y_AND_FLIP_UY",
            "class": "PHYSICAL_EQUIVARIANCE",
            "expected": "scalar channel evidence invariant and signed y-directed quantities equivariant",
        },
        {
            "perturbation_id": "PERT03_COORDINATE_JITTER_12_5_MM",
            "class": "METROLOGY_ROBUSTNESS",
            "expected": "bounded degradation without claim reversal",
        },
        {
            "perturbation_id": "PERT04_GRID_ORIGIN_HALF_CELL",
            "class": "PROJECTION_ROBUSTNESS",
            "expected": "representation result retained or exact disagreement reported",
        },
        {
            "perturbation_id": "PERT05_DROP_ONE_LIDAR",
            "class": "ADVERSARIAL_MISSING_MODALITY",
            "expected": "P02 ineligible; never silently reconstructed or called robust",
        },
    ]
    write_jsonl(out / "perturbation_registry.jsonl", perturbations)

    write_jsonl(
        out / "operation_depth_registry.jsonl",
        [
            {
                "operation_id": "GRAPH_DIFFUSION_ON_OCCUPIED_GRID",
                "recursive": True,
                "depth_values": list(range(0, 17)),
                "primary_depth_range": list(range(0, 17)),
                "T_e_applicability": "APPLICABLE_ONLY_IF_NULL_CALIBRATED_INTERIOR_ELBOW_GATE_PASSES",
                "endpoint_elbows_allowed": False,
            }
        ],
    )
    write_jsonl(
        out / "geometric_scale_registry.jsonl",
        [
            {
                "scale_id": "CARTESIAN_BIN_WIDTH_MM",
                "values_mm": [125, 250, 500, 1000],
                "primary_value_mm": 250,
                "selection_basis": "approximately one quarter of the 925 mm / 0.82D source plane scale; not selected from a field outcome",
                "S_e_applicability": "APPLICABLE_AS_GEOMETRIC_SCALE_ONLY; NEVER_BACKFILLED_FROM_CLOSURE",
            }
        ],
    )
    write_jsonl(
        out / "domain_baseline_registry.jsonl",
        [
            {
                "baseline_id": "B01_CONVENTIONAL_YAW_WAKE_DEFLECTION",
                "parent_control": "PARENT_TEST_1",
                "intervention_order": ["PARENT_TEST_2", "PARENT_TEST_3", "PARENT_TEST_4"],
                "condition_axis": "WT1 and WT2 yaw misalignment in degrees from TestMatrix",
                "estimator": "per-parent median absolute cross-stream ratio abs(uy)/max(abs(ux), registered numerical floor) on occupied downstream P01 cells",
                "comparison_rule": "a TLD channel that is no more stable than or is explained by conventional yaw response cannot receive extra construct support",
                "numeric_pooling_with_TLD_channels": False,
            }
        ],
    )
    write_jsonl(
        out / "failure_ledger.jsonl",
        [
            {
                "issue_code": "DOCUMENTATION_ARCHIVE_NAME_MISMATCH",
                "severity": "WARNING_RECONCILED",
                "evidence": "README says Single Wake.zip while DOI record deposits Multiple Wake.zip",
                "resolution": "the exact deposited archive contains precisely DATA_test_1.nc through DATA_test_4.nc and agrees one-to-one with TestMatrix.xlsx",
                "scientific_contract_changed": False,
            },
            {
                "issue_code": "NATIVE_NETCDF_UNIT_ATTRIBUTES_ABSENT",
                "severity": "WARNING_RESOLVED_CROSS_SOURCE",
                "evidence": "all NetCDF variable attribute maps are empty",
                "resolution": "coordinates are frozen as mm by agreement with *_Pos_*_mm and 925 mm plane metadata; velocities are frozen as m/s by agreement with Pitot_wind_speed_ms-1",
                "scientific_contract_changed": False,
            },
            {
                "issue_code": "FROZEN_MINIMUM_EFFECTIVE_PARENT_SUPPORT_NOT_MET",
                "severity": "EXECUTION_BLOCKER",
                "evidence": "four separately acquired run-level parents materialized; frozen method requires at least eight",
                "resolution": "assay stopped before preregistration and scoring; nested samples, lidars, and turbines were not promoted to independent parents",
                "scientific_contract_changed": False,
            },
        ],
    )

    translation = {
        "schema_version": "1.0.0",
        "domain_id": "ZENODO_18731994_WIND_TUNNEL_LIDAR_WAKE",
        "independent_parent": "one separately timestamped 600 s DATA_test_X.nc acquisition",
        "nested_replicate": "synchronized samples within an acquisition; never independent parents",
        "raw_field": "R2D2 and R2D3 line-of-sight velocities at their measured x/y/z positions",
        "source_derived_field": "source-reconstructed ux and uy at AvgPosition",
        "coordinates": "x/y/z in mm; 2D horizontal measurement plane with measured z variation retained",
        "boundary_conditions": "finite open measured footprint; NaN is missing, never zero or interpolation; no periodic spatial boundary",
        "domain_baseline": "conventional yaw-induced wake deflection, with Test 1 as control",
        "faithful_projections": ["P01_SOURCE_RECONSTRUCTED_VECTOR_GRID", "P02_DUAL_NATIVE_LOS_EVIDENCE_VECTOR"],
        "diagnostic_only_projections": ["P03_OCCUPIED_CELL_GRAPH"],
        "recursive_operation": "graph diffusion over occupied spatial cells",
        "geometric_scale_axis": "Cartesian bin width in mm",
        "T_e": "conditionally applicable only to a null-calibrated interior operation-depth elbow",
        "S_e": "geometric bin scale only; never closure depth or winner_N",
        "compatible_nulls": [row["null_id"] for row in nulls],
        "physical_perturbations": ["PERT02_REFLECT_Y_AND_FLIP_UY", "PERT03_COORDINATE_JITTER_12_5_MM"],
        "adversarial_perturbations": ["PERT05_DROP_ONE_LIDAR"],
        "invariants": ["source hashes", "parent identity", "missing mask", "unpooled modality identity"],
        "equivariants": ["y-directed signs under y reflection", "coordinate values under unit-preserving transforms"],
        "weakens_method": "registered channels fail to separate from adequate matched nulls or lack registered fragility/representation support",
        "neutral_result": "mixed nonbinary evidence or inadequate sensitivity under the frozen four-parent support",
        "invalidates_protocol": "source mismatch, unresolved units, parent leakage, null/projection selection after outcomes, or hidden failure",
        "binary_claim_sensitivity": "INSUFFICIENT_BY_DESIGN; four independent parents have minimum exact two-sided sign resolution 0.125",
        "claim_bearing_execution_authorized": False,
        "execution_blocker": "frozen minimum effective parent count is eight; materialized count is four",
    }
    write_json(out / "domain_translation.json", translation)

    source_custody = {
        "status": "PASS",
        "doi": "10.5281/zenodo.18731994",
        "license": "CC-BY-4.0",
        "dataset_freeze_commit": DATASET_FREEZE_COMMIT,
        "source_count": len(source_rows),
        "all_hashes_verified": True,
        "archive_safe": True,
        "member_inventory_exact": True,
        "candidate_substitution": False,
    }
    write_json(out / "source_custody.json", source_custody)
    write_json(
        out / "coordinate_integrity.json",
        {
            "status": "PASS_WITH_CROSS_SOURCE_UNIT_PROVENANCE",
            "checks": coordinate_checks,
            "units": "mm",
            "native_unit_attributes": False,
            "interpolation_performed": False,
            "rendered_pixels_used": False,
        },
    )
    write_json(
        out / "field_integrity.json",
        {
            "status": "PASS",
            "checks": field_checks,
            "units": "m/s",
            "all_four_components_present": True,
            "missing_values_preserved": True,
            "claim_metrics_computed": False,
        },
    )
    write_json(
        out / "parent_independence_precheck.json",
        {
            "status": "FAIL_FROZEN_MINIMUM_PARENT_SUPPORT",
            "independent_parent_count": len(parents),
            "effective_parent_count_for_frozen_assay": 4,
            "frozen_minimum_effective_parent_count": 8,
            "nested_samples_promoted": 0,
            "same_condition_replicates": 0,
            "shared_campaign": True,
            "external_validation_allowed": False,
            "binary_sensitivity_adequate": False,
            "minimum_exact_two_sided_sign_p": 2 / (2**4),
        },
    )
    write_json(
        out / "projection_integrity.json",
        {
            "status": "PASS",
            "faithful_projection_count": 2,
            "diagnostic_projection_count": 1,
            "outcome_selected_projection": False,
            "interpolation_allowed": False,
            "numeric_modality_averaging": False,
        },
    )
    write_json(
        out / "null_generation_audit.json",
        {
            "status": "FROZEN_NOT_YET_GENERATED",
            "family_count": 2,
            "children_per_parent_per_family": 127,
            "parent_local": True,
            "outcome_selected": False,
            "adequacy_must_be_checked_after_generation": True,
        },
    )
    write_json(
        out / "perturbation_nonredundancy_precheck.json",
        {
            "status": "PASS",
            "registered_count": len(perturbations),
            "null_family_reused_as_perturbation": False,
            "independent_pass_count_claimed": 0,
        },
    )
    write_json(
        out / "scout_eligibility.json",
        {
            "schema_version": "1.0.0",
            "scout_id": "SCOUT_ZENODO_18731994",
            "status": "INELIGIBLE_PARENT_SUPPORT",
            "closure_authorized": False,
            "materialized_fraction": 1.0,
            "effective_parent_count": 4.0,
            "frozen_minimum_effective_parent_count": 8,
            "checks": {
                "incident_materialized": True,
                "control_materialized": True,
                "source_provider_harness_boundaries": True,
                "effective_independent_evidence": False,
                "target_outcome_leakage": False,
                "coordinates_and_units_frozen": True,
                "projection_justified": True,
                "domain_baseline_available": True,
                "binary_sensitivity": False,
            },
            "failure_codes": ["INDEPENDENT_PARENT_SUPPORT_INSUFFICIENT"],
            "claim_ceiling": "DESCRIPTIVE_SOURCE_CUSTODY_ONLY",
        },
    )
    write_json(
        out / "contamination_prevention.json",
        {
            "status": "PASS",
            "method_frozen_before_candidate_search": True,
            "dataset_frozen_before_raw_access": True,
            "method_freeze_commit": METHOD_FREEZE_COMMIT,
            "dataset_freeze_commit": DATASET_FREEZE_COMMIT,
            "claim_metrics_computed_during_materialization": False,
            "test_matrix_use": "source mapping, parent identity, coordinates, units, and intervention metadata only",
            "candidate_substitution": False,
        },
    )
    receipt = {
        "status": "MATERIALIZED_ASSAY_EXECUTION_BLOCKED",
        "domain_id": translation["domain_id"],
        "source_custody": source_custody["status"],
        "coordinate_integrity": "PASS_WITH_CROSS_SOURCE_UNIT_PROVENANCE",
        "field_integrity": "PASS",
        "parent_count": 4,
        "nested_replicate_count": sum(row["lidar_sample_count"] for row in nested),
        "faithful_projection_count": 2,
        "registered_null_family_count": 2,
        "registered_perturbation_count": len(perturbations),
        "warnings": [
            "DOCUMENTATION_ARCHIVE_NAME_MISMATCH",
            "NATIVE_NETCDF_UNIT_ATTRIBUTES_ABSENT",
            "FOUR_PARENT_BINARY_SENSITIVITY_INADEQUATE",
        ],
        "blockers": ["FROZEN_MINIMUM_EFFECTIVE_PARENT_SUPPORT_NOT_MET"],
        "claim_metrics_computed": False,
        "preregistration_authorized": False,
        "scored_execution_authorized": False,
        "scientific_outcome": "GEOMETRY_INDEXED_TLD_HELDOUT_EXECUTION_BLOCKED",
        "protocol_outcome": "V030_GEOMETRY_FIELD_ASSAY_EXECUTION_BLOCKED",
        "candidate_substitution": "FORBIDDEN",
    }
    write_json(out / "materialization_receipt.json", receipt)
    write_json(
        out / "field_assay_blocker.json",
        {
            "schema_version": "1.0.0",
            "status": "BLOCKED_BEFORE_PREREGISTRATION_AND_SCORING",
            "issue_code": "FROZEN_MINIMUM_EFFECTIVE_PARENT_SUPPORT_NOT_MET",
            "frozen_minimum_effective_parents": 8,
            "materialized_effective_parents": 4,
            "nested_lidar_samples": sum(row["lidar_sample_count"] for row in nested),
            "nested_samples_promoted": 0,
            "lidars_promoted_to_parents": 0,
            "turbines_promoted_to_parents": 0,
            "method_freeze_commit": METHOD_FREEZE_COMMIT,
            "dataset_freeze_commit": DATASET_FREEZE_COMMIT,
            "candidate_substitution": "FORBIDDEN",
            "claim_metrics_computed": False,
            "preregistration_created": False,
            "scored_execution_count": 0,
            "scientific_outcome": "GEOMETRY_INDEXED_TLD_HELDOUT_EXECUTION_BLOCKED",
            "protocol_outcome": "V030_GEOMETRY_FIELD_ASSAY_EXECUTION_BLOCKED",
            "next_legal_action": "design a future version with a new prospectively frozen candidate-selection policy; v0.3.0 may not substitute this dataset",
        },
    )

    checksum_names = sorted(
        path.name
        for path in out.iterdir()
        if path.is_file() and path.name != "SHA256SUMS_INPUTS.txt"
    )
    lines = [f"{sha256(out / name)}  {name}" for name in checksum_names]
    with (out / "SHA256SUMS_INPUTS.txt").open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        handle.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
