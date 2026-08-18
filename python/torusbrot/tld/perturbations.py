"""Historical and modern structural perturbation operators."""

from __future__ import annotations

import numpy as np

from .scoring import FloatArray


def adjacent_order_mutation(
    omega: FloatArray, p_swap: float, rng: np.random.Generator
) -> FloatArray:
    result = omega.copy()
    for index in range(len(result) - 1):
        if rng.random() < p_swap:
            result[index], result[index + 1] = result[index + 1], result[index]
    return result


def global_order_mutation(omega: FloatArray, p_swap: float, rng: np.random.Generator) -> FloatArray:
    result = omega.copy()
    for index in range(len(result)):
        if rng.random() < p_swap:
            other = int(rng.integers(0, len(result)))
            result[index], result[other] = result[other], result[index]
    return result


def value_noise(
    omega: FloatArray,
    epsilon: float,
    sigma_omega: FloatArray,
    rng: np.random.Generator,
) -> FloatArray:
    return omega + epsilon * sigma_omega * rng.standard_normal(len(omega))


def anchor(omega: FloatArray, reference: FloatArray, alpha: float) -> FloatArray:
    return omega if alpha <= 0 else (1.0 - alpha) * omega + alpha * reference


def matched_multiset_control(values: FloatArray, seed: int) -> FloatArray:
    rng = np.random.default_rng(seed)
    return values[rng.permutation(len(values))]
