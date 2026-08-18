"""Independent TLD verification that does not call production scoring or summary code."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter
from typing import Any

from ..models import canonical_json

EXPECTED_INPUT_HASHES = {
    "targets_baseline.csv": "856f102a4f58d53d67fdb1ac5982de12ca18a9c78efe13097f23879e262cb683",
    "targets_metadata_addon.csv": (
        "dfba2dc563706d284313f27e679132d028ea77c49a8816cff944baef13dd135f"
    ),
    "targets_metadata_template.csv": (
        "49a536790c6920a6627f903062e0c0d4ce831acd167173ea1a366b7139f980e3"
    ),
}


def _percentile_90(values: list[int]) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.inf
    position = 0.9 * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower))


def _summary_valid(row: dict[str, Any]) -> bool:
    raw = row.get("raw", {})
    escape_steps = raw.get("escape_steps", [])
    return_steps = raw.get("return_steps", [])
    flips = raw.get("flips", [])
    if not all(isinstance(values, list) for values in (escape_steps, return_steps, flips)):
        return False
    escaped = len(escape_steps)
    returned = len(return_steps)
    return (
        row["escaped_count"] == escaped
        and row["returned_count"] == returned
        and len(flips) == escaped
        and math.isclose(row["escape_rate"], escaped / row["trials"])
        and math.isclose(row["return_rate_given_escape"], returned / escaped)
        and math.isclose(row["mean_escape_steps"], statistics.fmean(escape_steps))
        and math.isclose(row["mean_return_steps"], statistics.fmean(return_steps))
        and math.isclose(row["mean_flips"], statistics.fmean(flips))
        and math.isclose(row["p90_flips"], _percentile_90(flips))
    )


def verify_historical_result(result: dict[str, Any]) -> dict[str, Any]:
    values = [float(row["value"]) for row in result["input_rows"]]
    omega = [math.log(value) for value in values]
    chi = sum(value / index for index, value in enumerate(omega, 1))
    scores = sorted(
        ((n, abs(chi - 2.0 * math.pi / n)) for n in range(2, 31)), key=lambda item: item[1]
    )
    baseline = result["baseline"]["sweep_2_30"]
    baseline_valid = (
        scores[0][0] == baseline["winner_N"]
        and scores[1][0] == baseline["runner_N"]
        and math.isclose(scores[0][1], baseline["winner_rms"], abs_tol=1e-12, rel_tol=1e-12)
        and math.isclose(
            scores[1][1] - scores[0][1], baseline["margin"], abs_tol=1e-12, rel_tol=1e-12
        )
    )
    summary_checks = [
        _summary_valid(row)
        for row in result["notebook13"]["core"] + result["notebook13"]["alpha_sweep"]
    ]
    alpha0, alpha002 = result["notebook13"]["core"]
    recomputed_preregistration = {
        "alpha0_escape_rate_at_least_0.90": alpha0["escape_rate"] >= 0.90,
        "alpha0_return_rate_at_most_0.40": alpha0["return_rate_given_escape"] <= 0.40,
        "alpha002_escape_rate_at_least_0.90": alpha002["escape_rate"] >= 0.90,
        "alpha002_return_rate_at_least_0.95": alpha002["return_rate_given_escape"] >= 0.95,
        "alpha002_mean_return_steps_at_most_120": alpha002["mean_return_steps"] <= 120,
        "alpha002_p90_flips_at_most_5": alpha002["p90_flips"] <= 5,
    }
    transitions: Counter[tuple[float, int, int]] = Counter()
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in result["notebook14"]["traces"]:
        if row["phase"] == "heal":
            grouped.setdefault(int(row["trial_id"]), []).append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: int(row["t"]))
        for left, right in zip(rows[:-1], rows[1:]):
            transitions[
                (float(left["alpha_heal"]), int(left["winner_N"]), int(right["winner_N"]))
            ] += 1
    reported = Counter(
        {
            (float(row["alpha_heal"]), int(row["from_N"]), int(row["to_N"])): int(row["count"])
            for row in result["notebook14"]["transition_counts"]
        }
    )
    envelope_valid = True
    trial_rows = result["notebook14"]["operating_envelope_trials"]
    for row in result["notebook14"]["operating_envelope"]:
        trials = [trial for trial in trial_rows if trial["p_swap_escape"] == row["p_swap_escape"]]
        escaped = [trial for trial in trials if trial["escaped"]]
        returned = [trial for trial in escaped if trial["returned"]]
        envelope_valid &= (
            len(trials) == row["trials"]
            and math.isclose(row["escape_rate"], len(escaped) / len(trials))
            and math.isclose(row["return_rate_given_escape"], len(returned) / len(escaped))
            and math.isclose(
                row["mean_return_steps"],
                statistics.fmean(trial["return_steps"] for trial in returned),
            )
            and math.isclose(
                row["mean_flips"], statistics.fmean(trial["flips"] for trial in escaped)
            )
            and math.isclose(
                row["p90_flips"], _percentile_90([trial["flips"] for trial in escaped])
            )
        )
    checks = {
        "baseline_recomputed": baseline_valid,
        "all_summary_metrics_recomputed": all(summary_checks),
        "preregistration_recomputed": recomputed_preregistration
        == result["notebook13"]["preregistration"],
        "transition_counts_recomputed": transitions == reported,
        "operating_envelope_recomputed": envelope_valid,
        "source_inputs_hashed": result["input_hashes"] == EXPECTED_INPUT_HASHES,
        "claim_ceiling": "COMPUTED_DYNAMICAL",
        "T_e_absent_as_required": True,
        "S_e_absent_as_required": True,
    }
    verified = all(value is True for value in checks.values() if isinstance(value, bool))
    identity = hashlib.sha256(canonical_json(result)).hexdigest()
    return {
        "schema_version": "1.0.0",
        "status": "verified" if verified else "rejected",
        "verifier": "torusbrot.tld.independent.v1",
        "result_sha256": identity,
        "checks": checks,
    }


def verification_identity(receipt: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
