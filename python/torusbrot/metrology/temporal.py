"""Descriptive lag diagnostics for uniformly sampled real vector signals.

These support estimator uncertainty within an acquisition. Neither samples nor
bootstrap draws acquire independent-system status. Phase/coherence inference is
outside this module's contract.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray


def temporal_diagnostics(
    values: NDArray[np.float64],
    time_seconds: NDArray[np.float64],
    *,
    max_lag: int = 32,
    block_lengths: tuple[int, ...] = (8, 16, 32),
    replicates: int = 199,
    seed: int = 20260913,
) -> dict[str, Any]:
    values = np.asarray(values, dtype=float)
    time = np.asarray(time_seconds, dtype=float)
    if values.ndim != 2 or values.shape[1] != 3 or len(time) != len(values) or len(time) < 16:
        raise ValueError("requires chronological n-by-3 u/v/vorticity signal, n>=16")
    if (
        not np.all(np.isfinite(values))
        or not np.all(np.isfinite(time))
        or not np.all(np.diff(time) > 0)
    ):
        raise ValueError("finite complete chronological signals required")
    dt = float(np.median(np.diff(time)))
    if not np.allclose(np.diff(time), dt, rtol=1e-10, atol=0):
        raise ValueError("gaps/nonuniform sampling require a separately registered estimator")
    if (
        not 1 <= max_lag < len(values)
        or replicates < 20
        or not block_lengths
        or any(b < 2 or b > len(values) // 2 for b in block_lengths)
    ):
        raise ValueError("invalid lag/bootstrap contract")
    centered = values - np.mean(values, axis=0)
    energy = np.sum(centered**2, axis=0)
    rho = np.full((max_lag + 1, 3), np.nan)
    for k in range(max_lag + 1):
        products = np.sum(centered[: len(values) - k] * centered[k:], axis=0)
        np.divide(products, energy, out=rho[k], where=energy > 0)
    summaries = {}
    for j, name in enumerate(("u", "v", "vorticity")):
        if energy[j] == 0:
            summaries[name] = {"status": "UNDEFINED_CONSTANT_SIGNAL"}
            continue
        nonpositive = np.flatnonzero(rho[1:, j] <= 0)
        cutoff = int(nonpositive[0] + 1) if len(nonpositive) else max_lag + 1
        tau = float(1 + 2 * np.sum(rho[1:cutoff, j]))
        power = np.abs(np.fft.rfft(centered[:, j])) ** 2
        power[0] = 0
        peak = int(np.argmax(power))
        frequency = float(np.fft.rfftfreq(len(time), dt)[peak])
        summaries[name] = {
            "status": "DESCRIPTIVE_CONDITIONAL_STATIONARITY",
            "acf": rho[:, j].tolist(),
            "first_nonpositive_lag": cutoff if len(nonpositive) else None,
            "tau_factor": tau,
            "tau_convention": "1 + 2 sum rho(k), stop BEFORE first nonpositive or max_lag",
            "conditional_mean_ess": len(time) / tau,
            "ess_is_independent_system_count": False,
            "dominant_fft_frequency_hz": frequency,
            "dominant_fft_period_s": None if frequency == 0 else 1 / frequency,
            "fft_resolution_hz": 1 / (len(time) * dt),
            "half_record_mean_difference": float(
                np.mean(values[len(time) // 2 :, j]) - np.mean(values[: len(time) // 2, j])
            ),
            "standard_deviation": float(np.std(values[:, j], ddof=1)),
            "limitation": (
                "oscillations, drift or long memory can invalidate scalar tau/ESS "
                "and stationary bootstrap interpretation"
            ),
        }
    cross = []
    denominator = np.sqrt(energy[0] * energy[1])
    if denominator > 0:
        cross = [
            float(np.sum(centered[: len(time) - k, 0] * centered[k:, 1]) / denominator)
            for k in range(max_lag + 1)
        ]
    rng = np.random.default_rng(seed)
    blocks = []
    for block in block_lengths:
        means = []
        for _ in range(replicates):
            starts = rng.integers(0, len(time), int(np.ceil(len(time) / block)))
            indices = ((starts[:, None] + np.arange(block)) % len(time)).ravel()[: len(time)]
            means.append(np.mean(values[indices], axis=0))
        blocks.append(
            {
                "block_length": block,
                "replicates": replicates,
                "mean_percentile_interval_95": np.quantile(
                    means, [0.025, 0.975], axis=0
                ).T.tolist(),
                "interpretation": (
                    "conditional stationary circular-block sampling interval, "
                    "no population inference"
                ),
            }
        )
    return {
        "sampling_interval_s": dt,
        "duration_s": float(time[-1] - time[0]),
        "gaps": 0,
        "window": "rectangular; mean removed; no spatial FFT or missing-value fill",
        "signals": summaries,
        "cross_correlation_u_now_v_later": cross,
        "bootstrap_sensitivity": blocks,
        "independent_system_count_added": 0,
    }
