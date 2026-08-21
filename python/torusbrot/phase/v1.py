from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import pi

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
ComplexArray = NDArray[np.complex128]
BoolArray = NDArray[np.bool_]


def _wrap(angle: FloatArray | float) -> FloatArray | float:
    return (np.asarray(angle) + pi) % (2.0 * pi) - pi


def _components(signs: NDArray[np.int8], eligible: BoolArray, target: int) -> int:
    visited = np.zeros_like(eligible, dtype=bool)
    count = 0
    height, width = eligible.shape
    for y, x in np.argwhere(eligible & (signs == target)):
        if visited[y, x]:
            continue
        count += 1
        stack = [(int(y), int(x))]
        visited[y, x] = True
        while stack:
            cy, cx = stack.pop()
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if (
                    0 <= ny < height
                    and 0 <= nx < width
                    and eligible[ny, nx]
                    and signs[ny, nx] == target
                    and not visited[ny, nx]
                ):
                    visited[ny, nx] = True
                    stack.append((ny, nx))
    return count


def vector_chirality_metrics(
    values: FloatArray,
    mask: BoolArray | None = None,
    *,
    spacing: tuple[float, float] = (1.0, 1.0),
) -> dict[str, float | int]:
    """Local signed-curl evidence for a registered planar vector field.

    Only centered stencils whose four neighbors and center are observed are eligible.
    This avoids treating zero fill across a mask boundary as measured flow.
    """

    vector = np.asarray(values, dtype=np.float64)
    if vector.ndim != 3 or vector.shape[-1] != 2 or min(vector.shape[:2]) < 3:
        raise ValueError("vector chirality requires (y,x,2) with at least a 3x3 grid")
    observed = np.all(np.isfinite(vector), axis=-1)
    if mask is not None:
        supplied = np.asarray(mask, dtype=bool)
        if supplied.shape != vector.shape[:2]:
            raise ValueError("mask must match vector grid")
        observed &= supplied
    dy, dx = spacing
    if not np.isfinite([dy, dx]).all() or dy <= 0.0 or dx <= 0.0:
        raise ValueError("spacing must be two positive finite values")
    eligible = np.zeros_like(observed)
    eligible[1:-1, 1:-1] = (
        observed[1:-1, 1:-1]
        & observed[:-2, 1:-1]
        & observed[2:, 1:-1]
        & observed[1:-1, :-2]
        & observed[1:-1, 2:]
    )
    if not np.any(eligible):
        raise ValueError("no complete centered stencil remains")
    safe = np.where(observed[..., None], vector, 0.0)
    u, v = safe[..., 0], safe[..., 1]
    du_dy, du_dx = np.gradient(u, dy, dx)
    dv_dy, dv_dx = np.gradient(v, dy, dx)
    curl = dv_dx - du_dy
    divergence = du_dx + dv_dy
    local = curl[eligible]
    magnitude = float(np.mean(np.abs(local)))
    signed_mean = float(np.mean(local))
    positive = local[local > 0.0]
    negative = local[local < 0.0]
    signs = np.sign(curl).astype(np.int8)
    return {
        "eligible_stencil_count": int(np.sum(eligible)),
        "signed_mean_curl": signed_mean,
        "mean_absolute_curl": magnitude,
        "positive_circulation_mean": float(np.mean(positive)) if len(positive) else 0.0,
        "negative_circulation_magnitude_mean": float(-np.mean(negative)) if len(negative) else 0.0,
        "positive_fraction": float(np.mean(local > 0.0)),
        "negative_fraction": float(np.mean(local < 0.0)),
        "chirality_cancellation_ratio": abs(signed_mean) / max(magnitude, np.finfo(float).eps),
        "positive_domain_count": _components(signs, eligible, 1),
        "negative_domain_count": _components(signs, eligible, -1),
        "divergence_energy": float(np.mean(divergence[eligible] ** 2)),
    }


