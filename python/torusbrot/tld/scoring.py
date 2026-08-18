"""Ladder materialization and closure scoring."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class ClosureScore:
    chi: float
    winner_N: int
    winner_rms: float
    runner_N: int
    runner_rms: float
    margin: float
    rms_by_N: dict[int, float]

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["rms_by_N"] = {str(key): score for key, score in self.rms_by_N.items()}
        return value


def materialize_ladder(
    values: Iterable[float], sigmas: Iterable[float]
) -> tuple[FloatArray, FloatArray]:
    value_array = np.asarray(tuple(values), dtype=np.float64)
    sigma_array = np.asarray(tuple(sigmas), dtype=np.float64)
    if value_array.size < 4 or value_array.shape != sigma_array.shape:
        raise ValueError("TLD ladder requires at least four aligned value/sigma rows")
    if not np.all(np.isfinite(value_array)) or not np.all(value_array > 0):
        raise ValueError("TLD ladder values must be finite and positive")
    if not np.all(np.isfinite(sigma_array)) or not np.all(sigma_array >= 0):
        raise ValueError("TLD ladder sigmas must be finite and nonnegative")
    return np.log(value_array), sigma_array / value_array


def score_ladder(omega: FloatArray, n_values: Iterable[int]) -> ClosureScore:
    weights = 1.0 / np.arange(1, len(omega) + 1, dtype=np.float64)
    chi = float(np.sum(weights * omega))
    rms_by_n = {int(n): float(abs(chi - (2.0 * math.pi / int(n)))) for n in n_values}
    ordered = sorted(rms_by_n.items(), key=lambda item: item[1])
    winner, runner = ordered[:2]
    return ClosureScore(
        chi=chi,
        winner_N=winner[0],
        winner_rms=winner[1],
        runner_N=runner[0],
        runner_rms=runner[1],
        margin=float(runner[1] - winner[1]),
        rms_by_N=rms_by_n,
    )


def is_closed(score: ClosureScore, *, center: int, minimum_margin: float) -> bool:
    return score.winner_N == center and score.margin >= minimum_margin
