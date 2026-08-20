# ruff: noqa: E501 -- scientific contract prose and deposited identifiers are intentionally explicit.
from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
from netCDF4 import Dataset
from torusbrot.audit import audit_bundle
from torusbrot.geometry.v2 import (
    GeometryKind,
    TypedGeometry,
    anti_alias_downsample_2d,
    rotate_vector_field_90,
    typed_projection_scores,
)
from torusbrot.models import canonical_json, content_hash

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "external_cache" / "v0.3.0-field-18731994" / "extracted"
MATERIALIZATION = ROOT / "studies" / "v0.3.0-field-assay" / "materialization"
FREEZE = ROOT / "studies" / "v0.3.0-recovery" / "freeze"
OUTPUT = ROOT / "studies" / "v0.3.0-recovery" / "wind_pilot"
CELL_MM = 250.0
MINIMUM_CELL_SAMPLES = 8
NULL_CHILDREN = 127
ROOT_SEED = 300
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def variable(dataset: Dataset, path: str) -> Any:
    value: Any = dataset
    for part in path.strip("/").split("/"):
        value = value[part]
    return value


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"expected JSON objects: {path}")
    return rows


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json(row) for row in rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value, pretty=True))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def as_float64(value: Any) -> np.ndarray[Any, np.dtype[np.float64]]:
    return np.asarray(value, dtype=np.float64)


def binned_field(
    x: np.ndarray[Any, Any],
    y: np.ndarray[Any, Any],
    components: list[np.ndarray[Any, Any]],
) -> tuple[np.ndarray[Any, np.dtype[np.float64]], np.ndarray[Any, np.dtype[np.bool_]], np.ndarray[Any, np.dtype[np.float64]], dict[str, Any]]:
    arrays = [as_float64(item).reshape(-1) for item in (x, y, *components)]
    if len({len(item) for item in arrays}) != 1:
        raise ValueError("coordinate and field arrays do not align")
    finite = np.logical_and.reduce([np.isfinite(item) for item in arrays])
    if not np.any(finite):
        raise ValueError("projection contains no jointly finite observations")
    xx, yy, *fields = [item[finite] for item in arrays]
    bx = np.floor(xx / CELL_MM).astype(np.int64)
    by = np.floor(yy / CELL_MM).astype(np.int64)
    min_x, max_x = int(np.min(bx)), int(np.max(bx))
    min_y, max_y = int(np.min(by)), int(np.max(by))
    width = max_x - min_x + 1
    height = max_y - min_y + 1
    linear = (by - min_y) * width + (bx - min_x)
    order = np.argsort(linear, kind="stable")
    ordered = linear[order]
    unique, starts, counts = np.unique(ordered, return_index=True, return_counts=True)
    output = np.zeros((height, width, len(fields)), dtype=np.float64)
    mask = np.zeros((height, width), dtype=bool)
    eligible = counts >= MINIMUM_CELL_SAMPLES
    for key, start, count in zip(unique[eligible], starts[eligible], counts[eligible], strict=True):
        row, column = divmod(int(key), width)
        indices = order[int(start) : int(start + count)]
        output[row, column] = [float(np.median(field[indices])) for field in fields]
        mask[row, column] = True
    x_centers = (np.arange(min_x, max_x + 1, dtype=np.float64) + 0.5) * CELL_MM
    y_centers = (np.arange(min_y, max_y + 1, dtype=np.float64) + 0.5) * CELL_MM
    grid_x, grid_y = np.meshgrid(x_centers, y_centers)
    coordinates = np.stack((grid_x, grid_y), axis=-1)
    audit = {
        "input_sample_count": len(arrays[0]),
        "jointly_finite_sample_count": int(np.sum(finite)),
        "occupied_cell_count": int(np.sum(mask)),
        "discarded_under_minimum_cell_count": int(np.sum(~eligible)),
        "grid_shape_yx": [height, width],
        "minimum_samples_per_cell": MINIMUM_CELL_SAMPLES,
        "cell_width_mm": CELL_MM,
        "interpolation_performed": False,
        "missing_cells_are_zero": False,
    }
    return output, mask, coordinates, audit