def u1_plaquette_metrics(
    values: ComplexArray,
    mask: BoolArray | None = None,
    *,
    relative_amplitude_floor: float = 1e-12,
    branch_margin: float = 1e-6,
) -> dict[str, float | int]:
    """Global-offset-invariant phase-link and winding diagnostics.

    The scalar-derived link product telescopes to unity and is not promoted to a
    nontrivial gauge connection. Wrapped winding is reported separately and is only
    invariant to a global U(1) offset (or sufficiently smooth zero-winding frame change).
    """

    field = np.asarray(values, dtype=np.complex128)
    if field.ndim != 2 or min(field.shape) < 2:
        raise ValueError("U1 plaquettes require a complex 2D grid")
    observed = np.isfinite(field.real) & np.isfinite(field.imag)
    if mask is not None:
        supplied = np.asarray(mask, dtype=bool)
        if supplied.shape != field.shape:
            raise ValueError("mask must match complex field")
        observed &= supplied
    amplitudes = np.abs(field[observed])
    if not len(amplitudes):
        raise ValueError("no observed complex samples")
    floor = max(np.finfo(float).eps, relative_amplitude_floor * float(np.median(amplitudes)))
    valid = observed & (np.abs(field) > floor)
    eligible = valid[:-1, :-1] & valid[:-1, 1:] & valid[1:, 1:] & valid[1:, :-1]
    if not np.any(eligible):
        raise ValueError("no complete nonzero plaquette remains")
    a = field[:-1, :-1]
    b = field[:-1, 1:]
    c = field[1:, 1:]
    d = field[1:, :-1]
    increments = np.stack(
        (
            np.angle(b * np.conjugate(a)),
            np.angle(c * np.conjugate(b)),
            np.angle(d * np.conjugate(c)),
            np.angle(a * np.conjugate(d)),
        ),
        axis=-1,
    )
    sums = np.sum(increments, axis=-1)
    winding = np.rint(sums / (2.0 * pi)).astype(np.int64)
    reliable = eligible & np.all(np.abs(increments) <= pi - branch_margin, axis=-1)
    selected_reliable = winding[reliable]
    link_products = np.exp(1j * sums[eligible])
    return {
        "eligible_plaquette_count": int(np.sum(eligible)),
        "branch_reliable_plaquette_count": int(np.sum(reliable)),
        "instrument_limited_plaquette_count": int(np.sum(eligible & ~reliable)),
        "positive_winding_count": int(np.sum(selected_reliable > 0)),
        "negative_winding_count": int(np.sum(selected_reliable < 0)),
        "nonzero_winding_count": int(np.sum(selected_reliable != 0)),
        "signed_winding_sum": int(np.sum(selected_reliable)),
        "mean_absolute_winding": float(np.mean(np.abs(selected_reliable)))
        if len(selected_reliable)
        else 0.0,
        "phase_gradient_mean_absolute": float(np.mean(np.abs(increments[eligible]))),
        "scalar_derived_link_product_max_error_from_unity": float(
            np.max(np.abs(link_products - 1.0))
        ),
        "scalar_derived_holonomy_is_algebraically_trivial": 1,
        "arbitrary_local_gauge_invariant": 0,
        "global_phase_offset_invariant": 1,
        "amplitude_floor": floor,
    }


@dataclass(frozen=True)
class O2Element:
    theta: float
    s: int

    def __post_init__(self) -> None:
        if self.s not in {-1, 1} or not np.isfinite(self.theta):
            raise ValueError("O2 element requires finite theta and s in {-1,+1}")


def o2_compose(left: O2Element, right: O2Element) -> O2Element:
    """Return left*right under (theta,s)(phi,t)=(theta+s*phi,st)."""

    return O2Element(float(_wrap(left.theta + left.s * right.theta)), left.s * right.s)


def o2_inverse(element: O2Element) -> O2Element:
    return O2Element(float(_wrap(-element.s * element.theta)), element.s)


