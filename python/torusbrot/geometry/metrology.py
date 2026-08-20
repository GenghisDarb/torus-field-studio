from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from torusbrot.geometry.models import CurvatureResult, ObservableClass

FloatArray = NDArray[np.float64]


def robust_scale(values: FloatArray) -> float:
    array = np.asarray(values, dtype=np.float64)
    median = float(np.median(array))
    return float(1.4826 * np.median(np.abs(array - median)))


def _peak_prominence(trace: FloatArray) -> tuple[FloatArray, float, int]:
    log_trace = np.log(np.asarray(trace, dtype=np.float64))
    curvature = -(log_trace[2:] - 2.0 * log_trace[1:-1] + log_trace[:-2])
    peak_index = int(np.argmax(curvature))
    return curvature, float(curvature[peak_index]), peak_index


def interior_relative_curvature(
    trace: FloatArray,
    coordinates: list[int],
    *,
    null_traces: FloatArray | None = None,
    bootstrap_samples: int = 256,
    seed: int = 300,
) -> CurvatureResult:
    values = np.asarray(trace, dtype=np.float64)
    if values.ndim != 1 or len(values) != len(coordinates) or len(values) < 5:
        raise ValueError("curvature requires an aligned trace of at least five points")
    if not np.all(np.isfinite(values)) or not np.all(values > 0):
        raise ValueError("curvature trace must be finite and strictly positive")
    scale = robust_scale(np.log(values))
    if scale <= np.finfo(np.float64).eps:
        return CurvatureResult(
            status="REJECTED_FLATLINE_OR_ZERO_VARIANCE",
            sign_convention="positive = downward knee in log(trace)",
            interior_indices=coordinates[1:-1],
            curvature=[],
            candidate_elbows=[],
            selected_elbow=None,
            robust_trace_scale=scale,
            relative_prominence=None,
            null_standardized_prominence=None,
            bootstrap_stability=None,
            endpoint_excluded=True,
            boundary_pinning=False,
        )
    curvature, peak, peak_index = _peak_prominence(values)
    selected = coordinates[peak_index + 1]
    relative = peak / max(scale, np.finfo(np.float64).eps)
    order = np.argsort(curvature)[::-1][: min(3, len(curvature))]
    candidates = [coordinates[int(index) + 1] for index in order]
    z_value: float | None = None
    stability: float | None = None
    if null_traces is not None:
        null_array = np.asarray(null_traces, dtype=np.float64)
        if null_array.ndim != 2 or null_array.shape[1] != len(values):
            raise ValueError("null traces must have shape (children, trace points)")
        null_peaks = np.asarray([_peak_prominence(row)[1] for row in null_array])
        null_median = float(np.median(null_peaks))
        null_scale = robust_scale(null_peaks)
        z_value = (peak - null_median) / max(null_scale, np.finfo(np.float64).eps)
        rng = np.random.default_rng(seed)
        selections = []
        for _ in range(bootstrap_samples):
            indices = rng.integers(0, len(null_array), len(null_array))
            reference = np.median(null_array[indices], axis=0)
            perturbed = np.maximum(values - reference + np.median(reference), np.finfo(float).eps)
            _, _, index = _peak_prominence(perturbed)
            selections.append(coordinates[index + 1])
        stability = float(np.mean(np.asarray(selections) == selected))
    return CurvatureResult(
        status="COMPUTED_INTERIOR_ONLY",
        sign_convention="positive = downward knee in log(trace)",
        interior_indices=coordinates[1:-1],
        curvature=[float(value) for value in curvature],
        candidate_elbows=candidates,
        selected_elbow=selected,
        robust_trace_scale=scale,
        relative_prominence=float(relative),
        null_standardized_prominence=None if z_value is None else float(z_value),
        bootstrap_stability=stability,
        endpoint_excluded=True,
        boundary_pinning=selected in {coordinates[0], coordinates[-1]},
    )


def measurement_repeat_policy(observable_class: ObservableClass) -> dict[str, object]:
    policies: dict[ObservableClass, dict[str, object]] = {
        ObservableClass.DETERMINISTIC_SEMANTIC: {
            "authorized_runs": 1,
            "duplicate_clean_replay": True,
            "comparison": "exact_or_semantic",
            "timing_average_claim_bearing": False,
        },
        ObservableClass.STOCHASTIC_SEMANTIC: {
            "registered_seeds_required": True,
            "trial_count_preregistered": True,
            "uncertainty_required": True,
            "adaptive_stopping": False,
        },
        ObservableClass.NOISY_NUMERIC: {
            "repetitions_preregistered": True,
            "robust_location": True,
            "confidence_interval": True,
            "variance_floor_analysis": True,
        },
        ObservableClass.TIMING_OR_RESOURCE: {
            "warmup_policy": True,
            "randomized_order": True,
            "paired_comparisons": True,
            "cold_warm_cache_separated": True,
            "causal_authority": False,
        },
        ObservableClass.FLAKINESS_DIAGNOSTIC: {
            "repeated_clean_replay": True,
            "failure_frequency": True,
            "single_run_causal_attribution": False,
        },
        ObservableClass.ENVIRONMENT_DEPENDENT: {
            "environment_strata": True,
            "pooling_requires_hierarchical_model": True,
        },
    }
    return {"observable_class": observable_class.value, **policies[observable_class]}
