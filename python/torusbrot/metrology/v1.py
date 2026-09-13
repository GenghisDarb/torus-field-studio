"""Cartesian rectilinear vector metrology with explicit units and valid support.

All derivatives use quadratic three-point interpolation on physical coordinates.
Interior stencils include the center even on a uniform grid; boundaries use a
second-order one-sided stencil. An invalid sample invalidates the whole stencil.
No claim is made for curvilinear, irregular or three-dimensional geometries.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
OPERATOR_ID = "RECTILINEAR_COORDINATE_MASK_UNIT_V1"
_LENGTH = {"m": 1.0, "mm": 0.001, "cm": 0.01, "1": 1.0, "deposited_coordinate": 1.0}
_VELOCITY = {"m/s": 1.0, "mm/s": 0.001, "cm/s": 0.01, "1": 1.0}


@dataclass(frozen=True)
class Hierarchy:
    system: str
    campaign: str
    acquisition: str
    condition: str = "unspecified"
    pair: str | None = None
    independent_system: bool = False


@dataclass(frozen=True)
class RectilinearVectorField:
    values: FloatArray
    x: FloatArray
    y: FloatArray
    mask: BoolArray
    coordinate_unit: str
    velocity_unit: str
    hierarchy: Hierarchy
    projection_id: str
    component_basis: str = "CARTESIAN_X_Y"
    orientation: str = "X_RIGHT_Y_UP_CCW_POSITIVE"
    boundary: str = "SECOND_ORDER_ONE_SIDED_COMPLETE_STENCIL"
    geometry_kind: str = "RECTILINEAR_VECTOR_2D"
    time: FloatArray | None = None
    time_unit: str | None = None
    provenance: str = "RAW_OBSERVATION"

    def __post_init__(self) -> None:
        values = np.asarray(self.values, dtype=np.float64)
        x, y = np.asarray(self.x, dtype=np.float64), np.asarray(self.y, dtype=np.float64)
        mask = np.asarray(self.mask)
        if self.geometry_kind != "RECTILINEAR_VECTOR_2D":
            raise ValueError("unsupported geometry: validated rectilinear 2D only")
        if (
            self.component_basis != "CARTESIAN_X_Y"
            or self.orientation != "X_RIGHT_Y_UP_CCW_POSITIVE"
        ):
            raise ValueError("unregistered basis/orientation convention")
        if self.boundary != "SECOND_ORDER_ONE_SIDED_COMPLETE_STENCIL":
            raise ValueError("unregistered boundary stencil")
        if self.coordinate_unit not in _LENGTH or self.velocity_unit not in _VELOCITY:
            raise ValueError("unregistered coordinate or velocity units")
        if not self.projection_id or not all(
            (self.hierarchy.system, self.hierarchy.campaign, self.hierarchy.acquisition)
        ):
            raise ValueError("projection and hierarchy identities are mandatory")
        if x.ndim != 1 or y.ndim != 1 or min(x.size, y.size) < 3:
            raise ValueError("at least three coordinates per rectilinear axis required")
        for axis in (x, y):
            d = np.diff(axis)
            if not np.all(np.isfinite(axis)) or not (np.all(d > 0) or np.all(d < 0)):
                raise ValueError("coordinates must be finite and strictly monotone")
        if values.ndim not in (3, 4) or values.shape[-3:] != (len(y), len(x), 2):
            raise ValueError("values require (y,x,2) or (time,y,x,2)")
        if mask.dtype != np.bool_ or mask.shape != values.shape[:-1]:
            raise ValueError("explicit boolean mask must match all sample axes")
        if not np.all(np.isfinite(values[mask])):
            raise ValueError("observed velocity must be finite")
        if values.ndim == 4:
            t = np.asarray(self.time, dtype=np.float64)
            if (
                t.ndim != 1
                or len(t) != len(values)
                or not np.all(np.isfinite(t))
                or not np.all(np.diff(t) > 0)
            ):
                raise ValueError("chronological time must align with frames")
            if self.time_unit not in {"s", "ms", "1"}:
                raise ValueError("time units must be registered")
        elif self.time is not None:
            raise ValueError("a single frame cannot carry a time array")
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)
        object.__setattr__(self, "mask", mask)


@dataclass(frozen=True)
class DerivativeResult:
    curl: FloatArray
    divergence: FloatArray
    support: BoolArray
    area_weights: FloatArray
    derivative_unit: str
    area_unit: str
    operator_id: str = OPERATOR_ID


def _stencils(coordinates: FloatArray) -> tuple[NDArray[np.int64], FloatArray]:
    n = len(coordinates)
    centers = np.clip(np.arange(n), 1, n - 2)
    indices = centers[:, None] + np.array([-1, 0, 1])[None, :]
    delta = coordinates[indices] - coordinates[:, None]
    # Solve the polynomial moments: sum(w)=0, sum(w*dx)=1, sum(w*dx^2)=0.
    matrix = np.stack((np.ones_like(delta), delta, delta**2), axis=1)
    target = np.broadcast_to(np.array([0.0, 1.0, 0.0]), (n, 3))
    return indices, np.linalg.solve(matrix, target[..., None])[..., 0]


def _differentiate(
    values: FloatArray, mask: BoolArray, coordinates: FloatArray, axis: int
) -> tuple[FloatArray, BoolArray]:
    indices, weights = _stencils(coordinates)
    moved, valid = np.moveaxis(values, axis, -1), np.moveaxis(mask, axis, -1)
    support = np.all(valid[..., indices], axis=-1)
    # Missing entries stay NaN in this temporary buffer; never physical zeros.
    observations = np.where(valid, moved, np.nan)
    result = np.sum(observations[..., indices] * weights, axis=-1)
    return np.moveaxis(np.where(support, result, np.nan), -1, axis), np.moveaxis(support, -1, axis)


def area_weights(x: FloatArray, y: FloatArray) -> FloatArray:
    """Tensor trapezoid weights over the bounded coordinate domain, not exterior cells."""

    def weights(axis: FloatArray) -> FloatArray:
        d = np.abs(np.diff(axis))
        return np.r_[d[0] / 2, (d[:-1] + d[1:]) / 2, d[-1] / 2]

    return weights(y)[:, None] * weights(x)[None, :]


def derivatives(field: RectilinearVectorField) -> DerivativeResult:
    x = field.x * _LENGTH[field.coordinate_unit]
    y = field.y * _LENGTH[field.coordinate_unit]
    velocity = field.values * _VELOCITY[field.velocity_unit]
    du_dx, sx = _differentiate(velocity[..., 0], field.mask, x, -1)
    du_dy, sy = _differentiate(velocity[..., 0], field.mask, y, -2)
    dv_dx, _ = _differentiate(velocity[..., 1], field.mask, x, -1)
    dv_dy, _ = _differentiate(velocity[..., 1], field.mask, y, -2)
    support = sx & sy & field.mask
    numerator = "m/s" if field.velocity_unit != "1" else "1"
    denominator = "m" if field.coordinate_unit in {"m", "mm", "cm"} else field.coordinate_unit
    unit = "s^-1" if numerator == "m/s" and denominator == "m" else f"({numerator})/({denominator})"
    return DerivativeResult(
        np.where(support, dv_dx - du_dy, np.nan),
        np.where(support, du_dx + dv_dy, np.nan),
        support,
        area_weights(x, y),
        unit,
        f"{denominator}^2",
    )


def field_from_coordinate_mesh(
    *, values: FloatArray, x_mesh: FloatArray, y_mesh: FloatArray, mask: BoolArray, **metadata: Any
) -> RectilinearVectorField:
    """Resolve grid axes from registered coordinate arrays, never array-shape labels.

    Components already represent Cartesian X/Y; only sample axes are transposed.
    Nonrectilinear meshes are rejected instead of silently rasterized.
    """
    x, y = np.asarray(x_mesh), np.asarray(y_mesh)
    if x.ndim != 2 or x.shape != y.shape or values.shape[-3:-1] != x.shape:
        raise ValueError("coordinate mesh and sample axes must align")
    if np.array_equal(x, np.broadcast_to(x[0:1, :], x.shape)) and np.array_equal(
        y, np.broadcast_to(y[:, 0:1], y.shape)
    ):
        return RectilinearVectorField(values=values, x=x[0], y=y[:, 0], mask=mask, **metadata)
    if np.array_equal(x, np.broadcast_to(x[:, 0:1], x.shape)) and np.array_equal(
        y, np.broadcast_to(y[0:1, :], y.shape)
    ):
        return RectilinearVectorField(
            values=np.swapaxes(values, -3, -2),
            x=x[:, 0],
            y=y[0],
            mask=np.swapaxes(mask, -2, -1),
            **metadata,
        )
    raise ValueError("unsupported nonrectilinear coordinate mesh; metric/projection required")


def regional_summary(result: DerivativeResult, region: BoolArray | None = None) -> dict[str, Any]:
    if result.curl.ndim != 2:
        raise ValueError("regional summaries are acquisition-local frames; do not pool time")
    support = result.support.copy()
    if region is not None:
        if np.asarray(region).dtype != np.bool_ or region.shape != support.shape:
            raise ValueError("region must be an aligned boolean mask")
        support &= region
    if not np.any(support):
        return {"status": "NO_VALID_SUPPORT", "supported_cells": 0}
    w, curl, div = result.area_weights[support], result.curl[support], result.divergence[support]
    positive = float(np.sum(w * np.maximum(curl, 0)))
    negative = float(np.sum(w * np.minimum(curl, 0)))
    absolute = positive - negative
    net = positive + negative
    order = np.argsort(curl)
    cdf = (np.cumsum(w[order]) - w[order] / 2) / np.sum(w)
    return {
        "status": "COMPUTED_DESCRIPTIVE",
        "operator_id": result.operator_id,
        "supported_cells": int(np.sum(support)),
        "domain_cells": int(support.size),
        "supported_area": float(np.sum(w)),
        "area_unit": result.area_unit,
        "curl_unit": result.derivative_unit,
        "signed_mean_curl": float(np.average(curl, weights=w)),
        "curl_energy": float(np.average(curl**2, weights=w)),
        "divergence_energy": float(np.average(div**2, weights=w)),
        "positive_vorticity_integral": positive,
        "negative_vorticity_integral": negative,
        "net_vorticity_integral": net,
        "absolute_vorticity_integral": absolute,
        "circulation_integral_unit": f"({result.derivative_unit})*({result.area_unit})",
        "cancellation_fraction": None if absolute == 0 else 1 - abs(net) / absolute,
        "area_weighted_curl_quantiles": np.interp(
            [0.025, 0.25, 0.5, 0.75, 0.975], cdf, curl[order]
        ).tolist(),
        "uncertainty": (
            "NO_INSTRUMENT_CI; numerical convergence and support sensitivity "
            "are separate diagnostics"
        ),
    }


def circulation(field: RectilinearVectorField, loop_yx: list[tuple[int, int]]) -> dict[str, Any]:
    """Trapezoidal line integral on a registered simple axis-adjacent sample loop."""
    if field.values.ndim != 3 or len(loop_yx) < 4 or len(set(loop_yx)) != len(loop_yx):
        raise ValueError("requires a simple loop of at least four distinct sample indices")
    indices = np.asarray(loop_yx, dtype=int)
    if (
        np.any(indices < 0)
        or np.any(indices[:, 0] >= len(field.y))
        or np.any(indices[:, 1] >= len(field.x))
    ):
        raise ValueError("loop outside field")
    if np.any(np.sum(np.abs(np.roll(indices, -1, axis=0) - indices), axis=1) != 1):
        raise ValueError("loop edges must be grid-adjacent; no implicit interpolation")
    yy, xx = indices[:, 0], indices[:, 1]
    if not np.all(field.mask[yy, xx]):
        return {"status": "UNDEFINED_MISSING_LOOP_SAMPLES", "circulation": None}
    points = np.stack((field.x[xx], field.y[yy]), axis=-1) * _LENGTH[field.coordinate_unit]
    values = field.values[yy, xx] * _VELOCITY[field.velocity_unit]
    integral = np.sum(
        (values + np.roll(values, -1, axis=0)) / 2 * (np.roll(points, -1, axis=0) - points)
    )
    signed_area = 0.5 * np.sum(
        points[:, 0] * np.roll(points[:, 1], -1) - points[:, 1] * np.roll(points[:, 0], -1)
    )
    return {
        "status": "COMPUTED",
        "circulation": float(integral),
        "signed_loop_area": float(signed_area),
        "loop_orientation": "CCW" if signed_area > 0 else "CW",
        "quadrature": "TRAPEZOID_ON_REGISTERED_EDGES",
        "circulation_unit": (
            f"{'m/s' if field.velocity_unit != '1' else '1'} * "
            f"{'m' if field.coordinate_unit in {'m', 'mm', 'cm'} else field.coordinate_unit}"
        ),
        "uncertainty": "DISCRETIZATION_NOT_AN_INSTRUMENT_CONFIDENCE_INTERVAL",
    }


def frame_at(field: RectilinearVectorField, index: int) -> RectilinearVectorField:
    if field.values.ndim != 4:
        raise ValueError("requires time-resolved field")
    return replace(
        field,
        values=field.values[index],
        mask=field.mask[index],
        time=None,
        time_unit=None,
        projection_id=f"{field.projection_id}:frame:{index}",
    )


def nondimensionalize(
    field: RectilinearVectorField, *, length_m: float, speed_m_per_s: float
) -> RectilinearVectorField:
    if field.coordinate_unit not in {"m", "mm", "cm"} or field.velocity_unit not in {
        "m/s",
        "mm/s",
        "cm/s",
    }:
        raise ValueError("physical units required before nondimensionalization")
    if not np.isfinite(length_m + speed_m_per_s) or min(length_m, speed_m_per_s) <= 0:
        raise ValueError("positive finite reference scales required")
    return replace(
        field,
        x=field.x * _LENGTH[field.coordinate_unit] / length_m,
        y=field.y * _LENGTH[field.coordinate_unit] / length_m,
        values=field.values * _VELOCITY[field.velocity_unit] / speed_m_per_s,
        coordinate_unit="1",
        velocity_unit="1",
        projection_id=f"{field.projection_id}:nondimensional:L={length_m}:U={speed_m_per_s}",
    )


def rotate90(field: RectilinearVectorField) -> RectilinearVectorField:
    moved = np.swapaxes(field.values, -3, -2)
    values = np.stack((-moved[..., 1], moved[..., 0]), axis=-1)
    return replace(
        field,
        x=-field.y,
        y=field.x,
        values=values,
        mask=np.swapaxes(field.mask, -2, -1),
        projection_id=f"{field.projection_id}:proper-rotation-pi/2",
    )


def reflect_y(field: RectilinearVectorField) -> RectilinearVectorField:
    values = field.values.copy()
    values[..., 1] *= -1
    return replace(
        field,
        y=-field.y,
        values=values,
        projection_id=f"{field.projection_id}:spatial-reflection-y",
    )


def reorder(
    field: RectilinearVectorField, *, reverse_x: bool = False, reverse_y: bool = False
) -> RectilinearVectorField:
    sx, sy = slice(None, None, -1 if reverse_x else 1), slice(None, None, -1 if reverse_y else 1)
    return replace(
        field,
        x=field.x[sx],
        y=field.y[sy],
        values=field.values[..., sy, sx, :],
        mask=field.mask[..., sy, sx],
        projection_id=f"{field.projection_id}:reordered",
    )


def resample_bilinear(
    field: RectilinearVectorField, x: FloatArray, y: FloatArray, *, error_bound: float
) -> RectilinearVectorField:
    """Declared reconstruction; all four input corners required, no extrapolation.

    error_bound is a caller-supplied absolute component bound justified by their
    reference/convergence study. It is recorded, not estimated from observations.
    """
    if field.values.ndim != 3 or not np.isfinite(error_bound) or error_bound < 0:
        raise ValueError("single frame and finite declared interpolation error required")
    source = reorder(field, reverse_x=field.x[0] > field.x[-1], reverse_y=field.y[0] > field.y[-1])
    x, y = np.asarray(x), np.asarray(y)
    if (
        x.min() < source.x[0]
        or x.max() > source.x[-1]
        or y.min() < source.y[0]
        or y.max() > source.y[-1]
    ):
        raise ValueError("extrapolation forbidden")
    ix = np.clip(np.searchsorted(source.x, x) - 1, 0, len(source.x) - 2)
    iy = np.clip(np.searchsorted(source.y, y) - 1, 0, len(source.y) - 2)
    a = (x - source.x[ix]) / (source.x[ix + 1] - source.x[ix])
    b = (y - source.y[iy]) / (source.y[iy + 1] - source.y[iy])
    output = np.zeros((len(y), len(x), 2))
    mask = np.ones((len(y), len(x)), dtype=bool)
    for dy, wy in ((0, 1 - b), (1, b)):
        for dx, wx in ((0, 1 - a), (1, a)):
            corner_mask = source.mask[(iy + dy)[:, None], (ix + dx)[None, :]]
            mask &= corner_mask
            corner = source.values[(iy + dy)[:, None], (ix + dx)[None, :]]
            output += (
                np.where(corner_mask[..., None], corner, np.nan)
                * wy[:, None, None]
                * wx[None, :, None]
            )
    output[~mask] = np.nan
    return replace(
        field,
        x=x,
        y=y,
        values=output,
        mask=mask,
        projection_id=f"{field.projection_id}:bilinear",
        provenance=(
            f"RECONSTRUCTED_BILINEAR; declared_component_error_bound={error_bound} "
            f"{field.velocity_unit}; NOT_OBSERVATIONS"
        ),
    )
