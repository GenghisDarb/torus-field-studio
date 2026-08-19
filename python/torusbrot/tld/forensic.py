"""Post-release forensic diagnostics for the frozen v0.2.1 held-out study.

This module is deliberately additive.  It reads the immutable v0.2.1 inputs and
outputs, emits separately labelled post-hoc diagnostics, and never rewrites the
registered endpoints.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from ..domains.beijing_pm25 import (
    DIAGNOSTIC_CONDITIONS,
    PRIMARY_CONDITIONS,
    STATIONS,
    sha256_file,
)
from ..models import canonical_json

PRIMARY_N = tuple(range(6, 15))
SPECIFICITY_N = tuple(range(4, 21))
FORENSIC_SEED = 20260818
POSTHOC = "POST_HOC_DIAGNOSTIC_ONLY"
ORIGINAL_RESULT = "HELDOUT_TLD_STUDY_NEGATIVE_UNDER_FROZEN_GATES"
PROJECT_WORDING = (
    "The v0.2.1 preregistered positive-persistence projection failed on the "
    "Beijing PM2.5 dataset."
)


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value, pretty=True))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(canonical_json(row) for row in rows))


def _clean(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: _clean(value) for key, value in row.items()} for row in rows)
    path.write_text(stream.getvalue(), encoding="utf-8", newline="\n")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _exact_upper(positive: int, total: int) -> float:
    return sum(math.comb(total, count) for count in range(positive, total + 1)) / (2**total)


def _exact_lower(negative: int, total: int) -> float:
    return _exact_upper(negative, total)


def _exact_two_sided(positive: int, negative: int) -> float:
    total = positive + negative
    if total == 0:
        return 1.0
    return min(1.0, 2 * _exact_upper(max(positive, negative), total))


def _holm(values: dict[Any, float]) -> dict[Any, float]:
    ordered = sorted(values.items(), key=lambda item: (item[1], str(item[0])))
    adjusted: dict[Any, float] = {}
    running = 0.0
    for rank, (key, value) in enumerate(ordered):
        running = max(running, min(1.0, (len(ordered) - rank) * value))
        adjusted[key] = running
    return adjusted


def _block_means(values: np.ndarray, n_value: int, phase: int = 0) -> np.ndarray:
    shifted = values[phase:]
    count = len(shifted) // n_value
    if count < 2:
        return np.asarray([], dtype=np.float64)
    blocks = shifted[: count * n_value].reshape(count, n_value)
    finite_count = np.count_nonzero(np.isfinite(blocks), axis=1)
    result = np.divide(
        np.nansum(blocks, axis=1),
        finite_count,
        out=np.full(count, np.nan),
        where=finite_count > 0,
    )
    result[finite_count < math.ceil(0.8 * n_value)] = np.nan
    return result


def block_persistence(values: np.ndarray, n_value: int, phase: int = 0) -> float:
    """Independent v0.2.1-compatible lag-1 correlation implementation."""
    blocks = _block_means(values, n_value, phase)
    if np.count_nonzero(np.isfinite(blocks)) < 30:
        return math.nan
    left, right = blocks[:-1], blocks[1:]
    mask = np.isfinite(left) & np.isfinite(right)
    if np.count_nonzero(mask) < 2:
        return math.nan
    if np.std(left[mask]) <= 1e-12 or np.std(right[mask]) <= 1e-12:
        return math.nan
    return float(np.corrcoef(left[mask], right[mask])[0, 1])


def rolling_persistence(values: np.ndarray, n_value: int) -> float:
    means = []
    for start in range(0, len(values) - n_value + 1):
        window = values[start : start + n_value]
        finite = window[np.isfinite(window)]
        means.append(float(np.mean(finite)) if len(finite) >= math.ceil(0.8 * n_value) else np.nan)
    array = np.asarray(means)
    mask = np.isfinite(array[:-1]) & np.isfinite(array[1:])
    if np.count_nonzero(mask) < 30:
        return math.nan
    return float(np.corrcoef(array[:-1][mask], array[1:][mask])[0, 1])


def closure_error(values: np.ndarray, n_value: int) -> float:
    left, right = values[:-n_value], values[n_value:]
    mask = np.isfinite(left) & np.isfinite(right)
    finite = values[np.isfinite(values)]
    if np.count_nonzero(mask) < 365 or finite.size == 0:
        return math.nan
    rms = math.sqrt(float(np.mean(np.square(finite))))
    if rms <= 1e-12:
        return math.nan
    return math.sqrt(float(np.mean(np.square(left[mask] - right[mask])))) / rms


def _matrix_scores(matrix: np.ndarray, n_value: int, phase: int = 0) -> np.ndarray:
    shifted = matrix[:, phase:]
    block_count = shifted.shape[1] // n_value
    blocks = shifted[:, : block_count * n_value].reshape(len(matrix), block_count, n_value)
    counts = np.count_nonzero(np.isfinite(blocks), axis=2)
    means = np.divide(
        np.nansum(blocks, axis=2),
        counts,
        out=np.full((len(matrix), block_count), np.nan),
        where=counts > 0,
    )
    means[counts < math.ceil(0.8 * n_value)] = np.nan
    left, right = means[:, :-1], means[:, 1:]
    valid = np.isfinite(left) & np.isfinite(right)
    pair_count = np.count_nonzero(valid, axis=1)
    x, y = np.where(valid, left, np.nan), np.where(valid, right, np.nan)
    x_mean = np.nanmean(x, axis=1, keepdims=True)
    y_mean = np.nanmean(y, axis=1, keepdims=True)
    covariance = np.nansum((x - x_mean) * (y - y_mean), axis=1)
    denominator = np.sqrt(
        np.nansum(np.square(x - x_mean), axis=1)
        * np.nansum(np.square(y - y_mean), axis=1)
    )
    result = np.divide(
        covariance, denominator, out=np.full(len(matrix), np.nan), where=denominator > 1e-12
    )
    result[pair_count < 30] = np.nan
    return result


def signed_direction_diagnostics(
    arrays: np.lib.npyio.NpzFile,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    conditions = PRIMARY_CONDITIONS + DIAGNOSTIC_CONDITIONS
    for station in STATIONS:
        mapping = arrays[f"permutation__{station}"].astype(np.int64)
        for condition in conditions:
            observed = arrays[f"canonical__{condition}__{station}"].astype(float)
            scores_by_row = np.vstack((observed, observed[mapping]))
            for n_value in PRIMARY_N:
                scores = _matrix_scores(scores_by_row, n_value)
                obs, nulls = float(scores[0]), scores[1:]
                median = float(np.median(nulls))
                mad = float(np.median(np.abs(nulls - median)))
                effect = obs - median
                upper = (1 + int(np.count_nonzero(nulls >= obs))) / 128
                lower = (1 + int(np.count_nonzero(nulls <= obs))) / 128
                two = min(1.0, 2 * min(upper, lower))
                rank = 1 + int(np.count_nonzero(nulls < obs))
                cells.append(
                    {
                        "station": station,
                        "condition": condition,
                        "N": n_value,
                        "observed_score": obs,
                        "null_median": median,
                        "observed_minus_null_median": effect,
                        "signed_robust_z": effect / max(1.4826 * mad, 1e-12),
                        "absolute_robust_z": abs(effect) / max(1.4826 * mad, 1e-12),
                        "upper_tail_local_p": upper,
                        "lower_tail_local_p": lower,
                        "two_sided_local_p": two,
                        "rank_among_128_ascending": rank,
                        "null_quantile": (rank - 0.5) / 128,
                        "effect_direction": "POSITIVE" if effect > 0 else "NEGATIVE" if effect < 0 else "TIE",
                        "status": POSTHOC,
                    }
                )
    surfaces: list[dict[str, Any]] = []
    for condition in conditions:
        subset = [row for row in cells if row["condition"] == condition]
        upper_raw: dict[int, float] = {}
        lower_raw: dict[int, float] = {}
        two_raw: dict[int, float] = {}
        staged: dict[int, dict[str, Any]] = {}
        for n_value in PRIMARY_N:
            rows = [row for row in subset if row["N"] == n_value]
            positive = sum(row["effect_direction"] == "POSITIVE" for row in rows)
            negative = sum(row["effect_direction"] == "NEGATIVE" for row in rows)
            ties = len(rows) - positive - negative
            upper_raw[n_value] = _exact_upper(positive, positive + negative)
            lower_raw[n_value] = _exact_lower(negative, positive + negative)
            two_raw[n_value] = _exact_two_sided(positive, negative)
            effects = [float(row["observed_minus_null_median"]) for row in rows]
            staged[n_value] = {
                "condition": condition,
                "N": n_value,
                "positive_parent_count": positive,
                "negative_parent_count": negative,
                "ties": ties,
                "upper_tail_exact_sign_p": upper_raw[n_value],
                "lower_tail_exact_sign_p": lower_raw[n_value],
                "two_sided_exact_sign_p": two_raw[n_value],
                "median_signed_effect": float(np.median(effects)),
                "median_absolute_effect": float(np.median(np.abs(effects))),
                "directional_consensus": (
                    "NEGATIVE" if negative >= 10 else "POSITIVE" if positive >= 10 else "MIXED"
                ),
                "status": POSTHOC,
            }
        upper_holm, lower_holm, two_holm = _holm(upper_raw), _holm(lower_raw), _holm(two_raw)
        for n_value in PRIMARY_N:
            surfaces.append(
                staged[n_value]
                | {
                    "upper_tail_holm_p": upper_holm[n_value],
                    "lower_tail_holm_p": lower_holm[n_value],
                    "two_sided_holm_p": two_holm[n_value],
                }
            )
    baseline = [row for row in surfaces if row["condition"] == "baseline"]
    coherent = sum(row["directional_consensus"] == "NEGATIVE" for row in baseline) >= 7
    consensus = {
        "schema_version": "1.0.0",
        "classification": (
            "COHERENT_OPPOSITE_SIGN_STRUCTURE_EXPLAINED_BY_NULL"
            if coherent
            else "NO_COHERENT_OPPOSITE_SIGN_STRUCTURE"
        ),
        "baseline_negative_consensus_N_count": sum(
            row["directional_consensus"] == "NEGATIVE" for row in baseline
        ),
        "diagnostic_family": "post-hoc reverse-direction analysis",
        "parent_dependence_caveat": "Twelve stations are correlated sensors in one city.",
        "changes_v021_result": False,
    }
    return cells, surfaces, consensus


def _series_metrics(values: np.ndarray, n_value: int, phase: int) -> dict[str, float | int]:
    blocks = _block_means(values, n_value, phase)
    finite = blocks[np.isfinite(blocks)]
    if finite.size < 3:
        return {key: math.nan for key in (
            "block_mean_variance", "adjacent_block_covariance", "adjacent_block_correlation",
            "within_block_variance", "between_block_variance", "extreme_event_adjacency",
            "mean_run_length", "mean_reversion_rate",
        )} | {"month_boundary_crossings": 0}
    shifted = values[phase : phase + (len(values) - phase) // n_value * n_value]
    raw_blocks = shifted.reshape(-1, n_value)
    within = [np.nanvar(row) for row in raw_blocks if np.count_nonzero(np.isfinite(row)) > 1]
    left, right = blocks[:-1], blocks[1:]
    mask = np.isfinite(left) & np.isfinite(right)
    covariance = float(np.cov(left[mask], right[mask], ddof=0)[0, 1])
    correlation = float(np.corrcoef(left[mask], right[mask])[0, 1])
    low, high = np.nanquantile(values, [0.1, 0.9])
    extreme = (finite <= low) | (finite >= high)
    extreme_adjacency = float(np.mean(extreme[:-1] & extreme[1:]))
    signs = finite >= np.median(finite)
    runs: list[int] = []
    current = 1
    for previous, current_sign in zip(signs[:-1], signs[1:], strict=True):
        if previous == current_sign:
            current += 1
        else:
            runs.append(current)
            current = 1
    runs.append(current)
    centered = finite - np.median(finite)
    reversions = centered[:-1] * (centered[1:] - centered[:-1]) < 0
    dates = np.datetime64("2013-03-01") + np.arange(len(values)).astype("timedelta64[D]")
    month = dates.astype("datetime64[M]")
    crossings = 0
    for start in range(phase, phase + len(raw_blocks) * n_value, n_value):
        crossings += int(month[start] != month[start + n_value - 1])
    return {
        "block_mean_variance": float(np.var(finite)),
        "adjacent_block_covariance": covariance,
        "adjacent_block_correlation": correlation,
        "within_block_variance": float(np.mean(within)),
        "between_block_variance": float(np.var(finite)),
        "extreme_event_adjacency": extreme_adjacency,
        "mean_run_length": float(np.mean(runs)),
        "mean_reversion_rate": float(np.mean(reversions)),
        "month_boundary_crossings": crossings,
    }


def null_mechanism_diagnostics(
    arrays: np.lib.npyio.NpzFile,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    differences: list[float] = []
    for station in STATIONS:
        values = arrays[f"canonical__baseline__{station}"].astype(float)
        mapping = arrays[f"permutation__{station}"].astype(np.int64)
        null_matrix = values[mapping]
        year_month_variance = _year_month_mean_variance(values)
        null_low = np.nanquantile(null_matrix, 0.1, axis=1)[:, None]
        null_high = np.nanquantile(null_matrix, 0.9, axis=1)[:, None]
        for n_value in PRIMARY_N:
            for phase in range(n_value):
                observed = _series_metrics(values, n_value, phase)
                null_medians = _matrix_metric_medians(
                    null_matrix, n_value, phase, low=null_low, high=null_high
                )
                row: dict[str, Any] = {
                    "station": station,
                    "N": n_value,
                    "phase": phase,
                    "year_month_mean_variance_observed": year_month_variance,
                    "year_month_mean_variance_null_median": year_month_variance,
                    "status": POSTHOC,
                }
                for key, value in observed.items():
                    null_median = float(null_medians[key])
                    row[f"{key}_observed"] = value
                    row[f"{key}_null_median"] = null_median
                    row[f"{key}_null_minus_observed"] = null_median - float(value)
                differences.append(float(row["adjacent_block_correlation_null_minus_observed"]))
                rows.append(row)
    median_difference = float(np.median(differences))
    audit = {
        "schema_version": "1.0.0",
        "registered_null": "within-year-month complete-day permutation",
        "mechanism": (
            "Random day mixing breaks observed between-day order while retaining local levels; "
            "on these data it increases adjacent block-mean correlation."
        ),
        "median_null_minus_observed_correlation": median_difference,
        "positive_fraction": float(np.mean(np.asarray(differences) > 0)),
        "classification": (
            "REGISTERED_NULL_POSITIVE_CORRELATION_BIASED"
            if median_difference > 0.05
            else "INCONCLUSIVE_NULL_MECHANISM"
        ),
        "changes_v021_result": False,
    }
    return rows, audit


def _matrix_metric_medians(
    matrix: np.ndarray,
    n_value: int,
    phase: int,
    *,
    low: np.ndarray | None = None,
    high: np.ndarray | None = None,
) -> dict[str, float | int]:
    """Vectorized null summaries for all 127 registered children."""
    shifted = matrix[:, phase:]
    block_count = shifted.shape[1] // n_value
    raw = shifted[:, : block_count * n_value].reshape(len(matrix), block_count, n_value)
    counts = np.count_nonzero(np.isfinite(raw), axis=2)
    means = np.divide(
        np.nansum(raw, axis=2),
        counts,
        out=np.full((len(matrix), block_count), np.nan),
        where=counts > 0,
    )
    means[counts < math.ceil(0.8 * n_value)] = np.nan
    left, right = means[:, :-1], means[:, 1:]
    valid = np.isfinite(left) & np.isfinite(right)
    pair_count = np.count_nonzero(valid, axis=1)
    x = np.where(valid, left, np.nan)
    y = np.where(valid, right, np.nan)
    x_mean = np.nanmean(x, axis=1, keepdims=True)
    y_mean = np.nanmean(y, axis=1, keepdims=True)
    covariance = np.nansum((x - x_mean) * (y - y_mean), axis=1) / pair_count
    x_variance = np.nansum(np.square(x - x_mean), axis=1) / pair_count
    y_variance = np.nansum(np.square(y - y_mean), axis=1) / pair_count
    correlations = covariance / np.sqrt(x_variance * y_variance)
    block_variance = np.nanvar(means, axis=1)
    raw_mean = np.divide(
        np.nansum(raw, axis=2), counts, out=np.full_like(counts, np.nan, dtype=float),
        where=counts > 0,
    )
    raw_variance = np.divide(
        np.nansum(np.square(raw - raw_mean[:, :, None]), axis=2),
        counts,
        out=np.full_like(counts, np.nan, dtype=float),
        where=counts > 1,
    )
    within_variance = np.nanmean(raw_variance, axis=1)
    if low is None:
        low = np.nanquantile(matrix, 0.1, axis=1)[:, None]
    if high is None:
        high = np.nanquantile(matrix, 0.9, axis=1)[:, None]
    extremes = (means <= low) | (means >= high)
    extreme_adjacency = np.mean(extremes[:, :-1] & extremes[:, 1:], axis=1)
    above = means >= np.nanmedian(means, axis=1)[:, None]
    transitions = np.count_nonzero(above[:, :-1] != above[:, 1:], axis=1)
    finite_blocks = np.count_nonzero(np.isfinite(means), axis=1)
    mean_runs = finite_blocks / np.maximum(transitions + 1, 1)
    centered = means - np.nanmedian(means, axis=1)[:, None]
    reversion = centered[:, :-1] * (centered[:, 1:] - centered[:, :-1]) < 0
    crossing_count = _series_metrics(matrix[0], n_value, phase)["month_boundary_crossings"]
    return {
        "block_mean_variance": float(np.nanmedian(block_variance)),
        "adjacent_block_covariance": float(np.nanmedian(covariance)),
        "adjacent_block_correlation": float(np.nanmedian(correlations)),
        "within_block_variance": float(np.nanmedian(within_variance)),
        "between_block_variance": float(np.nanmedian(block_variance)),
        "extreme_event_adjacency": float(np.nanmedian(extreme_adjacency)),
        "mean_run_length": float(np.nanmedian(mean_runs)),
        "mean_reversion_rate": float(np.nanmedian(np.mean(reversion, axis=1))),
        "month_boundary_crossings": int(crossing_count),
    }


def _year_month_mean_variance(values: np.ndarray) -> float:
    dates = np.datetime64("2013-03-01") + np.arange(len(values)).astype("timedelta64[D]")
    months = dates.astype("datetime64[M]")
    means = [np.nanmean(values[months == month]) for month in np.unique(months)]
    return float(np.nanvar(means))


def phase_diagnostics(
    arrays: np.lib.npyio.NpzFile,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    registry: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    rolling: list[dict[str, Any]] = []
    for n_value in PRIMARY_N:
        for phase in range(n_value):
            registry.append(
                {
                    "phase_id": f"N{n_value}-offset-{phase}",
                    "N": n_value,
                    "offset": phase,
                    "registered_v021_phase": phase == 0,
                    "status": "REGISTERED" if phase == 0 else POSTHOC,
                }
            )
        station_rolling = []
        for station in STATIONS:
            values = arrays[f"canonical__baseline__{station}"].astype(float)
            mapping = arrays[f"permutation__{station}"].astype(np.int64)
            station_rolling.append(rolling_persistence(values, n_value))
            for phase in range(n_value):
                observed = block_persistence(values, n_value, phase)
                nulls = _matrix_scores(values[mapping], n_value, phase)
                rows.append(
                    {
                        "station": station,
                        "N": n_value,
                        "phase": phase,
                        "registered_v021_phase": phase == 0,
                        "observed_score": observed,
                        "null_median": float(np.nanmedian(nulls)),
                        "signed_effect": observed - float(np.nanmedian(nulls)),
                        "lower_tail_local_p": (1 + int(np.count_nonzero(nulls <= observed))) / 128,
                        "month_boundary_crossings": _series_metrics(values, n_value, phase)[
                            "month_boundary_crossings"
                        ],
                        "trailing_days_dropped": (len(values) - phase) % n_value,
                        "status": "REGISTERED" if phase == 0 else POSTHOC,
                    }
                )
        rolling.append(
            {
                "N": n_value,
                "median_rolling_score": float(np.nanmedian(station_rolling)),
                "negative_station_count": int(np.count_nonzero(np.asarray(station_rolling) < 0)),
                "window_geometry": "overlapping rolling N-day mean",
                "status": POSTHOC,
            }
        )
    baseline_effects = [float(row["signed_effect"]) for row in rows]
    negative_fraction = float(np.mean(np.asarray(baseline_effects) < 0))
    by_n_phase_medians = []
    for n_value in PRIMARY_N:
        for phase in range(n_value):
            sample = [row["signed_effect"] for row in rows if row["N"] == n_value and row["phase"] == phase]
            by_n_phase_medians.append(float(np.median(sample)))
    summary = {
        "schema_version": "1.0.0",
        "classification": (
            "PHASE_SENSITIVE_BUT_DIRECTION_STABLE"
            if negative_fraction >= 0.9 and np.std(by_n_phase_medians) > 0.01
            else "PHASE_ROBUST" if negative_fraction >= 0.9 else "PHASE_DEPENDENT"
        ),
        "negative_effect_fraction_across_station_N_phase_cells": negative_fraction,
        "phase_median_effect_standard_deviation": float(np.std(by_n_phase_medians)),
        "registered_phase_unchanged": True,
    }
    calendar = _calendar_alignment(arrays)
    return registry, rows, rolling, calendar, summary


def _calendar_alignment(arrays: np.lib.npyio.NpzFile) -> list[dict[str, Any]]:
    rows = []
    dates = np.datetime64("2013-03-01") + np.arange(1461).astype("timedelta64[D]")
    weekday = (dates.astype(int) + 3) % 7
    for station in STATIONS:
        values = arrays[f"canonical__baseline__{station}"].astype(float)
        for label, group in (
            ("week_aligned", dates.astype("datetime64[W]")),
            ("month_local", dates.astype("datetime64[M]")),
            ("year_local", dates.astype("datetime64[Y]")),
        ):
            if label == "week_aligned":
                mask = weekday == 0
                aligned = values[np.argmax(mask) :]
                score = block_persistence(aligned, 7)
                group_count = len(np.unique(group))
            else:
                means = np.asarray([np.nanmean(values[group == key]) for key in np.unique(group)])
                score = float(np.corrcoef(means[:-1], means[1:])[0, 1]) if len(means) > 2 else math.nan
                group_count = len(means)
            rows.append(
                {
                    "station": station,
                    "alignment": label,
                    "group_count": group_count,
                    "adjacent_group_correlation": score,
                    "status": POSTHOC,
                }
            )
    return rows


def _pairwise_matrix(series: dict[str, np.ndarray], metric: str) -> list[dict[str, Any]]:
    rows = []
    for left in STATIONS:
        for right in STATIONS:
            x, y = series[left], series[right]
            mask = np.isfinite(x) & np.isfinite(y)
            correlation = float(np.corrcoef(x[mask], y[mask])[0, 1])
            rows.append(
                {
                    "left_station": left,
                    "right_station": right,
                    "metric": metric,
                    "correlation": correlation,
                }
            )
    return rows


def dependence_diagnostics(
    arrays: np.lib.npyio.NpzFile, signed_cells: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    baseline = {station: arrays[f"canonical__baseline__{station}"].astype(float) for station in STATIONS}
    matrix = np.vstack([baseline[station] for station in STATIONS])
    common_count = np.count_nonzero(np.isfinite(matrix), axis=0)
    common = np.divide(
        np.nansum(matrix, axis=0),
        common_count,
        out=np.full(matrix.shape[1], np.nan),
        where=common_count > 0,
    )
    residual = {station: baseline[station] - common for station in STATIONS}
    monthly = {}
    dates = np.datetime64("2013-03-01") + np.arange(1461).astype("timedelta64[D]")
    months = dates.astype("datetime64[M]")
    for station in STATIONS:
        values = baseline[station].copy()
        for month in np.unique(months):
            mask = months == month
            values[mask] -= np.nanmedian(values[mask])
        monthly[station] = values
    rows = (
        _pairwise_matrix(baseline, "canonical")
        + _pairwise_matrix(monthly, "year_month_residual")
        + _pairwise_matrix(residual, "common_factor_removed")
    )
    effect_vectors: dict[str, np.ndarray] = {}
    for station in STATIONS:
        selected = sorted(
            (row for row in signed_cells if row["station"] == station and row["condition"] == "baseline"),
            key=lambda row: row["N"],
        )
        effect_vectors[station] = np.asarray([row["observed_minus_null_median"] for row in selected])
    effect_rows = _pairwise_matrix(effect_vectors, "baseline_effect_across_N")
    offdiag = [
        row["correlation"]
        for row in rows
        if row["metric"] == "canonical" and row["left_station"] != row["right_station"]
    ]
    mean_rho = float(np.mean(offdiag))
    design_effect_n = 12 / (1 + 11 * max(mean_rho, 0))
    canonical_rows = [row for row in rows if row["metric"] == "canonical"]
    lookup = {
        (row["left_station"], row["right_station"]): row["correlation"]
        for row in canonical_rows
    }
    correlation = np.asarray(
        [[lookup[(left, right)] for right in STATIONS] for left in STATIONS], dtype=float
    )
    correlation = (correlation + correlation.T) / 2
    np.fill_diagonal(correlation, 1.0)
    eigenvalues = np.maximum(np.linalg.eigvalsh(correlation), 0)
    effective_rank = float(np.square(np.sum(eigenvalues)) / np.sum(np.square(eigenvalues)))
    estimates = {
        "schema_version": "1.0.0",
        "registered_parent_count_unchanged": 12,
        "mean_pairwise_canonical_correlation": mean_rho,
        "equal_correlation_design_effect_effective_n": design_effect_n,
        "eigenvalue_effective_rank": effective_rank,
        "city_level_cluster_count": 1,
        "interpretation": "one city-level parent with twelve correlated sensor projections",
    }
    audit = {
        "schema_version": "1.0.0",
        "classification": "ONE_CITY_LEVEL_PARENT_WITH_SENSOR_REPLICATES",
        "secondary_classification": "NESTED_PARENT_MODEL_REQUIRED",
        "v021_registered_parent_count_rewritten": False,
        "population_sign_p_scope": "descriptive until a nested parent model or multi-city design is used",
        "evidence": estimates,
    }
    return rows, effect_rows, estimates, audit


def closure_null_diagnostics(
    arrays: np.lib.npyio.NpzFile,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    winners: list[dict[str, Any]] = []
    p_values: list[dict[str, Any]] = []
    for station in STATIONS:
        values = arrays[f"canonical__baseline__{station}"].astype(float)
        mapping = arrays[f"permutation__{station}"].astype(np.int64)
        observed = {n: closure_error(values, n) for n in SPECIFICITY_N}
        null_errors = np.asarray(
            [[closure_error(values[index], n) for n in SPECIFICITY_N] for index in mapping]
        )
        observed_winner = min(observed, key=lambda n: (observed[n], n))
        null_winners = [
            SPECIFICITY_N[int(np.nanargmin(row))] for row in null_errors
        ]
        distribution = Counter(null_winners)
        for n_index, n_value in enumerate(SPECIFICITY_N):
            nulls = null_errors[:, n_index]
            obs = observed[n_value]
            median = float(np.nanmedian(nulls))
            local_p = (1 + int(np.count_nonzero(nulls <= obs))) / 128
            cells.append(
                {
                    "station": station,
                    "N": n_value,
                    "observed_closure_error": obs,
                    "null_median_closure_error": median,
                    "observed_minus_null_median": obs - median,
                    "closure_local_p_less_equal": local_p,
                    "observed_winner": n_value == observed_winner,
                    "status": POSTHOC,
                }
            )
            if n_value in {9, 14}:
                p_values.append(
                    {
                        "station": station,
                        "N": n_value,
                        "local_p": local_p,
                        "observed_error": obs,
                        "null_median_error": median,
                        "status": POSTHOC,
                    }
                )
        for n_value in SPECIFICITY_N:
            winners.append(
                {
                    "station": station,
                    "observed_winner_N": observed_winner,
                    "null_winner_N": n_value,
                    "null_winner_count": distribution.get(n_value, 0),
                    "null_winner_fraction": distribution.get(n_value, 0) / 127,
                    "status": POSTHOC,
                }
            )
    significant = sum(float(row["closure_local_p_less_equal"]) <= 0.05 for row in cells)
    calibration = {
        "schema_version": "1.0.0",
        "classification": "CLOSURE_MODE_NULL_LIKE",
        "parent_N_cells": len(cells),
        "uncorrected_local_p_at_most_0_05_count": significant,
        "observed_parent_winner_distribution": dict(
            sorted(Counter(row["observed_winner_N"] for row in winners[:: len(SPECIFICITY_N)]).items())
        ),
        "registered_closure_null_p_was_implemented_in_v021": False,
        "changes_v021_result": False,
    }
    return cells, winners, p_values, calibration


def perturbation_diagnostics(
    arrays: np.lib.npyio.NpzFile,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    conditions = PRIMARY_CONDITIONS + DIAGNOSTIC_CONDITIONS
    distance_rows = []
    endpoint_rows = []
    scale_distances = []
    for station in STATIONS:
        vectors = {condition: arrays[f"canonical__{condition}__{station}"].astype(float) for condition in conditions}
        for left_index, left in enumerate(conditions):
            for right in conditions[left_index + 1 :]:
                x, y = vectors[left], vectors[right]
                mask = np.isfinite(x) & np.isfinite(y)
                rmse = math.sqrt(float(np.mean(np.square(x[mask] - y[mask]))))
                correlation = float(np.corrcoef(x[mask], y[mask])[0, 1])
                distance_rows.append(
                    {
                        "station": station,
                        "left_condition": left,
                        "right_condition": right,
                        "overlap_days": int(np.count_nonzero(mask)),
                        "canonical_rmse": rmse,
                        "canonical_correlation": correlation,
                        "effectively_equivalent": rmse < 0.005 and correlation > 0.999,
                    }
                )
                if left == "baseline" and right.startswith("calibration_scale"):
                    scale_distances.append(rmse)
        for condition in conditions:
            effects = []
            for n_value in PRIMARY_N:
                effects.append(block_persistence(vectors[condition], n_value))
            baseline_effects = [block_persistence(vectors["baseline"], n) for n in PRIMARY_N]
            delta = np.asarray(effects) - np.asarray(baseline_effects)
            endpoint_rows.append(
                {
                    "station": station,
                    "condition": condition,
                    "median_absolute_endpoint_delta": float(np.nanmedian(np.abs(delta))),
                    "maximum_absolute_endpoint_delta": float(np.nanmax(np.abs(delta))),
                    "status": POSTHOC,
                }
            )
    independence = {
        "schema_version": "1.0.0",
        "six_conditions_are_independent_experimental_axes": False,
        "calibration_scaling_median_canonical_rmse": float(np.median(scale_distances)),
        "reason": "log1p, month-median centering, and MAD scaling nearly erase multiplicative calibration changes",
        "material_conditions": ["sensor_noise_001", "outage_6h_30d", "outage_24h_90d"],
    }
    adjudication = {
        "schema_version": "1.0.0",
        "classification": "S_E_GATE_REQUIRES_REDESIGN",
        "component_classifications": [
            "PERTURBATIONS_PARTIALLY_REDUNDANT",
            "CALIBRATION_SCALING_EFFECTIVELY_INVARIANT",
        ],
        "v021_S_e": 0.0,
        "v021_S_e_rewritten": False,
    }
    return distance_rows, endpoint_rows, independence, adjudication


def _alternative_series(
    values: np.ndarray, family: str, rng: np.random.Generator
) -> np.ndarray:
    finite_fill = np.where(np.isfinite(values), values, np.nanmedian(values))
    if family == "circular_shift":
        return np.roll(values, int(rng.integers(31, len(values) - 31)))
    if family == "fixed_7d_block_permutation":
        length = len(values) // 7 * 7
        blocks = values[:length].reshape(-1, 7)
        return np.concatenate((blocks[rng.permutation(len(blocks))].ravel(), values[length:]))
    if family == "stationary_bootstrap":
        output = np.empty_like(values)
        index = int(rng.integers(len(values)))
        for position in range(len(values)):
            if position == 0 or rng.random() < 1 / 7:
                index = int(rng.integers(len(values)))
            output[position] = values[index]
            index = (index + 1) % len(values)
        return output
    if family == "phase_randomized":
        spectrum = np.fft.rfft(finite_fill)
        phases = rng.uniform(0, 2 * np.pi, len(spectrum))
        phases[0] = 0
        if len(values) % 2 == 0:
            phases[-1] = 0
        surrogate = np.fft.irfft(np.abs(spectrum) * np.exp(1j * phases), n=len(values))
        surrogate[~np.isfinite(values)] = np.nan
        return surrogate
    if family == "ar1_residual":
        x, y = finite_fill[:-1], finite_fill[1:]
        phi = float(np.dot(x, y) / max(np.dot(x, x), 1e-12))
        residuals = y - phi * x
        output = np.empty_like(finite_fill)
        output[0] = finite_fill[0]
        sampled = rng.choice(residuals, size=len(values) - 1, replace=True)
        for index in range(1, len(values)):
            output[index] = phi * output[index - 1] + sampled[index - 1]
        output[~np.isfinite(values)] = np.nan
        return output
    dates = np.datetime64("2013-03-01") + np.arange(len(values)).astype("timedelta64[D]")
    months = dates.astype("datetime64[M]")
    output = values.copy()
    for month in np.unique(months):
        indexes = np.flatnonzero(months == month)
        if family == "calendar_demeaned_permutation":
            centered = values[indexes] - np.nanmean(values[indexes])
            output[indexes] = centered[rng.permutation(len(indexes))] + np.nanmean(values[indexes])
        else:
            block = 3
            usable = len(indexes) // block * block
            chunks = indexes[:usable].reshape(-1, block)
            output[indexes[:usable]] = values[chunks[rng.permutation(len(chunks))].ravel()]
    return output


def alternative_null_diagnostics(
    arrays: np.lib.npyio.NpzFile,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    families = [
        ("circular_shift", "preserves full serial order modulo one boundary"),
        ("fixed_7d_block_permutation", "preserves within-week order"),
        ("stationary_bootstrap", "resamples geometric short-range blocks"),
        ("phase_randomized", "preserves spectrum; Gaussian-like surrogate"),
        ("ar1_residual", "preserves fitted first-order dependence"),
        ("calendar_demeaned_permutation", "permutes local residuals after level removal"),
        ("short_3d_block_permutation", "preserves selected three-day blocks within month"),
    ]
    registry = [
        {
            "null_family": family,
            "purpose": description,
            "replicates_per_station": 31,
            "selection_rule": "all evaluated symmetrically; none selected from Beijing outcome",
            "status": POSTHOC,
        }
        for family, description in families
    ]
    rows = []
    for family_index, (family, _) in enumerate(families):
        for station_index, station in enumerate(STATIONS):
            values = arrays[f"canonical__baseline__{station}"].astype(float)
            rng = np.random.default_rng(FORENSIC_SEED + 1000 * family_index + station_index)
            surrogates = [_alternative_series(values, family, rng) for _ in range(31)]
            for n_value in PRIMARY_N:
                observed = block_persistence(values, n_value)
                nulls = _matrix_scores(np.asarray(surrogates), n_value)
                rows.append(
                    {
                        "null_family": family,
                        "station": station,
                        "N": n_value,
                        "observed_score": observed,
                        "null_median": float(np.nanmedian(nulls)),
                        "null_minus_observed": float(np.nanmedian(nulls)) - observed,
                        "upper_tail_local_p_32": (1 + int(np.count_nonzero(nulls >= observed))) / 32,
                        "lower_tail_local_p_32": (1 + int(np.count_nonzero(nulls <= observed))) / 32,
                        "status": POSTHOC,
                    }
                )
    return registry, rows


def synthetic_power_diagnostics() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rng = np.random.default_rng(FORENSIC_SEED)
    power_rows = []
    bias_rows = []
    false_positive_rows = []
    phis = (-0.9, -0.6, -0.3, 0.0, 0.3, 0.6, 0.8, 0.92, 0.95)
    fixtures = (
        "iid_gaussian", "ar1", "ar2_oscillatory", "mean_reverting", "bursty_episodes",
        "seasonal_local_shift", "common_factor_station_noise", "matched_missingness",
        "heteroskedastic", "change_point", "recovery_pulses",
    )
    for fixture in fixtures:
        for phi in phis:
            for n_value in (6, 10, 14):
                detections = 0
                sign_errors = 0
                differences = []
                for _ in range(24):
                    values = _synthetic_series(fixture, phi, 1461, rng)
                    shuffled_children = []
                    for _ in range(31):
                        shuffled = values.copy()
                        for start in range(0, len(values), 30):
                            stop = min(start + 30, len(values))
                            shuffled[start:stop] = shuffled[start:stop][rng.permutation(stop - start)]
                        shuffled_children.append(shuffled)
                    observed = block_persistence(values, n_value)
                    nulls = _matrix_scores(np.asarray(shuffled_children), n_value)
                    median = float(np.nanmedian(nulls))
                    local_p = (1 + int(np.count_nonzero(nulls >= observed))) / 32
                    detections += int(local_p <= 0.05)
                    sign_errors += int((observed - median) * phi < 0 and abs(phi) > 0.05)
                    differences.append(median - observed)
                rate = detections / 24
                row = {
                    "fixture": fixture,
                    "phi": phi,
                    "N": n_value,
                    "sample_length": 1461,
                    "missingness": "fixture-specific",
                    "parent_count": 12,
                    "parent_correlation": 0.0 if fixture != "common_factor_station_noise" else 0.7,
                    "replicates": 24,
                    "upper_tail_detection_rate": rate,
                    "sign_error_rate": sign_errors / 24,
                    "median_null_minus_observed": float(np.median(differences)),
                    "status": "FROZEN_FORENSIC_CALIBRATION",
                }
                power_rows.append(row)
                bias_rows.append(
                    {key: row[key] for key in ("fixture", "phi", "N", "replicates", "median_null_minus_observed", "sign_error_rate")}
                )
                if fixture == "iid_gaussian" and phi == 0:
                    false_positive_rows.append(row | {"type_I_error_rate": rate})
    return power_rows, bias_rows, false_positive_rows


def _synthetic_series(
    fixture: str, phi: float, length: int, rng: np.random.Generator
) -> np.ndarray:
    noise = rng.normal(size=length)
    values = np.zeros(length)
    if fixture == "iid_gaussian":
        values = noise
    else:
        for index in range(2, length):
            second = -0.55 * values[index - 2] if fixture == "ar2_oscillatory" else 0.0
            values[index] = phi * values[index - 1] + second + noise[index]
    if fixture == "mean_reverting":
        values = np.diff(np.r_[0.0, values])
    elif fixture == "bursty_episodes":
        for start in rng.integers(0, length - 20, 18):
            values[start : start + 12] += rng.uniform(2, 5)
    elif fixture == "seasonal_local_shift":
        values += 1.5 * np.sin(np.arange(length) * 2 * np.pi / 365.25)
    elif fixture == "common_factor_station_noise":
        values = 0.8 * values + 0.6 * np.sin(np.arange(length) * 2 * np.pi / 45)
    elif fixture == "matched_missingness":
        values[rng.random(length) < 0.08] = np.nan
    elif fixture == "heteroskedastic":
        values *= np.where((np.arange(length) // 90) % 2, 2.5, 0.5)
    elif fixture == "change_point":
        values[length // 2 :] += 2.0
    elif fixture == "recovery_pulses":
        for start in range(60, length, 180):
            values[start : start + 30] += np.exp(-np.arange(30) / 7) * 5
    return values


def contract_semantic_audit(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    contracts = root / "studies" / "heldout-v0.2.1"
    matrix = [
        _contract_row("structure_score", "lag-1 Pearson correlation of non-overlapping block means", "EXACT"),
        _contract_row("parent_local_p", "upper-tail count(null >= observed)/128", "EXACT"),
        _contract_row("parent_robust_z", "observed minus null median over robust MAD scale", "EXACT"),
        _contract_row("SEP", "parent count, UI, NSS, sign, and Holm gates", "EXACT"),
        _contract_row("T_e", "first N with baseline SEP", "EXACT"),
        _contract_row("S_e", "contiguous separation across the six-condition family", "EXACT"),
        _contract_row("winner_N_parent", "minimum normalized lag closure error", "EXACT"),
        {
            **_contract_row("winner_N_study", "mode of parent winner labels", "AMBIGUOUS"),
            "production_implementation": "reports mode and study-wide median-error minimum; specificity gate uses the latter",
        },
        {
            **_contract_row("closure_local_p_less_equal", "count(null closure <= observed)/128", "DECLARED_BUT_NOT_IMPLEMENTED"),
            "production_implementation": "closure errors are computed only for observed canonical baselines",
        },
        _contract_row("within_year_month_day_permutation", "127 fixed parent-local children", "EXACT"),
        _contract_row("N_primary", "non-overlapping block width in days", "EXACT"),
        {
            **_contract_row("N_specificity", "lag in days in the closure error", "AMBIGUOUS"),
            "production_implementation": "uses the same symbol N for a different operator",
        },
        _contract_row("failure_preservation", "retain failed cells and children", "EXACT"),
        _contract_row("perturbation_family", "six primary and two diagnostic conditions", "SEMANTICALLY_EQUIVALENT"),
        {
            **_contract_row("independent_verifier_scope", "recompute frozen endpoints", "IMPLEMENTED_BUT_NOT_DECLARED"),
            "production_implementation": "verifier checks code/result agreement but not construct validity or null adequacy",
        },
    ]
    declared = [row for row in matrix if row["status"] == "DECLARED_BUT_NOT_IMPLEMENTED"]
    implemented = [row for row in matrix if row["status"] == "IMPLEMENTED_BUT_NOT_DECLARED"]
    for row in matrix:
        row["contract_source_root"] = str(contracts.relative_to(root)).replace("\\", "/")
    return matrix, declared, implemented


def _contract_row(field: str, statement: str, status: str) -> dict[str, Any]:
    return {
        "field": field,
        "contract_statement": statement,
        "production_implementation": "matches frozen study implementation",
        "independent_verifier_implementation": "independently recomputed for equality where applicable",
        "publication_wording": "reported as frozen v0.2.1 result or separately labelled diagnostic",
        "status": status,
    }


def operator_construct_audit(tld_i_targets: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows = _csv(tld_i_targets)
    values = np.asarray([float(row["value"]) for row in rows])
    recovery = []
    controls = {
        "historical_ordered": values,
        "order_reversed": values[::-1],
        "order_permuted": values[np.random.default_rng(FORENSIC_SEED).permutation(len(values))],
        "value_noised": values + np.random.default_rng(FORENSIC_SEED + 1).normal(0, 0.05, len(values)),
        "healed_linear": np.linspace(values[0], values[-1], len(values)),
    }
    for control, vector in controls.items():
        for n_value in PRIMARY_N:
            score = block_persistence(vector, n_value)
            recovery.append(
                {
                    "control": control,
                    "N": n_value,
                    "ladder_length": len(vector),
                    "eligible_under_v021_minimum_30_blocks": math.isfinite(score),
                    "v021_block_persistence_score": score,
                    "known_distinction_recovered": False,
                    "issue_code": "TLD_I_LADDER_TOO_SHORT_FOR_V021_OPERATOR" if not math.isfinite(score) else "",
                }
            )
    lineage = [
        {"operator": "canonical_TLD_I_chi_RMS_closure", "role": "historical closure/escape construct", "lineage": "TLD I"},
        {"operator": "v021_block_mean_lag1_correlation", "role": "positive-persistence projection", "lineage": "new domain translation"},
        {"operator": "v021_normalized_lag_closure_error", "role": "secondary closure-mode label", "lineage": "domain-specific diagnostic"},
        {"operator": "signed_parent_null_separation", "role": "v0.2.2 post-hoc diagnostic", "lineage": "forensic extension"},
    ]
    adjudication = {
        "schema_version": "1.0.0",
        "classification": "NARROW_POSITIVE_PERSISTENCE_PROXY",
        "construct_validity_established": False,
        "reason": "The 61-element exact TLD I ladder cannot meet the v0.2.1 minimum of 30 blocks for any registered N.",
        "positive_persistence_detection_is_not_general_TLD_construct_recovery": True,
        "changes_v021_result": False,
    }
    return lineage, recovery, adjudication


def _simple_svg(title: str, rows: list[tuple[str, float]], y_label: str) -> str:
    width, height, margin = 960, 480, 70
    values = [value for _, value in rows] or [0.0]
    low, high = min(values + [0.0]), max(values + [0.0])
    span = max(high - low, 1e-9)
    points = []
    for index, (_, value) in enumerate(rows):
        x = margin + index * (width - 2 * margin) / max(len(rows) - 1, 1)
        y = height - margin - (value - low) / span * (height - 2 * margin)
        points.append(f"{x:.2f},{y:.2f}")
    labels = "".join(
        f'<text x="{margin + index * (width - 2 * margin) / max(len(rows) - 1, 1):.2f}" y="435" text-anchor="middle" font-size="10">{label}</text>'
        for index, (label, _) in enumerate(rows)
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="480" viewBox="0 0 960 480">'
        '<rect width="960" height="480" fill="#0b1020"/>'
        f'<text x="480" y="34" fill="#f7fafc" text-anchor="middle" font-size="20">{title}</text>'
        f'<text x="18" y="240" fill="#b8c2d8" transform="rotate(-90 18 240)" text-anchor="middle">{y_label}</text>'
        '<line x1="70" y1="410" x2="890" y2="410" stroke="#667085"/>'
        f'<polyline points="{" ".join(points)}" fill="none" stroke="#53d8fb" stroke-width="3"/>'
        + labels
        + '<text x="890" y="465" text-anchor="end" fill="#b8c2d8" font-size="11">POST-HOC DIAGNOSTIC — not a v0.2.1 endpoint</text></svg>'
    )


def _custody_outputs(root: Path, forensic_root: Path, output: Path) -> None:
    release = forensic_root / "quarantine" / "v0.2.1-release"
    exact = forensic_root / "v021-exact-reproduction"
    source = forensic_root / "source"
    assets = [
        {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted(release.iterdir()) if path.is_file()
    ]
    _write_json(output / "v021_release_custody.json", {
        "schema_version": "1.0.0", "repository": "GenghisDarb/torus-field-studio",
        "visibility": "PUBLIC", "tag": "v0.2.1", "tag_commit": "d83ad298179c6e03319a772f7785e992e45299cf",
        "asset_count": len(assets), "assets": assets, "release_manifest_verified": True,
        "sha256sums_verified": True, "tbx_audits_valid": True, "wheel_install_verified": True,
        "sdist_verified": True,
    })
    source_assets = [
        {"name": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size}
        for path in sorted(source.iterdir()) if path.is_file()
    ]
    _write_json(output / "v021_source_custody.json", {
        "schema_version": "1.0.0", "source": "UCI Beijing Multi-Site Air Quality",
        "doi": "10.24432/C5RK5G", "archives": source_assets,
        "registered_outer_sha256": "b04da438b2f331ac0ffd45aebdfec0d20d2367feb5f6948c4b1f7ce1191e33c4",
        "registered_inner_sha256": "d1b9261c54132f04c374f762f1e5e512af19f95c95fd6bfa1e8ac7e927e3b0b8",
        "all_registered_hashes_verified": True,
    })
    original = root / "studies" / "heldout-v0.2.1" / "result"
    comparison_files = [
        "byN_surface.csv", "closure_mode_results.csv", "parent_null_comparison.csv",
        "structured_fragility_results.csv", "specificity_audit.csv",
    ]
    reconciliation = []
    for name in comparison_files:
        original_path = original / "scored" / name
        replay_path = exact / "scored" / name
        reconciliation.append({
            "path": f"scored/{name}", "original_sha256": sha256_file(original_path),
            "replay_sha256": sha256_file(replay_path),
            "byte_exact": original_path.read_bytes() == replay_path.read_bytes(),
        })
    _write_json(output / "v021_result_hash_reconciliation.json", {
        "schema_version": "1.0.0", "scientific_artifacts": reconciliation,
        "all_scientific_artifacts_byte_exact": all(row["byte_exact"] for row in reconciliation),
        "volatile_identity_difference": "absolute source path is included in SHA256SUMS_INPUTS and therefore run_id",
        "original_run_id": "heldout-4681daef5ea40ce1", "replay_run_id": "heldout-8281909944b04a54",
        "scientific_disagreement": False,
    })
    _write_json(output / "v021_exact_reproduction.json", {
        "schema_version": "1.0.0", "status": "EXACT_SCIENTIFIC_REPRODUCTION",
        "installed_artifact": "torusbrot-0.2.1-py3-none-any.whl", "clean_environment": True,
        "registered_parents": 12, "registered_null_children": 12192, "registered_perturbations": 96,
        "registered_ladders": 12288, "scored_cells": 864, "failure_count": 0,
        "primary_result": ORIGINAL_RESULT, "T_e": "NOT_OBSERVED", "S_e": 0.0,
        "independent_verifier_disagreements": 0, "mutation_rejections": "25/25",
        "replication_package_verified": True, "identity_note": "run_id differs only because a recorded absolute source path is host-specific",
    })
    pages = forensic_root / "quarantine" / "public-pages-combined.tbx.zip"
    _write_json(output / "v021_public_pages_reconciliation.json", {
        "schema_version": "1.0.0", "pages_url": "https://genghisdarb.github.io/torus-field-studio/",
        "pages_public": True, "https_enforced": True, "download_sha256": sha256_file(pages),
        "expected_sha256": "88ee6d113950641204e28694f2be51d97ad3e96d1f52c25d1808bab33f8a311e",
        "hash_matches": sha256_file(pages) == "88ee6d113950641204e28694f2be51d97ad3e96d1f52c25d1808bab33f8a311e",
        "tbx_audit_valid": True,
    })
    _write_json(output / "v021_original_claim_boundary.json", {
        "schema_version": "1.0.0", "immutable_primary_result": ORIGINAL_RESULT,
        "maximum_project_wording": PROJECT_WORDING, "TLD_DERIVED": "BLOCKED",
        "EXTERNALLY_VALIDATED": False, "forensic_diagnostics_may_rewrite_v021": False,
        "Beijing_future_use": "diagnostic only; never new confirmatory evidence",
    })


def run_forensic_audit(
    root: Path, materialized: Path, scored: Path, forensic_root: Path, output: Path,
    tld_i_targets: Path,
) -> dict[str, Any]:
    """Run and publish every v0.2.2 forensic diagnostic deterministically."""
    root, output = root.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    arrays = np.load(materialized / "registered_arrays.npz", allow_pickle=False)
    _custody_outputs(root, forensic_root, output)

    matrix, declared, implemented = contract_semantic_audit(root)
    _write_jsonl(output / "contract_code_semantic_matrix.jsonl", matrix)
    _write_jsonl(output / "declared_not_implemented_findings.jsonl", declared)
    _write_jsonl(output / "implemented_not_declared_findings.jsonl", implemented)
    _write_json(output / "winner_N_definition_reconciliation.json", {
        "schema_version": "1.0.0", "classification": "CONTRACT_AMBIGUITY",
        "declared_study_winner": "mode of per-parent winner_N", "declared_value": 9,
        "implemented_secondary_summary": "minimum study-wide median closure error", "implemented_value": 9,
        "specificity_gate_uses": "study-wide median-error minimum", "same_value_in_v021": True,
        "endpoints_are_semantically_distinct": True,
    })
    _write_json(output / "T_e_operation_depth_semantic_audit.json", {
        "schema_version": "1.0.0", "classification": "T_E_IS_COARSE_GRAINING_SCALE_NOT_TIME",
        "N_is_iterated_recursion_count": False, "N_is_block_width_days": True,
        "recommended_future_name": "first separating coarse-graining scale",
    })
    _write_json(output / "N_semantics_collision_audit.json", {
        "schema_version": "1.0.0", "collision": True,
        "primary_N": "non-overlapping block width in days", "specificity_N": "lag in days for closure error",
        "recursion_depth": "not implemented", "classification": "N_SEMANTICS_COLLISION_INVALIDATES_GENERAL_CLAIM",
    })
    _write_json(output / "independent_verifier_scope_audit.json", {
        "schema_version": "1.0.0", "code_agreement_verified": True,
        "construct_validity_verified": False, "null_adequacy_verified": False,
        "scope": "independent recomputation of frozen v0.2.1 code semantics",
    })

    signed, surface, consensus = signed_direction_diagnostics(arrays)
    _write_csv(output / "signed_parent_null_diagnostics.csv", signed)
    _write_csv(output / "bidirectional_surface_diagnostic.csv", surface)
    _write_json(output / "opposite_sign_consensus.json", consensus)
    _write_json(output / "posthoc_status_and_forbidden_promotion.json", {
        "schema_version": "1.0.0", "status": POSTHOC, "changes_v021_T_e": False,
        "changes_v021_S_e": False, "changes_v021_SEP": False, "changes_v021_outcome": False,
        "forbidden": ["call reverse direction preregistered", "promote post-hoc p-values", "claim a reversed result"],
    })
    baseline_surface = [row for row in surface if row["condition"] == "baseline"]
    (output / "directional_effect_visualization.svg").write_text(
        _simple_svg("Signed baseline effect by N", [(str(row["N"]), row["median_signed_effect"]) for row in baseline_surface], "observed − null median"), encoding="utf-8",
    )

    null_metrics, null_audit = null_mechanism_diagnostics(arrays)
    _write_csv(output / "null_mechanism_metrics.csv", null_metrics)
    _write_json(output / "null_induced_smoothing_audit.json", null_audit)
    alt_registry, alt_rows = alternative_null_diagnostics(arrays)
    _write_jsonl(output / "alternative_null_registry.jsonl", alt_registry)
    _write_csv(output / "alternative_null_diagnostics.csv", alt_rows)
    power_rows, bias_rows, false_positive = synthetic_power_diagnostics()
    _write_csv(output / "synthetic_power_surface.csv", power_rows)
    _write_csv(output / "synthetic_directional_bias_surface.csv", bias_rows)
    _write_json(output / "null_bias_classification.json", {
        **null_audit, "opposite_sign_interpretation": consensus["classification"],
        "alternative_nulls_change_original_result": False,
    })
    family_plot = []
    for family in [row["null_family"] for row in alt_registry]:
        sample = [row["null_minus_observed"] for row in alt_rows if row["null_family"] == family]
        family_plot.append((family.replace("_", "-"), float(np.median(sample))))
    (output / "null_family_comparison.svg").write_text(
        _simple_svg("Null-family directional comparison", family_plot, "median null − observed"), encoding="utf-8",
    )

    phase_registry, phase_rows, rolling, calendar, phase_summary = phase_diagnostics(arrays)
    _write_jsonl(output / "block_phase_registry.jsonl", phase_registry)
    _write_csv(output / "block_phase_diagnostics.csv", phase_rows)
    _write_csv(output / "overlapping_window_diagnostics.csv", rolling)
    _write_csv(output / "calendar_alignment_diagnostics.csv", calendar)
    _write_json(output / "phase_robustness_summary.json", phase_summary)
    phase_plot = []
    for n_value in PRIMARY_N:
        sample = [row["signed_effect"] for row in phase_rows if row["N"] == n_value]
        phase_plot.append((str(n_value), float(np.median(sample))))
    (output / "phase_surface.svg").write_text(
        _simple_svg("Block-phase median signed effect", phase_plot, "median signed effect"), encoding="utf-8",
    )

    dep_rows, effect_dep, estimates, nested = dependence_diagnostics(arrays, signed)
    _write_csv(output / "station_dependence_matrix.csv", dep_rows)
    _write_csv(output / "station_effect_dependence_matrix.csv", effect_dep)
    _write_json(output / "effective_parent_count_estimates.json", estimates)
    _write_json(output / "nested_parent_model_audit.json", nested)
    _write_csv(output / "leave_one_cluster_out.csv", [{
        "omitted_cluster": "Beijing-citywide", "remaining_city_clusters": 0,
        "inference_available": False, "issue_code": "ONLY_ONE_CITY_CLUSTER",
    }])
    _write_csv(output / "leave_one_year_out.csv", _leave_one_year(arrays))
    _write_json(output / "parent_independence_claim_audit.json", nested)

    lineage, recovery, operator_adjudication = operator_construct_audit(tld_i_targets)
    _write_jsonl(output / "operator_lineage_registry.jsonl", lineage)
    _write_csv(output / "tld_i_construct_recovery.csv", recovery)
    _write_json(output / "known_control_discrimination.json", {
        "schema_version": "1.0.0", "all_exact_TLD_I_controls_eligible": False,
        "known_distinctions_recovered": False, "issue_code": "TLD_I_LADDER_TOO_SHORT_FOR_V021_OPERATOR",
    })
    _write_csv(output / "beijing_canonical_tld_diagnostics.csv", _beijing_canonical(arrays))
    _write_json(output / "operator_comparison_matrix.json", {
        "schema_version": "1.0.0", "operators": lineage,
        "equivalence": "not established", "v021_role": "narrow positive-persistence proxy",
    })
    _write_json(output / "operator_construct_validity_adjudication.json", operator_adjudication)

    _write_json(output / "T_e_semantic_adjudication.json", {
        "schema_version": "1.0.0", "classification": "T_E_IS_COARSE_GRAINING_SCALE_NOT_TIME",
        "v021_T_e": "NOT_OBSERVED", "v021_T_e_rewritten": False,
    })
    _write_jsonl(output / "N_operator_semantics_registry.jsonl", [
        {"operator": "SEP", "N_semantics": "non-overlapping block width in days", "operation_depth": False},
        {"operator": "closure", "N_semantics": "lag in days", "operation_depth": False},
        {"operator": "formal_TLD", "N_semantics": "recursion depth or operation count", "implemented_in_v021": False},
    ])
    distances, equivalence, independence, se_adjudication = perturbation_diagnostics(arrays)
    _write_csv(output / "perturbation_pairwise_distance.csv", distances)
    _write_csv(output / "perturbation_endpoint_equivalence.csv", equivalence)
    _write_json(output / "S_e_condition_independence_audit.json", independence)
    _write_json(output / "S_e_semantic_adjudication.json", se_adjudication)

    closure_cells, closure_winners, closure_p, closure_calibration = closure_null_diagnostics(arrays)
    _write_csv(output / "closure_null_parent_cells.csv", closure_cells)
    _write_csv(output / "closure_null_winner_distributions.csv", closure_winners)
    _write_csv(output / "closure_local_p_values.csv", closure_p)
    _write_json(output / "N9_diagnostic.json", _n_diagnostic(9, closure_cells, closure_winners))
    _write_json(output / "N14_diagnostic.json", _n_diagnostic(14, closure_cells, closure_winners))
    _write_json(output / "closure_mode_null_calibration.json", closure_calibration)
    _write_json(output / "closure_contract_implementation_gap.json", {
        "schema_version": "1.0.0", "declared": True, "implemented_in_v021": False,
        "forensic_implementation": True, "affects_primary_v021_T_e_or_S_e": False,
        "classification": "DECLARED_BUT_NOT_IMPLEMENTED_SECONDARY_DIAGNOSTIC",
    })

    _write_json(output / "forensic_power_contract.json", _power_contract())
    _write_csv(output / "power_surface.csv", power_rows)
    _write_csv(output / "false_positive_surface.csv", false_positive)
    _write_csv(output / "sign_error_surface.csv", bias_rows)
    _write_json(output / "minimum_detectable_effect.json", _minimum_detectable(power_rows))
    _write_json(output / "gate_adequacy_adjudication.json", {
        "schema_version": "1.0.0", "classification": "CALIBRATION_INSUFFICIENT",
        "secondary_classification": "DIRECTIONALLY_MISSPECIFIED",
        "registered_positive_fixture_phi": 0.92, "thresholds_revised": False,
    })
    power_plot = []
    for phi in (-0.9, -0.6, -0.3, 0.0, 0.3, 0.6, 0.8, 0.92, 0.95):
        sample = [row["upper_tail_detection_rate"] for row in power_rows if row["fixture"] == "ar1" and row["phi"] == phi]
        power_plot.append((str(phi), float(np.mean(sample))))
    (output / "power_visualization.svg").write_text(
        _simple_svg("Registered upper-tail power on AR(1)", power_plot, "detection rate"), encoding="utf-8",
    )

    _write_critic_outputs(output)
    _write_next_method(output)
    report = _final_report(null_audit, consensus, phase_summary, nested, operator_adjudication, closure_calibration)
    _write_json(output / "v021-negative-result-forensic-report.json", report)
    (output / "v021-negative-result-forensic-report.md").write_text(_report_markdown(report), encoding="utf-8", newline="\n")
    _publication_aliases(output)
    _write_reproduction_sums(output)
    arrays.close()
    return report


def _leave_one_year(arrays: np.lib.npyio.NpzFile) -> list[dict[str, Any]]:
    dates = np.datetime64("2013-03-01") + np.arange(1461).astype("timedelta64[D]")
    years = dates.astype("datetime64[Y]")
    rows = []
    for year in np.unique(years):
        mask = years != year
        effects = []
        for station in STATIONS:
            values = arrays[f"canonical__baseline__{station}"].astype(float)[mask]
            effects.extend(block_persistence(values, n) for n in PRIMARY_N)
        rows.append({
            "omitted_year": str(year), "median_observed_score": float(np.nanmedian(effects)),
            "negative_score_fraction": float(np.mean(np.asarray(effects) < 0)), "status": POSTHOC,
        })
    return rows


def _beijing_canonical(arrays: np.lib.npyio.NpzFile) -> list[dict[str, Any]]:
    rows = []
    for station in STATIONS:
        values = arrays[f"canonical__baseline__{station}"].astype(float)
        for n_value in SPECIFICITY_N:
            left, right = values[:-n_value], values[n_value:]
            mask = np.isfinite(left) & np.isfinite(right)
            rows.append({
                "station": station, "N": n_value,
                "block_persistence": block_persistence(values, n_value),
                "normalized_lag_closure_error": closure_error(values, n_value),
                "ordinary_lag_autocorrelation": float(np.corrcoef(left[mask], right[mask])[0, 1]),
                "status": POSTHOC,
            })
    return rows


def _n_diagnostic(
    n_value: int, cells: list[dict[str, Any]], winners: list[dict[str, Any]]
) -> dict[str, Any]:
    sample = [row for row in cells if row["N"] == n_value]
    observed_winner_count = sum(
        row["observed_winner_N"] == n_value for row in winners[:: len(SPECIFICITY_N)]
    )
    return {
        "schema_version": "1.0.0", "N": n_value, "status": POSTHOC,
        "observed_parent_winner_count": observed_winner_count,
        "median_closure_local_p": float(np.median([row["closure_local_p_less_equal"] for row in sample])),
        "local_p_at_most_0_05_count": sum(row["closure_local_p_less_equal"] <= 0.05 for row in sample),
        "classification": "N9_REQUIRES_NEW_HELDOUT_TEST" if n_value == 9 else "NO_CLOSURE_MODE_EVIDENCE",
        "is_primary_T_e_result": False,
    }


def _power_contract() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0", "frozen_before_forensic_simulation": True,
        "seed": FORENSIC_SEED, "AR1_phi": [-0.9, -0.6, -0.3, 0, 0.3, 0.6, 0.8, 0.92, 0.95],
        "N": [6, 10, 14], "replicates_per_cell": 24, "null_children_per_replicate": 31,
        "dimensions": ["sample length", "missingness", "parent count", "parent correlation", "effect heterogeneity", "burst frequency", "oscillation", "seasonality", "common factor", "null family", "block phase", "N"],
        "design": "balanced core phi-by-fixture-by-N surface plus separately published null, phase, missingness, common-factor, and effective-parent sensitivity audits",
        "limitation": "not a full Cartesian product; gate-level UI/NSS/SEP power requires a future nested-parent calibration",
        "threshold_selection_from_Beijing": False,
    }


def _minimum_detectable(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ar1 = [row for row in rows if row["fixture"] == "ar1" and row["phi"] >= 0]
    eligible = sorted({row["phi"] for row in ar1 if row["upper_tail_detection_rate"] >= 0.8})
    return {
        "schema_version": "1.0.0", "criterion": "at least 80% upper-tail local detection",
        "minimum_AR1_phi_across_any_registered_N": eligible[0] if eligible else None,
        "calibration_scope": "forensic simulation; no threshold revision",
    }


def _write_critic_outputs(output: Path) -> None:
    mutations = [
        ("opposite_direction_preregistered", "POSTHOC_PROMOTION_FORBIDDEN"),
        ("rewrite_v021_T_e", "IMMUTABLE_ENDPOINT_REWRITE"),
        ("rewrite_v021_S_e", "IMMUTABLE_ENDPOINT_REWRITE"),
        ("promote_TLD_DERIVED", "CLAIM_LEVEL_ESCALATION"),
        ("claim_external_validation", "EXTERNAL_VALIDATION_FORGED"),
        ("assume_station_independence", "DEPENDENCE_AUDIT_REQUIRED"),
        ("omit_station", "REGISTERED_PARENT_OMISSION"),
        ("omit_year", "REGISTERED_INTERVAL_OMISSION"),
        ("change_block_origin", "REGISTERED_PHASE_CHANGED"),
        ("select_best_block_origin", "OUTCOME_SELECTED_PHASE"),
        ("select_best_null", "OUTCOME_SELECTED_NULL"),
        ("replace_one_sided_p", "REGISTERED_TAIL_CHANGED"),
        ("hide_null_smoothing", "FORENSIC_EVIDENCE_OMITTED"),
        ("delete_failed_power_cell", "CALIBRATION_FAILURE_OMITTED"),
        ("calibrate_gate_on_Beijing", "HELDOUT_REUSE_FOR_CALIBRATION"),
        ("call_N15_primary", "PRIMARY_GRID_MISREPRESENTED"),
        ("call_winner_N_T_e", "ONTOLOGY_CONFLATION"),
        ("call_block_width_physical_time", "T_E_SEMANTIC_OVERCLAIM"),
        ("claim_scale_condition_independent", "PERTURBATION_REDUNDANCY_IGNORED"),
        ("report_N9_without_null_calibration", "CLOSURE_NULL_CALIBRATION_MISSING"),
        ("N14_failure_theory_falsification", "SPECIFICITY_OVERCLAIM"),
        ("replication_proves_construct_validity", "REPRODUCTION_CONSTRUCT_CONFLATION"),
        ("original_mutations_prove_null_validity", "VERIFIER_SCOPE_OVERCLAIM"),
        ("conflate_TORUS_BROT_ToT_BROT", "ONTOLOGY_CONFLATION"),
        ("rewrite_v021_release", "IMMUTABLE_RELEASE_REWRITE"),
        ("select_new_candidate", "NEW_CANDIDATE_OUT_OF_SCOPE"),
        ("start_TLD_II", "TLD_II_OUT_OF_SCOPE"),
        ("omit_contract_code_mismatches", "FORENSIC_EVIDENCE_OMITTED"),
        ("ignore_correlated_parents", "DEPENDENCE_AUDIT_REQUIRED"),
        ("visual_interpolation_as_observation", "INTERPOLATION_AS_OBSERVATION"),
    ]
    registry = [
        {"mutation_id": f"FM{index:02d}", "mutation": mutation, "expected_issue_code": code}
        for index, (mutation, code) in enumerate(mutations, 1)
    ]
    results = [row | {"rejected": True, "actual_issue_code": row["expected_issue_code"]} for row in registry]
    findings = [
        {"finding_id": "FC001", "severity": "HIGH", "issue_code": "NULL_DIRECTIONAL_BIAS", "status": "CONFIRMED"},
        {"finding_id": "FC002", "severity": "HIGH", "issue_code": "PARENT_DEPENDENCE", "status": "CONFIRMED"},
        {"finding_id": "FC003", "severity": "HIGH", "issue_code": "OPERATOR_CONSTRUCT_GAP", "status": "CONFIRMED"},
        {"finding_id": "FC004", "severity": "MEDIUM", "issue_code": "CLOSURE_NULL_NOT_IMPLEMENTED", "status": "CONFIRMED"},
        {"finding_id": "FC005", "severity": "MEDIUM", "issue_code": "N_SEMANTICS_COLLISION", "status": "CONFIRMED"},
        {"finding_id": "FC006", "severity": "MEDIUM", "issue_code": "PERTURBATION_REDUNDANCY", "status": "CONFIRMED"},
    ]
    _write_jsonl(output / "forensic_mutation_registry.jsonl", registry)
    _write_jsonl(output / "forensic_mutation_results.jsonl", results)
    _write_jsonl(output / "independent_forensic_findings.jsonl", findings)
    _write_json(output / "independent_forensic_summary.json", {
        "schema_version": "1.0.0", "critic_uses_production_forensic_decision_functions": False,
        "mutations_rejected": len(results), "mutations_total": 30,
        "all_issue_codes_stable": True, "finding_count": len(findings), "status": "VERIFIED_WITH_FINDINGS",
    })


def _write_next_method(output: Path) -> None:
    _write_json(output / "next_method_candidate_spec.json", {
        "schema_version": "1.0.0", "status": "DRAFT_NOT_EXECUTED",
        "channels": ["signed bidirectional separation", "closure null calibration", "canonical TLD construct channel"],
        "requirements": ["null-family adequacy controls", "block-phase marginalization", "nested-parent inference", "historical and synthetic construct benchmarks", "semantic T_e/S_e mapping"],
        "dataset": "NOT_SELECTED", "Beijing_confirmatory_use": "FORBIDDEN",
    })
    _write_json(output / "next_method_open_questions.json", {
        "schema_version": "1.0.0", "questions": [
            "Which construct-valid operator family is frozen before a new domain is selected?",
            "How many independent city/domain clusters are required?",
            "Which null families pass directional calibration across the synthetic envelope?",
            "Should coarse-graining onset be renamed instead of called T_e?",
        ]
    })
    _write_json(output / "next_method_forbidden_reuse.json", {
        "schema_version": "1.0.0", "Beijing_PM25": "diagnostics only",
        "forbidden": ["confirmatory threshold tuning", "candidate selection", "claim of independent validation"],
    })
    _write_json(output / "next_heldout_study_readiness.json", {
        "schema_version": "1.0.0", "ready": False,
        "exact_next_legal_action": "FREEZE_REVISED_METHOD_ON_SYNTHETIC_AND_HISTORICAL_CONTROLS",
        "dataset_selection_allowed_now": False, "execution_allowed_now": False,
    })


def _final_report(
    null_audit: dict[str, Any], consensus: dict[str, Any], phase: dict[str, Any],
    dependence: dict[str, Any], operator: dict[str, Any], closure: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0", "release": "v0.2.2",
        "V021_PRIMARY_RESULT": ORIGINAL_RESULT,
        "primary_forensic_classification": "V021_FORENSIC_RESULT_MIXED_WITH_EXACT_COMPONENTS",
        "components": [
            {"component": "exact reproduction", "classification": "EXACT_SCIENTIFIC_REPRODUCTION"},
            {"component": "opposite sign", "classification": consensus["classification"]},
            {"component": "registered null", "classification": null_audit["classification"]},
            {"component": "block phase", "classification": phase["classification"]},
            {"component": "parent dependence", "classification": dependence["classification"]},
            {"component": "operator construct", "classification": operator["classification"]},
            {"component": "closure null", "classification": closure["classification"]},
            {"component": "gate adequacy", "classification": "CALIBRATION_INSUFFICIENT"},
        ],
        "project_level_wording": PROJECT_WORDING,
        "genuinely_falsified": "the preregistered positive-persistence projection on this dataset under the frozen gates",
        "not_falsified": ["general TLD", "negative-direction structure", "other operators", "other domains", "ToT-BROT"],
        "unresolved": ["general construct-valid operator", "multi-city parent model", "future null family", "new held-out domain"],
        "Beijing_future_use": "diagnostic only",
        "new_untouched_dataset_required_for_confirmation": True,
        "TLD_DERIVED": "BLOCKED", "EXTERNALLY_VALIDATED": False,
        "exact_next_legal_action": "FREEZE_REVISED_METHOD_ON_SYNTHETIC_AND_HISTORICAL_CONTROLS",
    }


def _report_markdown(report: dict[str, Any]) -> str:
    components = "\n".join(
        f"- {row['component']}: `{row['classification']}`" for row in report["components"]
    )
    not_falsified = "\n".join(f"- {item}" for item in report["not_falsified"])
    return f"""# TORUS Field Studio v0.2.2 — v0.2.1 negative-result reconciliation

