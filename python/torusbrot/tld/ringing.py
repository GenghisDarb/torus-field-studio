"""Ringing and winner-state transition endpoints."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

import numpy as np


def winner_flips(sequence: Iterable[int]) -> int:
    values = tuple(sequence)
    return sum(left != right for left, right in zip(values[:-1], values[1:]))


def p90(values: Iterable[int]) -> float:
    materialized = tuple(values)
    return float(np.percentile(materialized, 90)) if materialized else float("inf")


def transition_counts(sequence: Iterable[int]) -> Counter[tuple[int, int]]:
    values = tuple(sequence)
    return Counter(zip(values[:-1], values[1:]))
