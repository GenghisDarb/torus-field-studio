"""Calibrate held-out separation gates using synthetic fixtures only.

This script intentionally has no file input and cannot read the held-out UCI
archive. It exercises the preregistered statistic on deterministic negative
and positive synthetic parent ensembles before the real study is executed.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np

N_GRID = tuple(range(6, 15))
PARENT_COUNT = 12
NULLS_PER_PARENT = 127
LOCAL_ALPHA = 0.05
UI_MIN = 0.50
NSS_MIN = 2.0
FAMILY_ALPHA = 0.05
SEED = 20260818


def calendar_groups(length: int) -> list[np.ndarray]:
    start = date(2013, 3, 1)
    grouped: dict[tuple[int, int], list[int]] = {}
    for offset in range(length):
        current = start + timedelta(days=offset)
        grouped.setdefault((current.year, current.month), []).append(offset)
    return [np.asarray(indices, dtype=np.int64) for indices in grouped.values()]


def matched_null(values: np.ndarray, groups: list[np.ndarray], seed: int) -> np.ndarray:
    result = values.copy()
    rng = np.random.default_rng(seed)
    for indices in groups:
        result[indices] = values[rng.permutation(indices)]
    return result


def coarse_persistence(values: np.ndarray, n: int) -> float:
    blocks: list[float] = []
    minimum = math.ceil(0.80 * n)
    for start in range(0, len(values) - n + 1, n):
        block = values[start : start + n]
        finite = block[np.isfinite(block)]
        if finite.size >= minimum:
            blocks.append(float(np.mean(finite)))
    if len(blocks) < 30:
        return math.nan
    left = np.asarray(blocks[:-1], dtype=np.float64)
    right = np.asarray(blocks[1:], dtype=np.float64)
    if np.std(left) <= 1e-12 or np.std(right) <= 1e-12:
        return math.nan
    return float(np.corrcoef(left, right)[0, 1])


def one_sided_sign_p(positive: int, total: int) -> float:
    return sum(math.comb(total, k) for k in range(positive, total + 1)) / (2**total)


def holm_adjust(raw: dict[int, float]) -> dict[int, float]:
    ordered = sorted(raw.items(), key=lambda item: (item[1], item[0]))
    adjusted: dict[int, float] = {}
    running = 0.0
    count = len(ordered)
    for rank, (n_value, p_value) in enumerate(ordered):
        running = max(running, min(1.0, (count - rank) * p_value))
        adjusted[n_value] = running
    return adjusted


def evaluate(parents: list[np.ndarray], seed_offset: int) -> dict[str, object]:
    groups = calendar_groups(len(parents[0]))
    rows: list[dict[str, object]] = []
    raw_p: dict[int, float] = {}
    staged: dict[int, tuple[list[float], list[float], list[float]]] = {}
    for n_value in N_GRID:
        observed: list[float] = []
        null_medians: list[float] = []
        local_p_values: list[float] = []
        robust_z: list[float] = []
        for parent_index, parent in enumerate(parents):
            observed_score = coarse_persistence(parent, n_value)
            null_scores = np.asarray(
                [
                    coarse_persistence(
                        matched_null(
                            parent,
                            groups,
                            SEED + seed_offset + parent_index * 10000 + child_index,
                        ),
                        n_value,
                    )
                    for child_index in range(NULLS_PER_PARENT)
                ],
                dtype=np.float64,
            )
            null_scores = null_scores[np.isfinite(null_scores)]
            if not math.isfinite(observed_score) or null_scores.size != NULLS_PER_PARENT:
                raise RuntimeError("synthetic calibration produced an ineligible cell")
            median = float(np.median(null_scores))
            mad = float(np.median(np.abs(null_scores - median)))
            p_value = (1 + int(np.count_nonzero(null_scores >= observed_score))) / (
                NULLS_PER_PARENT + 1
            )
            observed.append(observed_score)
            null_medians.append(median)
            local_p_values.append(p_value)
            robust_z.append((observed_score - median) / max(1.4826 * mad, 1e-12))
        positive = sum(left > right for left, right in zip(observed, null_medians, strict=True))
        raw_p[n_value] = one_sided_sign_p(positive, len(observed))
        staged[n_value] = (local_p_values, robust_z, observed)
    adjusted = holm_adjust(raw_p)
    for n_value in N_GRID:
        local_p_values, robust_z, observed = staged[n_value]
        ui = sum(value <= LOCAL_ALPHA for value in local_p_values) / len(local_p_values)
        nss = float(np.median(robust_z))
        sep = ui >= UI_MIN and nss >= NSS_MIN and adjusted[n_value] <= FAMILY_ALPHA
        rows.append(
            {
                "N": n_value,
                "UI": ui,
                "NSS": nss,
                "holm_p": adjusted[n_value],
                "mean_observed_score": float(np.mean(observed)),
                "SEP": sep,
            }
        )
    return {"rows": rows, "separated_depths": [row["N"] for row in rows if row["SEP"]]}


def fixtures() -> tuple[list[np.ndarray], list[np.ndarray]]:
    length = 1461
    groups = calendar_groups(length)
    negative: list[np.ndarray] = []
    positive: list[np.ndarray] = []
    for parent_index in range(PARENT_COUNT):
        rng = np.random.default_rng(SEED + parent_index)
        negative.append(rng.normal(0.0, 1.0, length))
        # The matched null permutes days inside calendar months. Build the
        # positive fixture at that same semantic level: every month has the
        # same zero-mean/unit-scale marginal distribution, while its daily
        # order carries persistent AR(1) structure. This avoids treating
        # between-month drift as the intended positive control.
        state = np.empty(length, dtype=np.float64)
        for indices in groups:
            innovation = rng.normal(0.0, 0.35, len(indices))
            monthly = np.zeros(len(indices), dtype=np.float64)
            for index in range(1, len(indices)):
                monthly[index] = 0.92 * monthly[index - 1] + innovation[index]
            monthly = (monthly - np.mean(monthly)) / np.std(monthly)
            state[indices] = monthly
        positive.append(state)
    return negative, positive


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    negative, positive = fixtures()
    result = {
        "schema_version": "1.0.0",
        "fixture_only": True,
        "real_source_accessed": False,
        "seed": SEED,
        "parent_count": PARENT_COUNT,
        "nulls_per_parent": NULLS_PER_PARENT,
        "thresholds": {
            "local_alpha": LOCAL_ALPHA,
            "UI_min": UI_MIN,
            "NSS_min": NSS_MIN,
            "family_alpha": FAMILY_ALPHA,
        },
        "fixtures": {
            "negative": "independent standard-normal daily values",
            "positive": (
                "calendar-month-local AR(1), phi=0.92, with every month "
                "standardized to zero mean and unit scale"
            ),
        },
        "negative_fixture": evaluate(negative, 1000000),
        "positive_fixture": evaluate(positive, 2000000),
    }
    result["calibration_passed"] = (
        not result["negative_fixture"]["separated_depths"]
        and bool(result["positive_fixture"]["separated_depths"])
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        print(rendered, end="")
    return 0 if result["calibration_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