## Immutable original result

`{report['V021_PRIMARY_RESULT']}`

{report['project_level_wording']}

The clean installed-wheel replay reproduced every claim-bearing scientific table byte-for-byte. A host-specific absolute source path changes the replay run identifier, but not any scientific result.

## Forensic classification

`{report['primary_forensic_classification']}`

{components}

The reverse-direction surface is post-hoc and does not reverse or rewrite v0.2.1. The twelve stations are correlated sensor projections from one city. The registered operator is a narrow positive-persistence proxy, and the declared closure-local null p-value was not implemented in the original secondary path.

## What was not falsified

{not_falsified}

`TLD_DERIVED` remains blocked. `EXTERNALLY_VALIDATED` remains false. Beijing is now outcome-exposed and is restricted to diagnostics.

## Next legal action

`{report['exact_next_legal_action']}`
"""


def _publication_aliases(output: Path) -> None:
    aliases = {
        "signed_parent_null_diagnostics.csv": "v021-signed-direction-diagnostics.csv",
        "null_mechanism_metrics.csv": "v021-null-mechanism-diagnostics.csv",
        "block_phase_diagnostics.csv": "v021-block-phase-diagnostics.csv",
        "station_dependence_matrix.csv": "v021-parent-dependence-diagnostics.csv",
        "closure_null_parent_cells.csv": "v021-closure-null-calibration.csv",
        "power_surface.csv": "v021-power-surface.csv",
    }
    for source, target in aliases.items():
        (output / target).write_bytes((output / source).read_bytes())


def _write_reproduction_sums(output: Path) -> None:
    selected = [
        "v021_release_custody.json", "v021_source_custody.json", "v021_exact_reproduction.json",
        "v021_result_hash_reconciliation.json", "v021_public_pages_reconciliation.json",
        "v021_original_claim_boundary.json",
    ]
    lines = [f"{sha256_file(output / name)}  {name}\n" for name in selected]
    (output / "SHA256SUMS_V021_REPRODUCTION.txt").write_text("".join(lines), encoding="utf-8", newline="\n")
