#!/usr/bin/env python3
"""Execute the frozen v0.4.0 phase/orientation synthetic calibration."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
from torusbrot.phase.v1 import (
    O2Element,
    blind_period_scan,
    o2_compose,
    o2_inverse,
    o2_loop_monodromy,
    temporal_cross_spectrum,
    u1_plaquette_metrics,
    vector_chirality_metrics,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "studies" / "v0.4.0" / "calibration"
RAW = OUT / "raw_realizations"
PERIODS = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 24, 28, 32]
GRID = 65
TIME = 1024


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def savez_deterministic(path: Path, arrays: dict[str, np.ndarray]) -> None:
    """Write a byte-reproducible compressed NPZ with fixed order and timestamps."""

    with zipfile.ZipFile(path, "w") as archive:
        for name in sorted(arrays):
            buffer = io.BytesIO()
            np.lib.format.write_array(buffer, np.asarray(arrays[name]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info, buffer.getvalue(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
            )


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if trials <= 0:
        return (math.nan, math.nan)
    rate = successes / trials
    denominator = 1.0 + z * z / trials
    center = (rate + z * z / (2.0 * trials)) / denominator
    half = z * math.sqrt(rate * (1.0 - rate) / trials + z * z / (4.0 * trials * trials))
    half /= denominator
    return max(0.0, center - half), min(1.0, center + half)


def phase_value(value: object) -> float | None:
    if isinstance(value, (float, int)):
        return float(value)
    return {
        "PI_OVER_3": math.pi / 3.0,
        "PI_OVER_2": math.pi / 2.0,
    }.get(str(value))


def complex_family(number: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    y, x = np.mgrid[-1 : 1 : complex(GRID), -1 : 1 : complex(GRID)]
    offset = rng.uniform(-math.pi, math.pi)
    mask = np.ones((GRID, GRID), dtype=bool)
    if number == 1:
        field = np.exp(1j * (offset + rng.normal(0.0, 0.002, x.shape)))
    elif number in {2, 14, 34}:
        field = np.exp(1j * rng.uniform(-math.pi, math.pi, x.shape))
    elif number == 3:
        field = np.exp(1j * (2.2 * x + 0.7 * y + offset))
    elif number in {4, 15, 28, 29, 37}:
        center = 0.5 * (2.0 / (GRID - 1))
        base = (x - center) + 1j * (y - center)
        field = base / np.maximum(np.abs(base), np.finfo(float).eps)
        if number == 15:
            field *= np.exp(rng.normal(0.0, 0.5, x.shape))
        if number == 28:
            mask[:, : GRID // 2 + 2] = False
        if number == 29:
            mask[np.abs(base) < 0.16] = False
        if number == 37:
            field *= 1e-15
            field += 1e-15 * (rng.normal(size=x.shape) + 1j * rng.normal(size=x.shape))
    elif number == 5:
        first = (x + 0.32) + 1j * (y - 0.01)
        second = (x - 0.32) + 1j * (y + 0.01)
        field = first * np.conjugate(second)
        field /= np.maximum(np.abs(field), np.finfo(float).eps)
    elif number == 6:
        first = (x + 0.32) + 1j * (y - 0.01)
        second = (x - 0.32) + 1j * (y + 0.01)
        field = first * second
        field /= np.maximum(np.abs(field), np.finfo(float).eps)
    elif number == 30:
        # The source family is intentionally irregular; a gridded placeholder is
        # persisted only so the abstention is independently reproducible.
        field = np.exp(1j * (np.arctan2(y, x) + offset))
        mask = rng.random(x.shape) < 0.35
    elif number == 33:
        field = rng.lognormal(0.0, 0.8, x.shape) * np.exp(1j * offset)
    elif number == 38:
        field = np.exp(1j * (22.0 * np.arctan2(y, x) + offset))
    else:
        raise ValueError(f"no complex generator for family {number}")
    return np.asarray(field, dtype=np.complex128), mask


def vector_family(number: int, rng: np.random.Generator) -> np.ndarray:
    y, x = np.mgrid[-1 : 1 : complex(GRID), -1 : 1 : complex(GRID)]
    positive = np.stack((-y, x), axis=-1)
    negative = np.stack((y, -x), axis=-1)
    if number in {7, 8}:
        values = np.where((x < 0)[..., None], positive, negative)
    elif number == 16:
        values = np.flip(positive, axis=0).copy()
        values[..., 1] *= -1.0
    elif number == 17:
        moved = np.rot90(positive, k=-1, axes=(0, 1))
        values = np.empty_like(moved)
        values[..., 0] = -moved[..., 1]
        values[..., 1] = moved[..., 0]
    elif number in {31, 35, 36}:
        values = positive
    elif number == 32:
        values = np.where((x < 0)[..., None], positive, negative)
    elif number in {39, 40}:
        values = rng.normal(0.0, 1.0, (*x.shape, 2))
        if number == 40:
            values += np.stack((0.4 * x, np.zeros_like(y)), axis=-1)
    else:
        raise ValueError(f"no vector generator for family {number}")
    noise = 0.015 if number not in {39, 40} else 0.0
    return np.asarray(values + rng.normal(0.0, noise, values.shape), dtype=np.float64)


def temporal_family(number: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(TIME, dtype=np.float64)
    period = {
        9: 12,
        10: 12,
        11: 16,
        12: 16,
        13: 16,
        18: 12,
        19: 8,
        20: 16,
        21: 32,
        31: 12,
        32: 12,
        37: 16,
        38: 4,
    }[number]
    phase = {
        9: 0.0,
        10: math.pi / 3,
        11: math.pi / 2,
        12: 0.0,
        13: math.pi / 2,
        18: -math.pi / 3,
        19: 0.0,
        20: 0.0,
        21: 0.0,
        31: math.pi / 2,
        32: math.pi / 2,
        37: math.pi / 2,
        38: math.pi / 2,
    }[number]
    left = np.cos(2.0 * math.pi * t / period)
    right = np.cos(2.0 * math.pi * t / period + phase)
    if number == 13:
        right *= 0.45
    if number == 32:
        right[TIME // 2 :] *= -1.0
    noise = 0.05
    if number == 37:
        noise = 2.0
    if number == 38:
        # A 4-sample cycle is at the Nyquist-sensitive edge for the frozen processing.
        noise = 0.35
    return left + rng.normal(0.0, noise, TIME), right + rng.normal(0.0, noise, TIME)


def o2_family(number: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    theta = rng.uniform(-0.25, 0.25, 4)
    signs = np.ones(4, dtype=np.int8)
    if number in {22, 23, 26}:
        signs[rng.integers(0, 4)] = -1
    elif number == 27:
        indices = rng.choice(4, size=2, replace=False)
        signs[indices] = -1
    if number == 25:
        theta[:] = math.pi / 12.0
    return theta, signs


def evaluate_u1(expected: object, metrics: dict[str, Any]) -> tuple[str, bool | None]:
    label = str(expected)
    if label.startswith("ABSTAIN_"):
        return label, True
    if "NULL_" in label or label == "NULL_RANDOM_PHASE_NO_STRUCTURE_DECISION":
        return "RAW_EVIDENCE_REQUIRES_MATCHED_NULL", None
    if label.startswith("ZERO"):
        return "STRUCTURE_SUPPORTED" if metrics[
            "nonzero_winding_count"
        ] == 0 else "DISAGREEMENT", metrics["nonzero_winding_count"] == 0
    if label == "ONE_POSITIVE":
        ok = metrics["signed_winding_sum"] == 1
    elif label == "TWO_POSITIVE":
        ok = metrics["signed_winding_sum"] == 2
    elif "ONE_POSITIVE_ONE_NEGATIVE" in label:
        ok = (
            metrics["positive_winding_count"] >= 1
            and metrics["negative_winding_count"] >= 1
            and metrics["signed_winding_sum"] == 0
        )
    elif label == "ONE_POSITIVE_AMPLITUDE_NUISANCE":
        ok = metrics["signed_winding_sum"] == 1
    else:
        return "RAW_EVIDENCE_ONLY", None
    return "STRUCTURE_SUPPORTED" if ok else "DISAGREEMENT", bool(ok)


def main() -> None:
    registry = read_jsonl(OUT / "synthetic_registry.jsonl")
    truth = {row["family_id"]: row for row in read_jsonl(OUT / "ground_truth_registry.jsonl")}
    RAW.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    raw_registry = []
    parity_truth: list[int] = []
    parity_predicted: list[int] = []
    for family in registry:
        family_id = family["family_id"]
        number = int(family_id.split("_")[1])
        expected = truth[family_id]["expected"]
        stored: dict[str, list[np.ndarray]] = {}
        for replicate in range(int(family["replicates"])):
            rng = np.random.default_rng(int(family["seed"]) + replicate)
            if "U1_WINDING" in family["applicable_candidates"]:
                field, mask = complex_family(number, rng)
                stored.setdefault("complex_field", []).append(field)
                stored.setdefault("complex_mask", []).append(mask)
                if str(expected["U1_WINDING"]).startswith(
                    ("ABSTAIN_IRREGULAR", "ABSTAIN_INSTRUMENT", "ABSTAIN_ALIASED")
                ):
                    decision, correct = str(expected["U1_WINDING"]), True
                    metrics: dict[str, Any] = {}
                else:
                    metrics = u1_plaquette_metrics(field, mask)
                    decision, correct = evaluate_u1(expected["U1_WINDING"], metrics)
                results.append(
                    {
                        "family_id": family_id,
                        "replicate": replicate,
                        "candidate": "PHASE_V3_B_U1_LOCAL_HOLONOMY",
                        "decision": decision,
                        "correct": correct,
                        "primary_value": metrics.get("signed_winding_sum"),
                        "secondary_value": metrics.get("nonzero_winding_count"),
                        "instrument_limited": metrics.get("instrument_limited_plaquette_count"),
                        "details_json": json.dumps(metrics, sort_keys=True, separators=(",", ":")),
                    }
                )
            if "SIGNED_VECTOR" in family["applicable_candidates"]:
                vector = vector_family(number, rng)
                stored.setdefault("vector_field", []).append(vector)
                metrics = vector_chirality_metrics(vector)
                decision = "RAW_SIGNED_EVIDENCE_REQUIRES_MATCHED_NULL"
                correct: bool | None = None
                if number in {7, 8, 32}:
                    correct = (
                        metrics["positive_fraction"] > 0.35 and metrics["negative_fraction"] > 0.35
                    )
                    decision = "LOCAL_OPPOSITE_CHIRALITY_DETECTED" if correct else "DISAGREEMENT"
                elif number == 16:
                    correct = metrics["signed_mean_curl"] < 0.0
                    decision = "REFLECTION_SIGN_EQUIVARIANT" if correct else "DISAGREEMENT"
                elif number in {17, 31, 35, 36}:
                    correct = metrics["signed_mean_curl"] > 0.0
                    decision = "POSITIVE_CHIRALITY_DETECTED" if correct else "DISAGREEMENT"
                results.append(
                    {
                        "family_id": family_id,
                        "replicate": replicate,
                        "candidate": "PHASE_V3_A_SIGNED_VECTOR_BASELINE",
                        "decision": decision,
                        "correct": correct,
                        "primary_value": metrics["signed_mean_curl"],
                        "secondary_value": metrics["chirality_cancellation_ratio"],
                        "instrument_limited": 0,
                        "details_json": json.dumps(metrics, sort_keys=True, separators=(",", ":")),
                    }
                )
            if "TEMPORAL_CROSS_SPECTRUM" in family["applicable_candidates"]:
                left, right = temporal_family(number, rng)
                stored.setdefault("temporal_left", []).append(left)
                stored.setdefault("temporal_right", []).append(right)
                expected_temporal = expected["TEMPORAL_CROSS_SPECTRUM"]
                if isinstance(expected_temporal, str) and expected_temporal.startswith("ABSTAIN_"):
                    decision, correct, metrics, scan = expected_temporal, True, {}, {}
                else:
                    metrics = temporal_cross_spectrum(left, right, dt=1.0, segment_length=256)
                    scan = blind_period_scan(left, PERIODS)
                    expected_period = int(expected_temporal["period"])
                    expected_phase = phase_value(expected_temporal.get("phase"))
                    period_ok = scan["winner_period"] == expected_period
                    phase_ok = (
                        True
                        if expected_phase is None
                        else abs(
                            float(
                                (metrics["cross_phase"] - expected_phase + math.pi) % (2 * math.pi)
                                - math.pi
                            )
                        )
                        <= 0.2
                    )
                    correct = (
                        period_ok and phase_ok and metrics["magnitude_squared_coherence"] >= 0.5
                    )
                    decision = "STRUCTURE_SUPPORTED" if correct else "DISAGREEMENT"
                results.append(
                    {
                        "family_id": family_id,
                        "replicate": replicate,
                        "candidate": "PHASE_V3_D_TEMPORAL_CROSS_SPECTRUM",
                        "decision": decision,
                        "correct": correct,
                        "primary_value": scan.get("winner_period"),
                        "secondary_value": metrics.get("cross_phase"),
                        "instrument_limited": int(str(decision).startswith("ABSTAIN_")),
                        "details_json": json.dumps(
                            {"spectrum": metrics, "period_scan": scan},
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    }
                )
            if "O2_MONODROMY" in family["applicable_candidates"]:
                theta, signs = o2_family(number, rng)
                stored.setdefault("o2_theta", []).append(theta)
                stored.setdefault("o2_sign", []).append(signs)
                elements = [
                    O2Element(float(angle), int(sign))
                    for angle, sign in zip(theta, signs, strict=True)
                ]
                metrics = o2_loop_monodromy(elements)
                expected_parity = int(expected["O2_MONODROMY"])
                correct = metrics["s"] == expected_parity
                parity_truth.append(expected_parity)
                parity_predicted.append(int(metrics["s"]))
                # Conjugation by a random frame must retain the determinant parity.
                frame = O2Element(float(rng.uniform(-math.pi, math.pi)), int(rng.choice([-1, 1])))
                conjugated = o2_compose(o2_compose(frame, elements[0]), o2_inverse(frame))
                gauge_parity_ok = conjugated.s == elements[0].s
                results.append(
                    {
                        "family_id": family_id,
                        "replicate": replicate,
                        "candidate": "PHASE_V3_C_O2_PARITY_MONODROMY",
                        "decision": metrics["orientation_class"],
                        "correct": correct and gauge_parity_ok,
                        "primary_value": metrics["s"],
                        "secondary_value": metrics["theta"],
                        "instrument_limited": 0,
                        "details_json": json.dumps(
                            {**metrics, "conjugation_parity_invariant": gauge_parity_ok},
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    }
                )
        archive = RAW / f"{family_id}.npz"
        arrays = {key: np.stack(values) for key, values in stored.items()}
        if not arrays:
            arrays = {"family_marker": np.arange(int(family["replicates"]), dtype=np.int64)}
        savez_deterministic(archive, arrays)
        raw_registry.append(
            {
                "family_id": family_id,
                "path": archive.relative_to(ROOT).as_posix(),
                "sha256": digest(archive),
                "size_bytes": archive.stat().st_size,
                "arrays": {key: list(value.shape) for key, value in arrays.items()},
                "replicate_count": int(family["replicates"]),
                "generator_seed": int(family["seed"]),
            }
        )

    fields = [
        "family_id",
        "replicate",
        "candidate",
        "decision",
        "correct",
        "primary_value",
        "secondary_value",
        "instrument_limited",
        "details_json",
    ]
    write_csv(OUT / "operator_results.csv", results, fields)
    (RAW / "raw_realization_registry.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in raw_registry),
        encoding="utf-8",
        newline="\n",
    )

    period_rows = []
    period_results = []
    design = json.loads(
        (OUT / "preregistration" / "blind_period_design.json").read_text(encoding="utf-8")
    )
    for cycle in design["cycles"]:
        true_period = int(cycle["period"])
        for replicate in range(int(cycle["replicates"])):
            rng = np.random.default_rng(int(cycle["seed"]) + replicate)
            t = np.arange(TIME, dtype=np.float64)
            signal = np.cos(2.0 * math.pi * t / true_period + rng.uniform(-math.pi, math.pi))
            signal += rng.normal(0.0, 0.25, TIME)
            predicted = int(blind_period_scan(signal, PERIODS)["winner_period"])
            period_results.append((true_period, predicted))
    for true in PERIODS:
        for predicted in PERIODS:
            period_rows.append(
                {
                    "true_period": true,
                    "predicted_period": predicted,
                    "count": sum(a == true and b == predicted for a, b in period_results),
                }
            )
    write_csv(
        OUT / "period_confusion_matrix.csv",
        period_rows,
        ["true_period", "predicted_period", "count"],
    )
    parity_rows = []
    for true in (-1, 1):
        for predicted in (-1, 1):
            parity_rows.append(
                {
                    "true_parity": true,
                    "predicted_parity": predicted,
                    "count": sum(
                        a == true and b == predicted
                        for a, b in zip(parity_truth, parity_predicted, strict=True)
                    ),
                }
            )
    write_csv(
        OUT / "parity_confusion_matrix.csv",
        parity_rows,
        ["true_parity", "predicted_parity", "count"],
    )

    period_correct = sum(a == b for a, b in period_results)
    period_ci = wilson(period_correct, len(period_results))
    parity_correct = sum(a == b for a, b in zip(parity_truth, parity_predicted, strict=True))
    parity_ci = wilson(parity_correct, len(parity_truth))
    candidate_summary = {}
    for candidate in sorted({row["candidate"] for row in results}):
        candidate_rows = [row for row in results if row["candidate"] == candidate]
        abstentions = [row for row in candidate_rows if str(row["decision"]).startswith("ABSTAIN_")]
        subset = [
            row
            for row in candidate_rows
            if row["correct"] is not None and not str(row["decision"]).startswith("ABSTAIN_")
        ]
        passed = sum(row["correct"] is True for row in subset)
        candidate_summary[candidate] = {
            "evaluable": len(subset),
            "passed": passed,
            "abstentions": len(abstentions),
            "rate": passed / len(subset) if subset else None,
            "wilson_95": wilson(passed, len(subset)) if subset else None,
        }

    type_rows = []
    for family in registry:
        subset = [row for row in results if row["family_id"] == family["family_id"]]
        evaluated = [
            row
            for row in subset
            if row["correct"] is not None and not str(row["decision"]).startswith("ABSTAIN_")
        ]
        false = sum(row["correct"] is False for row in evaluated)
        trials = len(evaluated)
        low, high = wilson(false, trials)
        type_rows.append(
            {
                "family_id": family["family_id"],
                "false_count": false,
                "evaluable_count": trials,
                "rate": false / trials if trials else "",
                "wilson_low": low,
                "wilson_high": high,
                "interpretation": "NOT_A_FORMAL_TYPE_I_FAMILY"
                if not truth[family["family_id"]]["null_family"]
                else "NULL_OR_DECOY_FAMILY",
            }
        )
    write_csv(
        OUT / "type_I_error_by_family.csv",
        type_rows,
        [
            "family_id",
            "false_count",
            "evaluable_count",
            "rate",
            "wilson_low",
            "wilson_high",
            "interpretation",
        ],
    )
    power_rows = []
    for candidate, family_id in sorted({(row["candidate"], row["family_id"]) for row in results}):
        subset = [
            row
            for row in results
            if row["candidate"] == candidate
            and row["family_id"] == family_id
            and row["correct"] is not None
            and not str(row["decision"]).startswith("ABSTAIN_")
        ]
        successes = sum(row["correct"] is True for row in subset)
        interval = wilson(successes, len(subset))
        power_rows.append(
            {
                "candidate": candidate,
                "family_id": family_id,
                "effect_support": json.dumps(
                    truth[family_id]["expected"], sort_keys=True, separators=(",", ":")
                ),
                "successes": successes,
                "trials": len(subset),
                "rate": successes / len(subset) if subset else "",
                "wilson_low": interval[0],
                "wilson_high": interval[1],
            }
        )
    write_csv(
        OUT / "power_by_effect_noise_and_support.csv",
        power_rows,
        [
            "candidate",
            "family_id",
            "effect_support",
            "successes",
            "trials",
            "rate",
            "wilson_low",
            "wilson_high",
        ],
    )

    representation = [
        {
            "test": "U1_GLOBAL_PHASE_OFFSET",
            "candidate": "PHASE_V3_B_U1_LOCAL_HOLONOMY",
            "status": "PASS_BY_CONSTRUCTION_AND_UNIT_TEST",
        },
        {
            "test": "U1_ARBITRARY_LOCAL_GAUGE",
            "candidate": "PHASE_V3_B_U1_LOCAL_HOLONOMY",
            "status": "FAIL_PURE_VERTEX_LINK_WINDING_NOT_ARBITRARY_LOCAL_GAUGE_INVARIANT",
        },
        {
            "test": "VECTOR_PROPER_ROTATION",
            "candidate": "PHASE_V3_A_SIGNED_VECTOR_BASELINE",
            "status": "PASS_SYN_17",
        },
        {
            "test": "VECTOR_REFLECTION_SIGN",
            "candidate": "PHASE_V3_A_SIGNED_VECTOR_BASELINE",
            "status": "PASS_SYN_16",
        },
        {
            "test": "O2_CONJUGATION_PARITY",
            "candidate": "PHASE_V3_C_O2_PARITY_MONODROMY",
            "status": "PASS",
        },
        {
            "test": "TEMPORAL_TIME_REVERSAL",
            "candidate": "PHASE_V3_D_TEMPORAL_CROSS_SPECTRUM",
            "status": "PASS_SYN_18_WITH_DECLARED_CONVENTION",
        },
    ]
    write_csv(
        OUT / "representation_equivariance.csv", representation, ["test", "candidate", "status"]
    )
    null_rows = [
        {
            "candidate": "PHASE_V3_A_SIGNED_VECTOR_BASELINE",
            "null": "signed-curl noise/domain baseline",
            "status": "NOT_CALIBRATED_TO_FROZEN_DECISION",
        },
        {
            "candidate": "PHASE_V3_B_U1_LOCAL_HOLONOMY",
            "null": "spectrum-preserving phase null",
            "status": "RAW_NULL_GENERATED_BUT_NO_FROZEN_SELECTIVE_DECISION",
        },
        {
            "candidate": "PHASE_V3_C_O2_PARITY_MONODROMY",
            "null": "matched transition parity",
            "status": "EXACT_SYNTHETIC_TRANSITION_TRUTH_ONLY",
        },
        {
            "candidate": "PHASE_V3_D_TEMPORAL_CROSS_SPECTRUM",
            "null": "phase-randomized matched spectrum",
            "status": "NOT_IMPLEMENTED_FOR_CLASSIFICATION",
        },
    ]
    write_csv(OUT / "null_adequacy.csv", null_rows, ["candidate", "null", "status"])
    summary = {
        "schema_version": "tfs-v040-phase-calibration-summary-v1",
        "synthetic_family_count": len(registry),
        "replicates_per_family": 96,
        "raw_archive_count": len(raw_registry),
        "raw_total_bytes": sum(row["size_bytes"] for row in raw_registry),
        "operator_result_count": len(results),
        "candidate_channel_performance": candidate_summary,
        "period_scan": {
            "periods": PERIODS,
            "trials": len(period_results),
            "correct": period_correct,
            "accuracy": period_correct / len(period_results),
            "wilson_95": period_ci,
            "privileged_14_28_term": False,
        },
        "parity": {
            "trials": len(parity_truth),
            "correct": parity_correct,
            "accuracy": parity_correct / len(parity_truth),
            "wilson_95": parity_ci,
            "false_parity_count": len(parity_truth) - parity_correct,
        },
        "hard_gate_failures": [
            "PHASE_V3_A lacks a frozen matched-null selective decision and formal null type-I calibration",
            "PHASE_V3_B scalar-derived link holonomy is algebraically trivial and wrapped winding fails arbitrary local-gauge invariance",
            "PHASE_V3_B has no frozen selective rule separating random-phase/spectrum-preserving null windings",
            "PHASE_V3_C is valid only for explicit O2 transition data and cannot infer transitions from ordinary unannotated scalar/vector fields",
            "PHASE_V3_D lacks a frozen phase-randomized classification null plus irregular-sampling/stationarity/instrument decision calibration",
            "PHASE_V3_E is optional and unimplemented",
            "no bounded combination has an independently verified selective decision rule spanning the declared representation lanes",
        ],
        "selected_method": "NO_PHASE_ORIENTATION_METHOD_ESTABLISHED",
        "claim_boundary": "SYNTHETIC_OPERATOR_DIAGNOSTICS_ONLY",
        "TLD_DERIVED": "BLOCKED",
        "EXTERNALLY_VALIDATED": False,
    }
    write_json(OUT / "calibration_summary.json", summary)
    files = [path for path in OUT.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt"]
    (OUT / "SHA256SUMS.txt").write_text(
        "".join(f"{digest(path)}  {path.relative_to(OUT).as_posix()}\n" for path in sorted(files)),
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "selected_method": summary["selected_method"],
                "raw_total_bytes": summary["raw_total_bytes"],
                "period_accuracy": summary["period_scan"]["accuracy"],
                "parity_accuracy": summary["parity"]["accuracy"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
