"""Production TLD I reproduction independent of notebook imports and outputs."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any

import numpy as np

from .contracts import HistoricalTldIContract
from .endpoints import preregistration_results
from .perturbations import adjacent_order_mutation, global_order_mutation
from .recovery import run_summary, run_trace
from .registry import build_registries
from .ringing import transition_counts, winner_flips
from .scoring import materialize_ladder, score_ladder


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_inputs(source_root: Path) -> tuple[list[dict[str, str]], dict[str, str]]:
    inputs = source_root / "data_inputs"
    names = ("targets_baseline.csv", "targets_metadata_template.csv", "targets_metadata_addon.csv")
    hashes = {name: _sha256(inputs / name) for name in names}
    with (inputs / names[0]).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    return rows, hashes


def reproduce_tld_i(
    source_root: str | Path, contract: HistoricalTldIContract | None = None
) -> dict[str, Any]:
    contract = contract or HistoricalTldIContract()
    root = Path(source_root)
    rows, input_hashes = _load_inputs(root)
    values = [float(row["value"]) for row in rows]
    sigmas = [float(row["sigma"]) for row in rows]
    omega0, sigma_omega = materialize_ladder(values, sigmas)
    baseline_sweep = score_ladder(omega0, range(2, 31))
    baseline_window = score_ladder(omega0, contract.n_window)
    registries = build_registries(
        baseline_sha256=input_hashes["targets_baseline.csv"],
        values_sha256=hashlib.sha256(omega0.tobytes()).hexdigest(),
        contract=contract,
    )

    rng = np.random.default_rng(contract.seed)
    np.random.seed(contract.seed)
    summary_arguments = {
        "omega0": omega0,
        "sigma_omega": sigma_omega,
        "n_window": contract.n_window,
        "center": contract.n_center,
        "minimum_margin": baseline_window.margin,
        "mutation": adjacent_order_mutation,
        "p_swap": contract.p_swap_escape,
        "epsilon": contract.epsilon_heal,
        "max_escape_steps": contract.max_escape_steps,
        "max_heal_steps": contract.max_heal_steps_notebook13,
        "rng": rng,
    }
    core = [
        {
            "alpha_heal": alpha,
            **run_summary(
                **summary_arguments,
                alpha=alpha,
                trials=contract.core_trials,
            ),
        }
        for alpha in (0.0, 0.02)
    ]
    alpha_sweep = [
        {
            "alpha_heal": alpha,
            **run_summary(
                **summary_arguments,
                alpha=alpha,
                trials=contract.alpha_sweep_trials,
            ),
        }
        for alpha in contract.alpha_sweep
    ]
    preregistration = preregistration_results(core[0], core[1], contract)

    traces: list[dict[str, Any]] = []
    trace_summaries: list[dict[str, Any]] = []
    trial_id = 0
    for alpha in contract.trace_alphas:
        for index in range(contract.notebook14_trace_trials):
            trial_id += 1
            seed = 1000 + 100 * int(alpha * 100) + index
            trace = run_trace(
                omega0=omega0,
                sigma_omega=sigma_omega,
                n_window=contract.n_window,
                center=contract.n_center,
                minimum_margin=baseline_window.margin,
                mutation=global_order_mutation,
                p_swap=contract.p_swap_escape,
                epsilon=contract.epsilon_heal,
                alpha=alpha,
                max_escape_steps=contract.max_escape_steps,
                max_heal_steps=contract.max_heal_steps_notebook14,
                seed=seed,
            )
            for row in trace["trace"]:
                traces.append(row | {"trial_id": trial_id, "alpha_heal": alpha, "seed": seed})
            trace_summaries.append(
                {
                    "trial_id": trial_id,
                    "alpha_heal": alpha,
                    "seed": seed,
                    "escaped": trace["escaped"],
                    "escape_steps": trace["escape_steps"],
                    "returned": trace["returned"],
                    "return_steps": trace["return_steps"],
                }
            )

    transition_rows = []
    for alpha in contract.trace_alphas:
        counts: dict[tuple[int, int], int] = {}
        for summary in (row for row in trace_summaries if row["alpha_heal"] == alpha):
            sequence = [
                int(row["winner_N"])
                for row in traces
                if row["trial_id"] == summary["trial_id"] and row["phase"] == "heal"
            ]
            for pair, count in transition_counts(sequence).items():
                counts[pair] = counts.get(pair, 0) + count
        transition_rows.extend(
            {
                "alpha_heal": alpha,
                "from_N": pair[0],
                "to_N": pair[1],
                "count": count,
            }
            for pair, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
        )

    envelope = []
    envelope_trials: list[dict[str, Any]] = []
    for p_swap in contract.envelope_p_swap:
        summaries = []
        for index in range(contract.notebook14_envelope_trials):
            seed0 = 12000 + int(p_swap * 100000)
            trial = run_trace(
                omega0=omega0,
                sigma_omega=sigma_omega,
                n_window=contract.n_window,
                center=contract.n_center,
                minimum_margin=baseline_window.margin,
                mutation=global_order_mutation,
                p_swap=p_swap,
                epsilon=contract.epsilon_heal,
                alpha=0.02,
                max_escape_steps=contract.max_escape_steps,
                max_heal_steps=contract.max_heal_steps_notebook14,
                seed=seed0 + index,
            )
            summaries.append(trial)
            envelope_trials.append(
                {
                    "p_swap_escape": p_swap,
                    "seed": seed0 + index,
                    "escaped": trial["escaped"],
                    "escape_steps": trial["escape_steps"],
                    "returned": trial["returned"],
                    "return_steps": trial["return_steps"],
                    "flips": winner_flips(
                        int(row["winner_N"]) for row in trial["trace"] if row["phase"] == "heal"
                    ),
                }
            )
        escaped = [item for item in summaries if item["escaped"]]
        returned = [item for item in escaped if item["returned"]]
        flips = [
            winner_flips(int(row["winner_N"]) for row in item["trace"] if row["phase"] == "heal")
            for item in escaped
        ]
        envelope.append(
            {
                "trials": len(summaries),
                "p_swap_escape": p_swap,
                "eps_heal": contract.epsilon_heal,
                "alpha_heal": 0.02,
                "escape_rate": len(escaped) / len(summaries),
                "return_rate_given_escape": len(returned) / len(escaped),
                "mean_return_steps": float(np.mean([item["return_steps"] for item in returned])),
                "mean_flips": float(np.mean(flips)),
                "p90_flips": float(np.percentile(flips, 90)),
            }
        )

    return {
        "schema_version": "1.0.0",
        "contract": contract.to_dict() | {"sha256": contract.sha256},
        "input_hashes": input_hashes,
        "input_rows": rows,
        "registries": registries,
        "baseline": {
            "sweep_2_30": baseline_sweep.to_dict(),
            "window_7_13": baseline_window.to_dict(),
        },
        "notebook13": {
            "core": core,
            "alpha_sweep": alpha_sweep,
            "preregistration": preregistration,
        },
        "notebook14": {
            "traces": traces,
            "trace_summary": trace_summaries,
            "transition_counts": transition_rows,
            "operating_envelope": envelope,
            "operating_envelope_trials": envelope_trials,
        },
    }
