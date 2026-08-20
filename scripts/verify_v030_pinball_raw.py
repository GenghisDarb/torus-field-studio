# ruff: noqa: E501 -- frozen identifiers and comparison paths remain explicit.
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from numpy.typing import NDArray
from torusbrot.models import canonical_json

ROOT = Path(__file__).resolve().parents[1]
HELDOUT = ROOT / "studies" / "v0.3.0-recovery" / "heldout"
SOURCE = ROOT / "external_cache" / "v0.3.0-field-20794709" / "extracted"
MATERIALIZATION = HELDOUT / "materialization"
PREREGISTRATION = HELDOUT / "preregistration"
EXECUTION = HELDOUT / "execution"
OUTPUT = HELDOUT / "raw_verification"
RUN_ID = "pinball-heldout-e9e3d7666b2b10cb"
ROOT_SEED = 20260820
NULL_CHILDREN = 127
JOINT_REPLICATES = 999
CONVERSION = 0.00029076921 * 120.0 / 0.31
TOLERANCE = 1e-12

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path)
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value, pretty=True))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(canonical_json(row) for row in rows))


def derived_seed(label: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{ROOT_SEED}:{label}".encode()).digest()[:8], "big")


def neighbor(values: FloatArray, mask: BoolArray) -> float:
    centered = values - float(np.mean(values[mask]))
    variance = float(np.mean(centered[mask] ** 2))
    if variance <= np.finfo(float).eps:
        return 0.0
    products: list[FloatArray] = []
    horizontal = mask[:, :-1] & mask[:, 1:]
    vertical = mask[:-1, :] & mask[1:, :]
    if np.any(horizontal):
        products.append(centered[:, :-1][horizontal] * centered[:, 1:][horizontal])
    if np.any(vertical):
        products.append(centered[:-1, :][vertical] * centered[1:, :][vertical])
    return 0.0 if not products else float(np.mean(np.concatenate(products)) / variance)


def score(values: FloatArray, mask: BoolArray) -> dict[str, float]:
    u = np.where(mask, values[..., 0], 0.0)
    v = np.where(mask, values[..., 1], 0.0)
    du_dy, du_dx = np.gradient(u)
    dv_dy, dv_dx = np.gradient(v)
    curl = dv_dx - du_dy
    divergence = du_dx + dv_dy
    curl_energy = float(np.mean(curl[mask] ** 2))
    signed_curl = float(np.mean(curl[mask]))
    return {
        "u_neighbor_coherence": neighbor(u, mask),
        "v_neighbor_coherence": neighbor(v, mask),
        "signed_mean_curl": signed_curl,
        "curl_energy": curl_energy,
        "curl_coherence": signed_curl**2 / max(curl_energy, np.finfo(float).eps),
        "divergence_energy": float(np.mean(divergence[mask] ** 2)),
    }


def downsample(values: FloatArray, mask: BoolArray) -> tuple[FloatArray, BoolArray]:
    height = values.shape[0] // 2 * 2
    width = values.shape[1] // 2 * 2
    source = values[:height, :width].reshape(height // 2, 2, width // 2, 2, 2)
    source_mask = mask[:height, :width].reshape(height // 2, 2, width // 2, 2)
    weights = source_mask[..., np.newaxis]
    sums = np.sum(np.where(weights, source, 0.0), axis=(1, 3))
    counts = np.sum(weights, axis=(1, 3))
    output = np.divide(sums, np.maximum(counts, 1), out=np.zeros_like(sums), where=counts > 0)
    return output, counts[..., 0] > 0


def rotation(values: FloatArray, mask: BoolArray) -> tuple[FloatArray, BoolArray]:
    moved = np.rot90(values, k=-1, axes=(0, 1))
    rotated = np.empty_like(moved)
    rotated[..., 0] = -moved[..., 1]
    rotated[..., 1] = moved[..., 0]
    return rotated, np.rot90(mask, k=-1, axes=(0, 1))


def rotation_audit(values: FloatArray, mask: BoolArray) -> dict[str, Any]:
    original = score(values, mask)
    rotated_values, rotated_mask = rotation(values, mask)
    rotated = score(rotated_values, rotated_mask)
    disagreements = {
        "curl_coherence_invariant": abs(original["curl_coherence"] - rotated["curl_coherence"]),
        "curl_energy_invariant": abs(original["curl_energy"] - rotated["curl_energy"]),
        "divergence_energy_invariant": abs(original["divergence_energy"] - rotated["divergence_energy"]),
        "u_to_v_neighbor_equivariance": abs(original["u_neighbor_coherence"] - rotated["v_neighbor_coherence"]),
        "v_to_u_neighbor_equivariance": abs(original["v_neighbor_coherence"] - rotated["u_neighbor_coherence"]),
        "signed_mean_curl_invariant": abs(original["signed_mean_curl"] - rotated["signed_mean_curl"]),
    }
    return {
        "status": "PASS" if max(disagreements.values()) <= 1e-10 else "FAIL",
        "absolute_disagreements": disagreements,
    }


def null_samples(values: FloatArray, mask: BoolArray, seed: int) -> dict[str, list[float]]:
    observed = score(values, mask)
    occupied = values[mask].copy()
    rng = np.random.default_rng(seed)
    output: dict[str, list[float]] = {name: [] for name in observed}
    for _ in range(NULL_CHILDREN):
        child = np.zeros_like(values)
        child[mask] = occupied[rng.permutation(len(occupied))]
        for name, value in score(child, mask).items():
            output[name].append(float(value))
    return output


def scale_views(values: FloatArray, mask: BoolArray) -> list[dict[str, Any]]:
    rows = []
    current_values = values
    current_mask = mask
    for index, ell in enumerate((1, 2, 4)):
        if index:
            current_values, current_mask = downsample(current_values, current_mask)
        rows.append(
            {
                "ell_cells": ell,
                "observed_cells": int(np.sum(current_mask)),
                "channels": score(current_values, current_mask),
            }
        )
    return rows


def perturbations(values: FloatArray, mask: BoolArray, seed: int) -> dict[str, Any]:
    observed = score(values, mask)
    rng = np.random.default_rng(seed)
    occupied_indices = np.flatnonzero(mask)
    dropout_count = max(1, int(np.ceil(0.05 * len(occupied_indices))))
    dropout_mask = mask.copy()
    dropout_mask.flat[rng.choice(occupied_indices, size=dropout_count, replace=False)] = False
    dropout = score(values, dropout_mask)
    noisy_values = values.copy()
    noise_scales = []
    for component in range(2):
        component_values = values[..., component][mask]
        noise_scale = 0.01 * float(np.sqrt(np.mean(component_values**2)))
        noise_scales.append(noise_scale)
        noisy_values[..., component][mask] += rng.normal(0.0, noise_scale, len(component_values))
    noisy = score(noisy_values, mask)
    reduced_values, reduced_mask = downsample(values, mask)
    reduced = score(reduced_values, reduced_mask)
    return {
        "rotation": rotation_audit(values, mask),
        "dropout_count": dropout_count,
        "dropout_fraction": dropout_count / len(occupied_indices),
        "dropout_delta": {name: dropout[name] - value for name, value in observed.items()},
        "noise_scales": noise_scales,
        "noise_delta": {name: noisy[name] - value for name, value in observed.items()},
        "downsample_delta": {name: reduced[name] - value for name, value in observed.items()},
    }


def raw_acquisition(member: str, pair_id: str, role: str) -> dict[str, Any]:
    path = SOURCE.joinpath(*Path(member).parts)
    with h5py.File(path, "r") as source:
        u = np.asarray(source["U"][:], dtype=np.float64)
        v = np.asarray(source["V"][:], dtype=np.float64)
        x = np.asarray(source["X"][:], dtype=np.float64)
        y = np.asarray(source["Y"][:], dtype=np.float64)
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError(f"RAW_VERIFIER_NONFINITE_COORDINATES:{member}")
    mask = np.all(np.isfinite(u) & np.isfinite(v), axis=0)
    if int(np.sum(mask)) < 16:
        raise ValueError(f"RAW_VERIFIER_INSUFFICIENT_CELLS:{member}")
    u *= CONVERSION
    v *= CONVERSION
    mean = np.zeros((*mask.shape, 2), dtype=np.float64)
    mean[..., 0][mask] = np.mean(u[:, mask], axis=0)
    mean[..., 1][mask] = np.mean(v[:, mask], axis=0)
    fluctuations = np.zeros((*u.shape, 2), dtype=np.float64)
    fluctuations[..., 0][:, mask] = u[:, mask] - mean[..., 0][mask]
    fluctuations[..., 1][:, mask] = v[:, mask] - mean[..., 1][mask]
    p02_rows = [score(frame, mask) for frame in fluctuations]
    p02 = {
        f"median_{name}": float(np.median([row[name] for row in p02_rows]))
        for name in p02_rows[0]
    }
    p01 = score(mean, mask)
    u_abs = np.abs(mean[..., 0][mask])
    v_abs = np.abs(mean[..., 1][mask])
    floor = max(float(np.finfo(float).eps), 1e-12 * float(np.median(u_abs)))
    return {
        "member": member,
        "P01_channels": p01,
        "P02_channels": p02,
        "nulls": null_samples(mean, mask, derived_seed(f"null:{pair_id}:{role}:{member}")),
        "scales": scale_views(mean, mask),
        "perturbations": perturbations(mean, mask, derived_seed(f"perturbation:{pair_id}:{role}:{member}")),
        "baseline": {
            "median_absolute_cross_stream_ratio": float(np.median(v_abs / np.maximum(u_abs, floor))),
            "numerical_floor": floor,
        },
        "snapshot_count": u.shape[0],
        "grid_shape_yx": list(mask.shape),
        "observed_cells": int(np.sum(mask)),
    }


def compare_numeric(path: str, expected: Any, actual: Any, ledger: list[dict[str, Any]]) -> None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        if set(expected) != set(actual):
            ledger.append({"path": path, "issue": "KEY_SET_MISMATCH", "expected": sorted(expected), "actual": sorted(actual)})
            return
        for name in expected:
            compare_numeric(f"{path}.{name}", expected[name], actual[name], ledger)
        return
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            ledger.append({"path": path, "issue": "LENGTH_MISMATCH", "expected": len(expected), "actual": len(actual)})
            return
        for index, (left, right) in enumerate(zip(expected, actual, strict=True)):
            compare_numeric(f"{path}[{index}]", left, right, ledger)
        return
    if isinstance(expected, int | float) and isinstance(actual, int | float):
        if not np.isclose(float(expected), float(actual), rtol=0.0, atol=TOLERANCE):
            ledger.append({"path": path, "issue": "NUMERIC_DISAGREEMENT", "expected": expected, "actual": actual})
        return
    if expected != actual:
        ledger.append({"path": path, "issue": "VALUE_DISAGREEMENT", "expected": expected, "actual": actual})


def independent_joint(observed: FloatArray, children: FloatArray, channel: str) -> dict[str, Any]:
    rng = np.random.default_rng(derived_seed(f"joint-null:{channel}"))
    selections = rng.integers(0, NULL_CHILDREN, size=(JOINT_REPLICATES, 28))
    indices = np.broadcast_to(np.arange(28), selections.shape)
    joint = np.median(children[indices, selections], axis=1)
    observed_statistic = float(np.median(observed))
    null_median = float(np.median(joint))
    scale = float(1.4826 * np.median(np.abs(joint - null_median)))
    return {
        "within_campaign_observed_median_pair_delta": observed_statistic,
        "joint_null_median": null_median,
        "joint_null_q025": float(np.quantile(joint, 0.025)),
        "joint_null_q975": float(np.quantile(joint, 0.975)),
        "observed_minus_joint_null_median": observed_statistic - null_median,
        "robust_standardized_effect": (observed_statistic - null_median) / max(scale, np.finfo(float).eps),
        "joint_null_robust_scale": scale,
        "joint_null_values": [float(value) for value in joint],
    }


def main() -> None:
    pairs = read_jsonl(MATERIALIZATION / "paired_acquisition_registry.jsonl")
    preregistration = read_json(PREREGISTRATION / "run_contract.json")
    if len(pairs) != 28 or preregistration["run_id"] != RUN_ID:
        raise SystemExit("RAW_VERIFIER_FROZEN_INPUT_MISMATCH")
    raw: dict[str, dict[str, Any]] = {}
    registry_rows = []
    for pair in pairs:
        for role, key in (("ACTUATED", "actuated_member"), ("REFERENCE", "reference_member")):
            member = pair[key]
            recomputed = raw_acquisition(member, pair["pair_id"], role)
            raw[member] = recomputed
            registry_rows.append(
                {
                    "pair_id": pair["pair_id"],
                    "role": role,
                    "member": member,
                    "recomputation_sha256": hashlib.sha256(canonical_json(recomputed)).hexdigest(),
                    "snapshot_count": recomputed["snapshot_count"],
                    "grid_shape_yx": recomputed["grid_shape_yx"],
                    "observed_cells": recomputed["observed_cells"],
                    "P01_channel_count": len(recomputed["P01_channels"]),
                    "P02_channel_count": len(recomputed["P02_channels"]),
                    "null_children_per_channel": NULL_CHILDREN,
                }
            )
    # Production outputs are loaded only after raw recomputation is complete.
    production_acquisitions = read_jsonl(EXECUTION / "acquisition_evidence.jsonl")
    production_nulls = read_jsonl(EXECUTION / "acquisition_null_children.jsonl")
    production_pairs = read_jsonl(EXECUTION / "pair_evidence.jsonl")
    production_pair_nulls = read_jsonl(EXECUTION / "pair_null_children.jsonl")
    production_joint = read_json(EXECUTION / "joint_null_evidence.json")
    acquisition_by_member = {row["member"]: row for row in production_acquisitions}
    null_by_member = {row["member"]: row for row in production_nulls}
    pair_by_id = {row["pair_id"]: row for row in production_pairs}
    pair_null_by_id = {row["pair_id"]: row for row in production_pair_nulls}
    ledger: list[dict[str, Any]] = []
    for member, recomputed in raw.items():
        production = acquisition_by_member[member]
        compare_numeric(f"{member}.P01", recomputed["P01_channels"], production["P01_channels"], ledger)
        compare_numeric(f"{member}.P02", recomputed["P02_channels"], production["P02_channels"], ledger)
        compare_numeric(f"{member}.nulls", recomputed["nulls"], null_by_member[member]["samples_by_channel"], ledger)
        production_scales = [
            {
                "ell_cells": row["ell_cells"],
                "observed_cells": row["observed_cells"],
                "channels": row["channels"],
            }
            for row in production["scale_views"]
        ]
        compare_numeric(f"{member}.scales", recomputed["scales"], production_scales, ledger)
        perturbation = production["perturbations"]
        production_perturbation = {
            "rotation": {
                "status": perturbation["PERT01_ROTATE_90_WITH_COORDINATES_COMPONENTS_AND_MASK"]["status"],
                "absolute_disagreements": perturbation["PERT01_ROTATE_90_WITH_COORDINATES_COMPONENTS_AND_MASK"]["absolute_disagreements"],
            },
            "dropout_count": perturbation["PERT02_MASK_DROPOUT_5_PERCENT"]["dropped_cell_count"],
            "dropout_fraction": perturbation["PERT02_MASK_DROPOUT_5_PERCENT"]["actual_fraction"],
            "dropout_delta": perturbation["PERT02_MASK_DROPOUT_5_PERCENT"]["channel_delta"],
            "noise_scales": perturbation["PERT03_RELATIVE_COMPONENT_NOISE_1_PERCENT"]["component_sigma"],
            "noise_delta": perturbation["PERT03_RELATIVE_COMPONENT_NOISE_1_PERCENT"]["channel_delta"],
            "downsample_delta": perturbation["PERT04_ANTI_ALIASED_SCALE_2X"]["channel_delta"],
        }
        compare_numeric(f"{member}.perturbations", recomputed["perturbations"], production_perturbation, ledger)
        compare_numeric(f"{member}.baseline", recomputed["baseline"], production["domain_baseline"], ledger)
        compare_numeric(f"{member}.snapshot_count", recomputed["snapshot_count"], production["projection_audit"]["snapshot_count"], ledger)
        compare_numeric(f"{member}.grid_shape", recomputed["grid_shape_yx"], production["projection_audit"]["grid_shape_yx"], ledger)
        compare_numeric(f"{member}.observed_cells", recomputed["observed_cells"], production["projection_audit"]["observed_grid_cells"], ledger)
    observed_by_channel: dict[str, list[float]] = {}
    null_by_channel: dict[str, list[list[float]]] = {}
    for pair in pairs:
        pair_id = pair["pair_id"]
        actuated = raw[pair["actuated_member"]]
        reference = raw[pair["reference_member"]]
        production = pair_by_id[pair_id]
        production_null = pair_null_by_id[pair_id]["null_child_pair_deltas_by_channel"]
        for projection in ("P01", "P02"):
            recomputed_delta = {
                name: actuated[f"{projection}_channels"][name] - reference[f"{projection}_channels"][name]
                for name in actuated[f"{projection}_channels"]
            }
            compare_numeric(f"{pair_id}.{projection}_delta", recomputed_delta, production[f"{projection}_pair_delta"], ledger)
            if projection == "P01":
                for channel, value in recomputed_delta.items():
                    null_delta = np.asarray(actuated["nulls"][channel]) - np.asarray(reference["nulls"][channel])
                    compare_numeric(f"{pair_id}.null_delta.{channel}", [float(item) for item in null_delta], production_null[channel], ledger)
                    observed_by_channel.setdefault(channel, []).append(float(value))
                    null_by_channel.setdefault(channel, []).append([float(item) for item in null_delta])
    for channel, saved in production_joint["channels"].items():
        independently_recomputed = independent_joint(
            np.asarray(observed_by_channel[channel], dtype=np.float64),
            np.asarray(null_by_channel[channel], dtype=np.float64),
            channel,
        )
        expected = {name: saved[name] for name in independently_recomputed}
        compare_numeric(f"joint.{channel}", independently_recomputed, expected, ledger)
    verification = {
        "schema_version": "1.0.0",
        "run_id": RUN_ID,
        "status": "PASS" if not ledger else "FAIL",
        "raw_hdf5_field_values_reopened_for_verification": True,
        "production_runner_imported": False,
        "production_results_loaded_after_raw_recomputation": True,
        "new_scored_execution": False,
        "new_claim_adjudication": False,
        "scored_execution_count": 1,
        "acquisitions_recomputed": len(raw),
        "paired_blocks_recomputed": len(pairs),
        "P01_channels_recomputed": True,
        "P02_channels_recomputed": True,
        "null_children_recomputed": len(raw) * NULL_CHILDREN,
        "scale_views_recomputed": True,
        "perturbations_recomputed": True,
        "domain_baseline_recomputed": True,
        "pair_deltas_recomputed": True,
        "joint_null_replicates_recomputed_per_channel": JOINT_REPLICATES,
        "disagreement_count": len(ledger),
        "TLD_DERIVED": "BLOCKED",
        "EXTERNALLY_VALIDATED": False,
    }
    write_json(OUTPUT / "independent_raw_recomputation.json", verification)
    write_jsonl(OUTPUT / "raw_recomputation_registry.jsonl", registry_rows)
    write_jsonl(OUTPUT / "independent_disagreement_ledger.jsonl", ledger)
    write_json(
        OUTPUT / "independent_verifier_scope.json",
        {
            "schema_version": "1.0.0",
            "primary_evidence": ["raw HDF5 U, V, X, Y arrays", "frozen pair registry", "frozen run contract"],
            "production_evidence_use": "comparison only after all 56 raw acquisitions were independently recomputed",
            "production_runner_imported": False,
            "ControllerGate_modified": False,
            "second_scored_execution": False,
            "claim_authority": "NONE_VERIFICATION_ONLY",
        },
    )
    print(json.dumps(verification, indent=2, sort_keys=True))
    if ledger:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
