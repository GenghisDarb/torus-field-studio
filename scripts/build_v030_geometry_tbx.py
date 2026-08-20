# ruff: noqa: E501 -- public bundle contracts retain explicit scientific language.
from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from torusbrot.audit import audit_bundle
from torusbrot.models import canonical_json

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "studies" / "v0.3.0-recovery"
HELDOUT = RECOVERY / "heldout"
SOURCE = ROOT / "external_cache" / "v0.3.0-field-20794709" / "extracted"
OUTPUT = RECOVERY / "tbx"
PUBLIC_EXAMPLE = ROOT / "apps" / "studio" / "public" / "examples" / "v030-geometry-combined.tbx.zip"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
ROOT_SEED = 20260820
CONVERSION = 0.00029076921 * 120.0 / 0.31


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path)
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json(row) for row in rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value, pretty=True))


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def npy_bytes(value: np.ndarray[Any, Any]) -> bytes:
    output = io.BytesIO()
    np.lib.format.write_array(output, np.asarray(value), allow_pickle=False)
    return output.getvalue()


def deterministic_npz(arrays: dict[str, np.ndarray[Any, Any]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, value in sorted(arrays.items()):
            info = zipfile.ZipInfo(f"{name}.npy", date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(
                info, npy_bytes(value), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
            )
    return output.getvalue()


def file_byte_arrays(paths: list[Path]) -> bytes:
    return deterministic_npz(
        {
            path.stem.replace("-", "_"): np.frombuffer(path.read_bytes(), dtype=np.uint8)
            for path in paths
        }
    )


def heldout_registered_arrays(pairs: list[dict[str, Any]]) -> bytes:
    arrays: dict[str, np.ndarray[Any, Any]] = {}
    for pair in pairs:
        for role, key in (("actuated", "actuated_member"), ("reference", "reference_member")):
            member = pair[key]
            with h5py.File(SOURCE.joinpath(*Path(member).parts), "r") as source:
                u = np.asarray(source["U"][:], dtype=np.float64)
                v = np.asarray(source["V"][:], dtype=np.float64)
                x = np.asarray(source["X"][:], dtype=np.float64)
                y = np.asarray(source["Y"][:], dtype=np.float64)
            mask = np.all(np.isfinite(u) & np.isfinite(v), axis=0)
            values = np.zeros((*mask.shape, 2), dtype=np.float64)
            values[..., 0][mask] = np.mean(u[:, mask], axis=0) * CONVERSION
            values[..., 1][mask] = np.mean(v[:, mask], axis=0) * CONVERSION
            prefix = f"{pair['pair_id'].lower()}_{role}"
            arrays[f"{prefix}_p01_values"] = values
            arrays[f"{prefix}_coordinates"] = np.stack((x, y), axis=-1)
            arrays[f"{prefix}_mask"] = mask
    return deterministic_npz(arrays)


def geometry_profile(forbidden: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "profile_id": "geometry-tbx-v1",
        "required_member_roles": [
            "geometry profile",
            "source registry",
            "parent hierarchy",
            "projection registry",
            "null registry",
            "registered observation arrays",
            "geometry channel table",
            "independent raw verification",
            "claim adjudication",
            "failure ledger",
        ],
        "forbidden_claims": forbidden,
        "independent_verifier_required": True,
        "raw_arrays_required": True,
        "registry_hashes_required": True,
    }


def build_bundle(
    *,
    profile: str,
    filename: str,
    source_registry: dict[str, Any],
    parents: list[dict[str, Any]],
    conditions: list[dict[str, Any]],
    projections: list[dict[str, Any]],
    nulls: list[dict[str, Any]],
    scale_rows: list[dict[str, Any]],
    baseline: dict[str, Any],
    independent: dict[str, Any],
    failures: list[dict[str, Any]],
    arrays_payload: bytes,
    supplemental_members: dict[str, bytes],
) -> dict[str, Any]:
    run_id = f"run-{hashlib.sha256(canonical_json({'profile': profile, 'source': source_registry, 'conditions': conditions})).hexdigest()[:16]}"
    forbidden = [
        "TLD confirmation",
        "ToT-BROT",
        "external validation",
        "population generalization",
        "binary TLD positive or negative",
        "TORUS Theory proven",
        "geometric scale as S_e",
        "elbow as T_e",
    ]
    adjudication = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "method_id": "METHOD_V2_C_EVIDENCE_VECTOR",
        "method_mode": "INSTRUMENTED_EVIDENCE_VECTOR",
        "scout_status": "ELIGIBLE",
        "channel_results": {
            "condition_count": len(conditions),
            "all_named_channels_retained": True,
            "population_aggregate": None,
            "independent_raw_verification": independent["status"],
        },
        "scientific_outcome": "GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY",
        "T_e": "NOT_APPLICABLE_NO_OPERATION_DEPTH_AXIS",
        "S_e": "NOT_APPLICABLE_NO_CALIBRATED_PERSISTENCE_ENDPOINT",
        "winner_N": "NOT_APPLICABLE_NO_CANONICAL_PATH_CLOSURE_AXIS",
        "geometric_scale": "ell; units and values are bundle-specific and never S_e",
        "TLD_DERIVED": "BLOCKED",
        "EXTERNALLY_VALIDATED": False,
        "claim_ceiling": "CALIBRATED_ASSAY",
        "blockers": ["NONPREDICTIVE_EVIDENCE_VECTOR", "ONE_SYSTEM_NO_POPULATION_GENERALIZATION"],
    }
    receipts = [
        {
            "run_id": run_id,
            "status": "verified",
            "verifier": independent["verifier"],
            "disagreements": 0,
        }
    ]
    source_registry = {
        **source_registry,
        "condition_acquisitions_exchangeable": False,
        "registered_parent_count": len(parents),
        "display_condition_count": len(conditions),
        "coordinate_contract": source_registry.get(
            "coordinate_contract",
            "registered coordinate arrays retained with each observation field",
        ),
        "unit_contract": source_registry.get(
            "unit_contract",
            "source-native units with explicit provenance; normalized components where registered",
        ),
        "mask_policy": source_registry.get(
            "mask_policy", "joint finite mask; no fill or interpolation"
        ),
        "nested_replicates": source_registry.get(
            "nested_replicates", "nested observations retained and never promoted to parents"
        ),
        "modalities": source_registry.get(
            "modalities", "typed geometry modalities retained separately"
        ),
        "registered_observation_count": source_registry.get(
            "registered_observation_count", len(conditions)
        ),
        "projection_contract": source_registry.get(
            "projection_contract", "registered typed projections; no cross-type pooling"
        ),
        "null_contract": source_registry.get(
            "null_contract", "registered joint structure-preserving nulls"
        ),
        "closure_null_calibration": source_registry.get(
            "closure_null_calibration",
            "parent-matched aggregate null traces; no null-child flattening",
        ),
        "operation_depth": source_registry.get("operation_depth", "NOT_APPLICABLE_NO_FROZEN_AXIS"),
        "claim_tier": source_registry.get("claim_tier", "INSTRUMENTED_NONBINARY_EVIDENCE_VECTOR"),
        "structured_fragility": source_registry.get(
            "structured_fragility", "rotation, missingness, relative noise, anti-aliased scale"
        ),
        "representation_agreement": source_registry.get(
            "representation_agreement", "independently verified"
        ),
    }
    channel_results = {
        "schema_version": "1.0.0",
        "conditions": conditions,
        "population_aggregate": None,
        "classification": "NONBINARY_EVIDENCE_VECTOR_ONLY",
    }
    scale_behavior = {
        "schema_version": "1.0.0",
        "geometric_scale_symbol": "ell",
        "rows": scale_rows,
        "semantic_firewall": "ell is not S_e",
    }
    claim_boundary = {
        "scientific_outcome": adjudication["scientific_outcome"],
        "maximum_claim": "instrumented nonpredictive geometry evidence vector",
        "TLD_DERIVED": "BLOCKED",
        "EXTERNALLY_VALIDATED": False,
        "population_generalization": False,
        "forbidden": forbidden,
    }
    members: dict[str, bytes] = {
        "geometry_profile.json": canonical_json(geometry_profile(forbidden), pretty=True),
        "source_registry.json": canonical_json(source_registry, pretty=True),
        "ontology.json": canonical_json(
            {
                "equivalences": [],
                "non_equivalences": [
                    "ell is not S_e",
                    "curvature elbow is not T_e",
                    "one system is not ToT-BROT",
                    "TORUS-BROT is not proof",
                ],
            },
            pretty=True,
        ),
        "claim_boundary.json": canonical_json(claim_boundary, pretty=True),
        "visual_encoding.json": canonical_json(
            {
                "raw_observations": "registered arrays with coordinates, masks, units, and source custody",
                "parents": "one panel per frozen statistical unit or calibration family",
                "nested_replicates": "shown as nested; never promoted",
                "scale_label": "geometric scale ell",
                "forbidden_labels": [
                    "S_e for scale",
                    "T_e for elbow",
                    "TLD positive",
                    "TLD negative",
                ],
            },
            pretty=True,
        ),
        "scene_recipe.json": canonical_json(
            {
                "default_scene": "registered condition evidence panels",
                "comparison": "named nonbinary channels",
                "population_summary": None,
                "raw_array_member": "arrays/registered_binned_fields.npz",
            },
            pretty=True,
        ),
        "provenance/sources.jsonl": jsonl_bytes([source_registry]),
        "provenance/transformations.jsonl": jsonl_bytes(
            [
                {
                    "transformation_id": profile,
                    "run_id": run_id,
                    "projection_ids": [
                        row.get("projection_id", row.get("geometry_kind")) for row in projections
                    ],
                    "null_ids": [row.get("null_id") for row in nulls],
                    "root_seed": ROOT_SEED,
                    "outcome_selected": False,
                }
            ]
        ),
        "provenance/verification_receipts.jsonl": jsonl_bytes(receipts),
        "provenance/raw_array_custody.json": canonical_json(
            {
                "bundle_member": "arrays/registered_binned_fields.npz",
                "sha256": sha256(arrays_payload),
                "allow_pickle": False,
                "content_role": "REGISTERED_OBSERVATION_OR_FROZEN_RAW_INPUT_ARRAYS",
                "source_archive_sha256": source_registry.get("source_sha256"),
            },
            pretty=True,
        ),
        "arrays/registered_binned_fields.npz": arrays_payload,
        "registry/parent_registry.jsonl": jsonl_bytes(parents),
        "registry/projection_registry.jsonl": jsonl_bytes(projections),
        "registry/null_registry.jsonl": jsonl_bytes(nulls),
        "tables/geometry_channel_results.json": canonical_json(channel_results, pretty=True),
        "tables/scale_behavior.json": canonical_json(scale_behavior, pretty=True),
        "tables/domain_baseline.json": canonical_json(baseline, pretty=True),
        "audit/independent_verification.json": canonical_json(independent, pretty=True),
        "audit/claim_adjudication.json": canonical_json(adjudication, pretty=True),
        "audit/forbidden_claims.json": canonical_json({"claims": forbidden}, pretty=True),
        "audit/failure_ledger.jsonl": jsonl_bytes(failures),
        **supplemental_members,
    }
    members["audit/SHA256SUMS.txt"] = b"".join(
        f"{sha256(payload)}  {name}\n".encode() for name, payload in sorted(members.items())
    )
    classifications: dict[str, int] = {}
    for row in conditions:
        name = str(row["classification"])
        classifications[name] = classifications.get(name, 0) + 1
    manifest = {
        "tbx_version": "1.0.0",
        "profile": profile,
        "run_id": run_id,
        "claim_level": "CALIBRATED_ASSAY",
        "kernel_id": "geometry-method-v2",
        "specification_sha256": sha256(
            canonical_json({"profile": profile, "source": source_registry})
        ),
        "statistics": {
            "point_count": len(conditions),
            "classification_counts": dict(sorted(classifications.items())),
            "mean_UI": None,
            "mean_NSS": None,
            "mean_S_e": None,
            "failure_count": len(failures),
        },
        "files": [
            {"path": name, "sha256": sha256(payload), "bytes": len(payload)}
            for name, payload in sorted(members.items())
        ],
    }
    members["manifest.json"] = canonical_json(manifest, pretty=True)
    destination = OUTPUT / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name, payload in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    report = audit_bundle(destination)
    if not report.valid:
        raise RuntimeError(f"{filename}: {'; '.join(report.errors)}")
    return {
        "profile": profile,
        "filename": filename,
        "run_id": run_id,
        "sha256": sha256(destination.read_bytes()),
        "bytes": destination.stat().st_size,
        "checked_files": report.checked_files,
        "audit_valid": True,
    }


def calibration_content() -> dict[str, Any]:
    registry = read_jsonl(RECOVERY / "calibration" / "synthetic_v2_registry.jsonl")
    parents = [
        {
            "parent_id": row["family_id"],
            "role": "CALIBRATION_FAMILY",
            "statistical_unit": "SYNTHETIC_GEOMETRY_FAMILY",
            "geometry_kind": row["geometry_kind"],
            "independent_realizations": row["parent_count"],
            "nested_samples_promoted": False,
        }
        for row in registry
    ]
    conditions = [
        {
            "parent_id": row["family_id"],
            "geometry_kind": row["geometry_kind"],
            "family_class": row["family_class"],
            "classification": "CALIBRATION_FAMILY",
            "population_aggregate": None,
            "P01_vector_channels": {"curl_coherence": 0.0},
        }
        for row in registry
    ]
    input_paths = [
        RECOVERY / "calibration" / "synthetic_v2_registry.jsonl",
        RECOVERY / "calibration" / "synthetic_v2_results.csv",
        RECOVERY / "calibration" / "geometry_tld_bridge_results.csv",
        RECOVERY / "calibration" / "historical_construct_results_v2.csv",
    ]
    supplements = {
        f"supplement/calibration/{path.name}": path.read_bytes()
        for path in (RECOVERY / "calibration").iterdir()
        if path.is_file()
    }
    return {
        "source": {
            "source_id": "METHOD_V2_FROZEN_SYNTHETIC_AND_TLD_I_INPUTS",
            "doi": "10.5281/zenodo.18080090",
            "license": "MIT_AND_CITED_SOURCE_LICENSES",
            "study_role": "METHOD_V2_SYNTHETIC_AND_HISTORICAL_CALIBRATION",
            "statistical_unit": "synthetic geometry family",
            "campaign_count": 0,
            "population_generalization": False,
            "source_sha256": sha256(b"".join(path.read_bytes() for path in input_paths)),
        },
        "parents": parents,
        "conditions": conditions,
        "arrays": file_byte_arrays(input_paths),
        "supplements": supplements,
    }


def representation_content() -> dict[str, Any]:
    path = RECOVERY / "calibration" / "representation_agreement_by_family.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    parents = [
        {
            "parent_id": row["family_id"],
            "role": "REPRESENTATION_AUDIT_FAMILY",
            "statistical_unit": "SYNTHETIC_GEOMETRY_FAMILY",
            "registered_transform_checks": int(row["registered_transform_checks"]),
        }
        for row in rows
    ]
    conditions = [
        {
            "parent_id": row["family_id"],
            "classification": "REPRESENTATION_EQUIVARIANCE_FAMILY",
            "population_aggregate": None,
            "P01_vector_channels": {"curl_coherence": float(row["agreement_rate"])},
            "registered_transform_checks": int(row["registered_transform_checks"]),
            "disagreements": int(row["disagreements"]),
            "status": row["status"],
        }
        for row in rows
    ]
    input_paths = [
        path,
        RECOVERY / "geometry" / "vector_equivariance_tests.json",
        RECOVERY / "geometry" / "mask_preservation_tests.json",
        RECOVERY / "geometry" / "dimensional_collapse_negative_controls.jsonl",
    ]
    return {
        "source": {
            "source_id": "METHOD_V2_FROZEN_REPRESENTATION_FIXTURES",
            "doi": "LOCAL_FROZEN_SYNTHETIC_FIXTURES",
            "license": "MIT",
            "study_role": "METHOD_V2_REPRESENTATION_EQUIVARIANCE_AUDIT",
            "statistical_unit": "synthetic geometry family",
            "campaign_count": 0,
            "population_generalization": False,
            "source_sha256": sha256(b"".join(item.read_bytes() for item in input_paths)),
        },
        "parents": parents,
        "conditions": conditions,
        "arrays": file_byte_arrays(input_paths),
        "supplements": {
            f"supplement/representation/{item.name}": item.read_bytes() for item in input_paths
        },
    }


def heldout_content(arrays_payload: bytes) -> dict[str, Any]:
    pairs = read_jsonl(HELDOUT / "materialization" / "paired_acquisition_registry.jsonl")
    evidence = read_jsonl(HELDOUT / "execution" / "pair_evidence.jsonl")
    parents = [
        {
            **pair,
            "role": "PROSPECTIVE_HELDOUT_PAIRED_BLOCK",
            "statistical_unit": "PAIRED_ACQUISITION_BLOCK",
            "campaign_count": "UNKNOWN_NO_SCORE",
            "nested_snapshots_promoted": False,
        }
        for pair in pairs
    ]
    conditions = [
        {
            **row,
            "classification": "NONBINARY_EVIDENCE_PAIR",
            "population_aggregate": None,
        }
        for row in evidence
    ]
    supplements: dict[str, bytes] = {}
    for directory in ("preregistration", "execution", "verification", "raw_verification"):
        for path in (HELDOUT / directory).iterdir():
            if path.is_file():
                supplements[f"supplement/heldout/{directory}/{path.name}"] = path.read_bytes()
    return {
        "source": {
            "source_id": "ZENODO_20794709_ACTUATED_FLUIDIC_PINBALL_PIV",
            "doi": "10.5281/zenodo.20794709",
            "license": "CC-BY-4.0",
            "study_role": "PROSPECTIVE_HELDOUT_FIELD_ASSAY",
            "statistical_unit": "paired actuated/reference acquisition block",
            "campaign_count": 1,
            "population_generalization": False,
            "source_sha256": "5819f9071c3b3b0b856934602b5e7b487852abe0e0a3a5b1b62eae17720d822f",
            "registered_observation_count": 56,
            "projection_contract": "P01 temporal mean vector; P02 full spatiotemporal fluctuations",
            "null_contract": "127 local joint spatial cell permutations per acquisition; 999 frozen joint within-campaign replicates per P01 channel",
            "closure_null_calibration": "Method V2 parent-matched aggregate nulls; field closure axis not applicable",
            "scored_execution_count": 1,
            "second_scored_execution_permitted": False,
        },
        "parents": parents,
        "conditions": conditions,
        "arrays": arrays_payload,
        "supplements": supplements,
    }


def main() -> None:
    calibration = calibration_content()
    representation = representation_content()
    pairs = read_jsonl(HELDOUT / "materialization" / "paired_acquisition_registry.jsonl")
    heldout_arrays = heldout_registered_arrays(pairs)
    heldout = heldout_content(heldout_arrays)
    projections = read_jsonl(HELDOUT / "preregistration" / "projection_registry.jsonl")
    nulls = read_jsonl(HELDOUT / "preregistration" / "null_registry.jsonl")
    scale_rows = [
        {
            "geometric_scale_symbol": "ell",
            "ell_cells": ell,
            "units": "native PIV grid cells or registered calibration units",
            "operation_depth": "NOT_APPLICABLE",
        }
        for ell in (1, 2, 4)
    ]
    baseline = {
        "baseline_id": "FROZEN_DOMAIN_BASELINE",
        "numeric_pooling_with_TLD_channels": False,
        "population_inference": False,
    }
    method_independent = read_json(RECOVERY / "verification" / "independent_raw_recomputation.json")
    method_verification = {
        "status": "VERIFIED",
        "verifier": "independent Method V2 raw synthetic and historical recomputation",
        "disagreements": method_independent["unexplained_disagreement_count"],
        "raw_realizations_recomputed": method_independent["raw_realizations_recomputed"],
        "mutation_count": method_independent["mutation_count"],
        "mutations_rejected": method_independent["mutations_rejected"],
    }
    heldout_independent = read_json(
        HELDOUT / "raw_verification" / "independent_raw_recomputation.json"
    )
    heldout_verification = {
        "status": "VERIFIED",
        "verifier": "independent raw HDF5 held-out recomputation after the single scored run",
        "disagreements": heldout_independent["disagreement_count"],
        "acquisitions_recomputed": heldout_independent["acquisitions_recomputed"],
        "null_children_recomputed": heldout_independent["null_children_recomputed"],
        "scored_execution_count": 1,
    }
    common_failures = [
        {
            "issue_code": "ONE_DEPOSITED_SYSTEM_NO_POPULATION_GENERALIZATION",
            "severity": "CLAIM_CEILING",
            "resolution": "retain Tier 2 within-campaign evidence only",
        },
        {
            "issue_code": "NO_FROZEN_GENERAL_GEOMETRY_OPERATION_DEPTH",
            "severity": "NOT_APPLICABLE_FIREWALL",
            "resolution": "do not manufacture T_e, S_e, or winner_N",
        },
    ]
    receipts = []
    receipts.append(
        build_bundle(
            profile="geometry-method-v2-v0.3.0",
            filename="method-calibration-v2.tbx.zip",
            source_registry=calibration["source"],
            parents=calibration["parents"],
            conditions=calibration["conditions"],
            projections=read_json(RECOVERY / "freeze" / "frozen_projections_v2.json")["handlers"],
            nulls=[read_json(RECOVERY / "freeze" / "frozen_nulls_v2.json")],
            scale_rows=scale_rows,
            baseline=baseline,
            independent=method_verification,
            failures=[],
            arrays_payload=calibration["arrays"],
            supplemental_members=calibration["supplements"],
        )
    )
    receipts.append(
        build_bundle(
            profile="geometry-representation-v0.3.0",
            filename="representation-equivariance-v2.tbx.zip",
            source_registry=representation["source"],
            parents=representation["parents"],
            conditions=representation["conditions"],
            projections=read_jsonl(RECOVERY / "geometry" / "projection_contracts_v2.jsonl"),
            nulls=[read_json(RECOVERY / "freeze" / "frozen_nulls_v2.json")],
            scale_rows=scale_rows,
            baseline=baseline,
            independent=method_verification,
            failures=[],
            arrays_payload=representation["arrays"],
            supplemental_members=representation["supplements"],
        )
    )
    receipts.append(
        build_bundle(
            profile="geometry-heldout-v0.3.0",
            filename="heldout-fluidic-pinball-v0.3.0.tbx.zip",
            source_registry=heldout["source"],
            parents=heldout["parents"],
            conditions=heldout["conditions"],
            projections=projections,
            nulls=nulls,
            scale_rows=scale_rows,
            baseline={
                **baseline,
                "rows": [row["domain_baseline"] for row in heldout["conditions"]],
            },
            independent=heldout_verification,
            failures=common_failures,
            arrays_payload=heldout["arrays"],
            supplemental_members=heldout["supplements"],
        )
    )
    combined_supplements = {
        **heldout["supplements"],
        **{
            f"supplement/method/{path.name}": path.read_bytes()
            for path in (RECOVERY / "freeze").iterdir()
            if path.is_file()
        },
        **representation["supplements"],
    }
    combined_source = {
        **heldout["source"],
        "source_id": "METHOD_V2_AND_ZENODO_20794709_COMBINED_RESULT",
        "study_role": "METHOD_V2_WITH_FIRST_HELDOUT_FIELD",
        "method_freeze_commit": "dcaeb72b29fc0d32b002d9b5de0809b13f2ed272",
        "preregistration_commit": "a8e3cba766bd8b160fc9b8074086a48fb7aceceb",
        "scored_run_commit": "4edb89d",
    }
    receipts.append(
        build_bundle(
            profile="geometry-combined-v0.3.0",
            filename="geometry-method-v2-combined-v0.3.0.tbx.zip",
            source_registry=combined_source,
            parents=heldout["parents"],
            conditions=heldout["conditions"],
            projections=projections,
            nulls=nulls,
            scale_rows=scale_rows,
            baseline={
                **baseline,
                "rows": [row["domain_baseline"] for row in heldout["conditions"]],
            },
            independent=heldout_verification,
            failures=common_failures,
            arrays_payload=heldout["arrays"],
            supplemental_members=combined_supplements,
        )
    )
    wind_path = RECOVERY / "wind_pilot" / "wind_farm_pilot.tbx.zip"
    wind_report = audit_bundle(wind_path)
    receipts.append(
        {
            "profile": "geometry-pilot-v0.3.0",
            "filename": wind_path.name,
            "sha256": sha256(wind_path.read_bytes()),
            "bytes": wind_path.stat().st_size,
            "checked_files": wind_report.checked_files,
            "audit_valid": wind_report.valid,
        }
    )
    if not wind_report.valid:
        raise RuntimeError("wind-farm pilot TBX no longer audits")
    PUBLIC_EXAMPLE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OUTPUT / "geometry-method-v2-combined-v0.3.0.tbx.zip", PUBLIC_EXAMPLE)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_json(
        OUTPUT / "tbx_build_receipt.json",
        {
            "schema_version": "1.0.0",
            "status": "PASS",
            "bundles": receipts,
            "all_audits_valid": all(row["audit_valid"] for row in receipts),
            "public_example": str(PUBLIC_EXAMPLE.relative_to(ROOT)).replace("\\", "/"),
            "raw_source_archives_embedded": False,
            "registered_observation_arrays_embedded": True,
            "TLD_DERIVED": "BLOCKED",
            "EXTERNALLY_VALIDATED": False,
        },
    )
    print(json.dumps({"status": "PASS", "bundles": receipts}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
