"""Escape, recovery, and trace execution for the registered historical operators."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Any

import numpy as np

from .perturbations import anchor, value_noise
from .ringing import p90, winner_flips
from .scoring import FloatArray, is_closed, score_ladder

Mutation = Callable[[FloatArray, float, np.random.Generator], FloatArray]


def run_summary(
    *,
    omega0: FloatArray,
    sigma_omega: FloatArray,
    n_window: tuple[int, ...],
    center: int,
    minimum_margin: float,
    mutation: Mutation,
    p_swap: float,
    epsilon: float,
    alpha: float,
    trials: int,
    max_escape_steps: int,
    max_heal_steps: int,
    rng: np.random.Generator,
) -> dict[str, Any]:
    escaped_count = 0
    returned_count = 0
    escape_steps: list[int] = []
    return_steps: list[int] = []
    flips: list[int] = []
    competitors: Counter[int] = Counter()
    for _ in range(trials):
        omega = omega0.copy()
        escaped = False
        for step in range(1, max_escape_steps + 1):
            omega = mutation(omega, p_swap, rng)
            if not is_closed(
                score_ladder(omega, n_window), center=center, minimum_margin=minimum_margin
            ):
                escaped = True
                escaped_count += 1
                escape_steps.append(step)
                break
        if not escaped:
            continue
        winner_sequence: list[int] = []
        returned = False
        for step in range(1, max_heal_steps + 1):
            omega = value_noise(omega, epsilon, sigma_omega, rng)
            omega = anchor(omega, omega0, alpha)
            current = score_ladder(omega, n_window)
            winner_sequence.append(current.winner_N)
            if current.winner_N != center:
                competitors[current.winner_N] += 1
            if is_closed(current, center=center, minimum_margin=minimum_margin):
                returned = True
                returned_count += 1
                return_steps.append(step)
                break
        flips.append(winner_flips(winner_sequence))
        if not returned:
            continue
    return {
        "trials": trials,
        "escaped_count": escaped_count,
        "returned_count": returned_count,
        "escape_rate": escaped_count / trials,
        "return_rate_given_escape": returned_count / escaped_count if escaped_count else 0.0,
        "mean_escape_steps": float(np.mean(escape_steps)) if escape_steps else float("inf"),
        "mean_return_steps": float(np.mean(return_steps)) if return_steps else float("inf"),
        "mean_flips": float(np.mean(flips)) if flips else float("inf"),
        "p90_flips": p90(flips),
        "competitors": {str(key): count for key, count in competitors.items()},
        "raw": {
            "escape_steps": escape_steps,
            "return_steps": return_steps,
            "flips": flips,
        },
    }


def run_trace(
    *,
    omega0: FloatArray,
    sigma_omega: FloatArray,
    n_window: tuple[int, ...],
    center: int,
    minimum_margin: float,
    mutation: Mutation,
    p_swap: float,
    epsilon: float,
    alpha: float,
    max_escape_steps: int,
    max_heal_steps: int,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    omega = omega0.copy()

    def append(phase: str, step: int) -> None:
        score = score_ladder(omega, n_window)
        rows.append(
            {
                "phase": phase,
                "t": step,
                "chi": score.chi,
                "winner_N": score.winner_N,
                "winner_rms": score.winner_rms,
                "runner_N": score.runner_N,
                "runner_rms": score.runner_rms,
                "margin": score.margin,
            }
        )

    append("start", 0)
    escaped = False
    escape_step = None
    for step in range(1, max_escape_steps + 1):
        omega = mutation(omega, p_swap, rng)
        append("escape", step)
        current = score_ladder(omega, n_window)
        if not is_closed(current, center=center, minimum_margin=minimum_margin):
            escaped = True
            escape_step = step
            break
    returned = False
    return_step = None
    if escaped:
        for step in range(1, max_heal_steps + 1):
            omega = value_noise(omega, epsilon, sigma_omega, rng)
            omega = anchor(omega, omega0, alpha)
            append("heal", step)
            current = score_ladder(omega, n_window)
            if is_closed(current, center=center, minimum_margin=minimum_margin):
                returned = True
                return_step = step
                break
    return {
        "escaped": escaped,
        "escape_steps": escape_step,
        "returned": returned,
        "return_steps": return_step,
        "trace": rows,
    }
