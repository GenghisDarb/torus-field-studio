from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Any

import numpy as np
from numpy.typing import NDArray

from torusbrot.geometry.metrology import interior_relative_curvature, robust_scale
from torusbrot.geometry.models import SeparationResult

FloatArray = NDArray[np.float64]


def _scalar_field(field: FloatArray) -> FloatArray:
    array = np.asarray(field, dtype=np.float64)
    if array.ndim >= 3 and array.shape[-1] in {2, 3}:
        array = np.linalg.norm(array, axis=-1)
    while array.ndim > 2:
        array = np.mean(array, axis=0)
    if array.ndim == 1:
        array = array[np.newaxis, :]
    return array


def _looks_like_graph(array: FloatArray) -> bool:
    return (
        array.ndim == 2
        and array.shape[0] == array.shape[1]
        and array.shape[0] >= 6
        and np.allclose(array, array.T)
        and np.allclose(np.diag(array), 0.0)
        and np.all((array == 0.0) | (array == 1.0))
    )


def field_projection_scores(field: FloatArray) -> dict[str, float]:
    """Return two independently implemented, scale-free field summaries."""

    array = np.asarray(field, dtype=np.float64)
    if _looks_like_graph(array):
        eigenvalues = np.linalg.eigvalsh(array)
        spectral_gap = float((eigenvalues[-1] - eigenvalues[-2]) / max(abs(eigenvalues[-1]), 1.0))
        degrees = np.sum(array, axis=1)
        two_step = array @ array
        triangles = float(np.trace(two_step @ array) / 6.0)
        wedges = float(np.sum(degrees * np.maximum(degrees - 1.0, 0.0)) / 2.0)
        clustering = triangles * 3.0 / max(wedges, 1.0)
        return {
            "graph_spectral_gap": spectral_gap,
            "graph_triangle_clustering": float(clustering),
        }
    scalar = _scalar_field(array)
    centered = scalar - np.mean(scalar)
    variance = float(np.mean(centered * centered))
    if variance <= np.finfo(float).eps:
        return {"neighbor_coherence": 0.0, "spectral_concentration": 0.0}
    horizontal = float(np.mean(centered[:, :-1] * centered[:, 1:]) / variance)
    vertical = (
        float(np.mean(centered[:-1, :] * centered[1:, :]) / variance)
        if scalar.shape[0] > 1
        else horizontal
    )
    coherence = 0.5 * (horizontal + vertical)
    spectrum = np.abs(np.fft.rfft2(centered)) ** 2
    spectrum.flat[0] = 0.0
    flat = np.sort(spectrum.ravel())
    tail = max(1, int(np.ceil(0.05 * len(flat))))
    concentration = float(np.sum(flat[-tail:]) / max(np.sum(flat), np.finfo(float).eps))
    return {
        "neighbor_coherence": coherence,
        "spectral_concentration": concentration,
    }


def coordinate_permutation_null(field: FloatArray, rng: np.random.Generator) -> FloatArray:
    array = np.asarray(field, dtype=np.float64)
    if _looks_like_graph(array):
        upper = array[np.triu_indices(len(array), 1)].copy()
        rng.shuffle(upper)
        result = np.zeros_like(array)
        result[np.triu_indices(len(array), 1)] = upper
        return result + result.T
    if array.ndim >= 3 and array.shape[-1] in {2, 3}:
        vectors = array.reshape(-1, array.shape[-1]).copy()
        rng.shuffle(vectors, axis=0)
        return vectors.reshape(array.shape)
    values = array.ravel().copy()
    rng.shuffle(values)
    return values.reshape(array.shape)


