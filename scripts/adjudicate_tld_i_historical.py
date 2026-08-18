"""Independently adjudicate the TLD I historical outputs against frozen contracts."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

FLOAT_ABS_TOL = 1e-12
FLOAT_REL_TOL = 1e-12
OUTPUTS = {
    13: [
        "notebook13_core_alpha_compare.csv",
        "notebook13_alpha_sweep.csv",
        "notebook13_prereg_eval.csv",
        "notebook13_run_summary.json",
    ],
    14: [
        "notebook14_config.json",
        "notebook14_pswap_envelope.csv",
        "notebook14_trace_summary.csv",
        "notebook14_trace_trials.csv",
        "notebook14_transition_counts.csv",
    ],
}


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def close(left: float, right: float) -> bool:
    return math.isclose(left, right, abs_tol=FLOAT_ABS_TOL, rel_tol=FLOAT_REL_TOL)


def line_endings(path: Path) -> dict[str, int]:
    data = path.read_bytes()
    return {"crlf": data.count(b"\r\n"), "bare_lf": data.count(b"\n") - data.count(b"\r\n")}


repository = Path.cwd().resolve()
source = (
    repository / "external_cache" / "zenodo" / "18080090" / "quarantine-custody" / "TORUS_Zenodo_v1"
)
historical = repository / "results" / "tld-i" / "historical"
contracts = repository / "results" / "tld-i" / "contracts"

contract_hashes = {}
for line in (contracts / "SHA256SUMS_CONTRACTS.txt").read_text(encoding="utf-8").splitlines():
    expected, name = line.split(maxsplit=1)
    actual = sha256(contracts / name.strip())
    if actual != expected:
        raise RuntimeError(f"Frozen contract changed: {name}")
    contract_hashes[name.strip()] = actual

comparisons = []
all_semantic_exact = True
for number, names in OUTPUTS.items():
    published_root = source / f"data_outputs_notebook{number}"
    generated_root = historical / f"notebook{number}" / "workspace"
    for name in names:
        published = published_root / name
        generated = generated_root / name
        if name.endswith(".csv"):
            published_value = read_csv(published)
            generated_value = read_csv(generated)
            semantic_exact = published_value == generated_value
            comparison_rule = "exact header, row order, membership, and serialized field values"
        else:
            published_value = json.loads(published.read_text(encoding="utf-8"))
            generated_value = json.loads(generated.read_text(encoding="utf-8"))
            excluded = []
            if name == "notebook13_run_summary.json":
                published_value.pop("timestamp_utc", None)
                generated_value.pop("timestamp_utc", None)
                excluded = ["timestamp_utc"]
            semantic_exact = published_value == generated_value
            comparison_rule = (
                f"exact parsed JSON excluding {excluded}" if excluded else "exact parsed JSON"
            )
        byte_identical = sha256(published) == sha256(generated)
        all_semantic_exact &= semantic_exact
        comparisons.append(
            {
                "notebook": number,
                "name": name,
                "published_bytes": published.stat().st_size,
                "generated_bytes": generated.stat().st_size,
                "published_sha256": sha256(published),
                "generated_sha256": sha256(generated),
                "byte_identical": byte_identical,
                "semantic_exact": semantic_exact,
                "comparison_rule": comparison_rule,
                "published_line_endings": line_endings(published),
                "generated_line_endings": line_endings(generated),
            }
        )

# Independent baseline calculation from raw CSV bytes, without notebook functions.
baseline_rows = read_csv(source / "data_inputs" / "targets_baseline.csv")
values = [float(row["value"]) for row in baseline_rows]
sigmas = [float(row["sigma"]) for row in baseline_rows]
omega = [math.log(value) for value in values]
chi = sum(value / index for index, value in enumerate(omega, start=1))


def score(n_values: list[int]) -> dict[str, Any]:
    rows = sorted(((n, abs(chi - (2.0 * math.pi / n))) for n in n_values), key=lambda item: item[1])
    return {
        "winner_N": rows[0][0],
        "winner_RMS": rows[0][1],
        "runner_N": rows[1][0],
        "runner_RMS": rows[1][1],
        "margin": rows[1][1] - rows[0][1],
    }


baseline_sweep = score(list(range(2, 31)))
baseline_window = score(list(range(7, 14)))
generated_summary = json.loads(
    (historical / "notebook13" / "workspace" / "notebook13_run_summary.json").read_text(
        encoding="utf-8"
    )
)
baseline_reported = generated_summary["baseline"]
baseline_checks = {
    "chi": close(chi, float(baseline_reported["chi0"])),
    "winner_N": baseline_sweep["winner_N"] == int(baseline_reported["winnerN_sweep2to30"]),
    "winner_RMS": close(
        baseline_sweep["winner_RMS"], float(baseline_reported["winnerR_sweep2to30"])
    ),
    "window_margin": close(
        baseline_window["margin"], float(baseline_reported["baseline_window_margin_7to13"])
    ),
}
if not all(baseline_checks.values()):
    raise RuntimeError(f"Independent baseline mismatch: {baseline_checks}")

# Notebook 13 rates and preregistration criteria are independently recomputed from counts.
core = read_csv(historical / "notebook13" / "workspace" / "notebook13_core_alpha_compare.csv")
alpha_sweep = read_csv(historical / "notebook13" / "workspace" / "notebook13_alpha_sweep.csv")
core_by_alpha = {float(row["alpha_heal"]): row for row in core}
rate_checks = []
for row in core + alpha_sweep:
    trials = int(row["trials"])
    escaped = int(row["escaped_count"])
    returned = int(row["returned_count"])
    rate_checks.append(
        {
            "alpha": float(row["alpha_heal"]),
            "trials": trials,
            "escape_rate_valid": close(float(row["escape_rate"]), escaped / trials),
            "return_rate_valid": close(float(row["return_rate_given_escape"]), returned / escaped),
            "competitor_counts_parse": isinstance(ast.literal_eval(row["competitors"]), dict),
        }
    )
if not all(
    all(value for key, value in row.items() if key.endswith("valid") or key.endswith("parse"))
    for row in rate_checks
):
    raise RuntimeError("Notebook 13 count/rate integrity failed")

alpha0 = core_by_alpha[0.0]
alpha002 = core_by_alpha[0.02]
preregistered = {
    "alpha0_escape_rate_at_least_0.90": float(alpha0["escape_rate"]) >= 0.90,
    "alpha0_return_rate_at_most_0.40": float(alpha0["return_rate_given_escape"]) <= 0.40,
    "alpha002_escape_rate_at_least_0.90": float(alpha002["escape_rate"]) >= 0.90,
    "alpha002_return_rate_at_least_0.95": float(alpha002["return_rate_given_escape"]) >= 0.95,
    "alpha002_mean_return_steps_at_most_120": float(alpha002["mean_return_steps"]) <= 120,
    "alpha002_p90_flips_at_most_5": float(alpha002["p90_flips"]) <= 5,
}
published_prereg_rows = read_csv(source / "data_outputs_notebook13" / "notebook13_prereg_eval.csv")
generated_prereg_rows = read_csv(
    historical / "notebook13" / "workspace" / "notebook13_prereg_eval.csv"
)

# Notebook 14 trace quality and independent endpoint reconstruction.
trace_rows = read_csv(historical / "notebook14" / "workspace" / "notebook14_trace_trials.csv")
trace_summary = read_csv(historical / "notebook14" / "workspace" / "notebook14_trace_summary.csv")
transition_rows = read_csv(
    historical / "notebook14" / "workspace" / "notebook14_transition_counts.csv"
)
config = json.loads(
    (historical / "notebook14" / "workspace" / "notebook14_config.json").read_text(encoding="utf-8")
)
margin_lock = float(config["BASELINE_MIN_MARGIN"])
grouped: dict[int, list[dict[str, str]]] = {}
for row in trace_rows:
    grouped.setdefault(int(row["trial_id"]), []).append(row)

recomputed_summaries = []
transition_counts: Counter[tuple[float, int, int]] = Counter()
flips_by_alpha: dict[float, list[int]] = {}
for trial_id, rows in sorted(grouped.items()):
    rows.sort(key=lambda row: ({"start": 0, "escape": 1, "heal": 2}[row["phase"]], int(row["t"])))
    start = [row for row in rows if row["phase"] == "start"]
    escape = [row for row in rows if row["phase"] == "escape"]
    heal = [row for row in rows if row["phase"] == "heal"]
    if len(start) != 1:
        raise RuntimeError(f"Trace trial {trial_id} does not have one start row")
    escaped = bool(escape) and not (
        int(escape[-1]["winner_N"]) == 10 and float(escape[-1]["margin"]) >= margin_lock
    )
    returned = (
        bool(heal) and int(heal[-1]["winner_N"]) == 10 and float(heal[-1]["margin"]) >= margin_lock
    )
    alpha = float(rows[0]["alpha_heal"])
    sequence = [int(row["winner_N"]) for row in sorted(heal, key=lambda row: int(row["t"]))]
    flips = sum(left != right for left, right in zip(sequence[:-1], sequence[1:]))
    flips_by_alpha.setdefault(alpha, []).append(flips)
    for left, right in zip(sequence[:-1], sequence[1:]):
        transition_counts[(alpha, left, right)] += 1
    recomputed_summaries.append(
        {
            "trial_id": str(trial_id),
            "alpha_heal": str(alpha),
            "seed": rows[0]["seed"],
            "escaped": str(escaped),
            "escape_steps": escape[-1]["t"] if escaped else "",
            "returned": str(returned),
            "return_steps": heal[-1]["t"] if returned else "",
        }
    )

summary_by_trial = {int(row["trial_id"]): row for row in trace_summary}
summary_matches = True
for recomputed in recomputed_summaries:
    reported = summary_by_trial[int(recomputed["trial_id"])]
    summary_matches &= all(reported[key] == value for key, value in recomputed.items())
reported_transitions = {
    (float(row["alpha_heal"]), int(row["from_N"]), int(row["to_N"])): int(row["count"])
    for row in transition_rows
}
transitions_match = dict(transition_counts) == reported_transitions
if not summary_matches or not transitions_match:
    raise RuntimeError("Notebook 14 independent trace verification failed")


def percentile90(values: list[int]) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * 0.9
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


trajectory_diagnostics = {}
for alpha, flips in sorted(flips_by_alpha.items()):
    matching = [row for row in trace_summary if close(float(row["alpha_heal"]), alpha)]
    return_steps = [int(row["return_steps"]) for row in matching if row["returned"] == "True"]
    trajectory_diagnostics[str(alpha)] = {
        "trials": len(matching),
        "all_escaped": all(row["escaped"] == "True" for row in matching),
        "all_returned": all(row["returned"] == "True" for row in matching),
        "mean_return_steps": statistics.fmean(return_steps),
        "median_return_steps": statistics.median(return_steps),
        "total_winner_state_transitions": sum(flips),
        "mean_winner_state_transitions": statistics.fmean(flips),
        "p90_winner_state_transitions": percentile90(flips),
    }

envelope = read_csv(historical / "notebook14" / "workspace" / "notebook14_pswap_envelope.csv")
envelope_summary = [
    {
        "p_swap_escape": float(row["p_swap_escape"]),
        "escape_rate": float(row["escape_rate"]),
        "return_rate_given_escape": float(row["return_rate_given_escape"]),
        "mean_return_steps": float(row["mean_return_steps"]),
        "p90_flips": float(row["p90_flips"]),
    }
    for row in envelope
]

data_quality = {
    "schema_version": "1.0.0",
    "assessed_at": datetime.now(UTC).isoformat(),
    "dataset_grain": {
        "baseline": "one row per ordered ladder rung",
        "notebook13_core": "one row per core alpha condition",
        "notebook13_sweep": "one row per alpha condition",
        "notebook14_trace": "one row per trial/phase/step",
        "notebook14_transition": "one row per alpha/from_N/to_N pair",
        "notebook14_envelope": "one row per p_swap condition",
    },
    "checks": {
        "baseline_rows": len(baseline_rows),
        "baseline_required_values_complete": all(
            row["value"] and row["sigma"] for row in baseline_rows
        ),
        "baseline_values_positive": all(value > 0 for value in values),
        "baseline_sigmas_nonnegative": all(value >= 0 for value in sigmas),
        "baseline_exact_duplicate_rows": len(baseline_rows)
        - len({tuple(row.items()) for row in baseline_rows}),
        "trace_rows": len(trace_rows),
        "trace_trials": len(grouped),
        "trace_composite_key_unique": len(trace_rows)
        == len({(row["trial_id"], row["phase"], row["t"]) for row in trace_rows}),
        "trace_allowed_phases": sorted({row["phase"] for row in trace_rows})
        == ["escape", "heal", "start"],
        "trace_required_fields_complete": all(
            all(value != "" for value in row.values()) for row in trace_rows
        ),
        "trace_summary_recomputed_exact": summary_matches,
        "transition_counts_recomputed_exact": transitions_match,
        "output_semantics_match_published": all_semantic_exact,
    },
    "issues": [
        {
            "severity": "high",
            "code": "HISTORICAL_MAX_HEAL_STEPS_DECLARATION_MISMATCH",
            "evidence": "PREREG_CRITERIA.md declares 400; Notebook 13 executes 300",
            "impact": "the stopping horizon can affect return-rate and step-distribution endpoints",
        },
        {
            "severity": "medium",
            "code": "HISTORICAL_ENVIRONMENT_NOT_EXACTLY_PINNED",
            "evidence": "requirements use lower bounds and the environment report lists ranges",
            "impact": (
                "future byte-level reproduction is not guaranteed even though this run is "
                "semantically exact"
            ),
        },
        {
            "severity": "low",
            "code": "SERIALIZATION_LINE_ENDINGS_DIFFER",
            "evidence": "published files use LF and the Windows run uses CRLF",
            "impact": "hashes differ; parsed values, headers, row order, and membership are exact",
        },
    ],
    "confidence": "ready_to_share_with_explicit_claim_caveats",
}

classification = (
    "EXACT_REPRODUCTION"
    if all_semantic_exact
    and all(baseline_checks.values())
    and summary_matches
    and transitions_match
    else "NONREPRODUCTION"
)
if classification != "EXACT_REPRODUCTION":
    raise RuntimeError("Historical outputs did not meet the frozen reproduction comparison")

summary = {
    "schema_version": "1.0.0",
    "adjudicated_at": datetime.now(UTC).isoformat(),
    "classification": classification,
    "high_level_outcome": "FIRST_PUBLISHED_TLD_RESULT_EXACTLY_REPRODUCED",
    "notebook13_classification": classification,
    "notebook14_classification": classification,
    "comparison_scope": (
        "exact parsed outputs under the pre-execution contract; timestamps excluded and line "
        "endings normalized"
    ),
    "byte_identical_outputs": False,
    "byte_difference_reason": (
        "Windows CRLF serialization for all outputs, plus the intentionally new Notebook 13 "
        "timestamp"
    ),
    "baseline": {
        "chi": chi,
        "winner_N": baseline_sweep["winner_N"],
        "winner_RMS": baseline_sweep["winner_RMS"],
        "runner_N": baseline_sweep["runner_N"],
        "runner_RMS": baseline_sweep["runner_RMS"],
        "margin": baseline_sweep["margin"],
        "window_7_13_margin": baseline_window["margin"],
        "independently_recomputed": True,
    },
    "notebook13": {
        "core": [
            {
                "alpha": float(row["alpha_heal"]),
                "trials": int(row["trials"]),
                "escape_rate": float(row["escape_rate"]),
                "return_rate_given_escape": float(row["return_rate_given_escape"]),
                "mean_return_steps": float(row["mean_return_steps"]),
                "p90_flips": float(row["p90_flips"]),
            }
            for row in core
        ],
        "alpha_sweep": [
            {
                "alpha": float(row["alpha_heal"]),
                "escape_rate": float(row["escape_rate"]),
                "return_rate_given_escape": float(row["return_rate_given_escape"]),
                "mean_return_steps": float(row["mean_return_steps"]),
                "p90_flips": float(row["p90_flips"]),
            }
            for row in alpha_sweep
        ],
        "preregistered_criteria": preregistered,
        "preregistered_pass_count": sum(preregistered.values()),
        "preregistered_criterion_count": len(preregistered),
        "published_prereg_table_exact": published_prereg_rows == generated_prereg_rows,
    },
    "notebook14": {
        "trajectory_diagnostics": trajectory_diagnostics,
        "transition_counts_recomputed_exact": transitions_match,
        "operating_envelope": envelope_summary,
    },
    "reproduction_blockers": [],
    "claim_blockers": [
        "Notebook 13 alpha=0.02 mean_return_steps exceeds the preregistered maximum",
        "Notebook 13 alpha=0.02 p90_flips exceeds the preregistered maximum",
        "PREREG_CRITERIA.md and executable Notebook 13 disagree on max_heal_steps",
        "This is self-reproduction of a published project release, not external validation",
    ],
    "historical_claim_level": "COMPUTED_DYNAMICAL",
    "tld_derived_status": "NOT_YET_ADJUDICATED_FOR_MODERN_LANE",
    "externally_validated": False,
    "frozen_contract_hashes": contract_hashes,
}

write_json(historical / "historical_output_comparison.json", comparisons)
write_json(historical / "historical_data_quality.json", data_quality)
write_json(historical / "historical_reproduction_summary.json", summary)

# Refresh the historical checksum ledger after adjudication artifacts are added.
checksum_path = historical / "SHA256SUMS_HISTORICAL.txt"
checksum_lines = []
for path in sorted(
    item for item in historical.rglob("*") if item.is_file() and item != checksum_path
):
    checksum_lines.append(f"{sha256(path)}  {path.relative_to(historical).as_posix()}")
checksum_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2, sort_keys=True))
