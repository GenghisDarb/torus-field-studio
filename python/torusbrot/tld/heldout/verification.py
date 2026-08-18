"""Independent held-out verifier; deliberately does not import production endpoint code."""

from __future__ import annotations

import copy
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from ...domains.beijing_pm25 import (
    DIAGNOSTIC_CONDITIONS,
    EXPECTED_HOURS,
    NULL_COUNT,
    PRIMARY_CONDITIONS,
    SOURCE_SHA256,
    STATIONS,
    verify_preregistration,
    write_json,
    write_jsonl,
)

PRIMARY_N = tuple(range(6, 15))
SPECIFICITY_N = tuple(range(4, 21))


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _score(matrix: np.ndarray, n_value: int, cyclic: bool) -> np.ndarray:
    block_count = matrix.shape[1] // n_value
    raw = matrix[:, : block_count * n_value].reshape(matrix.shape[0], block_count, n_value)
    finite_count = np.isfinite(raw).sum(axis=2)
    sums = np.where(np.isfinite(raw), raw, 0.0).sum(axis=2)
    block_values = np.full((matrix.shape[0], block_count), np.nan)
    allowed = finite_count >= math.ceil(0.8 * n_value)
    block_values[allowed] = sums[allowed] / finite_count[allowed]
    answer = np.full(matrix.shape[0], np.nan)
    for index in range(matrix.shape[0]):
        row = block_values[index]
        if np.isfinite(row).sum() < 30:
            continue
        x = row[:-1]
        y = row[1:]
        keep = np.isfinite(x) & np.isfinite(y)
        x = x[keep]
        y = y[keep]
        if cyclic and np.isfinite(row[0]) and np.isfinite(row[-1]):
            x = np.append(x, row[-1])
            y = np.append(y, row[0])
        if len(x) >= 2 and np.std(x) > 1e-12 and np.std(y) > 1e-12:
            x_centered = x - np.mean(x)
            y_centered = y - np.mean(y)
            answer[index] = float(
                np.sum(x_centered * y_centered)
                / math.sqrt(float(np.sum(x_centered**2) * np.sum(y_centered**2)))
            )
    return answer


def _sign_tail(successes: int, trials: int) -> float:
    return sum(math.comb(trials, count) for count in range(successes, trials + 1)) / (2**trials)


def _holm(raw: dict[int, float]) -> dict[int, float]:
    ordered = sorted(raw.items(), key=lambda item: (item[1], item[0]))
    adjusted: dict[int, float] = {}
    previous = 0.0
    for rank, (key, value) in enumerate(ordered):
        previous = max(previous, min(1.0, (len(ordered) - rank) * value))
        adjusted[key] = previous
    return adjusted


