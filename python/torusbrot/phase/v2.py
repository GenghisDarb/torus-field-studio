"""Conventional, observable-specific phase metrology (PHASE_V2).

No result in this module supplies TLD identity, a population sample size, a
physical manifold, or evidence for a preferred period. Undefined measurements
remain explicit states. Public result mappings are JSON serializable.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import pi

import numpy as np
from numpy.typing import ArrayLike


def sampled_winding(
    values: ArrayLike,
    *,
    mask: ArrayLike | None = None,
    amplitude_noise_bound: ArrayLike = 0.0,
    amplitude_floor: float = 0.0,
    branch_margin: float = 1e-6,
    sampling_admissible: bool = False,
) -> dict[str, object]:
    """Winding of a closed, ordered loop of complex samples, without repeated endpoint.

    Positive orientation is supplied array order. Principal arguments lie in
    [-pi,pi); near-pi edges abstain. A noise bound b_i is a deterministic bound
    on complex sample error in the same units as |z_i|, NOT a standard deviation.
    If b_i < |z_i|, asin(b_i/|z_i|) bounds its phase error. All edges must avoid
    the branch cut by their combined bounds plus branch_margin.

    Continuous winding additionally requires an external assurance that the
    true intersample phase lift has increments strictly between -pi and pi and
    never crosses a zero on the path. Sample values alone cannot verify this.
    Zeros inside a loop are allowed; missing/zero samples ON it are not filled.
    """
    z = np.asarray(values, dtype=np.complex128)
    if z.ndim != 1 or len(z) < 3:
        raise ValueError("winding requires an ordered 1D loop with at least 3 samples")
    if not np.isfinite(amplitude_floor) or amplitude_floor < 0:
        raise ValueError("amplitude_floor must be a finite nonnegative instrument value")
    if not np.isfinite(branch_margin) or not 0 <= branch_margin < pi:
        raise ValueError("branch_margin must lie in [0,pi)")
    noise = np.broadcast_to(np.asarray(amplitude_noise_bound, dtype=float), z.shape)
    if not np.all(np.isfinite(noise)) or np.any(noise < 0):
        raise ValueError("amplitude_noise_bound must be finite and nonnegative")
    observed = np.isfinite(z.real) & np.isfinite(z.imag)
    if mask is not None:
        supplied = np.asarray(mask, dtype=bool)
        if supplied.shape != z.shape:
            raise ValueError("mask must match the loop")
        observed &= supplied
    with np.errstate(over="ignore", invalid="ignore"):
        amplitude = np.abs(z)
    valid = observed & np.isfinite(amplitude) & (amplitude > amplitude_floor) & (amplitude > noise)
    result: dict[str, object] = {
        "operator_id": "SAMPLED_WINDING_V2",
        "status": "INDETERMINATE",
        "winding": None,
        "continuous_winding": None,
        "sample_count": len(z),
        "valid_sample_count": int(valid.sum()),
        "missing_sample_count": int((~observed).sum()),
        "phase_unidentifiable_sample_count": int((observed & ~valid).sum()),
        "global_phase_invariant": True,
        "arbitrary_local_gauge_invariant": False,
        "sampling_admissibility_supplied": bool(sampling_admissible),
        "uncertainty_kind": "DETERMINISTIC_COMPLEX_ERROR_BOUND",
        "amplitude_floor": float(amplitude_floor),
        "branch_margin_radians": float(branch_margin),
    }
    if not valid.all():
        result["reason"] = "INCOMPLETE_OR_UNIDENTIFIABLE_LOOP_PHASE"
        return result
    # Divide individual endpoints before multiplication: avoid |z_i*z_j|
    # overflow/underflow and any dimensional machine-epsilon threshold.
    unit = z / amplitude
    links = np.roll(unit, -1) * np.conjugate(unit)
    increments = (np.angle(links) + pi) % (2 * pi) - pi
    phase_error = np.arcsin(noise / amplitude)
    edge_error = phase_error + np.roll(phase_error, -1)
    branch_clearance = pi - np.abs(increments) - edge_error - branch_margin
    ambiguity = branch_clearance <= 0
    raw = float(np.sum(increments) / (2 * pi))
    nearest = int(np.rint(raw))
    residual = abs(raw - nearest)
    result.update({
        "increments_radians": increments.tolist(),
        "edge_phase_error_bound_radians": edge_error.tolist(),
        "ambiguous_edge_count": int(ambiguity.sum()),
        "minimum_branch_clearance_radians": float(branch_clearance.min()),
        "unrounded_winding": raw,
        "integer_residual": residual,
        "scalar_link_product_real": float(np.prod(links).real),
        "scalar_link_product_imag": float(np.prod(links).imag),
        "scalar_link_holonomy_trivial": True,
    })
    if ambiguity.any():
        result["reason"] = "BRANCH_UNCERTAINTY_OR_ALIASING"
    elif residual > 64 * np.finfo(float).eps * len(z):
        result["reason"] = "NUMERICAL_CLOSURE_INCONSISTENCY"
    else:
        result.update({
            "status": "ESTIMATED",
            "winding": nearest,
            "continuous_winding": nearest if sampling_admissible else None,
            "reason": "SAMPLED_WINDING_ONLY" if not sampling_admissible else
            "CONTINUOUS_WINDING_CONDITIONAL_ON_SUPPLIED_SAMPLING_AND_NOISE_BOUNDS",
        })
    return result


def covariant_phase_links(values: ArrayLike, transport: ArrayLike) -> list[complex]:
    """conj(z_i) U_ij z_j / |z_i z_j|; U transports j to i.

    Input transport must have a separately justified physical/model provenance.
    This calculation cannot establish that provenance or nontrivial curvature.
    """
    z = np.asarray(values, dtype=complex)
    u = np.asarray(transport, dtype=complex)
    if z.ndim != 1 or u.shape != z.shape or not len(z):
        raise ValueError("provide one explicit transport per closed-loop edge")
    if not np.isfinite(z).all() or not np.isfinite(u).all() or np.any(np.abs(z) == 0):
        raise ValueError("phase and transport must be finite with nonzero phase samples")
    if not np.allclose(np.abs(u), 1.0, rtol=1e-12, atol=1e-12):
        raise ValueError("U1 transport must have unit modulus")
    unit = z / np.abs(z)
    return (np.conjugate(unit) * u * np.roll(unit, -1)).tolist()


@dataclass(frozen=True)
class O2Element:
    theta: float
    s: int

    def __post_init__(self) -> None:
        if self.s not in (-1, 1) or not np.isfinite(self.theta):
            raise ValueError("O2 requires finite angle and determinant s in {-1,+1}")


def o2_compose(left: O2Element, right: O2Element) -> O2Element:
    """left after right: (theta,s)(phi,t)=(theta+s*phi,s*t)."""
    return O2Element(float((left.theta + left.s * right.theta + pi) % (2*pi) - pi),
                     left.s * right.s)


def o2_action(element: O2Element, value: complex) -> complex:
    return complex(np.exp(1j * element.theta) *
                   (value if element.s == 1 else np.conjugate(value)))


def o2_power(element: O2Element, exponent: int) -> O2Element:
    if not isinstance(exponent, (int, np.integer)) or exponent < 0:
        raise ValueError("exponent must be a nonnegative integer")
    total = O2Element(0.0, 1)
    for _ in range(exponent):
        total = o2_compose(total, element)
    return total


def o2_loop_monodromy(
    elements: Iterable[O2Element] | None,
    *,
    transition_provenance: str,
) -> dict[str, object]:
    """Composition from explicit transport maps, not from unannotated scalar fields.

    Items are traversed in supplied order: the last item acts last. Closure of
    the base path and frame conventions are part of the caller's contract.
    """
    allowed = {"MEASURED_TRANSITION_MAPS", "SUPPLIED_MODEL_TRANSITION_MAPS"}
    if elements is None or transition_provenance not in allowed:
        return {"operator_id": "EXPLICIT_O2_TRANSPORT_V2", "status": "NOT_IDENTIFIABLE",
                "reason": "MONODROMY_NOT_IDENTIFIABLE_FROM_THIS_OBSERVABLE", "parity": None}
    items = tuple(elements)
    if not items or not all(isinstance(item, O2Element) for item in items):
        raise ValueError("supply a nonempty sequence of O2Element transitions")
    total = O2Element(0.0, 1)
    for item in items:
        total = o2_compose(item, total)
    return {
        "operator_id": "EXPLICIT_O2_TRANSPORT_V2", "status": "ESTIMATED",
        "theta": total.theta, "parity": total.s,
        "reflection_count": sum(item.s == -1 for item in items),
        "transition_provenance": transition_provenance,
        "orientation_class": "REVERSING" if total.s == -1 else "PRESERVING",
        "physical_nonorientable_space_established": False,
    }


def _time_series(left: ArrayLike, right: ArrayLike, time: ArrayLike):
    x, y, t = (np.asarray(a, dtype=float) for a in (left, right, time))
    if x.ndim != 1 or y.shape != x.shape or t.shape != x.shape or len(x) < 8:
        raise ValueError("signals and time must be aligned 1D arrays of length >=8")
    if not all(np.isfinite(a).all() for a in (x, y, t)):
        raise ValueError("missing time/signal support requires a separately registered gap model")
    intervals = np.diff(t)
    dt = float(np.median(intervals))
    if dt <= 0 or np.any(intervals <= 0):
        raise ValueError("time must be strictly increasing")
    if not np.allclose(intervals / dt, 1.0, rtol=1e-7, atol=0):
        raise ValueError("irregular time or gaps require a separately validated spectral method")
    return x, y, t, dt


def _scaled_center(values):
    scale = float(np.max(np.abs(values)))
    if scale == 0:
        return np.zeros_like(values), 0.0
    normalized = values / scale
    return normalized - normalized.mean(), scale


def temporal_cross_spectrum(
    left: ArrayLike,
    right: ArrayLike,
    time: ArrayLike,
    *,
    segment_length: int = 128,
    window: str = "hann",
    time_unit: str = "s",
    frequency_index: int | None = None,
    independent_segments: bool = False,
    bootstrap_replicates: int = 0,
    bootstrap_seed: int = 0,
    confidence: float = 0.95,
) -> dict[str, object]:
    """Nonoverlapping Welch CSD, Sxy=conj(X)*Y, one-sided density normalization.

    Hann is periodic (DFT-even), boxcar is unwindowed. Each complete segment is
    demeaned. Tail samples are explicitly unused. Nonoverlap does not prove
    independence. Optional phase bootstrap is conditional on independently
    sampled/exchangeable segments and a preregistered frequency_index; it is
    refused for a selected peak. Phase intervals are offsets around the estimate
    (radians) to preserve the branch cut. No population confidence is implied.
    """
    x, y, t, dt = _time_series(left, right, time)
    if not isinstance(segment_length, (int, np.integer)) or not 8 <= segment_length <= len(x)//2:
        raise ValueError("segment_length must allow at least two nonoverlapping segments")
    if window not in {"hann", "boxcar"} or not time_unit.strip():
        raise ValueError("declare window hann/boxcar and nonempty time unit")
    if bootstrap_replicates < 0 or not 0 < confidence < 1:
        raise ValueError("invalid uncertainty settings")
    count = len(x) // segment_length
    used = count * segment_length
    w = 0.5 - 0.5 * np.cos(2*pi*np.arange(segment_length)/segment_length)
    if window == "boxcar":
        w = np.ones(segment_length)
    # Unit normalization removes avoidable overflow/underflow in coherence.
    sx, scale_x = _scaled_center(x[:used])
    sy, scale_y = _scaled_center(y[:used])
    xs, ys = sx.reshape(count, segment_length), sy.reshape(count, segment_length)
    xf = np.fft.rfft((xs - xs.mean(axis=1, keepdims=True)) * w, axis=1)
    yf = np.fft.rfft((ys - ys.mean(axis=1, keepdims=True)) * w, axis=1)
    cross = np.conjugate(xf) * yf
    pxx, pyy, pxy = (a.mean(axis=0) for a in (abs(xf)**2, abs(yf)**2, cross))
    support = (pxx > 0) & (pyy > 0)
    coherence = np.zeros_like(pxx)
    coherence[support] = abs(pxy[support])**2 / (pxx[support]*pyy[support])
    coherence = np.clip(coherence, 0, 1)
    frequencies = np.fft.rfftfreq(segment_length, dt)
    if frequency_index is not None and not 1 <= frequency_index < len(frequencies):
        raise ValueError("frequency_index must be a positive available Fourier bin")
    index = (int(np.argmax(abs(pxy[1:]))) + 1 if frequency_index is None else frequency_index)
    density_scale = np.full(len(pxx), dt / float(np.sum(w*w)))
    density_scale[1:-1 if segment_length % 2 == 0 else None] *= 2
    status = "ESTIMATED" if support[index] else "INDETERMINATE"
    result: dict[str, object] = {
        "operator_id": "TEMPORAL_CROSS_SPECTRUM_V2", "status": status,
        "time_unit": time_unit, "sampling_interval": dt,
        "duration": float(t[-1]-t[0]), "segment_length": int(segment_length),
        "segment_count": count, "overlap_samples": 0, "discarded_tail_samples": len(x)-used,
        "window": window, "detrend": "SEGMENT_CONSTANT", "frequency": frequencies.tolist(),
        "spectrum_support": support.tolist(),
        "coherence": [float(a) if b else None for a, b in zip(coherence, support, strict=True)],
        "cross_phase_radians": [float(np.angle(a)) if b else None
                                for a, b in zip(pxy, support, strict=True)],
        "normalized_auto_left_density": (pxx*density_scale).tolist(),
        "normalized_auto_right_density": (pyy*density_scale).tolist(),
        "normalized_cross_density_real": (pxy.real*density_scale).tolist(),
        "normalized_cross_density_imag": (pxy.imag*density_scale).tolist(),
        "left_amplitude_scale": scale_x, "right_amplitude_scale": scale_y,
        "density_units": "signal_unit_squared_per_inverse_time_unit_after_scale_restoration",
        "selected_frequency_index": int(index),
        "selection": "EXPLORATORY_MAX_CROSS_POWER" if frequency_index is None else "REGISTERED_BIN",
        "dominant_frequency": float(frequencies[index]) if support[index] else None,
        "dominant_period": float(1/frequencies[index]) if support[index] else None,
        "cross_phase": float(np.angle(pxy[index])) if support[index] else None,
        "magnitude_squared_coherence": float(coherence[index]) if support[index] else None,
        "independent_segments_assumed": bool(independent_segments),
        "independent_physical_system_count": None,
        "phase_uncertainty": {"status": "NOT_ESTIMATED"},
    }
    if bootstrap_replicates:
        if frequency_index is None or not independent_segments:
            raise ValueError("phase bootstrap requires registered bin and independent segments")
        if bootstrap_replicates < 100 or count < 4:
            raise ValueError("phase bootstrap requires >=100 replicates and >=4 segments")
        if support[index]:
            rng = np.random.default_rng(bootstrap_seed)
            estimates = np.array([cross[rng.integers(count, size=count), index].mean()
                                  for _ in range(bootstrap_replicates)])
            reference = float(np.angle(pxy[index]))
            offsets = np.angle(estimates * np.exp(-1j*reference))
            alpha = (1-confidence)/2
            bounds = np.quantile(offsets, [alpha, 1-alpha])
            result["phase_uncertainty"] = {
                "status": "CONDITIONAL_BOOTSTRAP", "confidence": confidence,
                "method": "SEGMENT_PERCENTILE_CIRCULAR_OFFSETS",
                "lower_offset_radians": float(bounds[0]),
                "upper_offset_radians": float(bounds[1]),
                "reference_phase_radians": reference, "replicates": bootstrap_replicates,
                "seed": bootstrap_seed, "scope": "ASSUMED_EXCHANGEABLE_INDEPENDENT_SEGMENTS",
                "warning": "Unreliable near zero cross-spectrum or wrapped diffuse phase",
            }
    return result


def lagged_phase_association(
    left: ArrayLike, right: ArrayLike, time: ArrayLike, *, lag: int = 1,
) -> dict[str, object]:
    """[mean(x_t*y_(t+l))-mean(y_t*x_(t+l))]/(2 sigma_x sigma_y).

    Unitless, order-sensitive, and antisymmetric under time reversal. This is
    lagged linear association, not causal direction or emergent time.
    """
    x, y, _, dt = _time_series(left, right, time)
    if not isinstance(lag, (int, np.integer)) or not 1 <= lag < len(x)//2:
        raise ValueError("lag must be a positive integer below half the sample count")
    a, _ = _scaled_center(x)
    b, _ = _scaled_center(y)
    denominator = float(2*np.sqrt(np.mean(a*a)*np.mean(b*b)))
    return {
        "operator_id": "ANTISYMMETRIC_LAG_ASSOCIATION_V2",
        "status": "ESTIMATED" if denominator > 0 else "INDETERMINATE",
        "value": float(np.mean(a[:-lag]*b[lag:]-b[:-lag]*a[lag:])/denominator)
        if denominator > 0 else None,
        "lag_samples": int(lag), "lag_time": float(lag*dt),
        "pair_count": len(x)-lag, "causal_interpretation": False,
    }


def lag_block_bootstrap(
    left: ArrayLike, right: ArrayLike, time: ArrayLike, *, lag: int,
    block_length: int, replicates: int, seed: int, stationarity_assumed: bool,
    confidence: float = 0.95,
) -> dict[str, object]:
    """Paired circular moving-block percentile interval, conditional on stationarity.

    Boundary joins alter lags; use block length much greater than lag and report
    sensitivity across registered block lengths. The output is acquisition-local
    resampling uncertainty, not a physical population interval.
    """
    x, y, t, _ = _time_series(left, right, time)
    if not stationarity_assumed:
        return {"status": "NOT_APPLICABLE", "reason": "STATIONARITY_NOT_ESTABLISHED"}
    if not 2*lag < block_length <= len(x)//2 or replicates < 100 or not 0 < confidence < 1:
        raise ValueError("require 2*lag < block_length <= n/2, >=100 replicates, 0<confidence<1")
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(replicates):
        starts = rng.integers(len(x), size=int(np.ceil(len(x)/block_length)))
        indices = ((starts[:, None]+np.arange(block_length)) % len(x)).ravel()[:len(x)]
        estimate = lagged_phase_association(x[indices], y[indices], t, lag=lag)["value"]
        if estimate is None:
            return {"status": "INDETERMINATE", "reason": "DEGENERATE_RESAMPLE"}
        values.append(estimate)
    alpha = (1-confidence)/2
    lower, upper = np.quantile(values, [alpha, 1-alpha])
    return {"status": "CONDITIONAL_BOOTSTRAP", "lower": float(lower), "upper": float(upper),
            "confidence": confidence, "block_length": block_length, "replicates": replicates,
            "seed": seed, "scope": "ACQUISITION_LOCAL_STATIONARY_CIRCULAR_MOVING_BLOCK",
            "null_distribution": False, "population_generalization": False}


def segment_phase_surrogate(values: ArrayLike, *, segment_length: int, seed: int) -> list[float]:
    """Randomize each segment's real-signal Fourier phases independently.

    Exact segment periodogram, mean, energy, and real-valuedness are preserved.
    Marginal amplitude distribution, segment boundaries, higher-order structure,
    and original relative phases are not. Pair with an unchanged other signal
    only for the registered null of independent segment phase relations.
    """
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or not np.isfinite(x).all() or segment_length < 8:
        raise ValueError("require finite 1D input and segment_length >=8")
    if len(x) % segment_length or len(x) < 2*segment_length:
        raise ValueError("surrogate requires >=2 complete segments without a tail")
    spectra = np.fft.rfft(x.reshape(-1, segment_length), axis=1)
    rng = np.random.default_rng(seed)
    phases = rng.uniform(-pi, pi, size=spectra.shape)
    phases[:, 0] = 0
    if segment_length % 2 == 0:
        phases[:, -1] = 0
    return np.fft.irfft(spectra*np.exp(1j*phases), n=segment_length, axis=1).ravel().tolist()


def integrated_autocorrelation(
    values: ArrayLike, time: ArrayLike, *, max_lag: int,
    applicability: str = "UNKNOWN",
) -> dict[str, object]:
    """tau_factor=1+2 sum rho(k), truncated before first nonpositive rho.

    Only a conditional estimate for stationary, short-memory, nonoscillatory
    series. No interpretation as a number of independent systems. Oscillatory,
    nonstationary and long-memory processes require another registered method.
    """
    x, _, _, dt = _time_series(values, values, time)
    if not 1 <= max_lag < len(x)//2:
        raise ValueError("max_lag must lie between 1 and n/2")
    a, _ = _scaled_center(x)
    power = float(np.dot(a, a))
    if power == 0:
        return {"status": "NOT_APPLICABLE", "reason": "ZERO_VARIANCE", "tau_factor": None}
    rho = np.array([np.dot(a[:-k], a[k:])/power for k in range(1, max_lag+1)])
    result: dict[str, object] = {
        "status": "NOT_APPLICABLE", "tau_factor": None,
        "autocorrelation": [1.0, *rho.tolist()], "sampling_interval": dt,
        "convention": "1+2*sum(rho), before first nonpositive lag",
        "estimator_specific_effective_sample_size": None,
        "independent_system_count": None,
    }
    if applicability != "STATIONARY_SHORT_MEMORY_NONOSCILLATORY":
        result["reason"] = "APPLICABILITY_NOT_ESTABLISHED"
        return result
    # An empirical guard catches strong oscillatory lobes; it cannot certify
    # stationarity or short memory, which remain external assumptions.
    if np.min(rho) < -max(0.2, 4/np.sqrt(len(x))):
        result["reason"] = "STRONG_NEGATIVE_LOBE_USE_OSCILLATORY_MODEL"
        return result
    crossings = np.flatnonzero(rho <= 0)
    if not len(crossings):
        result["status"] = "INDETERMINATE"
        result["reason"] = "NO_TRUNCATION_WITHIN_REGISTERED_WINDOW"
        return result
    stop = int(crossings[0])
    tau = float(1+2*np.sum(rho[:stop]))
    result.update({"status": "CONDITIONAL_ESTIMATE", "tau_factor": tau,
                   "tau_time": tau*dt, "last_included_lag": stop,
                   "estimator_specific_effective_sample_size": len(x)/tau,
                   "reason": "CONDITIONAL_MEAN_VARIANCE_APPROXIMATION"})
    return result