def o2_loop_monodromy(elements: Iterable[O2Element]) -> dict[str, float | int | str]:
    items = tuple(elements)
    if not items:
        raise ValueError("O2 loop requires at least one transition")
    total = O2Element(0.0, 1)
    for item in items:
        total = o2_compose(total, item)
    return {
        "theta": total.theta,
        "s": total.s,
        "reflection_count": sum(item.s == -1 for item in items),
        "orientation_class": "REVERSING" if total.s == -1 else "PRESERVING",
        "double_traversal_parity": total.s * total.s,
    }


def temporal_cross_spectrum(
    left: FloatArray,
    right: FloatArray,
    *,
    dt: float,
    segment_length: int | None = None,
) -> dict[str, float | int]:
    x = np.asarray(left, dtype=np.float64)
    y = np.asarray(right, dtype=np.float64)
    if (
        x.ndim != 1
        or y.shape != x.shape
        or len(x) < 16
        or not np.isfinite(x).all()
        or not np.isfinite(y).all()
    ):
        raise ValueError("cross spectrum requires aligned finite 1D signals of length >=16")
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("dt must be positive and finite")
    length = segment_length or min(256, 2 ** int(np.floor(np.log2(len(x) // 2))))
    if length < 8 or length > len(x):
        raise ValueError("invalid segment length")
    step = max(1, length // 2)
    starts = list(range(0, len(x) - length + 1, step))
    if not starts:
        raise ValueError("no complete spectral segment")
    window = np.hanning(length)
    cross = []
    auto_x = []
    auto_y = []
    for start in starts:
        xs = (x[start : start + length] - np.mean(x[start : start + length])) * window
        ys = (y[start : start + length] - np.mean(y[start : start + length])) * window
        xf = np.fft.rfft(xs)
        yf = np.fft.rfft(ys)
        cross.append(yf * np.conjugate(xf))
        auto_x.append(np.abs(xf) ** 2)
        auto_y.append(np.abs(yf) ** 2)
    sxy = np.mean(cross, axis=0)
    sxx = np.mean(auto_x, axis=0)
    syy = np.mean(auto_y, axis=0)
    frequencies = np.fft.rfftfreq(length, dt)
    strength = np.abs(sxy)
    strength[0] = 0.0
    index = int(np.argmax(strength))
    coherence = float(np.abs(sxy[index]) ** 2 / max(sxx[index] * syy[index], np.finfo(float).eps))
    return {
        "segment_length": length,
        "segment_count": len(starts),
        "dominant_frequency": float(frequencies[index]),
        "dominant_period": float(1.0 / frequencies[index])
        if frequencies[index] > 0
        else float("inf"),
        "cross_phase": float(np.angle(sxy[index])),
        "magnitude_squared_coherence": min(1.0, coherence),
    }


def blind_period_scan(signal: FloatArray, periods: Sequence[int]) -> dict[str, object]:
    values = np.asarray(signal, dtype=np.float64)
    candidates = tuple(int(period) for period in periods)
    if (
        values.ndim != 1
        or len(values) < 2 * min(candidates)
        or len(set(candidates)) != len(candidates)
    ):
        raise ValueError("period scan requires a long 1D signal and unique candidates")
    if not np.isfinite(values).all() or any(period < 2 for period in candidates):
        raise ValueError("period scan inputs must be finite with periods >=2")
    centered = values - np.mean(values)
    total = float(np.sum(centered**2))
    t = np.arange(len(values), dtype=np.float64)
    scores = {}
    for period in candidates:
        design = np.column_stack((np.sin(2.0 * pi * t / period), np.cos(2.0 * pi * t / period)))
        coefficients, *_ = np.linalg.lstsq(design, centered, rcond=None)
        fitted = design @ coefficients
        scores[str(period)] = float(np.sum(fitted**2) / max(total, np.finfo(float).eps))
    winner = min(candidates, key=lambda period: (-scores[str(period)], period))
    return {"winner_period": winner, "scores": scores, "period_family": list(candidates)}
