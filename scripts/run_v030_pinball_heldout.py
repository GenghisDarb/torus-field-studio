# ruff: noqa: E501 -- frozen protocol labels and audit prose are intentionally explicit.
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from numpy.typing import NDArray
from torusbrot.geometry.v2 import (
    GeometryKind,
    TypedGeometry,
    anti_alias_downsample_2d,
    rotate_vector_field_90,
    typed_projection_scores,
)
from torusbrot.models import canonical_json

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "external_cache" / "v0.3.0-field-20794709" / "ExperimentalDataset.full.zip"
SOURCE = ROOT / "external_cache" / "v0.3.0-field-20794709" / "extracted"
HELDOUT = ROOT / "studies" / "v0.3.0-recovery" / "heldout"
MATERIALIZATION = HELDOUT / "materialization"
PREREGISTRATION = HELDOUT / "preregistration"
AUTHORIZATION = HELDOUT / "authorization" / "scored_execution_authorization.json"
OUTPUT = HELDOUT / "execution"
SOURCE_SHA256 = "5819f9071c3b3b0b856934602b5e7b487852abe0e0a3a5b1b62eae17720d822f"
PREREGISTRATION_COMMIT = "a8e3cba766bd8b160fc9b8074086a48fb7aceceb"
AUTHORIZATION_COMMIT = "77624c6cd56fbdbe3b83a240898884ad9ab67442"
RUN_ID = "pinball-heldout-e9e3d7666b2b10cb"
ROOT_SEED = 20260820
NULL_CHILDREN = 127
JOINT_REPLICATES = 999
ROTATION_TOLERANCE = 1e-10
RESOLUTION_M_PER_PX = 0.00029076921
SAMPLING_FREQUENCY_HZ = 120.0
STREAM_VELOCITY_M_PER_S = 0.31
VELOCITY_CONVERSION = RESOLUTION_M_PER_PX * SAMPLING_FREQUENCY_HZ / STREAM_VELOCITY_M_PER_S

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


@dataclass(frozen=True)
class RegisteredProjections:
    p01: TypedGeometry
    p02: TypedGeometry
    audit: dict[str, Any]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"expected JSON objects: {path}")
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value, pretty=True))