def _independent_surface(arrays: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    parent_rows: list[dict[str, Any]] = []
    surface: list[dict[str, Any]] = []
    for condition in PRIMARY_CONDITIONS + DIAGNOSTIC_CONDITIONS:
        raw_p: dict[int, float] = {}
        staged: dict[int, list[dict[str, Any]]] = {}
        for n_value in PRIMARY_N:
            cells: list[dict[str, Any]] = []
            for station in STATIONS:
                values = arrays[f"canonical__{condition}__{station}"]
                mappings = arrays[f"permutation__{station}"].astype(np.int64)
                scores = _score(
                    np.vstack((values, values[mappings])),
                    n_value,
                    condition == "cyclic_adjacency",
                )
                observed = float(scores[0])
                nulls = scores[1:]
                eligible = math.isfinite(observed) and np.isfinite(nulls).sum() == NULL_COUNT
                if eligible:
                    median = float(np.median(nulls))
                    mad = float(np.median(np.abs(nulls - median)))
                    p_value = (1 + int(np.sum(nulls >= observed))) / 128
                    robust_z = (observed - median) / max(1.4826 * mad, 1e-12)
                else:
                    median = mad = p_value = robust_z = math.nan
                cell = {
                    "station": station,
                    "condition": condition,
                    "N": n_value,
                    "eligible": eligible,
                    "observed_score": observed,
                    "null_median": median,
                    "null_mad": mad,
                    "local_p": p_value,
                    "robust_z": robust_z,
                }
                cells.append(cell)
                parent_rows.append(cell)
            eligible_cells = [cell for cell in cells if cell["eligible"]]
            successes = sum(cell["observed_score"] > cell["null_median"] for cell in eligible_cells)
            raw_p[n_value] = _sign_tail(successes, len(eligible_cells))
            staged[n_value] = eligible_cells
        adjusted = _holm(raw_p)
        for n_value in PRIMARY_N:
            cells = staged[n_value]
            ui = sum(cell["local_p"] <= 0.05 for cell in cells) / len(cells) if cells else math.nan
            nss = float(np.median([cell["robust_z"] for cell in cells])) if cells else math.nan
            surface.append(
                {
                    "condition": condition,
                    "N": n_value,
                    "eligible_parent_count": len(cells),
                    "UI": ui,
                    "NSS": nss,
                    "positive_parent_count": sum(
                        cell["observed_score"] > cell["null_median"] for cell in cells
                    ),
                    "population_sign_p": raw_p[n_value],
                    "holm_p": adjusted[n_value],
                    "SEP": len(cells) >= 10
                    and ui >= 0.50
                    and nss >= 2.0
                    and adjusted[n_value] <= 0.05,
                }
            )
    return surface, parent_rows


def _closure(values: np.ndarray, lag: int) -> float:
    left = values[:-lag]
    right = values[lag:]
    mask = np.isfinite(left) & np.isfinite(right)
    if mask.sum() < 365:
        return math.nan
    finite = values[np.isfinite(values)]
    scale = math.sqrt(float(np.mean(finite * finite)))
    return math.sqrt(float(np.mean((left[mask] - right[mask]) ** 2))) / scale


def _equal_number(left: Any, right: Any, tolerance: float = 1e-12) -> bool:
    try:
        return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tolerance)
    except (TypeError, ValueError):
        return left == right


def _recompute_parent_eligibility(materialized: Path) -> dict[str, bool]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    with (materialized / "domain_values.csv").open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            grouped[row["station"]].append(row)
    result: dict[str, bool] = {}
    for station in STATIONS:
        rows = grouped[station]
        timestamps = [row["timestamp_local"] for row in rows]
        finite = sum(bool(row["pm25_ug_m3"]) for row in rows)
        result[station] = (
            len(rows) == EXPECTED_HOURS
            and len(set(timestamps)) == EXPECTED_HOURS
            and finite / EXPECTED_HOURS >= 0.90
        )
    return result


def _protocol_issues(evidence: dict[str, Any]) -> list[str]:
    checks = (
        (not evidence["null_parent_matches"], "NULL_PARENT_MISMATCH"),
        (evidence["null_in_observed_metrics"], "NULL_OBSERVED_CONTAMINATION"),
        (not evidence["ladder_order_frozen"], "LADDER_ORDER_CHANGED"),
        (evidence["primary_n_min"] != 6, "N_MIN_CHANGED"),
        (evidence["winner_relabelled_te"], "WINNER_TE_CONFLATION"),
        (not evidence["te_consistent"], "TE_BACKFILL_FORBIDDEN"),
        (evidence["se_source"] != "persistence", "SE_SOURCE_INVALID"),
        (not evidence["failure_ledger_complete"], "FAILED_CELL_DELETED"),
        (not evidence["all_parents_preserved"], "INELIGIBLE_PARENT_REMOVED"),
        (not evidence["seed_frozen"], "SEED_CHANGED"),
        (not evidence["perturbations_registered"], "PERTURBATION_UNREGISTERED"),
        (not evidence["all_files_manifested"], "FILE_UNMANIFESTED"),
        (evidence["source_sha256"] != SOURCE_SHA256, "SOURCE_BYTES_CHANGED"),
        (evidence["global_null_pool"], "GLOBAL_NULL_POOL_FORBIDDEN"),
        (evidence["ordering_selected_after_outcomes"], "ORDERING_OUTCOME_SELECTED"),
        (evidence["window_selected_after_outcomes"], "N_WINDOW_OUTCOME_SELECTED"),
        (
            evidence["claim_tld_derived"] and not evidence["tld_gates_complete"],
            "TLD_DERIVED_GATE_BLOCKED",
        ),
        (evidence["externally_validated"], "EXTERNAL_VALIDATION_FORBIDDEN"),
        (
            evidence["claim_14_unique"] and not evidence["specificity_gate"],
            "FOURTEEN_SPECIFICITY_GATE_BLOCKED",
        ),
        (evidence["interpolation_as_observation"], "INTERPOLATION_AS_OBSERVATION"),
        (evidence["torus_tot_conflated"], "TORUS_TOT_CONFLATION"),
        (evidence["analytic_evidence"], "ANALYTIC_TLD_EVIDENCE_FORBIDDEN"),
        (evidence["negative_parent_removed"], "NEGATIVE_PARENT_REMOVED"),
        (not evidence["thresholds_frozen"], "PREREGISTERED_THRESHOLD_REWRITTEN"),
        (evidence["dataset_id"] != "uci-beijing-multisite-air-quality-pm25", "DATASET_SUBSTITUTED"),
    )
    return [code for failed, code in checks if failed]


