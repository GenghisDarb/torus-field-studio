"""Preregistration and endpoint adjudication helpers."""

from __future__ import annotations

from typing import Any

from .contracts import HistoricalTldIContract


def preregistration_results(
    alpha0: dict[str, Any], alpha002: dict[str, Any], contract: HistoricalTldIContract
) -> dict[str, bool]:
    rules = contract.preregistration
    return {
        "alpha0_escape_rate_at_least_0.90": alpha0["escape_rate"] >= rules["escape_rate_min"],
        "alpha0_return_rate_at_most_0.40": alpha0["return_rate_given_escape"]
        <= rules["alpha0_return_rate_max"],
        "alpha002_escape_rate_at_least_0.90": alpha002["escape_rate"] >= rules["escape_rate_min"],
        "alpha002_return_rate_at_least_0.95": alpha002["return_rate_given_escape"]
        >= rules["alpha002_return_rate_min"],
        "alpha002_mean_return_steps_at_most_120": alpha002["mean_return_steps"]
        <= rules["alpha002_mean_return_steps_max"],
        "alpha002_p90_flips_at_most_5": alpha002["p90_flips"] <= rules["alpha002_p90_flips_max"],
    }
