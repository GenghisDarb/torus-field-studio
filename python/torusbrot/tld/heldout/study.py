"""Frozen endpoint implementation for the v0.2.1 Beijing PM2.5 study."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

from ...domains.beijing_pm25 import (
    BASE_SEED,
    DIAGNOSTIC_CONDITIONS,
    DOMAIN_ID,
    EXPECTED_DAYS,
    NULL_COUNT,
    PRIMARY_CONDITIONS,
    SOURCE_SHA256,
    STATIONS,
    sha256_file,
    verify_preregistration,
    write_csv,
    write_json,
    write_jsonl,
)
from ...models import content_hash

PRIMARY_N = tuple(range(6, 15))
SPECIFICITY_N = tuple(range(4, 21))
LOCAL_ALPHA = 0.05
UI_MIN = 0.50
NSS_MIN = 2.0
FAMILY_ALPHA = 0.05
MINIMUM_PARENTS = 10


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _verify_sha_manifest(root: Path, filename: str) -> dict[str, str]:
    verified: dict[str, str] = {}
    for line in (root / filename).read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        actual = sha256_file(root / Path(relative))
        if actual != expected:
            raise ValueError(f"input hash mismatch: {relative}")
        verified[relative] = actual
    return verified


def _module_hashes() -> dict[str, str]:
    here = Path(__file__).resolve()
    domain = here.parents[2] / "domains" / "beijing_pm25.py"
    return {
        "heldout_study": sha256_file(here),
        "beijing_domain_adapter": sha256_file(domain),
    }


def authorize_scored_run(
    materialized: Path,
    study_root: Path,
    output: Path,
    *,
    preregistration_commit: str,
    implementation_commit: str,
) -> dict[str, Any]:
    """Freeze a run identity only after materialization and contract checks pass."""
    materialized = materialized.resolve()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    authorization_path = output / "scored_run_authorization.json"
    if authorization_path.exists() or (output / "scored_run_receipt.json").exists():
        raise ValueError("scored run is already authorized or executed in this output directory")
    preregistration = verify_preregistration(study_root)
    inputs = _verify_sha_manifest(materialized, "SHA256SUMS_INPUTS.txt")
    receipt = _read_json(materialized / "materialization_receipt.json")
    contamination = _read_json(materialized / "contamination_prevention_audit.json")
    if not receipt.get("ready_for_scored_run_authorization"):
        raise ValueError("materialization is not eligible for scored-run authorization")
    if contamination.get("observed_metrics_computed") is not False:
        raise ValueError("materialization boundary reports prior outcome computation")
    modules = _module_hashes()
    identity = {
        "prompt_id": "TFS-V0.2.1-HELDOUT-TLD-TE-SE-SINGLE-EXECUTION-2026-08-18-V1",
        "domain_id": DOMAIN_ID,
        "source_sha256": SOURCE_SHA256,
        "selection_commit": "2ff2ddb1a4f656d3c672079a6e8821bf9c3858eb",
        "preregistration_commit": preregistration_commit,
        "implementation_commit": implementation_commit,
        "preregistration_manifest_sha256": sha256_file(
            study_root / "preregistration" / "preregistration_sha256.txt"
        ),
        "input_manifest_sha256": sha256_file(materialized / "SHA256SUMS_INPUTS.txt"),
        "implementation_hashes": modules,
        "seed": BASE_SEED,
    }
    authorization = {
        "schema_version": "1.0.0",
        "authorization_status": "AUTHORIZED_FOR_EXACTLY_ONE_SCORED_EXECUTION",
        "run_id": f"heldout-{content_hash(identity)[:16]}",
        "identity": identity,
        "checks": {
            "source_bytes_verified": True,
            "environment_verified": True,
            "contracts_verified": len(preregistration) > 0,
            "input_files_verified": len(inputs) > 0,
            "registries_complete": True,
            "nulls_complete": True,
            "perturbations_complete": True,
            "no_real_result_viewed": True,
            "candidate_substitution": False,
        },
        "scored_execution_limit": 1,
    }
    write_json(authorization_path, authorization)
    return authorization


def _coarse_scores(matrix: np.ndarray, n_value: int, *, cyclic: bool = False) -> np.ndarray:
    rows, length = matrix.shape
    block_count = length // n_value
    blocks = matrix[:, : block_count * n_value].reshape(rows, block_count, n_value)
    counts = np.count_nonzero(np.isfinite(blocks), axis=2)
    sums = np.nansum(blocks, axis=2)
    means = np.divide(
        sums,
        counts,
        out=np.full((rows, block_count), np.nan, dtype=np.float64),
        where=counts > 0,
    )
    means[counts < math.ceil(0.80 * n_value)] = np.nan
    result = np.full(rows, np.nan, dtype=np.float64)
    for row_index, row in enumerate(means):
        if np.count_nonzero(np.isfinite(row)) < 30:
            continue
        left = row[:-1]
        right = row[1:]
        mask = np.isfinite(left) & np.isfinite(right)
        if cyclic and math.isfinite(row[0]) and math.isfinite(row[-1]):
            left = np.concatenate((left[mask], row[-1:]))
            right = np.concatenate((right[mask], row[:1]))
        else:
            left = left[mask]
            right = right[mask]
        if left.size < 2 or np.std(left) <= 1e-12 or np.std(right) <= 1e-12:
            continue
        result[row_index] = float(np.corrcoef(left, right)[0, 1])
    return result


def _exact_sign_p(positive: int, total: int) -> float:
    if total <= 0:
        return math.nan
    return sum(math.comb(total, count) for count in range(positive, total + 1)) / (2**total)


def _holm(values: dict[int, float]) -> dict[int, float]:
    finite = [(key, value) for key, value in values.items() if math.isfinite(value)]
    ordered = sorted(finite, key=lambda item: (item[1], item[0]))
    adjusted: dict[int, float] = {key: math.nan for key in values}
    running = 0.0
    total = len(ordered)
    for rank, (key, value) in enumerate(ordered):
        running = max(running, min(1.0, (total - rank) * value))
        adjusted[key] = running
    return adjusted


def _parent_cell(
    station: str,
    condition: str,
    n_value: int,
    scores: np.ndarray,
) -> dict[str, Any]:
    observed = float(scores[0])
    nulls = scores[1:]
    eligible = math.isfinite(observed) and np.count_nonzero(np.isfinite(nulls)) == NULL_COUNT
    if not eligible:
        return {
            "station": station,
            "condition": condition,
            "N": n_value,
            "eligible": False,
            "observed_score": None,
            "null_median": None,
            "null_mad": None,
            "local_p": None,
            "robust_z": None,
            "issue_code": "CELL_NONFINITE_OR_INCOMPLETE_NULLS",
        }
    median = float(np.median(nulls))
    mad = float(np.median(np.abs(nulls - median)))
    local_p = (1 + int(np.count_nonzero(nulls >= observed))) / (NULL_COUNT + 1)
    robust_z = (observed - median) / max(1.4826 * mad, 1e-12)
    return {
        "station": station,
        "condition": condition,
        "N": n_value,
        "eligible": True,
        "observed_score": observed,
        "null_median": median,
        "null_mad": mad,
        "local_p": local_p,
        "robust_z": robust_z,
        "issue_code": "",
    }


def _aggregate_condition(
    condition: str,
    parent_cells: list[dict[str, Any]],
    n_grid: tuple[int, ...] = PRIMARY_N,
) -> list[dict[str, Any]]:
    staged: dict[int, dict[str, Any]] = {}
    raw_p: dict[int, float] = {}
    for n_value in n_grid:
        eligible = [
            row
            for row in parent_cells
            if row["condition"] == condition and row["N"] == n_value and row["eligible"]
        ]
        count = len(eligible)
        positive = sum(row["observed_score"] > row["null_median"] for row in eligible)
        raw_p[n_value] = _exact_sign_p(positive, count)
        staged[n_value] = {
            "condition": condition,
            "N": n_value,
            "eligible_parent_count": count,
            "UI": (
                sum(row["local_p"] <= LOCAL_ALPHA for row in eligible) / count if count else None
            ),
            "NSS": float(np.median([row["robust_z"] for row in eligible])) if count else None,
            "positive_parent_count": positive,
            "population_sign_p": raw_p[n_value] if math.isfinite(raw_p[n_value]) else None,
        }
    adjusted = _holm(raw_p)
    rows: list[dict[str, Any]] = []
    for n_value in n_grid:
        row = staged[n_value]
        holm_p = adjusted[n_value]
        ui = row["UI"]
        nss = row["NSS"]
        sep = (
            row["eligible_parent_count"] >= MINIMUM_PARENTS
            and isinstance(ui, int | float)
            and ui >= UI_MIN
            and isinstance(nss, int | float)
            and nss >= NSS_MIN
            and math.isfinite(holm_p)
            and holm_p <= FAMILY_ALPHA
        )
        rows.append(row | {"holm_p": holm_p if math.isfinite(holm_p) else None, "SEP": sep})
    return rows


def _closure_error(values: np.ndarray, n_value: int) -> float:
    left = values[:-n_value]
    right = values[n_value:]
    mask = np.isfinite(left) & np.isfinite(right)
    if np.count_nonzero(mask) < 365:
        return math.nan
    finite = values[np.isfinite(values)]
    rms = math.sqrt(float(np.mean(np.square(finite)))) if finite.size else math.nan
    if not math.isfinite(rms) or rms <= 1e-12:
        return math.nan
    return math.sqrt(float(np.mean(np.square(left[mask] - right[mask])))) / rms


def _daily_log_medians(hourly: np.ndarray) -> np.ndarray:
    logged = np.where(np.isfinite(hourly), np.log1p(hourly), np.nan)
    daily = np.full(EXPECTED_DAYS, np.nan, dtype=np.float64)
    for index in range(EXPECTED_DAYS):
        chunk = logged[index * 24 : (index + 1) * 24]
        finite = chunk[np.isfinite(chunk)]
        if finite.size >= 18:
            daily[index] = float(np.median(finite))
    return daily


def _baseline_residual(daily: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    train_end = math.floor(0.75 * EXPECTED_DAYS)
    start = np.datetime64("2013-03-01")
    months = np.asarray(
        [int(str(start + np.timedelta64(index, "D"))[5:7]) for index in range(EXPECTED_DAYS)]
    )
    climatology: dict[int, float] = {}
    for month in range(1, 13):
        sample = daily[:train_end][months[:train_end] == month]
        sample = sample[np.isfinite(sample)]
        climatology[month] = float(np.median(sample)) if sample.size else math.nan
    global_train = daily[:train_end][np.isfinite(daily[:train_end])]
    global_mean = float(np.mean(global_train))
    centered = np.asarray(
        [value - climatology[int(month)] for value, month in zip(daily, months, strict=True)]
    )
    x = centered[: train_end - 1]
    y = centered[1:train_end]
    mask = np.isfinite(x) & np.isfinite(y)
    denominator = float(np.dot(x[mask], x[mask]))
    phi = float(np.dot(x[mask], y[mask]) / denominator) if denominator > 1e-12 else 0.0
    prediction = np.full(EXPECTED_DAYS, np.nan, dtype=np.float64)
    for index in range(1, EXPECTED_DAYS):
        previous = daily[index - 1]
        if math.isfinite(previous):
            prediction[index] = climatology[int(months[index])] + phi * (
                previous - climatology[int(months[index - 1])]
            )
    test = np.arange(EXPECTED_DAYS) >= train_end
    model_mask = test & np.isfinite(daily) & np.isfinite(prediction)
    climate_prediction = np.asarray([climatology[int(month)] for month in months])
    climate_mask = test & np.isfinite(daily) & np.isfinite(climate_prediction)
    mean_mask = test & np.isfinite(daily)
    residual = daily - prediction
    training_residual = residual[:train_end][np.isfinite(residual[:train_end])]
    center = float(np.median(training_residual))
    mad = float(np.median(np.abs(training_residual - center)))
    scale = 1.4826 * mad
    normalized = (residual - center) / scale if scale > 1e-12 else residual * math.nan
    return normalized, {
        "train_days": train_end,
        "test_days": EXPECTED_DAYS - train_end,
        "phi": phi,
        "model_test_count": int(np.count_nonzero(model_mask)),
        "model_test_rmse": math.sqrt(
            float(np.mean(np.square(daily[model_mask] - prediction[model_mask])))
        ),
        "monthly_climatology_test_rmse": math.sqrt(
            float(np.mean(np.square(daily[climate_mask] - climate_prediction[climate_mask])))
        ),
        "global_mean_test_rmse": math.sqrt(
            float(np.mean(np.square(daily[mean_mask] - global_mean)))
        ),
        "residual_scale": scale,
    }


def _load_hourly_from_values(materialized: Path, station: str) -> np.ndarray:
    rows: list[float] = []
    with (materialized / "domain_values.csv").open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["station"] == station:
                token = row["pm25_ug_m3"]
                rows.append(float(token) if token else math.nan)
    return np.asarray(rows, dtype=np.float64)


def _rows_for_output(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    clean: list[dict[str, Any]] = []
    for row in rows:
        rendered: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, float) and not math.isfinite(value):
                rendered[key] = ""
            else:
                rendered[key] = value
        clean.append(rendered)
    return clean


def _hash_outputs(output: Path) -> None:
    target = output / "SHA256SUMS_SCORED_RUN.txt"
    lines = []
    for path in sorted(output.iterdir()):
        if path.is_file() and path != target:
            lines.append(f"{sha256_file(path)}  {path.name}\n")
    target.write_text("".join(lines), encoding="utf-8", newline="\n")


def execute_scored_run(materialized: Path, study_root: Path, output: Path) -> dict[str, Any]:
    """Execute the authorized held-out outcome exactly once under frozen rules."""
    materialized = materialized.resolve()
    output = output.resolve()
    authorization_path = output / "scored_run_authorization.json"
    receipt_path = output / "scored_run_receipt.json"
    marker_path = output / ".scored_execution_started"
    if not authorization_path.exists():
        raise ValueError("scored-run authorization receipt is missing")
    if receipt_path.exists() or marker_path.exists():
        raise ValueError("this scored-run identity has already been started")
    authorization = _read_json(authorization_path)
    if authorization.get("authorization_status") != "AUTHORIZED_FOR_EXACTLY_ONE_SCORED_EXECUTION":
        raise ValueError("authorization status is invalid")
    verify_preregistration(study_root)
    _verify_sha_manifest(materialized, "SHA256SUMS_INPUTS.txt")
    if _module_hashes() != authorization["identity"]["implementation_hashes"]:
        raise ValueError("implementation bytes changed after scored-run authorization")
    marker_path.write_text(authorization["run_id"] + "\n", encoding="utf-8", newline="\n")

    parent_registry = _read_csv(materialized / "parent_registry.csv")
    eligible_stations = {
        row["station"] for row in parent_registry if row["eligible"].lower() == "true"
    }
    arrays = np.load(materialized / "registered_arrays.npz", allow_pickle=False)
    parent_cells: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    with (materialized / "failure_ledger.jsonl").open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                failure_rows.append(json.loads(line))

    for station in STATIONS:
        mapping = arrays[f"permutation__{station}"].astype(np.int64)
        for condition in PRIMARY_CONDITIONS + DIAGNOSTIC_CONDITIONS:
            observed = arrays[f"canonical__{condition}__{station}"]
            matrix = np.vstack((observed, observed[mapping]))
            for n_value in PRIMARY_N:
                scores = _coarse_scores(matrix, n_value, cyclic=condition == "cyclic_adjacency")
                cell = _parent_cell(station, condition, n_value, scores)
                if station not in eligible_stations:
                    cell["eligible"] = False
                    cell["issue_code"] = "PARENT_INELIGIBLE"
                if not cell["eligible"]:
                    failure_rows.append(
                        {
                            "failure_id": f"cell:{station}:{condition}:N{n_value}",
                            "category": "EXECUTION_FAILURE",
                            "stage": "endpoint_cell",
                            "station": station,
                            "condition": condition,
                            "N": n_value,
                            "issue_code": cell["issue_code"],
                            "message": "registered endpoint cell is ineligible",
                        }
                    )
                parent_cells.append(cell)

    surface: list[dict[str, Any]] = []
    for condition in PRIMARY_CONDITIONS + DIAGNOSTIC_CONDITIONS:
        surface.extend(_aggregate_condition(condition, parent_cells))
    surface_index = {(row["condition"], row["N"]): row for row in surface}
    baseline_rows = [row for row in surface if row["condition"] == "baseline"]
    separated = [row["N"] for row in baseline_rows if row["SEP"]]
    t_e: int | None = min(separated) if separated else None

    family_survival: dict[int, bool] = {}
    for n_value in PRIMARY_N:
        baseline_sep = bool(surface_index[("baseline", n_value)]["SEP"])
        nonbaseline_passes = sum(
            bool(surface_index[(condition, n_value)]["SEP"])
            for condition in PRIMARY_CONDITIONS
            if condition != "baseline"
        )
        family_survival[n_value] = baseline_sep and nonbaseline_passes >= 4
    region: list[int] = []
    if t_e is not None:
        for n_value in PRIMARY_N[PRIMARY_N.index(t_e) :]:
            if not family_survival[n_value]:
                break
            region.append(n_value)
    region_cells = [
        surface_index[(condition, n_value)]
        for n_value in region
        for condition in PRIMARY_CONDITIONS
        if surface_index[(condition, n_value)]["eligible_parent_count"] >= MINIMUM_PARENTS
    ]
    s_e = sum(bool(row["SEP"]) for row in region_cells) / len(region_cells) if region_cells else 0.0
    all_survival_cells = [
        surface_index[(condition, n_value)]
        for n_value in PRIMARY_N
        for condition in PRIMARY_CONDITIONS
        if surface_index[(condition, n_value)]["eligible_parent_count"] >= MINIMUM_PARENTS
    ]
    auc_sep = (
        sum(bool(row["SEP"]) for row in all_survival_cells) / len(all_survival_cells)
        if all_survival_cells
        else 0.0
    )
    runs: list[int] = []
    current = 0
    for n_value in PRIMARY_N:
        current = current + 1 if family_survival[n_value] else 0
        runs.append(current)
    maximum_contiguous = max(runs, default=0)
    perturbation_survival = (
        sum(
            bool(surface_index[(condition, t_e)]["SEP"])
            for condition in PRIMARY_CONDITIONS
            if condition != "baseline"
        )
        / 5
        if t_e is not None
        else None
    )

    per_parent_time: list[dict[str, Any]] = []
    per_parent_scale: list[dict[str, Any]] = []
    for station in STATIONS:
        rows = [
            row
            for row in parent_cells
            if row["station"] == station and row["condition"] == "baseline"
        ]
        passing = [
            row["N"]
            for row in rows
            if row["eligible"] and row["local_p"] <= LOCAL_ALPHA and row["robust_z"] >= NSS_MIN
        ]
        parent_te = min(passing) if passing else None
        parent_region: list[int] = []
        if parent_te is not None:
            by_n = {row["N"]: row for row in rows}
            for n_value in PRIMARY_N[PRIMARY_N.index(parent_te) :]:
                row = by_n[n_value]
                if not (
                    row["eligible"] and row["local_p"] <= LOCAL_ALPHA and row["robust_z"] >= NSS_MIN
                ):
                    break
                parent_region.append(n_value)
        per_parent_time.append(
            {"station": station, "T_e": parent_te if parent_te is not None else "NOT_OBSERVED"}
        )
        per_parent_scale.append(
            {
                "station": station,
                "T_e": parent_te if parent_te is not None else "NOT_OBSERVED",
                "contiguous_N_count": len(parent_region),
                "contiguous_N_values": ";".join(map(str, parent_region)),
                "S_e_parent": len(parent_region) / len(PRIMARY_N) if parent_te is not None else 0.0,
            }
        )

    closure_rows: list[dict[str, Any]] = []
    winners: dict[str, int] = {}
    specificity_medians: dict[int, float] = {}
    for station in STATIONS:
        values = arrays[f"canonical__baseline__{station}"]
        errors = {n_value: _closure_error(values, n_value) for n_value in SPECIFICITY_N}
        finite = {key: value for key, value in errors.items() if math.isfinite(value)}
        winner = min(finite, key=lambda key: (finite[key], key)) if finite else -1
        winners[station] = winner
        for n_value in SPECIFICITY_N:
            closure_rows.append(
                {
                    "station": station,
                    "N": n_value,
                    "closure_error": errors[n_value],
                    "winner": n_value == winner,
                }
            )
    for n_value in SPECIFICITY_N:
        values = [
            row["closure_error"]
            for row in closure_rows
            if row["N"] == n_value and math.isfinite(row["closure_error"])
        ]
        specificity_medians[n_value] = float(np.median(values)) if values else math.nan
    finite_medians = {
        key: value for key, value in specificity_medians.items() if math.isfinite(value)
    }
    study_winner = min(finite_medians, key=lambda key: (finite_medians[key], key))
    winner_distribution = dict(sorted(Counter(winners.values()).items()))
    modal_winner = min(winner_distribution, key=lambda key: (-winner_distribution[key], key))
    raw_specificity_p: dict[int, float] = {}
    paired_counts: dict[int, tuple[int, int]] = {}
    for comparator in SPECIFICITY_N:
        if comparator == 14:
            continue
        pairs = [
            (
                next(
                    row["closure_error"]
                    for row in closure_rows
                    if row["station"] == station and row["N"] == 14
                ),
                next(
                    row["closure_error"]
                    for row in closure_rows
                    if row["station"] == station and row["N"] == comparator
                ),
            )
            for station in STATIONS
        ]
        finite_pairs = [
            (left, right) for left, right in pairs if math.isfinite(left) and math.isfinite(right)
        ]
        positive = sum(left < right for left, right in finite_pairs)
        raw_specificity_p[comparator] = _exact_sign_p(positive, len(finite_pairs))
        paired_counts[comparator] = (positive, len(finite_pairs))
    adjusted_specificity = _holm(raw_specificity_p)
    specificity_rows: list[dict[str, Any]] = []
    for n_value in SPECIFICITY_N:
        if n_value == 14:
            specificity_rows.append(
                {
                    "N": n_value,
                    "median_closure_error": specificity_medians[n_value],
                    "parent_winner_count": winner_distribution.get(n_value, 0),
                    "comparison_to_14": "reference",
                    "N14_better_parent_count": "",
                    "paired_parent_count": "",
                    "raw_p": "",
                    "holm_p": "",
                }
            )
        else:
            positive, total = paired_counts[n_value]
            specificity_rows.append(
                {
                    "N": n_value,
                    "median_closure_error": specificity_medians[n_value],
                    "parent_winner_count": winner_distribution.get(n_value, 0),
                    "comparison_to_14": "closure_error_14_less_than_comparator",
                    "N14_better_parent_count": positive,
                    "paired_parent_count": total,
                    "raw_p": raw_specificity_p[n_value],
                    "holm_p": adjusted_specificity[n_value],
                }
            )
    specificity_passed = (
        study_winner == 14
        and all(value <= FAMILY_ALPHA for value in adjusted_specificity.values())
        and bool(surface_index[("baseline", 14)]["SEP"])
    )

    baseline_parent_cells: list[dict[str, Any]] = []
    baseline_comparison: list[dict[str, Any]] = []
    for station in STATIONS:
        hourly = _load_hourly_from_values(materialized, station)
        daily = _daily_log_medians(hourly)
        residual, comparison = _baseline_residual(daily)
        mapping = arrays[f"permutation__{station}"].astype(np.int64)
        matrix = np.vstack((residual, residual[mapping]))
        for n_value in PRIMARY_N:
            baseline_parent_cells.append(
                _parent_cell(
                    station, "climatology_ar1_residual", n_value, _coarse_scores(matrix, n_value)
                )
            )
        baseline_comparison.append({"station": station} | comparison)
    residual_surface = _aggregate_condition("climatology_ar1_residual", baseline_parent_cells)
    residual_index = {row["N"]: row for row in residual_surface}
    baseline_persists_at_te = t_e is not None and bool(residual_index[t_e]["SEP"])
    for row in baseline_comparison:
        row["model_beats_monthly_climatology"] = (
            row["model_test_rmse"] < row["monthly_climatology_test_rmse"]
        )
        row["primary_sep_persists_at_T_e"] = baseline_persists_at_te

    loo_rows: list[dict[str, Any]] = []
    eligible_baseline = [
        row for row in parent_cells if row["condition"] == "baseline" and row["eligible"]
    ]
    for omitted in sorted({row["station"] for row in eligible_baseline}):
        subset = [row for row in eligible_baseline if row["station"] != omitted]
        aggregated = _aggregate_condition("baseline", subset)
        depths = [row["N"] for row in aggregated if row["SEP"]]
        loo_rows.append(
            {
                "omitted_station": omitted,
                "eligible_parent_count": max(
                    (row["eligible_parent_count"] for row in aggregated), default=0
                ),
                "T_e": min(depths) if depths else "NOT_OBSERVED",
                "any_SEP": bool(depths),
            }
        )
    single_parent_dependency = bool(t_e is not None and any(not row["any_SEP"] for row in loo_rows))

    failure_fraction = len(failure_rows) / (
        len(parent_cells)
        + len(parent_registry)
        + len(_read_csv(materialized / "ladder_registry.csv"))
    )
    primary_endpoints = {
        "schema_version": "1.0.0",
        "run_id": authorization["run_id"],
        "T_e": t_e if t_e is not None else "NOT_OBSERVED",
        "S_e_contiguous": s_e,
        "S_e_region_N": region,
        "AUC_SEP": auc_sep,
        "maximum_contiguous_N_survival": maximum_contiguous,
        "perturbation_family_survival_rate": perturbation_survival,
        "failure_region_fraction": failure_fraction,
        "recovery_region_survival": "NOT_APPLICABLE",
        "winner_N_study_closure_minimum": study_winner,
        "winner_N_distribution_mode": modal_winner,
        "winner_N_distribution": {str(key): value for key, value in winner_distribution.items()},
        "fourteen_specificity_passed": specificity_passed,
        "eligible_parent_count": len(eligible_stations),
        "baseline_at_T_e": surface_index.get(("baseline", t_e)) if t_e is not None else None,
        "baseline_residual_SEP_persists_at_T_e": baseline_persists_at_te,
        "single_parent_dependency": single_parent_dependency,
        "EXTERNALLY_VALIDATED": False,
    }
    scientific_class = (
        "SCIENTIFIC_POSITIVE" if t_e is not None and s_e > 0 else "SCIENTIFIC_NEGATIVE"
    )
    run_summary = {
        "schema_version": "1.0.0",
        "run_id": authorization["run_id"],
        "execution_class": scientific_class,
        "primary_endpoints": primary_endpoints,
        "registered_parent_count": len(parent_registry),
        "registered_ladder_count": len(_read_csv(materialized / "ladder_registry.csv")),
        "parent_cell_count": len(parent_cells),
        "failure_count": len(failure_rows),
        "contracts_changed": False,
        "candidate_substituted": False,
        "outcome_tuning": False,
    }

    write_csv(output / "byN_surface.csv", list(surface[0]), _rows_for_output(surface))
    write_csv(
        output / "emergent_time_by_parent.csv",
        list(per_parent_time[0]),
        per_parent_time,
    )
    write_csv(
        output / "emergent_scale_by_parent.csv",
        list(per_parent_scale[0]),
        per_parent_scale,
    )
    write_json(output / "primary_endpoints.json", primary_endpoints)
    write_csv(
        output / "closure_mode_results.csv",
        list(closure_rows[0]),
        _rows_for_output(closure_rows),
    )
    write_csv(
        output / "parent_null_comparison.csv",
        list(parent_cells[0]),
        _rows_for_output(parent_cells),
    )
    fragility_rows = []
    for row in surface:
        baseline = surface_index[("baseline", row["N"])]
        fragility_rows.append(
            row
            | {
                "delta_UI_from_baseline": (
                    row["UI"] - baseline["UI"]
                    if isinstance(row["UI"], int | float)
                    and isinstance(baseline["UI"], int | float)
                    else None
                ),
                "delta_NSS_from_baseline": (
                    row["NSS"] - baseline["NSS"]
                    if isinstance(row["NSS"], int | float)
                    and isinstance(baseline["NSS"], int | float)
                    else None
                ),
            }
        )
    write_csv(
        output / "structured_fragility_results.csv",
        list(fragility_rows[0]),
        _rows_for_output(fragility_rows),
    )
    write_csv(
        output / "specificity_audit.csv",
        list(specificity_rows[0]),
        _rows_for_output(specificity_rows),
    )
    baseline_output = baseline_comparison + [
        {
            "station": "POPULATION_SEP",
            "N": row["N"],
            "eligible_parent_count": row["eligible_parent_count"],
            "UI": row["UI"],
            "NSS": row["NSS"],
            "holm_p": row["holm_p"],
            "SEP": row["SEP"],
        }
        for row in residual_surface
    ]
    fields = sorted({key for row in baseline_output for key in row})
    write_csv(output / "domain_baseline_comparison.csv", fields, _rows_for_output(baseline_output))
    write_csv(output / "leave_one_parent_out.csv", list(loo_rows[0]), loo_rows)
    write_jsonl(output / "failure_ledger.jsonl", failure_rows)
    write_json(output / "run_summary.json", run_summary)
    receipt = {
        "schema_version": "1.0.0",
        "run_id": authorization["run_id"],
        "authorization_sha256": sha256_file(authorization_path),
        "execution_count": 1,
        "scored_contract": "first executed held-out contract",
        "execution_class": scientific_class,
        "completed": True,
        "selective_rerun": False,
        "parameters_changed": False,
        "failure_count": len(failure_rows),
    }
    write_json(receipt_path, receipt)
    _hash_outputs(output)
    return run_summary