def write_json_exclusive(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_json(value, pretty=True))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(canonical_json(row) for row in rows))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def derived_seed(label: str) -> int:
    digest = hashlib.sha256(f"{ROOT_SEED}:{label}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def vector_geometry(values: FloatArray, mask: BoolArray, coordinates: FloatArray, projection_id: str) -> TypedGeometry:
    return TypedGeometry(
        kind=GeometryKind.VECTOR_FIELD_2D,
        values=values,
        coordinates=coordinates,
        mask=mask,
        component_names=("u/U_infinity", "v/U_infinity"),
        orientation="deposited X/Y coordinate grid and component orientation",
        projection_id=projection_id,
    )


def build_registered_projections(
    u_displacement: FloatArray,
    v_displacement: FloatArray,
    x: FloatArray,
    y: FloatArray,
    projection_prefix: str,
) -> RegisteredProjections:
    u = np.asarray(u_displacement, dtype=np.float64)
    v = np.asarray(v_displacement, dtype=np.float64)
    xx = np.asarray(x, dtype=np.float64)
    yy = np.asarray(y, dtype=np.float64)
    if u.ndim != 3 or v.shape != u.shape or xx.shape != yy.shape or u.shape[1:] != xx.shape:
        raise ValueError("PINBALL_EXECUTION_ARRAY_SHAPE_MISMATCH")
    if not np.all(np.isfinite(xx)) or not np.all(np.isfinite(yy)):
        raise ValueError("PINBALL_EXECUTION_NONFINITE_COORDINATES")
    finite_vector = np.isfinite(u) & np.isfinite(v)
    spatial_mask = np.all(finite_vector, axis=0)
    if int(np.sum(spatial_mask)) < 16:
        raise ValueError("PINBALL_EXECUTION_INSUFFICIENT_OBSERVED_CELLS")
    u_scaled = u * VELOCITY_CONVERSION
    v_scaled = v * VELOCITY_CONVERSION
    mean_values = np.zeros((*xx.shape, 2), dtype=np.float64)
    mean_values[..., 0][spatial_mask] = np.mean(u_scaled[:, spatial_mask], axis=0)
    mean_values[..., 1][spatial_mask] = np.mean(v_scaled[:, spatial_mask], axis=0)
    coordinates = np.stack((xx, yy), axis=-1)
    p01 = vector_geometry(
        mean_values,
        spatial_mask,
        coordinates,
        f"{projection_prefix}:P01_REGISTERED_TEMPORAL_MEAN_VECTOR_FIELD",
    )
    fluctuations = np.zeros((*u.shape, 2), dtype=np.float64)
    fluctuations[..., 0][:, spatial_mask] = (
        u_scaled[:, spatial_mask] - mean_values[..., 0][spatial_mask]
    )
    fluctuations[..., 1][:, spatial_mask] = (
        v_scaled[:, spatial_mask] - mean_values[..., 1][spatial_mask]
    )
    spatiotemporal_mask = np.broadcast_to(spatial_mask, u.shape).copy()
    p02 = TypedGeometry(
        kind=GeometryKind.SPATIOTEMPORAL_VECTOR,
        values=fluctuations,
        coordinates=coordinates,
        mask=spatiotemporal_mask,
        time=np.arange(u.shape[0], dtype=np.float64) / SAMPLING_FREQUENCY_HZ,
        component_names=("u_prime/U_infinity", "v_prime/U_infinity"),
        orientation="deposited X/Y coordinate grid and component orientation",
        projection_id=f"{projection_prefix}:P02_REGISTERED_SPATIOTEMPORAL_VECTOR_FLUCTUATIONS",
    )
    return RegisteredProjections(
        p01=p01,
        p02=p02,
        audit={
            "snapshot_axis": 0,
            "snapshot_count": u.shape[0],
            "grid_shape_yx": list(xx.shape),
            "total_grid_cells": int(xx.size),
            "observed_grid_cells": int(np.sum(spatial_mask)),
            "excluded_grid_cells": int(xx.size - np.sum(spatial_mask)),
            "all_snapshots_required_for_p01_cell": True,
            "p02_uses_same_spatial_mask_as_p01": True,
            "interpolation_performed": False,
            "fill_performed": False,
            "velocity_conversion": {
                "formula": "deposited displacement * resolution_m_per_px * sampling_frequency_hz / stream_velocity_m_per_s",
                "factor": VELOCITY_CONVERSION,
            },
        },
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
    return {
        "status": "PASS" if max(comparisons.values()) <= ROTATION_TOLERANCE else "FAIL",
        "absolute_disagreements": comparisons,
        "tolerance": ROTATION_TOLERANCE,
        "coordinates_rotated": geometry.coordinates is not None,
        "components_rotated": True,
        "mask_rotated": geometry.mask is not None,
    }


def null_scores(geometry: TypedGeometry, *, seed: int, children: int = NULL_CHILDREN) -> dict[str, list[float]]:
    observed = typed_projection_scores(geometry)
    values = np.asarray(geometry.values, dtype=np.float64)
    mask = np.asarray(geometry.mask, dtype=bool)
    occupied = values[mask].copy()
    rng = np.random.default_rng(seed)
    samples: dict[str, list[float]] = {name: [] for name in observed}
    for child in range(children):
        permuted = np.zeros_like(values)
        permuted[mask] = occupied[rng.permutation(len(occupied))]
        scores = typed_projection_scores(
            vector_geometry(
                permuted,
                mask,
                np.asarray(geometry.coordinates, dtype=np.float64),
                f"{geometry.projection_id}:null-{child + 1:03d}",
            )
        )
        for name, value in scores.items():
            samples[name].append(float(value))
    return samples


def channel_summary(observed: dict[str, float], samples: dict[str, list[float]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for name, observed_value in observed.items():
        values = np.asarray(samples[name], dtype=np.float64)
        output[name] = {
            "observed": float(observed_value),
            "null_median": float(np.median(values)),
            "null_q025": float(np.quantile(values, 0.025)),
            "null_q975": float(np.quantile(values, 0.975)),
            "observed_minus_null_median": float(observed_value - np.median(values)),
        }
    return output


def perturbation_audit(geometry: TypedGeometry, *, seed: int) -> dict[str, Any]:
    observed = typed_projection_scores(geometry)
    values = np.asarray(geometry.values, dtype=np.float64)
    mask = np.asarray(geometry.mask, dtype=bool)
    coordinates = np.asarray(geometry.coordinates, dtype=np.float64)
    rng = np.random.default_rng(seed)
    occupied_indices = np.flatnonzero(mask)
    dropout_count = max(1, int(np.ceil(0.05 * len(occupied_indices))))
    dropout_mask = mask.copy()
    dropout_mask.flat[rng.choice(occupied_indices, size=dropout_count, replace=False)] = False
    dropout = typed_projection_scores(
        vector_geometry(values, dropout_mask, coordinates, f"{geometry.projection_id}:mask-dropout")
    )
    noisy_values = values.copy()
    noise_scales: list[float] = []
    for component in range(2):
        component_values = values[..., component][mask]
        scale = 0.01 * float(np.sqrt(np.mean(component_values**2)))
        noise_scales.append(scale)
        noisy_values[..., component][mask] += rng.normal(0.0, scale, size=len(component_values))
    noisy = typed_projection_scores(
        vector_geometry(noisy_values, mask, coordinates, f"{geometry.projection_id}:noise-1pct")
    )
    downsampled = typed_projection_scores(anti_alias_downsample_2d(geometry, factor=2))
    return {
        "PERT01_ROTATE_90_WITH_COORDINATES_COMPONENTS_AND_MASK": rotation_audit(geometry),
        "PERT02_MASK_DROPOUT_5_PERCENT": {
            "dropped_cell_count": dropout_count,
            "actual_fraction": dropout_count / len(occupied_indices),
            "channel_delta": {name: float(dropout[name] - value) for name, value in observed.items()},
            "threshold": None,
        },
        "PERT03_RELATIVE_COMPONENT_NOISE_1_PERCENT": {
            "noise_distribution": "independent Gaussian",
            "component_sigma": noise_scales,
            "scale_definition": "one percent of observed component RMS",
            "channel_delta": {name: float(noisy[name] - value) for name, value in observed.items()},
            "threshold": None,
        },
        "PERT04_ANTI_ALIASED_SCALE_2X": {
            "channel_delta": {name: float(downsampled[name] - value) for name, value in observed.items()},
            "threshold": None,
        },
    }


def scale_views(geometry: TypedGeometry) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current = geometry
    for index, ell in enumerate((1, 2, 4)):
        if index:
            current = anti_alias_downsample_2d(current, factor=2)
        rows.append(
            {
                "ell_cells": ell,
                "transform_count": index,
                "observed_cells": int(np.sum(current.mask)),
                "channels": typed_projection_scores(current),
                "S_e": "NOT_APPLICABLE",
            }
        )
    return rows


def baseline_ratio(geometry: TypedGeometry) -> dict[str, float]:
    values = np.asarray(geometry.values, dtype=np.float64)
    mask = np.asarray(geometry.mask, dtype=bool)
    u = np.abs(values[..., 0][mask])
    v = np.abs(values[..., 1][mask])
    floor = max(float(np.finfo(float).eps), 1e-12 * float(np.median(u)))
    return {
        "median_absolute_cross_stream_ratio": float(np.median(v / np.maximum(u, floor))),
        "numerical_floor": floor,
    }


def scalar_channel_delta(actuated: dict[str, float], reference: dict[str, float]) -> dict[str, float]:
    if set(actuated) != set(reference):
        raise ValueError("PINBALL_EXECUTION_CHANNEL_SET_MISMATCH")
    return {name: float(actuated[name] - reference[name]) for name in actuated}


def joint_null_summary(observed: FloatArray, children: FloatArray, *, seed: int) -> dict[str, Any]:
    observed_values = np.asarray(observed, dtype=np.float64)
    null_values = np.asarray(children, dtype=np.float64)
    if observed_values.shape != (28,) or null_values.shape != (28, NULL_CHILDREN):
        raise ValueError("PINBALL_EXECUTION_JOINT_NULL_SHAPE_MISMATCH")
    if not np.all(np.isfinite(observed_values)) or not np.all(np.isfinite(null_values)):
        raise ValueError("PINBALL_EXECUTION_JOINT_NULL_NONFINITE")
    rng = np.random.default_rng(seed)
    selections = rng.integers(0, NULL_CHILDREN, size=(JOINT_REPLICATES, 28))
    parent_indices = np.broadcast_to(np.arange(28), selections.shape)
    joint = np.median(null_values[parent_indices, selections], axis=1)
    observed_statistic = float(np.median(observed_values))
    null_median = float(np.median(joint))
    null_scale = float(1.4826 * np.median(np.abs(joint - null_median)))
    return {
        "within_campaign_observed_median_pair_delta": observed_statistic,
        "joint_null_median": null_median,
        "joint_null_q025": float(np.quantile(joint, 0.025)),
        "joint_null_q975": float(np.quantile(joint, 0.975)),
        "observed_minus_joint_null_median": observed_statistic - null_median,
        "robust_standardized_effect": (observed_statistic - null_median) / max(null_scale, np.finfo(float).eps),
        "joint_null_robust_scale": null_scale,
        "pair_count": 28,
        "joint_null_replicates": JOINT_REPLICATES,
        "joint_null_values": [float(value) for value in joint],
        "binary_threshold_applied": False,
        "p_value_computed": False,
        "population_generalization": False,
    }


def verify_pre_execution_contract(archive: Path) -> dict[str, Any]:
    authorization = read_json(AUTHORIZATION)
    scope = authorization.get("authorization_scope")
    if not isinstance(scope, dict):
        raise ValueError("PINBALL_EXECUTION_AUTHORIZATION_SCOPE_MISSING")
    required = {
        "authorization_status": authorization.get("status") == "AUTHORIZED_FOR_EXACTLY_ONE_SCORED_EXECUTION",
        "execution_limit": scope.get("permitted_scored_executions") == 1,
        "run_id": authorization.get("run_id") == RUN_ID,
        "source_sha256": authorization.get("source_sha256") == SOURCE_SHA256,
        "preregistration_commit": authorization.get("preregistration_commit") == PREREGISTRATION_COMMIT,
        "root_seed": authorization.get("root_seed") == ROOT_SEED,
        "tld_blocked": scope.get("tld_derived") == "BLOCKED",
        "external_false": scope.get("external_validation") is False,
        "claim_ceiling": scope.get("claim_ceiling") == "GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY",
        "source_archive_sha256": sha256_file(archive) == SOURCE_SHA256,
    }
    manifest_hash = sha256_file(PREREGISTRATION / "preregistration_manifest.json")
    pair_hash = sha256_file(MATERIALIZATION / "paired_acquisition_registry.jsonl")
    required["manifest_hash"] = authorization.get("preregistration_manifest_sha256") == manifest_hash
    required["pair_registry_hash"] = authorization.get("pair_registry_sha256") == pair_hash
    if not all(required.values()):
        failures = sorted(name for name, passed in required.items() if not passed)
        raise ValueError(f"PINBALL_EXECUTION_PRECONDITION_FAILED:{','.join(failures)}")
    return {
        "checks": required,
        "authorization_sha256": sha256_file(AUTHORIZATION),
        "preregistration_manifest_sha256": manifest_hash,
        "pair_registry_sha256": pair_hash,
        "source_sha256": SOURCE_SHA256,
    }


def load_acquisition(
    source_root: Path,
    member: str,
    structure: dict[str, Any],
) -> RegisteredProjections:
    path = source_root.joinpath(*Path(member).parts)
    if path.stat().st_size != structure["extracted_size"]:
        raise ValueError(f"PINBALL_EXECUTION_EXTRACTED_SIZE_MISMATCH:{member}")
    with h5py.File(path, "r") as source:
        for name in ("U", "V", "X", "Y"):
            expected = structure["datasets"][name]
            if list(source[name].shape) != expected["shape"] or str(source[name].dtype) != expected["dtype"]:
                raise ValueError(f"PINBALL_EXECUTION_HEADER_CHANGED:{member}:{name}")
        snapshots_attribute = np.asarray(source.attrs["Nsnapshots"]).reshape(-1)
        if len(snapshots_attribute) != 1 or int(snapshots_attribute[0]) != source["U"].shape[0]:
            raise ValueError(f"PINBALL_EXECUTION_SNAPSHOT_ATTRIBUTE_MISMATCH:{member}")
        u = np.asarray(source["U"][:], dtype=np.float64)
        v = np.asarray(source["V"][:], dtype=np.float64)
        x = np.asarray(source["X"][:], dtype=np.float64)
        y = np.asarray(source["Y"][:], dtype=np.float64)
    return build_registered_projections(u, v, x, y, member)


def evaluate_acquisition(
    projections: RegisteredProjections,
    *,
    null_seed: int,
    perturbation_seed: int,
) -> tuple[dict[str, Any], dict[str, list[float]]]:
    p01_scores = typed_projection_scores(projections.p01)
    p02_scores = typed_projection_scores(projections.p02)
    samples = null_scores(projections.p01, seed=null_seed)
    null_summary = channel_summary(p01_scores, samples)
    return (
        {
            "projection_audit": projections.audit,
            "P01_channels": p01_scores,
            "P01_null_summary": null_summary,
            "P02_channels": p02_scores,
            "scale_views": scale_views(projections.p01),
            "perturbations": perturbation_audit(projections.p01, seed=perturbation_seed),
            "domain_baseline": baseline_ratio(projections.p01),
        },
        samples,
    )


def pair_evidence(
    pair: dict[str, Any],
    actuated: dict[str, Any],
    reference: dict[str, Any],
    actuated_nulls: dict[str, list[float]],
    reference_nulls: dict[str, list[float]],
) -> tuple[dict[str, Any], dict[str, list[float]]]:
    p01_delta = scalar_channel_delta(actuated["P01_channels"], reference["P01_channels"])
    p02_delta = scalar_channel_delta(actuated["P02_channels"], reference["P02_channels"])
    null_delta = {
        name: [
            float(actuated_value - reference_value)
            for actuated_value, reference_value in zip(
                actuated_nulls[name], reference_nulls[name], strict=True
            )
        ]
        for name in p01_delta
    }
    scale_rows = []
    for actuated_scale, reference_scale in zip(
        actuated["scale_views"], reference["scale_views"], strict=True
    ):
        if actuated_scale["ell_cells"] != reference_scale["ell_cells"]:
            raise ValueError("PINBALL_EXECUTION_SCALE_ALIGNMENT_MISMATCH")
        scale_rows.append(
            {
                "ell_cells": actuated_scale["ell_cells"],
                "actuated_channels": actuated_scale["channels"],
                "reference_channels": reference_scale["channels"],
                "pair_delta": scalar_channel_delta(
                    actuated_scale["channels"], reference_scale["channels"]
                ),
                "cross_file_cell_alignment": "NOT_PERFORMED",
                "S_e": "NOT_APPLICABLE",
            }
        )
    actuated_baseline = actuated["domain_baseline"]
    reference_baseline = reference["domain_baseline"]
    return (
        {
            "pair_id": pair["pair_id"],
            "p": pair["p"],
            "actuated_member": pair["actuated_member"],
            "reference_member": pair["reference_member"],
            "spatial_grid_shape_match": pair["spatial_grid_shape_match"],
            "cross_file_cell_alignment": "NOT_PERFORMED_ACQUISITION_LEVEL_CHANNEL_COMPARISON_ONLY",
            "P01_actuated_channels": actuated["P01_channels"],
            "P01_reference_channels": reference["P01_channels"],
            "P01_pair_delta": p01_delta,
            "P02_actuated_channels": actuated["P02_channels"],
            "P02_reference_channels": reference["P02_channels"],
            "P02_pair_delta": p02_delta,
            "scale_views": scale_rows,
            "domain_baseline": {
                "actuated": actuated_baseline,
                "reference": reference_baseline,
                "pair_delta": float(
                    actuated_baseline["median_absolute_cross_stream_ratio"]
                    - reference_baseline["median_absolute_cross_stream_ratio"]
                ),
            },
            "classification": "NONBINARY_WITHIN_CAMPAIGN_EVIDENCE_VECTOR_COMPONENTS",
        },
        null_delta,
    )


def execute_once(source_root: Path) -> dict[str, Any]:
    pairs = read_jsonl(MATERIALIZATION / "paired_acquisition_registry.jsonl")
    structures = read_jsonl(MATERIALIZATION / "hdf5_structure_registry.jsonl")
    if len(pairs) != 28 or len(structures) != 57:
        raise ValueError("PINBALL_EXECUTION_FROZEN_HIERARCHY_CHANGED")
    structure_by_member = {row["member"]: row for row in structures}
    acquisition_rows: list[dict[str, Any]] = []
    null_rows: list[dict[str, Any]] = []
    evaluated: dict[str, dict[str, Any]] = {}
    nulls_by_member: dict[str, dict[str, list[float]]] = {}
    ordered_members: list[tuple[str, str, str, float]] = []
    for pair in pairs:
        ordered_members.extend(
            [
                (pair["pair_id"], "ACTUATED", pair["actuated_member"], pair["p"]),
                (pair["pair_id"], "REFERENCE", pair["reference_member"], pair["p"]),
            ]
        )
    if len({member for _, _, member, _ in ordered_members}) != 56:
        raise ValueError("PINBALL_EXECUTION_MEMBER_REUSE")
    for pair_id, role, member, p_value in ordered_members:
        projections = load_acquisition(source_root, member, structure_by_member[member])
        evaluation, samples = evaluate_acquisition(
            projections,
            null_seed=derived_seed(f"null:{pair_id}:{role}:{member}"),
            perturbation_seed=derived_seed(f"perturbation:{pair_id}:{role}:{member}"),
        )
        evaluated[member] = evaluation
        nulls_by_member[member] = samples
        acquisition_rows.append(
            {
                "pair_id": pair_id,
                "role": role,
                "member": member,
                "p": p_value,
                **evaluation,
                "population_independent_parent": False,
            }
        )
        null_rows.append(
            {
                "pair_id": pair_id,
                "role": role,
                "member": member,
                "null_id": "N01_PARENT_LOCAL_JOINT_SPATIAL_CELL_PERMUTATION",
                "children": NULL_CHILDREN,
                "seed_derivation": f"sha256({ROOT_SEED}:null:{pair_id}:{role}:{member}) first 64 bits",
                "joint_component_pairing_preserved": True,
                "mask_preserved": True,
                "samples_by_channel": samples,
            }
        )
    pair_rows: list[dict[str, Any]] = []
    pair_null_rows: list[dict[str, Any]] = []
    pair_nulls_by_channel: dict[str, list[list[float]]] = {}
    pair_observed_by_channel: dict[str, list[float]] = {}
    for pair in pairs:
        row, null_delta = pair_evidence(
            pair,
            evaluated[pair["actuated_member"]],
            evaluated[pair["reference_member"]],
            nulls_by_member[pair["actuated_member"]],
            nulls_by_member[pair["reference_member"]],
        )
        pair_rows.append(row)
        pair_null_rows.append(
            {
                "pair_id": pair["pair_id"],
                "p": pair["p"],
                "null_child_pair_deltas_by_channel": null_delta,
                "children": NULL_CHILDREN,
                "cross_pair_pooling": "FORBIDDEN_EXCEPT_FROZEN_JOINT_WITHIN_CAMPAIGN_MEDIAN",
            }
        )
        for name, value in row["P01_pair_delta"].items():
            pair_observed_by_channel.setdefault(name, []).append(value)
            pair_nulls_by_channel.setdefault(name, []).append(null_delta[name])
    joint = {
        "schema_version": "1.0.0",
        "run_id": RUN_ID,
        "aggregation_role": "WITHIN_CAMPAIGN_NONBINARY_EVIDENCE_VECTOR_ONLY",
        "channels": {
            name: joint_null_summary(
                np.asarray(pair_observed_by_channel[name], dtype=np.float64),
                np.asarray(pair_nulls_by_channel[name], dtype=np.float64),
                seed=derived_seed(f"joint-null:{name}"),
            )
            for name in sorted(pair_observed_by_channel)
        },
        "binary_threshold_applied": False,
        "multiple_testing_family": "NONE",
        "population_generalization": False,
    }
    return {
        "acquisition_rows": acquisition_rows,
        "null_rows": null_rows,
        "pair_rows": pair_rows,
        "pair_null_rows": pair_null_rows,
        "joint": joint,
    }


def adjudicate(outputs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    acquisition_rows = outputs["acquisition_rows"]
    joint = outputs["joint"]
    rotation_failures = [
        {"member": row["member"], "pair_id": row["pair_id"]}
        for row in acquisition_rows
        if row["perturbations"]["PERT01_ROTATE_90_WITH_COORDINATES_COMPONENTS_AND_MASK"]["status"]
        != "PASS"
    ]
    null_complete = all(
        all(len(values) == NULL_CHILDREN for values in row["samples_by_channel"].values())
        for row in outputs["null_rows"]
    )
    finite_channels = all(
        all(np.isfinite(value) for value in row["P01_channels"].values())
        and all(np.isfinite(value) for value in row["P02_channels"].values())
        for row in acquisition_rows
    )
    pair_complete = len(outputs["pair_rows"]) == 28
    joint_complete = all(
        row["joint_null_replicates"] == JOINT_REPLICATES
        for row in joint["channels"].values()
    )
    protocol = {
        "schema_version": "1.0.0",
        "run_id": RUN_ID,
        "source_custody": "PASS",
        "pair_hierarchy": "PASS" if pair_complete else "FAIL",
        "projection_completeness": "PASS" if finite_channels else "FAIL",
        "null_completeness": "PASS" if null_complete and joint_complete else "FAIL",
        "rotation_equivariance": "PASS" if not rotation_failures else "FAIL",
        "rotation_failures": rotation_failures,
        "all_28_pair_deltas_reported": pair_complete,
        "all_frozen_channels_reported": finite_channels,
        "binary_threshold_applied": False,
        "p_value_computed": False,
        "winner_selection_performed": False,
        "T_e_computed": False,
        "S_e_computed": False,
        "winner_N_computed": False,
        "second_scored_execution_attempted": False,
    }
    if rotation_failures:
        scientific_outcome = "GEOMETRY_INDEXED_TLD_HELDOUT_INVALIDATED_BY_PROTOCOL"
    elif not (pair_complete and finite_channels and null_complete and joint_complete):
        scientific_outcome = "GEOMETRY_INDEXED_TLD_HELDOUT_EXECUTION_BLOCKED"
    else:
        scientific_outcome = "GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY"
    claim = {
        "schema_version": "1.0.0",
        "run_id": RUN_ID,
        "scientific_outcome": scientific_outcome,
        "maximum_claim": "source-specific calibrated within-campaign nonbinary evidence vector across 28 paired acquisitions on one deposited system",
        "positive_negative_TLD_classification": "NOT_PERFORMED_FORBIDDEN_BY_METHOD_FREEZE",
        "population_generalization": False,
        "causal_actuation_claim": False,
        "T_e": "NOT_APPLICABLE_NO_OPERATION_DEPTH_AXIS",
        "S_e": "NOT_APPLICABLE_NO_CALIBRATED_PERSISTENCE_ENDPOINT",
        "winner_N": "NOT_APPLICABLE_NO_CANONICAL_PATH_CLOSURE_AXIS",
        "geometric_scale": "ell in {1, 2, 4} native PIV grid cells",
        "TLD_DERIVED": "BLOCKED",
        "EXTERNALLY_VALIDATED": False,
        "ToT_BROT": "FORBIDDEN",
        "TORUS_confirmation": "FORBIDDEN",
        "all_named_channels_retained": True,
        "binary_threshold_applied": False,
    }
    return protocol, claim


def run(archive: Path, source_root: Path, output: Path) -> None:
    preflight = verify_pre_execution_contract(archive)
    implementation_commit = git_head()
    attempt_path = output / "execution_attempt.json"
    if attempt_path.exists():
        raise SystemExit("PINBALL_SELECTIVE_RERUN_FORBIDDEN_EXISTING_EXECUTION_ATTEMPT")
    write_json_exclusive(
        attempt_path,
        {
            "schema_version": "1.0.0",
            "run_id": RUN_ID,
            "attempt_number": 1,
            "permitted_attempts": 1,
            "implementation_commit": implementation_commit,
            "authorization_commit": AUTHORIZATION_COMMIT,
            "authorization_sha256": preflight["authorization_sha256"],
            "created_before_field_value_access": True,
            "second_attempt_action": "INVALIDATE_PROTOCOL_DO_NOT_RERUN",
        },
    )
    write_json_exclusive(
        output / "field_value_access_receipt.json",
        {
            "schema_version": "1.0.0",
            "run_id": RUN_ID,
            "attempt_number": 1,
            "status": "AUTHORIZED_FIELD_VALUE_ACCESS_STARTED",
            "source_sha256": SOURCE_SHA256,
            "values_previously_read_for_scoring": False,
        },
    )
    try:
        outputs = execute_once(source_root)
        protocol, claim = adjudicate(outputs)
        write_jsonl(output / "acquisition_evidence.jsonl", outputs["acquisition_rows"])
        write_jsonl(output / "acquisition_null_children.jsonl", outputs["null_rows"])
        write_jsonl(output / "pair_evidence.jsonl", outputs["pair_rows"])
        write_jsonl(output / "pair_null_children.jsonl", outputs["pair_null_rows"])
        write_json(output / "joint_null_evidence.json", outputs["joint"])
        write_json(output / "protocol_audit.json", protocol)
        write_json(output / "claim_adjudication.json", claim)
        artifact_names = [
            "execution_attempt.json",
            "field_value_access_receipt.json",
            "acquisition_evidence.jsonl",
            "acquisition_null_children.jsonl",
            "pair_evidence.jsonl",
            "pair_null_children.jsonl",
            "joint_null_evidence.json",
            "protocol_audit.json",
            "claim_adjudication.json",
        ]
        manifest = {
            "schema_version": "1.0.0",
            "run_id": RUN_ID,
            "status": "ONE_SCORED_EXECUTION_COMPLETE",
            "scored_execution_count": 1,
            "second_scored_execution_permitted": False,
            "implementation_commit": implementation_commit,
            "authorization_commit": AUTHORIZATION_COMMIT,
            "preregistration_commit": PREREGISTRATION_COMMIT,
            "source_sha256": SOURCE_SHA256,
            "artifacts": [
                {"name": name, "sha256": sha256_file(output / name)}
                for name in artifact_names
            ],
        }
        write_json(output / "execution_manifest.json", manifest)
        write_json(
            output / "execution_receipt.json",
            {
                "schema_version": "1.0.0",
                "run_id": RUN_ID,
                "status": "PASS_ONE_SCORED_EXECUTION_PRESERVED",
                "scored_execution_count": 1,
                "second_scored_execution_permitted": False,
                "acquisition_count": len(outputs["acquisition_rows"]),
                "paired_block_count": len(outputs["pair_rows"]),
                "null_children_per_acquisition": NULL_CHILDREN,
                "joint_null_replicates": JOINT_REPLICATES,
                "scientific_outcome": claim["scientific_outcome"],
                "manifest_sha256": sha256_file(output / "execution_manifest.json"),
            },
        )
    except Exception as exc:
        write_json(
            output / "execution_failure_receipt.json",
            {
                "schema_version": "1.0.0",
                "run_id": RUN_ID,
                "status": "FAILED_FIRST_SCORED_EXECUTION_NO_RERUN_PERMITTED",
                "scored_execution_count": 1,
                "second_scored_execution_permitted": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "scientific_outcome": "GEOMETRY_INDEXED_TLD_HELDOUT_EXECUTION_BLOCKED",
            },
        )
        raise
    print(
        json.dumps(
            {
                "status": "PASS_ONE_SCORED_EXECUTION_PRESERVED",
                "run_id": RUN_ID,
                "scientific_outcome": claim["scientific_outcome"],
                "acquisitions": len(outputs["acquisition_rows"]),
                "pairs": len(outputs["pair_rows"]),
            },
            indent=2,
            sort_keys=True,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the single authorized v0.3.0 fluidic-pinball held-out assay")
    parser.add_argument("--archive", type=Path, default=ARCHIVE)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.archive.resolve(), args.source.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