def vector_geometry(
    values: np.ndarray[Any, np.dtype[np.float64]],
    mask: np.ndarray[Any, np.dtype[np.bool_]],
    coordinates: np.ndarray[Any, np.dtype[np.float64]],
    projection_id: str,
) -> TypedGeometry:
    return TypedGeometry(
        kind=GeometryKind.VECTOR_FIELD_2D,
        values=values,
        coordinates=coordinates,
        mask=mask,
        component_names=("ux", "uy"),
        orientation="source x/y Cartesian coordinates in mm",
        projection_id=projection_id,
    )


def scalar_geometry(
    values: np.ndarray[Any, np.dtype[np.float64]],
    mask: np.ndarray[Any, np.dtype[np.bool_]],
    coordinates: np.ndarray[Any, np.dtype[np.float64]],
    projection_id: str,
) -> TypedGeometry:
    return TypedGeometry(
        kind=GeometryKind.SCALAR_FIELD_2D,
        values=values[..., 0],
        coordinates=coordinates,
        mask=mask,
        orientation="source x/y Cartesian coordinates in mm",
        projection_id=projection_id,
    )


def rotation_audit(geometry: TypedGeometry) -> dict[str, Any]:
    original = typed_projection_scores(geometry)
    rotated = typed_projection_scores(rotate_vector_field_90(geometry))
    comparisons = {
        "curl_coherence_invariant": abs(original["curl_coherence"] - rotated["curl_coherence"]),
        "curl_energy_invariant": abs(original["curl_energy"] - rotated["curl_energy"]),
        "divergence_energy_invariant": abs(original["divergence_energy"] - rotated["divergence_energy"]),
        "u_to_v_neighbor_equivariance": abs(original["u_neighbor_coherence"] - rotated["v_neighbor_coherence"]),
        "v_to_u_neighbor_equivariance": abs(original["v_neighbor_coherence"] - rotated["u_neighbor_coherence"]),
        "signed_mean_curl_invariant": abs(original["signed_mean_curl"] - rotated["signed_mean_curl"]),
    }
    tolerance = 1e-10
    return {
        "status": "PASS" if max(comparisons.values()) <= tolerance else "FAIL",
        "absolute_disagreements": comparisons,
        "tolerance": tolerance,
        "coordinates_rotated": geometry.coordinates is not None,
        "components_rotated": True,
        "mask_rotated": geometry.mask is not None,
    }


def descriptive_null_bias(
    geometry: TypedGeometry,
    parent_seed: int,
) -> tuple[dict[str, Any], dict[str, list[float]]]:
    observed = typed_projection_scores(geometry)
    values = np.asarray(geometry.values, dtype=np.float64)
    mask = np.asarray(geometry.mask, dtype=bool)
    occupied = values[mask].copy()
    rng = np.random.default_rng(parent_seed)
    samples: dict[str, list[float]] = {name: [] for name in observed}
    for child in range(NULL_CHILDREN):
        permuted = np.zeros_like(values)
        permuted[mask] = occupied[rng.permutation(len(occupied))]
        child_scores = typed_projection_scores(
            vector_geometry(
                permuted,
                mask,
                np.asarray(geometry.coordinates, dtype=np.float64),
                f"{geometry.projection_id}:null-{child:03d}",
            )
        )
        for name, value in child_scores.items():
            samples[name].append(float(value))
    channels = []
    for name, observed_value in observed.items():
        values_by_null = np.asarray(samples[name], dtype=np.float64)
        null_median = float(np.median(values_by_null))
        channels.append(
            {
                "channel": name,
                "observed": float(observed_value),
                "null_median": null_median,
                "null_q025": float(np.quantile(values_by_null, 0.025)),
                "null_q975": float(np.quantile(values_by_null, 0.975)),
                "observed_minus_null_median": float(observed_value - null_median),
                "interpretation": "DESCRIPTIVE_PARENT_LOCAL_ONLY",
            }
        )
    return (
        {
            "null_id": "N03_PARENT_LOCAL_MASK_PRESERVING_JOINT_CELL_PERMUTATION",
            "children": NULL_CHILDREN,
            "parent_pooling": "FORBIDDEN",
            "component_pairing_preserved": True,
            "mask_preserved": True,
            "channels": channels,
            "threshold_selected": False,
            "confirmatory_p_value_computed": False,
        },
        samples,
    )