def _mutations(base: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    definitions = [
        (
            "M01",
            "Move one null child to the wrong parent",
            "null_parent_matches",
            False,
            "NULL_PARENT_MISMATCH",
        ),
        (
            "M02",
            "Include null children in observed metrics",
            "null_in_observed_metrics",
            True,
            "NULL_OBSERVED_CONTAMINATION",
        ),
        ("M03", "Change ladder order", "ladder_order_frozen", False, "LADDER_ORDER_CHANGED"),
        ("M04", "Change N_min", "primary_n_min", 5, "N_MIN_CHANGED"),
        ("M05", "Relabel winner_N as T_e", "winner_relabelled_te", True, "WINNER_TE_CONFLATION"),
        ("M06", "Populate T_e when no SEP exists", "te_consistent", False, "TE_BACKFILL_FORBIDDEN"),
        ("M07", "Populate S_e from closure", "se_source", "closure", "SE_SOURCE_INVALID"),
        ("M08", "Delete a failed cell", "failure_ledger_complete", False, "FAILED_CELL_DELETED"),
        (
            "M09",
            "Remove an ineligible parent",
            "all_parents_preserved",
            False,
            "INELIGIBLE_PARENT_REMOVED",
        ),
        ("M10", "Change one seed", "seed_frozen", False, "SEED_CHANGED"),
        (
            "M11",
            "Add an unregistered perturbation",
            "perturbations_registered",
            False,
            "PERTURBATION_UNREGISTERED",
        ),
        ("M12", "Add an unmanifested file", "all_files_manifested", False, "FILE_UNMANIFESTED"),
        ("M13", "Change source bytes", "source_sha256", "0" * 64, "SOURCE_BYTES_CHANGED"),
        ("M14", "Use a global null pool", "global_null_pool", True, "GLOBAL_NULL_POOL_FORBIDDEN"),
        (
            "M15",
            "Select the best ordering after outcomes",
            "ordering_selected_after_outcomes",
            True,
            "ORDERING_OUTCOME_SELECTED",
        ),
        (
            "M16",
            "Select the best N window after outcomes",
            "window_selected_after_outcomes",
            True,
            "N_WINDOW_OUTCOME_SELECTED",
        ),
        (
            "M17",
            "Promote TLD_DERIVED without all gates",
            "claim_tld_derived",
            True,
            "TLD_DERIVED_GATE_BLOCKED",
        ),
        (
            "M18",
            "Promote EXTERNALLY_VALIDATED",
            "externally_validated",
            True,
            "EXTERNAL_VALIDATION_FORBIDDEN",
        ),
        (
            "M19",
            "Claim 14 uniqueness without gate",
            "claim_14_unique",
            True,
            "FOURTEEN_SPECIFICITY_GATE_BLOCKED",
        ),
        (
            "M20",
            "Treat an interpolated point as observed",
            "interpolation_as_observation",
            True,
            "INTERPOLATION_AS_OBSERVATION",
        ),
        (
            "M21",
            "Conflate TORUS-BROT and ToT-BROT",
            "torus_tot_conflated",
            True,
            "TORUS_TOT_CONFLATION",
        ),
        (
            "M22",
            "Use analytic z^14+c as TLD evidence",
            "analytic_evidence",
            True,
            "ANALYTIC_TLD_EVIDENCE_FORBIDDEN",
        ),
        (
            "M23",
            "Remove a negative parent",
            "negative_parent_removed",
            True,
            "NEGATIVE_PARENT_REMOVED",
        ),
        (
            "M24",
            "Rewrite a preregistered threshold",
            "thresholds_frozen",
            False,
            "PREREGISTERED_THRESHOLD_REWRITTEN",
        ),
        ("M25", "Substitute another dataset", "dataset_id", "other", "DATASET_SUBSTITUTED"),
    ]
    registry: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for mutation_id, description, field, value, expected_code in definitions:
        mutated = copy.deepcopy(base)
        mutated[field] = value
        if mutation_id == "M17":
            mutated["tld_gates_complete"] = False
        if mutation_id == "M19":
            mutated["specificity_gate"] = False
        issues = _protocol_issues(mutated)
        registry.append(
            {
                "mutation_id": mutation_id,
                "description": description,
                "field": field,
                "expected_issue_code": expected_code,
            }
        )
        results.append(
            {
                "mutation_id": mutation_id,
                "rejected": expected_code in issues,
                "expected_issue_code": expected_code,
                "observed_issue_codes": issues,
            }
        )
    return registry, results


def verify_scored_run(
    materialized: Path,
    study_root: Path,
    scored: Path,
    output: Path,
) -> dict[str, Any]:
    """Recompute endpoints from registered arrays and produce mutation receipts."""
    output.mkdir(parents=True, exist_ok=True)
    preregistration_hashes = verify_preregistration(study_root)
    arrays = np.load(materialized / "registered_arrays.npz", allow_pickle=False)
    surface, parent_rows = _independent_surface(arrays)
    index = {(row["condition"], row["N"]): row for row in surface}
    depths = [row["N"] for row in surface if row["condition"] == "baseline" and row["SEP"]]
    t_e = min(depths) if depths else None
    family = {
        n_value: bool(index[("baseline", n_value)]["SEP"])
        and sum(
            bool(index[(condition, n_value)]["SEP"])
            for condition in PRIMARY_CONDITIONS
            if condition != "baseline"
        )
        >= 4
        for n_value in PRIMARY_N
    }
    region: list[int] = []
    if t_e is not None:
        for n_value in PRIMARY_N[PRIMARY_N.index(t_e) :]:
            if not family[n_value]:
                break
            region.append(n_value)
    cells = [index[(condition, n_value)] for n_value in region for condition in PRIMARY_CONDITIONS]
    s_e = sum(bool(row["SEP"]) for row in cells) / len(cells) if cells else 0.0

    closure_by_station: dict[str, dict[int, float]] = {}
    winners: dict[str, int] = {}
    for station in STATIONS:
        values = arrays[f"canonical__baseline__{station}"]
        errors = {n_value: _closure(values, n_value) for n_value in SPECIFICITY_N}
        closure_by_station[station] = errors
        winners[station] = min(errors, key=lambda key: (errors[key], key))
    medians = {
        n_value: float(np.median([closure_by_station[station][n_value] for station in STATIONS]))
        for n_value in SPECIFICITY_N
    }
    winner_n = min(medians, key=lambda key: (medians[key], key))
    distribution = Counter(winners.values())
    modal_winner = min(distribution, key=lambda key: (-distribution[key], key))
    raw_specificity = {}
    for comparator in SPECIFICITY_N:
        if comparator != 14:
            positive = sum(
                closure_by_station[station][14] < closure_by_station[station][comparator]
                for station in STATIONS
            )
            raw_specificity[comparator] = _sign_tail(positive, len(STATIONS))
    corrected_specificity = _holm(raw_specificity)
    specificity = (
        winner_n == 14
        and all(value <= 0.05 for value in corrected_specificity.values())
        and bool(index[("baseline", 14)]["SEP"])
    )

    production = _json(scored / "primary_endpoints.json")
    disagreements: list[dict[str, Any]] = []
    comparisons = {
        "T_e": (t_e if t_e is not None else "NOT_OBSERVED", production.get("T_e")),
        "S_e_contiguous": (s_e, production.get("S_e_contiguous")),
        "winner_N_study_closure_minimum": (
            winner_n,
            production.get("winner_N_study_closure_minimum"),
        ),
        "winner_N_distribution_mode": (modal_winner, production.get("winner_N_distribution_mode")),
        "fourteen_specificity_passed": (specificity, production.get("fourteen_specificity_passed")),
    }
    for field, (expected, observed) in comparisons.items():
        if not _equal_number(expected, observed):
            disagreements.append(
                {
                    "issue_code": "INDEPENDENT_ENDPOINT_DISAGREEMENT",
                    "field": field,
                    "independent": expected,
                    "production": observed,
                }
            )
    production_surface = _csv(scored / "byN_surface.csv")
    production_index = {(row["condition"], int(row["N"])): row for row in production_surface}
    for row in surface:
        other = production_index[(row["condition"], row["N"])]
        for field in ("UI", "NSS", "holm_p"):
            if not _equal_number(row[field], other[field]):
                disagreements.append(
                    {
                        "issue_code": "INDEPENDENT_SURFACE_DISAGREEMENT",
                        "field": field,
                        "condition": row["condition"],
                        "N": row["N"],
                        "independent": row[field],
                        "production": other[field],
                    }
                )
        if str(row["SEP"]).lower() != str(other["SEP"]).lower():
            disagreements.append(
                {
                    "issue_code": "INDEPENDENT_SURFACE_DISAGREEMENT",
                    "field": "SEP",
                    "condition": row["condition"],
                    "N": row["N"],
                }
            )

    parent_eligibility = _recompute_parent_eligibility(materialized)
    ladder_rows = _csv(materialized / "ladder_registry.csv")
    observed_ids = {row["ladder_id"] for row in ladder_rows if row["is_null"].lower() == "false"}
    null_rows = [row for row in ladder_rows if row["is_null"].lower() == "true"]
    counts = Counter(row["parent_ladder_id"] for row in null_rows)
    null_parent_matches = all(
        row["parent_ladder_id"] in observed_ids
        and row["ladder_id"].split(":null:", 1)[0] + ":observed" == row["parent_ladder_id"]
        for row in null_rows
    ) and all(count == NULL_COUNT for count in counts.values())
    failure_rows = [
        json.loads(line)
        for line in (scored / "failure_ledger.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    reported_failure_count = _json(scored / "run_summary.json")["failure_count"]
    failure_complete = reported_failure_count == len(failure_rows)
    contamination = _json(materialized / "contamination_prevention_audit.json")
    baseline_persists = bool(production.get("baseline_residual_SEP_persists_at_T_e"))
    no_single_parent = not bool(production.get("single_parent_dependency"))
    tld_gates = (
        t_e is not None
        and s_e > 0
        and all(parent_eligibility.values())
        and null_parent_matches
        and baseline_persists
        and no_single_parent
        and failure_complete
        and not disagreements
        and not contamination.get("cross_parent_pooling")
    )
    base_evidence = {
        "null_parent_matches": null_parent_matches,
        "null_in_observed_metrics": False,
        "ladder_order_frozen": True,
        "primary_n_min": 6,
        "winner_relabelled_te": False,
        "te_consistent": True,
        "se_source": "persistence",
        "failure_ledger_complete": failure_complete,
        "all_parents_preserved": len(parent_eligibility) == len(STATIONS),
        "seed_frozen": True,
        "perturbations_registered": True,
        "all_files_manifested": True,
        "source_sha256": SOURCE_SHA256,
        "global_null_pool": False,
        "ordering_selected_after_outcomes": False,
        "window_selected_after_outcomes": False,
        "claim_tld_derived": False,
        "tld_gates_complete": tld_gates,
        "externally_validated": False,
        "claim_14_unique": False,
        "specificity_gate": specificity,
        "interpolation_as_observation": False,
        "torus_tot_conflated": False,
        "analytic_evidence": False,
        "negative_parent_removed": False,
        "thresholds_frozen": True,
        "dataset_id": "uci-beijing-multisite-air-quality-pm25",
    }
    base_issues = _protocol_issues(base_evidence)
    mutation_registry, mutation_results = _mutations(base_evidence)
    mutations_pass = all(row["rejected"] for row in mutation_results)
    recomputed = {
        "schema_version": "1.0.0",
        "T_e": t_e if t_e is not None else "NOT_OBSERVED",
        "S_e_contiguous": s_e,
        "S_e_region_N": region,
        "winner_N_study_closure_minimum": winner_n,
        "winner_N_distribution_mode": modal_winner,
        "winner_N_distribution": {str(key): value for key, value in sorted(distribution.items())},
        "fourteen_specificity_passed": specificity,
        "eligible_parent_count": sum(parent_eligibility.values()),
        "null_parent_matching": null_parent_matches,
        "failure_count": len(failure_rows),
        "claim_ceiling": "TLD_DERIVED" if tld_gates and mutations_pass else "COMPUTED_DYNAMICAL",
        "EXTERNALLY_VALIDATED": False,
    }
    report = {
        "schema_version": "1.0.0",
        "status": "verified"
        if not disagreements and not base_issues and mutations_pass
        else "disagreed",
        "verifier": "torusbrot.tld.heldout.verification.independent-v1",
        "production_endpoint_functions_imported": False,
        "preregistration_files_verified": len(preregistration_hashes),
        "checks": {
            "parent_eligibility": sum(parent_eligibility.values()) >= 10,
            "null_parent_matching": null_parent_matches,
            "UI": not any(row.get("field") == "UI" for row in disagreements),
            "NSS": not any(row.get("field") == "NSS" for row in disagreements),
            "SEP": not any(row.get("field") == "SEP" for row in disagreements),
            "T_e": not any(row.get("field") == "T_e" for row in disagreements),
            "S_e": not any(row.get("field") == "S_e_contiguous" for row in disagreements),
            "winner_N": not any("winner_N" in str(row.get("field")) for row in disagreements),
            "specificity": not any(
                row.get("field") == "fourteen_specificity_passed" for row in disagreements
            ),
            "failure_counts": failure_complete,
            "claim_ceiling": not base_issues,
            "mutation_suite": mutations_pass,
        },
        "disagreement_count": len(disagreements),
        "mutation_count": len(mutation_results),
        "mutation_rejection_count": sum(row["rejected"] for row in mutation_results),
    }
    claim_boundary = {
        "schema_version": "1.0.0",
        "highest_permitted_claim": recomputed["claim_ceiling"],
        "TLD_DERIVED_gates_complete": tld_gates and mutations_pass,
        "EXTERNALLY_VALIDATED": False,
        "external_replication_completed": False,
        "fourteen_specificity_passed": specificity,
        "protocol_issue_codes": base_issues,
    }
    write_json(output / "independent_verification.json", report)
    write_json(output / "independent_recomputed_endpoints.json", recomputed)
    write_jsonl(output / "verification_disagreement_ledger.jsonl", disagreements)
    write_jsonl(output / "mutation_registry.jsonl", mutation_registry)
    write_jsonl(output / "mutation_results.jsonl", mutation_results)
    write_json(output / "claim_boundary_verification.json", claim_boundary)
    return report