def signed_bidirectional_separation(
    observed_by_parent: FloatArray,
    null_by_parent: FloatArray,
    *,
    family_size: int = 1,
) -> SeparationResult:
    observed = np.asarray(observed_by_parent, dtype=np.float64)
    nulls = np.asarray(null_by_parent, dtype=np.float64)
    if observed.ndim != 1 or nulls.ndim != 2 or nulls.shape[0] != len(observed):
        raise ValueError("expected parent vector and aligned parent-by-null matrix")
    if nulls.shape[1] < 2 or not np.all(np.isfinite(observed)) or not np.all(np.isfinite(nulls)):
        raise ValueError("separation inputs must be finite with at least two nulls per parent")
    parent_null_medians = np.median(nulls, axis=1)
    paired = observed - parent_null_medians
    effect = float(np.median(paired))
    scale = robust_scale(paired)
    if scale <= np.finfo(float).eps:
        pooled = (nulls - parent_null_medians[:, None]).ravel()
        scale = robust_scale(pooled)
    standardized = effect / max(scale, np.finfo(float).eps)
    pseudo = np.median(nulls - parent_null_medians[:, None], axis=0)
    upper = float((1 + np.sum(pseudo >= effect)) / (len(pseudo) + 1))
    lower = float((1 + np.sum(pseudo <= effect)) / (len(pseudo) + 1))
    two_sided = min(1.0, 2.0 * min(upper, lower))
    familywise = min(1.0, two_sided * max(family_size, 1))
    direction = "UPPER" if effect > 0 else "LOWER" if effect < 0 else "ZERO"
    uncertainty = float(
        1.4826 * np.median(np.abs(paired - np.median(paired))) / np.sqrt(len(paired))
    )
    return SeparationResult(
        observed_minus_null=effect,
        upper_tail_p=upper,
        lower_tail_p=lower,
        two_sided_p=two_sided,
        familywise_p=familywise,
        robust_standardized_effect=float(standardized),
        direction=direction,
        parent_count=len(observed),
        nested_parent_uncertainty=uncertainty,
        null_pseudo_effect_count=len(pseudo),
    )


def modal_closure_trace(field: FloatArray, n_values: Sequence[int]) -> FloatArray:
    scalar = _scalar_field(np.asarray(field, dtype=np.float64))
    centered = scalar - np.mean(scalar)
    power = np.sort((np.abs(np.fft.rfft2(centered)) ** 2).ravel())[::-1]
    total = max(float(np.sum(power)), np.finfo(float).eps)
    trace = []
    midpoint = float(np.median(n_values))
    for n_value in n_values:
        residual = float(np.sum(power[int(n_value) :]) / total)
        complexity = 0.0015 * (float(n_value) - midpoint) ** 2
        trace.append(residual + complexity + np.finfo(float).eps)
    return np.asarray(trace, dtype=np.float64)


def closure_null_calibration(
    observed_fields: Sequence[FloatArray],
    null_fields_by_parent: Sequence[Sequence[FloatArray]],
    *,
    n_values: Sequence[int] = tuple(range(6, 15)),
    seed: int = 300,
) -> dict[str, Any]:
    observed_traces = np.asarray(
        [modal_closure_trace(field, n_values) for field in observed_fields]
    )
    parent_trace = np.median(observed_traces, axis=0)
    null_traces = np.asarray(
        [
            modal_closure_trace(child, n_values)
            for children in null_fields_by_parent
            for child in children
        ]
    )
    null_parent_medians = np.asarray(
        [
            np.median([modal_closure_trace(child, n_values) for child in children], axis=0)
            for children in null_fields_by_parent
        ]
    )
    winner_index = int(np.argmin(parent_trace))
    winner = int(n_values[winner_index])
    null_winners = [int(n_values[int(np.argmin(trace))]) for trace in null_traces]
    local_p = float(
        (1 + np.sum(null_traces[:, winner_index] <= parent_trace[winner_index]))
        / (len(null_traces) + 1)
    )
    difference = parent_trace[winner_index] - null_traces[:, winner_index]
    effect = float(np.median(difference) / max(robust_scale(difference), np.finfo(float).eps))
    boundary_values = {int(n_values[0]), int(n_values[-1])}
    boundary_rate = float(np.mean([value in boundary_values for value in null_winners]))
    curvature = interior_relative_curvature(
        parent_trace,
        [int(value) for value in n_values],
        null_traces=null_parent_medians,
        seed=seed,
    )
    modes = Counter(null_winners)
    return {
        "winner_N": winner,
        "null_winner_distribution": {str(key): value for key, value in sorted(modes.items())},
        "local_closure_p": local_p,
        "robust_standardized_effect": effect,
        "boundary_rate": boundary_rate,
        "observed_trace": [float(value) for value in parent_trace],
        "mode_stability": float(modes[winner] / max(len(null_winners), 1)),
        "curvature": curvature.to_dict(),
        "winner_is_not_T_e": True,
        "winner_is_not_geometric_scale": True,
    }