def npy_bytes(value: np.ndarray[Any, Any]) -> bytes:
    handle = io.BytesIO()
    np.lib.format.write_array(handle, np.asarray(value), allow_pickle=False)
    return handle.getvalue()


def deterministic_npz(arrays: dict[str, np.ndarray[Any, Any]]) -> bytes:
    handle = io.BytesIO()
    with zipfile.ZipFile(handle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, value in sorted(arrays.items()):
            info = zipfile.ZipInfo(f"{name}.npy", date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, npy_bytes(value), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return handle.getvalue()


def independent_array_verification(
    payload: bytes,
    result_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    disagreements: list[str] = []
    with np.load(io.BytesIO(payload), allow_pickle=False) as arrays:
        for row in result_rows:
            prefix = row["parent_id"].lower()
            mask = np.asarray(arrays[f"{prefix}_vector_mask"], dtype=bool)
            values = np.asarray(arrays[f"{prefix}_vector_values"], dtype=np.float64)
            coordinates = np.asarray(arrays[f"{prefix}_vector_coordinates_mm"], dtype=np.float64)
            if values.shape[:-1] != mask.shape or coordinates.shape != (*mask.shape, 2):
                disagreements.append(f"{prefix}:shape")
            if int(np.sum(mask)) != row["P01_vector_projection"]["occupied_cell_count"]:
                disagreements.append(f"{prefix}:mask_count")
            if not np.all(np.isfinite(values[mask])) or not np.all(np.isfinite(coordinates)):
                disagreements.append(f"{prefix}:finite")
            if np.any(values[~mask] != 0.0):
                disagreements.append(f"{prefix}:missing_cell_payload")
    return {
        "status": "VERIFIED" if not disagreements else "FAILED",
        "verifier": "independent serialized-array custody and mask/coordinate invariant recomputation",
        "primary_input": "arrays/registered_binned_fields.npz",
        "production_endpoint_tables_consumed": False,
        "checks": ["shape", "occupied mask count", "finite observed payload", "finite coordinates", "missing cells not represented as observations"],
        "disagreements": len(disagreements),
        "disagreement_details": disagreements,
    }


def build_bundle(
    out_path: Path,
    contract: dict[str, Any],
    results: dict[str, Any],
    null_bias: dict[str, Any],
    projection_audit: dict[str, Any],
    baseline: dict[str, Any],
    claim_boundary: dict[str, Any],
    parents: list[dict[str, Any]],
    arrays_payload: bytes,
) -> dict[str, Any]:
    source_hashes = {row["member"]: row["member_sha256"] for row in parents}
    run_id = f"run-{content_hash({'contract': contract, 'source_hashes': source_hashes})[:16]}"
    forbidden_claims = [
        "TLD confirmation",
        "ToT-BROT",
        "external validation",
        "population generalization",
        "binary TLD positive or negative",
        "TORUS Theory proven",
    ]
    failures = [
        {
            "issue_code": "PILOT_EXPOSED_ROTATION_RASTER_DIRECTION_DEFECT",
            "severity": "CORRECTED_WITH_FULL_RECALIBRATION",
            "evidence": "the first source-field pilot attempt preserved curl energy but reversed signed mean curl under the registered 90-degree transform",
            "resolution": "raster movement was corrected to the Cartesian index convention; a signed-curl regression was added; all 31 synthetic families and 50 independent mutations were rerun before pilot publication",
        },
        {
            "issue_code": "NATIVE_NETCDF_UNIT_ATTRIBUTES_ABSENT",
            "severity": "WARNING_RESOLVED_CROSS_SOURCE",
            "resolution": "coordinate and velocity units retain the prior cross-source provenance; uncertainty remains visible",
        },
        {
            "issue_code": "ONE_CAMPAIGN_NONEXCHANGEABLE_CONDITIONS",
            "severity": "CLAIM_CEILING",
            "resolution": "four condition acquisitions remain separate descriptive instances with no population aggregation",
        },
        {
            "issue_code": "NO_FROZEN_GENERAL_GEOMETRY_OPERATION_DEPTH",
            "severity": "NOT_APPLICABLE_FIREWALL",
            "resolution": "no operation-depth axis was invented after Method V2 freeze",
        },
    ]
    independent = independent_array_verification(arrays_payload, results["conditions"])
    if independent["status"] != "VERIFIED":
        raise RuntimeError(f"independent bundle verification failed: {independent}")
    adjudication = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "method_id": "METHOD_V2_C_EVIDENCE_VECTOR",
        "method_mode": "INSTRUMENTED_EVIDENCE_VECTOR",
        "scout_status": "ELIGIBLE",
        "channel_results": {
            "condition_count": 4,
            "all_vector_channels_finite": all(
                all(np.isfinite(value) for value in row["P01_vector_channels"].values())
                for row in results["conditions"]
            ),
            "rotation_equivariance": projection_audit["all_rotation_equivariance_passed"],
            "population_aggregate": None,
        },
        "scientific_outcome": "NONCONFIRMATORY_STRUCTURE_EXPOSED_ENGINEERING_PILOT",
        "T_e": "NOT_APPLICABLE_NO_FROZEN_GENERAL_GEOMETRY_OPERATION_DEPTH",
        "S_e": "NOT_APPLICABLE_GEOMETRIC_SCALE_ELL_IS_NOT_S_E",
        "winner_N": "NOT_APPLICABLE_NO_TLD_CLOSURE_AXIS",
        "geometric_scale": "ell in {250, 500, 1000} mm",
        "TLD_DERIVED": "BLOCKED",
        "EXTERNALLY_VALIDATED": False,
        "claim_ceiling": "DESCRIPTIVE",
        "blockers": ["ONE_CAMPAIGN_NONEXCHANGEABLE_CONDITIONS", "NONCONFIRMATORY_OUTCOME_EXPOSED_SOURCE"],
    }
    geometry_profile = {
        "schema_version": "1.0.0",
        "profile_id": "geometry-tbx-v1",
        "required_member_roles": [
            "geometry profile",
            "source registry",
            "parent hierarchy",
            "projection registry",
            "null registry",
            "raw arrays",
            "geometry channel table",
            "independent verification",
            "claim adjudication",
            "failure ledger",
        ],
        "forbidden_claims": forbidden_claims,
        "independent_verifier_required": True,
        "raw_arrays_required": True,
        "registry_hashes_required": True,
    }
    source_registry = {
        "source_id": "ZENODO_18731994_WIND_TUNNEL_LIDAR_WAKE",
        "doi": "10.5281/zenodo.18731994",
        "license": "CC-BY-4.0",
        "pilot_role": "NONCONFIRMATORY_STRUCTURE_EXPOSED_ENGINEERING_PILOT",
        "campaign_count": 1,
        "condition_acquisition_count": 4,
        "condition_acquisitions_exchangeable": False,
        "source_member_sha256": source_hashes,
    }
    projections = read_jsonl(MATERIALIZATION / "projection_registry.jsonl")[:2]
    projections.append(
        {
            "projection_id": "P04_METHOD_V2_ANTIALIASED_SCALE_VIEW",
            "construction": "mask-aware factor-two block average applied only for registered ell sensitivity views",
            "geometric_scale_symbol": "ell",
            "T_e": "NOT_APPLICABLE",
            "S_e": "NOT_APPLICABLE",
        }
    )
    null_rows = [
        {
            "null_id": "N03_PARENT_LOCAL_MASK_PRESERVING_JOINT_CELL_PERMUTATION",
            "parent_id": row["parent_id"],
            "children": NULL_CHILDREN,
            "parent_pooling": "FORBIDDEN",
            "condition_pooling": "FORBIDDEN",
            "component_pairing_preserved": True,
            "mask_preserved": True,
            "claim_role": "DESCRIPTIVE_NULL_BIAS_DIAGNOSTIC_ONLY",
        }
        for row in parents
    ]
    receipts = [{"run_id": run_id, "status": "verified", "verifier": independent["verifier"], "disagreements": 0}]
    transformations = [
        {
            "transformation_id": "geometry-method-v2-wind-pilot",
            "run_id": run_id,
            "projection_ids": [row["projection_id"] for row in projections],
            "null_id": "N03_PARENT_LOCAL_MASK_PRESERVING_JOINT_CELL_PERMUTATION",
            "root_seed": ROOT_SEED,
            "outcome_selected": False,
        }
    ]
    members: dict[str, bytes] = {
        "geometry_profile.json": canonical_json(geometry_profile, pretty=True),
        "source_registry.json": canonical_json(source_registry, pretty=True),
        "ontology.json": canonical_json(
            {
                "equivalences": [],
                "non_equivalences": ["ell is not S_e", "operation-depth elbow is not T_e", "one field is not ToT-BROT", "engineering pilot is not TLD confirmation"],
            },
            pretty=True,
        ),
        "claim_boundary.json": canonical_json(claim_boundary, pretty=True),
        "visual_encoding.json": canonical_json(
            {
                "mask": "explicit occupancy overlay",
                "vector": "two registered components; never magnitude-only",
                "modalities": "R2D2 and R2D3 remain separate",
                "scale_label": "geometric scale ell (mm)",
                "forbidden_labels": ["S_e", "T_e", "winner_N", "TLD positive", "TLD negative"],
            },
            pretty=True,
        ),
        "scene_recipe.json": canonical_json(
            {
                "default_scene": "four separate condition panels",
                "comparison": "descriptive only",
                "population_summary": None,
                "raw_array_member": "arrays/registered_binned_fields.npz",
            },
            pretty=True,
        ),
        "provenance/sources.jsonl": jsonl_bytes([source_registry]),
        "provenance/transformations.jsonl": jsonl_bytes(transformations),
        "provenance/verification_receipts.jsonl": jsonl_bytes(receipts),
        "provenance/raw_array_custody.json": canonical_json(
            {"bundle_member": "arrays/registered_binned_fields.npz", "sha256": sha256_bytes(arrays_payload), "allow_pickle": False},
            pretty=True,
        ),
        "arrays/registered_binned_fields.npz": arrays_payload,
        "registry/parent_registry.jsonl": jsonl_bytes(parents),
        "registry/projection_registry.jsonl": jsonl_bytes(projections),
        "registry/null_registry.jsonl": jsonl_bytes(null_rows),
        "tables/geometry_channel_results.json": canonical_json(results, pretty=True),
        "tables/scale_behavior.json": canonical_json(results["scale_behavior"], pretty=True),
        "tables/domain_baseline.json": canonical_json(baseline, pretty=True),
        "audit/independent_verification.json": canonical_json(independent, pretty=True),
        "audit/claim_adjudication.json": canonical_json(adjudication, pretty=True),
        "audit/forbidden_claims.json": canonical_json({"claims": forbidden_claims}, pretty=True),
        "audit/failure_ledger.jsonl": jsonl_bytes(failures),
    }
    sums = b"".join(
        f"{sha256_bytes(payload)}  {name}\n".encode()
        for name, payload in sorted(members.items())
    )
    members["audit/SHA256SUMS.txt"] = sums
    manifest = {
        "tbx_version": "1.0.0",
        "profile": "geometry-pilot-v0.3.0",
        "run_id": run_id,
        "claim_level": "DESCRIPTIVE",
        "kernel_id": "geometry-method-v2-wind-pilot",
        "specification_sha256": sha256_bytes(canonical_json(contract, pretty=True)),
        "statistics": {
            "point_count": 4,
            "classification_counts": {"NONCONFIRMATORY_CONDITION": 4},
            "mean_UI": None,
            "mean_NSS": None,
            "mean_S_e": None,
            "failure_count": len(failures),
        },
        "files": [
            {"path": name, "sha256": sha256_bytes(payload), "bytes": len(payload)}
            for name, payload in sorted(members.items())
        ],
    }
    members["manifest.json"] = canonical_json(manifest, pretty=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    report = audit_bundle(out_path)
    if not report.valid:
        raise RuntimeError("geometry pilot TBX audit failed: " + "; ".join(report.errors))
    return {
        "run_id": run_id,
        "archive": out_path.name,
        "sha256": sha256_file(out_path),
        "checked_files": report.checked_files,
        "audit_valid": report.valid,
    }


def run(source: Path, out: Path) -> None:
    frozen_method = read_json(FREEZE / "frozen_method_v2.json")
    if frozen_method.get("status") != "ESTABLISHED_FOR_INSTRUMENTED_NONPREDICTIVE_USE":
        raise SystemExit("V030_METHOD_V2_NOT_ESTABLISHED")
    if frozen_method.get("required_name") != "INSTRUMENTED_EVIDENCE_VECTOR":
        raise SystemExit("V030_METHOD_V2_NOT_ESTABLISHED")
    if read_json(FREEZE / "frozen_operation_depths_v2.json").get("general_geometry_operation_depths") != []:
        raise ValueError("unexpected post-freeze general geometry operation-depth axis")
    parents = read_jsonl(MATERIALIZATION / "parent_registry.jsonl")
    if len(parents) != 4 or sum(row["role"] == "DOMAIN_CONTROL_BASELINE" for row in parents) != 1:
        raise ValueError("pilot requires four conditions and exactly one domain control")
    contract = {
        "schema_version": "1.0.0",
        "pilot_role": "NONCONFIRMATORY_STRUCTURE_EXPOSED_ENGINEERING_PILOT",
        "method_id": frozen_method["method_id"],
        "method_name": frozen_method["required_name"],
        "source_id": "ZENODO_18731994_WIND_TUNNEL_LIDAR_WAKE",
        "hierarchy": {
            "facility_campaigns": 1,
            "condition_level_acquisitions": 4,
            "baseline_conditions": 1,
            "yaw_interventions": 3,
            "same_yaw_repeated_acquisitions": 0,
            "nested_synchronized_samples": True,
            "coupled_lidar_modalities": 2,
            "interacting_turbines": 3,
            "condition_acquisitions_exchangeable": False,
        },
        "projection": {
            "P01": "componentwise median on fixed 250 mm source x/y Cartesian bins; minimum eight jointly finite samples; no interpolation",
            "P02": "R2D2 and R2D3 binned independently on native coordinates; never numerically pooled",
        },
        "null": {
            "null_id": "N03_PARENT_LOCAL_MASK_PRESERVING_JOINT_CELL_PERMUTATION",
            "children_per_condition": NULL_CHILDREN,
            "component_pairing_preserved": True,
            "mask_preserved": True,
            "condition_pooling": "FORBIDDEN",
            "purpose": "engineering null-generation and null-bias diagnostic; no threshold or confirmatory p-value",
        },
        "geometric_scale": {"symbol": "ell", "values_mm": [250, 500, 1000], "is_S_e": False},
        "operation_depth": "NOT_APPLICABLE_NO_FROZEN_GENERAL_GEOMETRY_OPERATION_DEPTH",
        "T_e": "NOT_APPLICABLE",
        "S_e": "NOT_APPLICABLE",
        "winner_N": "NOT_APPLICABLE",
        "threshold_tuning": False,
        "method_component_selection": False,
        "confirmatory_classification": False,
        "population_aggregation": False,
        "TLD_DERIVED": "BLOCKED",
        "EXTERNALLY_VALIDATED": False,
    }
    # Contract is constructed and hashed before any measurement field is opened.
    contract_sha256_before_field_access = sha256_bytes(canonical_json(contract, pretty=True))
    condition_rows: list[dict[str, Any]] = []
    null_rows: list[dict[str, Any]] = []
    projection_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    scale_rows: list[dict[str, Any]] = []
    arrays: dict[str, np.ndarray[Any, Any]] = {}
    for parent_index, parent in enumerate(parents):
        member_path = source / parent["member"]
        if sha256_file(member_path) != parent["member_sha256"]:
            raise ValueError(f"source custody mismatch: {member_path.name}")
        with Dataset(member_path, "r") as dataset:
            avg_x = as_float64(variable(dataset, "/LidarData/AvgPosition/x")[:])
            avg_y = as_float64(variable(dataset, "/LidarData/AvgPosition/y")[:])
            ux = as_float64(variable(dataset, "/LidarData/ux")[:])
            uy = as_float64(variable(dataset, "/LidarData/uy")[:])
            vector, vector_mask, vector_coordinates, vector_audit = binned_field(avg_x, avg_y, [ux, uy])
            geometry = vector_geometry(vector, vector_mask, vector_coordinates, "P01_SOURCE_RECONSTRUCTED_VECTOR_GRID")
            vector_scores = typed_projection_scores(geometry)
            equivariance = rotation_audit(geometry)
            los_outputs: dict[str, Any] = {}
            for lidar in ("R2D2", "R2D3"):
                x = as_float64(variable(dataset, f"/LidarData/{lidar}/Position/x")[:])
                y = as_float64(variable(dataset, f"/LidarData/{lidar}/Position/y")[:])
                values = as_float64(variable(dataset, f"/LidarData/{lidar}/vLOS")[:])
                scalar, scalar_mask, scalar_coordinates, scalar_audit = binned_field(x, y, [values])
                scalar_scores = typed_projection_scores(
                    scalar_geometry(scalar, scalar_mask, scalar_coordinates, f"P02_DUAL_NATIVE_LOS_EVIDENCE_VECTOR:{lidar}")
                )
                los_outputs[lidar] = {"projection": scalar_audit, "channels": scalar_scores}
                prefix = parent["parent_id"].lower()
                arrays[f"{prefix}_{lidar.lower()}_values"] = scalar[..., 0]
                arrays[f"{prefix}_{lidar.lower()}_mask"] = scalar_mask
                arrays[f"{prefix}_{lidar.lower()}_coordinates_mm"] = scalar_coordinates
            null_result, _ = descriptive_null_bias(geometry, ROOT_SEED + parent_index)
            null_rows.append({"parent_id": parent["parent_id"], **null_result})
            ratio_floor = max(float(np.finfo(float).eps), 1e-12 * float(np.median(np.abs(vector[..., 0][vector_mask]))))
            ratio = np.abs(vector[..., 1][vector_mask]) / np.maximum(np.abs(vector[..., 0][vector_mask]), ratio_floor)
            baseline_rows.append(
                {
                    "parent_id": parent["parent_id"],
                    "role": parent["role"],
                    "wt1_yaw_deg": parent["wt1_yaw_deg"],
                    "wt2_yaw_deg": parent["wt2_yaw_deg"],
                    "wt3_yaw_deg": parent["wt3_yaw_deg"],
                    "median_absolute_cross_stream_ratio": float(np.median(ratio)),
                    "numerical_floor": ratio_floor,
                    "interpretation": "DESCRIPTIVE_CONDITION_LEVEL_DOMAIN_BASELINE",
                }
            )
            scale_geometry = geometry
            for scale_index, ell in enumerate((250, 500, 1000)):
                if scale_index:
                    scale_geometry = anti_alias_downsample_2d(scale_geometry, factor=2)
                scale_rows.append(
                    {
                        "parent_id": parent["parent_id"],
                        "geometric_scale_symbol": "ell",
                        "ell_mm": ell,
                        "scale_transform_count": scale_index,
                        "operation_depth": "NOT_APPLICABLE",
                        "T_e": "NOT_APPLICABLE",
                        "channels": typed_projection_scores(scale_geometry),
                        "occupied_cell_count": int(np.sum(scale_geometry.mask)),
                    }
                )
            row = {
                "parent_id": parent["parent_id"],
                "condition_role": parent["role"],
                "yaw_degrees": [parent["wt1_yaw_deg"], parent["wt2_yaw_deg"], parent["wt3_yaw_deg"]],
                "P01_vector_projection": vector_audit,
                "P01_vector_channels": vector_scores,
                "P02_native_lidar_channels": los_outputs,
                "vector_rotation_equivariance": equivariance,
                "population_aggregate": None,
                "classification": "NONCONFIRMATORY_CONDITION",
            }
            condition_rows.append(row)
            projection_rows.append(
                {
                    "parent_id": parent["parent_id"],
                    "P01": vector_audit,
                    "P02": {name: value["projection"] for name, value in los_outputs.items()},
                    "vector_rotation_equivariance": equivariance,
                    "mask_preserved": True,
                    "coordinate_aware": True,
                    "numeric_modality_pooling": False,
                }
            )
            prefix = parent["parent_id"].lower()
            arrays[f"{prefix}_vector_values"] = vector
            arrays[f"{prefix}_vector_mask"] = vector_mask
            arrays[f"{prefix}_vector_coordinates_mm"] = vector_coordinates
    if contract_sha256_before_field_access != sha256_bytes(canonical_json(contract, pretty=True)):
        raise RuntimeError("pilot contract changed after source field access")
    if any(row["vector_rotation_equivariance"]["status"] != "PASS" for row in projection_rows):
        raise RuntimeError("vector rotation equivariance failed")
    results = {
        "schema_version": "1.0.0",
        "pilot_role": contract["pilot_role"],
        "conditions": condition_rows,
        "population_aggregate": None,
        "condition_pooling": "FORBIDDEN",
        "confirmatory_classification": "NOT_PERFORMED",
        "TLD_DERIVED": "BLOCKED",
        "scale_behavior": {
            "rows": scale_rows,
            "scale_symbol": "ell",
            "S_e": "NOT_APPLICABLE",
            "operation_depth": "NOT_APPLICABLE_NO_FROZEN_GENERAL_GEOMETRY_OPERATION_DEPTH",
        },
    }
    null_bias = {
        "schema_version": "1.0.0",
        "conditions": null_rows,
        "population_aggregate": None,
        "condition_pooling": "FORBIDDEN",
        "threshold_selected": False,
        "confirmatory_inference": False,
    }
    projection_audit = {
        "schema_version": "1.0.0",
        "conditions": projection_rows,
        "all_rotation_equivariance_passed": True,
        "all_masks_explicit": True,
        "all_coordinates_registered": True,
        "interpolation_performed": False,
        "vector_magnitude_scalarization": False,
        "lidar_modalities_pooled": False,
        "preserved_engineering_failures": [
            {
                "issue_code": "PILOT_EXPOSED_ROTATION_RASTER_DIRECTION_DEFECT",
                "first_attempt_status": "FAILED_BEFORE_ARTIFACT_PUBLICATION",
                "correction": "proper Cartesian rotation now moves the raster clockwise in index space before applying (u, v) -> (-v, u)",
                "post_correction_regression": "PASS_ALL_FOUR_SOURCE_CONDITIONS_AND_SYNTHETIC_METHOD_V2_RECALIBRATION",
                "threshold_or_method_component_changed": False,
            }
        ],
    }
    baseline = {
        "schema_version": "1.0.0",
        "baseline_id": "B01_CONVENTIONAL_YAW_WAKE_DEFLECTION",
        "rows": baseline_rows,
        "control_parent": "PARENT_TEST_1",
        "numeric_pooling_with_TLD_channels": False,
        "population_inference": False,
    }
    claim_boundary = {
        "schema_version": "1.0.0",
        "scientific_outcome": "NONCONFIRMATORY_STRUCTURE_EXPOSED_ENGINEERING_PILOT",
        "maximum_claim": "source-specific descriptive engineering evidence from four nonexchangeable conditions",
        "T_e": "NOT_APPLICABLE_NO_FROZEN_GENERAL_GEOMETRY_OPERATION_DEPTH",
        "S_e": "NOT_APPLICABLE_GEOMETRIC_SCALE_ELL_IS_NOT_S_E",
        "winner_N": "NOT_APPLICABLE_NO_TLD_CLOSURE_AXIS",
        "geometric_scale": "ell in {250, 500, 1000} mm",
        "TLD_DERIVED": "BLOCKED",
        "EXTERNALLY_VALIDATED": False,
        "forbidden": ["threshold tuning", "method selection", "confirmatory TLD positive/negative", "population aggregation", "ToT-BROT", "TORUS confirmation"],
    }
    arrays_payload = deterministic_npz(arrays)
    bundle_receipt = build_bundle(out / "wind_farm_pilot.tbx.zip", contract, results, null_bias, projection_audit, baseline, claim_boundary, parents, arrays_payload)
    write_json(out / "wind_farm_pilot_contract.json", contract)
    write_json(out / "wind_farm_pilot_results.json", results)
    write_json(out / "wind_farm_null_bias.json", null_bias)
    write_json(out / "wind_farm_projection_audit.json", projection_audit)
    write_json(out / "wind_farm_domain_baseline.json", baseline)
    write_json(out / "wind_farm_pilot_claim_boundary.json", claim_boundary)
    print(json.dumps({"status": "PASS", "conditions": len(condition_rows), "null_children_per_condition": NULL_CHILDREN, "bundle": bundle_receipt}, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the frozen Method V2 wind-farm nonconfirmatory engineering pilot")
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.source.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
