from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import NDArray

from torusbrot.tld.scoring import score_ladder

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


class GeometryKind(StrEnum):
    SCALAR_FIELD_2D = "ScalarField2D"
    VECTOR_FIELD_2D = "VectorField2D"
    SCALAR_VOLUME_3D = "ScalarVolume3D"
    VECTOR_VOLUME_3D = "VectorVolume3D"
    SPATIOTEMPORAL_SCALAR = "SpatiotemporalScalarField"
    SPATIOTEMPORAL_VECTOR = "SpatiotemporalVectorField"
    IRREGULAR_POINT_FIELD = "IrregularPointField"
    WEIGHTED_GRAPH = "WeightedGraphGeometry"
    DIRECTED_GRAPH = "DirectedGraphGeometry"
    CORRELATION = "CorrelationGeometry"
    MANIFOLD_POINT_CLOUD = "ManifoldPointCloud"
    MULTICOMPONENT_SINGLE_SYSTEM = "MultiComponentSingleSystemField"
    COUPLED_MULTI_SYSTEM = "CoupledMultiSystemField"


@dataclass(frozen=True)
class TypedGeometry:
    kind: GeometryKind
    values: FloatArray
    coordinates: FloatArray | None = None
    mask: BoolArray | None = None
    time: FloatArray | None = None
    component_names: tuple[str, ...] = ()
    orientation: str | None = None
    projection_id: str | None = None


@dataclass(frozen=True)
class PathEmbedding:
    representation: str
    values: FloatArray
    coordinates: FloatArray
    adjacency: FloatArray | None = None


def _finite_where_masked(values: FloatArray, mask: BoolArray) -> bool:
    expanded = mask
    while expanded.ndim < values.ndim:
        expanded = expanded[..., np.newaxis]
    return bool(np.all(np.isfinite(values[np.broadcast_to(expanded, values.shape)])))


def validate_typed_geometry(geometry: TypedGeometry) -> None:
    values = np.asarray(geometry.values, dtype=np.float64)
    component_axis_kinds = {
        GeometryKind.VECTOR_FIELD_2D,
        GeometryKind.VECTOR_VOLUME_3D,
        GeometryKind.SPATIOTEMPORAL_VECTOR,
        GeometryKind.MULTICOMPONENT_SINGLE_SYSTEM,
        GeometryKind.COUPLED_MULTI_SYSTEM,
    }
    point_kinds = {GeometryKind.IRREGULAR_POINT_FIELD, GeometryKind.MANIFOLD_POINT_CLOUD}
    if values.size == 0:
        raise ValueError("typed geometry values cannot be empty")
    if geometry.mask is None:
        if geometry.kind in component_axis_kinds:
            mask = np.ones(values.shape[:-1], dtype=bool)
        elif geometry.kind in point_kinds:
            mask = np.ones(values.shape[:1], dtype=bool)
        else:
            mask = np.ones(values.shape, dtype=bool)
    else:
        mask = np.asarray(geometry.mask, dtype=bool)
    if geometry.kind == GeometryKind.SCALAR_FIELD_2D and values.ndim != 2:
        raise ValueError("ScalarField2D requires (y, x) values")
    if geometry.kind == GeometryKind.VECTOR_FIELD_2D:
        if values.ndim != 3 or values.shape[-1] != 2:
            raise ValueError("VectorField2D requires (y, x, 2) values")
        if len(geometry.component_names) != 2:
            raise ValueError("VectorField2D requires two registered component names")
    if geometry.kind == GeometryKind.SCALAR_VOLUME_3D and values.ndim != 3:
        raise ValueError("ScalarVolume3D requires (z, y, x) values")
    if geometry.kind == GeometryKind.VECTOR_VOLUME_3D:
        if values.ndim != 4 or values.shape[-1] != 3:
            raise ValueError("VectorVolume3D requires (z, y, x, 3) values")
        if len(geometry.component_names) != 3:
            raise ValueError("VectorVolume3D requires three registered component names")
    if geometry.kind == GeometryKind.SPATIOTEMPORAL_SCALAR:
        if values.ndim != 3 or geometry.time is None or len(geometry.time) != values.shape[0]:
            raise ValueError("SpatiotemporalScalarField requires (time, y, x) and time coordinates")
    if geometry.kind == GeometryKind.SPATIOTEMPORAL_VECTOR:
        if (
            values.ndim != 4
            or values.shape[-1] != 2
            or geometry.time is None
            or len(geometry.time) != values.shape[0]
        ):
            raise ValueError(
                "SpatiotemporalVectorField requires (time, y, x, 2) and time coordinates"
            )
        if len(geometry.component_names) != 2:
            raise ValueError("SpatiotemporalVectorField requires two registered components")
    if geometry.kind in point_kinds:
        coordinates = (
            None
            if geometry.coordinates is None
            else np.asarray(geometry.coordinates, dtype=np.float64)
        )
        if coordinates is None or coordinates.ndim != 2:
            raise ValueError(f"{geometry.kind} requires explicit point coordinates")
        if len(coordinates) != len(values):
            raise ValueError(f"{geometry.kind} coordinates and values must align")
    if geometry.kind in {
        GeometryKind.MULTICOMPONENT_SINGLE_SYSTEM,
        GeometryKind.COUPLED_MULTI_SYSTEM,
    }:
        if values.ndim not in {3, 4} or values.shape[-1] < 2:
            raise ValueError("multicomponent geometry requires (..., components) values")
        if len(geometry.component_names) != values.shape[-1]:
            raise ValueError("every multicomponent channel requires a registered name")
    if geometry.kind in {GeometryKind.WEIGHTED_GRAPH, GeometryKind.DIRECTED_GRAPH}:
        if values.ndim != 2 or values.shape[0] != values.shape[1]:
            raise ValueError("Graph geometry requires a square adjacency matrix")
        if geometry.kind == GeometryKind.WEIGHTED_GRAPH and np.all((values == 0) | (values == 1)):
            raise ValueError("WeightedGraphGeometry requires retained nonbinary weights")
        if geometry.kind == GeometryKind.DIRECTED_GRAPH and np.allclose(values, values.T):
            raise ValueError("DirectedGraphGeometry requires retained direction")
    if geometry.kind == GeometryKind.CORRELATION:
        if values.ndim != 2 or values.shape[0] != values.shape[1]:
            raise ValueError("CorrelationGeometry requires a square matrix")
        if not np.allclose(values, values.T) or not np.allclose(np.diag(values), 1.0):
            raise ValueError("CorrelationGeometry must be symmetric with unit diagonal")
    if geometry.kind in component_axis_kinds:
        expected_mask_shape = values.shape[:-1]
    elif geometry.kind in point_kinds:
        expected_mask_shape = values.shape[:1]
    else:
        expected_mask_shape = values.shape
    if mask.shape != expected_mask_shape:
        raise ValueError(f"mask shape {mask.shape} does not match {expected_mask_shape}")
    if not _finite_where_masked(values, mask):
        raise ValueError("observed values must be finite; missingness belongs in the mask")
    if geometry.projection_id is None:
        raise ValueError("every typed geometry requires a registered projection_id")


def _masked_neighbor_coherence(values: FloatArray, mask: BoolArray) -> float:
    observed = values[mask]
    centered = values - float(np.mean(observed))
    variance = float(np.mean(centered[mask] ** 2))
    if variance <= np.finfo(float).eps:
        return 0.0
    products: list[FloatArray] = []
    horizontal = mask[:, :-1] & mask[:, 1:]
    if np.any(horizontal):
        products.append(centered[:, :-1][horizontal] * centered[:, 1:][horizontal])
    vertical = mask[:-1, :] & mask[1:, :]
    if np.any(vertical):
        products.append(centered[:-1, :][vertical] * centered[1:, :][vertical])
    if not products:
        return 0.0
    return float(np.mean(np.concatenate(products)) / variance)


def _masked_spectral_concentration(values: FloatArray, mask: BoolArray) -> float:
    observed = values[mask]
    centered = np.zeros_like(values, dtype=np.float64)
    centered[mask] = values[mask] - float(np.mean(observed))
    spectrum = np.abs(np.fft.fft2(centered)) ** 2
    spectrum.flat[0] = 0.0
    ordered = np.sort(spectrum.ravel())
    tail = max(1, int(np.ceil(0.05 * len(ordered))))
    return float(np.sum(ordered[-tail:]) / max(float(np.sum(ordered)), np.finfo(float).eps))


def _scalar_2d_scores(values: FloatArray, mask: BoolArray) -> dict[str, float]:
    return {
        "neighbor_coherence": _masked_neighbor_coherence(values, mask),
        "spectral_concentration": _masked_spectral_concentration(values, mask),
    }


def _lag1(values: FloatArray) -> float:
    if len(values) <= 2 or np.std(values) <= np.finfo(float).eps:
        return 0.0
    return float(np.corrcoef(values[:-1], values[1:])[0, 1])


def _scalar_volume_scores(values: FloatArray, mask: BoolArray) -> dict[str, float]:
    slice_scores = [_scalar_2d_scores(frame, mask[index]) for index, frame in enumerate(values)]
    slice_means = np.asarray(
        [float(np.mean(frame[mask[index]])) for index, frame in enumerate(values)]
    )
    return {
        "median_slice_neighbor_coherence": float(
            np.median([row["neighbor_coherence"] for row in slice_scores])
        ),
        "median_slice_spectral_concentration": float(
            np.median([row["spectral_concentration"] for row in slice_scores])
        ),
        "depth_lag1_slice_mean": _lag1(slice_means),
    }


def _vector_volume_scores(values: FloatArray, mask: BoolArray) -> dict[str, float]:
    prepared = np.where(mask[..., np.newaxis], values, 0.0)
    u, v, w = (prepared[..., index] for index in range(3))
    du_dz, du_dy, du_dx = np.gradient(u)
    dv_dz, dv_dy, dv_dx = np.gradient(v)
    dw_dz, dw_dy, dw_dx = np.gradient(w)
    curl_x = dw_dy - dv_dz
    curl_y = du_dz - dw_dx
    curl_z = dv_dx - du_dy
    divergence = du_dx + dv_dy + dw_dz
    curl_energy = float(
        np.mean((curl_x[mask] ** 2) + (curl_y[mask] ** 2) + (curl_z[mask] ** 2))
    )
    mean_curl_squared = float(
        np.mean(curl_x[mask]) ** 2
        + np.mean(curl_y[mask]) ** 2
        + np.mean(curl_z[mask]) ** 2
    )
    return {
        "u_volume_neighbor_coherence": _scalar_volume_scores(u, mask)[
            "median_slice_neighbor_coherence"
        ],
        "v_volume_neighbor_coherence": _scalar_volume_scores(v, mask)[
            "median_slice_neighbor_coherence"
        ],
        "w_volume_neighbor_coherence": _scalar_volume_scores(w, mask)[
            "median_slice_neighbor_coherence"
        ],
        "curl_energy_3d": curl_energy,
        "curl_coherence_3d": mean_curl_squared
        / max(curl_energy, np.finfo(float).eps),
        "divergence_energy_3d": float(np.mean(divergence[mask] ** 2)),
    }


def typed_projection_scores(geometry: TypedGeometry) -> dict[str, float]:
    """Project a typed geometry without silent scalarization or dimensional collapse."""

    validate_typed_geometry(geometry)
    values = np.asarray(geometry.values, dtype=np.float64)
    component_axis_kinds = {
        GeometryKind.VECTOR_FIELD_2D,
        GeometryKind.VECTOR_VOLUME_3D,
        GeometryKind.SPATIOTEMPORAL_VECTOR,
        GeometryKind.MULTICOMPONENT_SINGLE_SYSTEM,
        GeometryKind.COUPLED_MULTI_SYSTEM,
    }
    point_kinds = {GeometryKind.IRREGULAR_POINT_FIELD, GeometryKind.MANIFOLD_POINT_CLOUD}
    if geometry.mask is not None:
        mask = np.asarray(geometry.mask, dtype=bool)
    elif geometry.kind in component_axis_kinds:
        mask = np.ones(values.shape[:-1], dtype=bool)
    elif geometry.kind in point_kinds:
        mask = np.ones(values.shape[:1], dtype=bool)
    else:
        mask = np.ones(values.shape, dtype=bool)
    if geometry.kind == GeometryKind.SCALAR_FIELD_2D:
        return _scalar_2d_scores(values, mask)
    if geometry.kind == GeometryKind.VECTOR_FIELD_2D:
        u = np.where(mask, values[..., 0], 0.0)
        v = np.where(mask, values[..., 1], 0.0)
        du_dy, du_dx = np.gradient(u)
        dv_dy, dv_dx = np.gradient(v)
        curl = dv_dx - du_dy
        divergence = du_dx + dv_dy
        curl_energy = float(np.mean(curl[mask] ** 2))
        signed_mean_curl = float(np.mean(curl[mask]))
        return {
            "u_neighbor_coherence": _masked_neighbor_coherence(u, mask),
            "v_neighbor_coherence": _masked_neighbor_coherence(v, mask),
            "signed_mean_curl": signed_mean_curl,
            "curl_energy": curl_energy,
            "curl_coherence": signed_mean_curl**2
            / max(curl_energy, np.finfo(float).eps),
            "divergence_energy": float(np.mean(divergence[mask] ** 2)),
        }
    if geometry.kind == GeometryKind.SCALAR_VOLUME_3D:
        return _scalar_volume_scores(values, mask)
    if geometry.kind == GeometryKind.VECTOR_VOLUME_3D:
        return _vector_volume_scores(values, mask)
    if geometry.kind == GeometryKind.SPATIOTEMPORAL_SCALAR:
        frame_scores = [_scalar_2d_scores(frame, mask[index]) for index, frame in enumerate(values)]
        frame_means = np.asarray(
            [float(np.mean(frame[mask[index]])) for index, frame in enumerate(values)]
        )
        return {
            "median_frame_neighbor_coherence": float(
                np.median([row["neighbor_coherence"] for row in frame_scores])
            ),
            "median_frame_spectral_concentration": float(
                np.median([row["spectral_concentration"] for row in frame_scores])
            ),
            "temporal_lag1_frame_mean": _lag1(frame_means),
        }
    if geometry.kind == GeometryKind.SPATIOTEMPORAL_VECTOR:
        frame_rows = [
            typed_projection_scores(
                TypedGeometry(
                    kind=GeometryKind.VECTOR_FIELD_2D,
                    values=frame,
                    mask=mask[index],
                    component_names=geometry.component_names,
                    orientation=geometry.orientation,
                    projection_id=f"{geometry.projection_id}:frame",
                )
            )
            for index, frame in enumerate(values)
        ]
        return {
            f"median_{key}": float(np.median([row[key] for row in frame_rows]))
            for key in frame_rows[0]
        }
    if geometry.kind in {
        GeometryKind.MULTICOMPONENT_SINGLE_SYSTEM,
        GeometryKind.COUPLED_MULTI_SYSTEM,
    }:
        output: dict[str, float] = {}
        for index, name in enumerate(geometry.component_names):
            component = values[..., index]
            scores = (
                _scalar_2d_scores(component, mask)
                if component.ndim == 2
                else _scalar_volume_scores(component, mask)
            )
            output.update({f"component:{name}:{key}": value for key, value in scores.items()})
        observed = values[mask]
        correlations = np.corrcoef(observed, rowvar=False)
        for left in range(len(geometry.component_names)):
            for right in range(left + 1, len(geometry.component_names)):
                output[
                    f"cross_component_correlation:{geometry.component_names[left]}:"
                    f"{geometry.component_names[right]}"
                ] = float(correlations[left, right])
        return output
    if geometry.kind in {GeometryKind.WEIGHTED_GRAPH, GeometryKind.DIRECTED_GRAPH}:
        eigenvalues = np.linalg.eigvals(values)
        spectral_radius = float(np.max(np.abs(eigenvalues)))
        total_weight = float(np.sum(np.abs(values)))
        reciprocity = float(
            np.sum(np.minimum(np.abs(values), np.abs(values.T)))
            / max(total_weight, np.finfo(float).eps)
        )
        return_traces = [
            abs(float(np.trace(np.linalg.matrix_power(values, power))))
            / max(
                len(values) * max(spectral_radius, np.finfo(float).eps) ** power,
                np.finfo(float).eps,
            )
            for power in range(2, len(values) + 1)
        ]
        return {
            "spectral_radius": spectral_radius,
            "weighted_reciprocity": reciprocity,
            "signed_three_cycle_trace": float(np.trace(values @ values @ values)),
            "normalized_three_cycle_trace": float(np.trace(values @ values @ values))
            / max(total_weight**3, np.finfo(float).eps),
            "maximum_normalized_return_trace": max(return_traces),
            "total_absolute_edge_weight": total_weight,
        }
    if geometry.kind in {GeometryKind.IRREGULAR_POINT_FIELD, GeometryKind.MANIFOLD_POINT_CLOUD}:
        coordinates = np.asarray(geometry.coordinates, dtype=np.float64)
        observed_coordinates = coordinates[mask]
        centered = observed_coordinates - np.mean(observed_coordinates, axis=0, keepdims=True)
        singular = np.linalg.svd(centered, compute_uv=False)
        anisotropy = float(singular[0] / max(singular[-1], np.finfo(float).eps))
        if values.ndim == 1:
            point_values = values[mask]
        elif values.shape[-1] == 1:
            point_values = values[mask, 0]
        else:
            raise ValueError("vector point fields require an explicitly registered vector handler")
        distances = np.linalg.norm(
            observed_coordinates[:, None, :] - observed_coordinates[None, :, :], axis=-1
        )
        np.fill_diagonal(distances, np.inf)
        neighbor = np.argmin(distances, axis=1)
        centered_values = point_values - float(np.mean(point_values))
        variance = float(np.mean(centered_values**2))
        local = float(
            np.mean(centered_values * centered_values[neighbor])
            / max(variance, np.finfo(float).eps)
        )
        return {"coordinate_anisotropy": anisotropy, "nearest_neighbor_value_coherence": local}
    if geometry.kind == GeometryKind.CORRELATION:
        eigenvalues = np.linalg.eigvalsh(values)
        return {
            "effective_rank": float(
                np.exp(
                    -np.sum(
                        (eigenvalues / max(float(np.sum(eigenvalues)), np.finfo(float).eps))
                        * np.log(
                            np.maximum(
                                eigenvalues
                                / max(float(np.sum(eigenvalues)), np.finfo(float).eps),
                                np.finfo(float).eps,
                            )
                        )
                    )
                )
            ),
            "minimum_eigenvalue": float(eigenvalues[0]),
        }
    raise ValueError(f"no registered projection handler for {geometry.kind}")


def rotate_vector_field_90(geometry: TypedGeometry) -> TypedGeometry:
    if geometry.kind not in {
        GeometryKind.VECTOR_FIELD_2D,
        GeometryKind.SPATIOTEMPORAL_VECTOR,
    }:
        raise ValueError("90-degree component rotation requires a 2D vector field")
    validate_typed_geometry(geometry)
    axes = (0, 1) if geometry.kind == GeometryKind.VECTOR_FIELD_2D else (1, 2)
    moved = np.rot90(geometry.values, axes=axes)
    rotated = np.empty_like(moved)
    rotated[..., 0] = -moved[..., 1]
    rotated[..., 1] = moved[..., 0]
    mask = None if geometry.mask is None else np.rot90(geometry.mask, axes=axes)
    coordinates = None
    if geometry.coordinates is not None:
        coordinate_axes = axes
        if geometry.kind == GeometryKind.SPATIOTEMPORAL_VECTOR:
            coordinate_axes = (0, 1) if geometry.coordinates.ndim == 3 else (1, 2)
        moved_coordinates = np.rot90(geometry.coordinates, axes=coordinate_axes)
        coordinates = np.empty_like(moved_coordinates)
        coordinates[..., 0] = -moved_coordinates[..., 1]
        coordinates[..., 1] = moved_coordinates[..., 0]
    return replace(
        geometry,
        values=rotated,
        coordinates=coordinates,
        mask=mask,
        orientation=f"rot90({geometry.orientation or 'registered'})",
        projection_id=f"{geometry.projection_id}:rot90",
    )


def reflect_vector_field_y(geometry: TypedGeometry) -> TypedGeometry:
    if geometry.kind != GeometryKind.VECTOR_FIELD_2D:
        raise ValueError("y reflection requires VectorField2D")
    validate_typed_geometry(geometry)
    moved = np.flip(geometry.values, axis=0).copy()
    moved[..., 1] *= -1.0
    mask = None if geometry.mask is None else np.flip(geometry.mask, axis=0).copy()
    coordinates = None
    if geometry.coordinates is not None:
        coordinates = np.flip(geometry.coordinates, axis=0).copy()
        coordinates[..., 1] *= -1.0
    return replace(
        geometry,
        values=moved,
        coordinates=coordinates,
        mask=mask,
        orientation=f"reflect_y({geometry.orientation or 'registered'})",
        projection_id=f"{geometry.projection_id}:reflect-y",
    )


def anti_alias_downsample_2d(geometry: TypedGeometry, factor: int = 2) -> TypedGeometry:
    if factor < 2:
        raise ValueError("downsampling factor must be at least two")
    if geometry.kind not in {GeometryKind.SCALAR_FIELD_2D, GeometryKind.VECTOR_FIELD_2D}:
        raise ValueError("registered 2D downsampling supports scalar/vector fields only")
    validate_typed_geometry(geometry)
    values = np.asarray(geometry.values, dtype=np.float64)
    height = values.shape[0] // factor * factor
    width = values.shape[1] // factor * factor
    mask = (
        np.ones(values.shape[:2], dtype=bool)
        if geometry.mask is None
        else np.asarray(geometry.mask, dtype=bool)
    )[:height, :width]
    channels = 1 if values.ndim == 2 else values.shape[-1]
    source = values[:height, :width]
    if values.ndim == 2:
        source = source[..., np.newaxis]
    prepared = source.reshape(
        height // factor,
        factor,
        width // factor,
        factor,
        channels,
    )
    block_mask = mask.reshape(height // factor, factor, width // factor, factor)
    weights = block_mask[:, :, :, :, np.newaxis]
    sums = np.sum(np.where(weights, prepared, 0.0), axis=(1, 3))
    counts = np.sum(weights, axis=(1, 3))
    output_mask = counts[..., 0] > 0
    output = np.divide(
        sums,
        np.maximum(counts, 1),
        out=np.zeros_like(sums),
        where=counts > 0,
    )
    if values.ndim == 2:
        output = output[..., 0]
    return replace(
        geometry,
        values=np.asarray(output, dtype=np.float64),
        mask=output_mask,
        coordinates=None,
        projection_id=f"{geometry.projection_id}:antialias-{factor}",
    )


def joint_parent_null_distribution(
    observed_by_parent: FloatArray,
    null_children_by_parent: FloatArray,
    *,
    replicates: int = 999,
    seed: int = 300,
) -> dict[str, Any]:
    observed = np.asarray(observed_by_parent, dtype=np.float64)
    nulls = np.asarray(null_children_by_parent, dtype=np.float64)
    if observed.ndim != 1 or nulls.ndim != 2 or nulls.shape[0] != len(observed):
        raise ValueError("expected a parent vector and aligned parent-by-child null matrix")
    if replicates < 999:
        raise ValueError("joint null inference requires at least 999 replicates")
    if nulls.shape[1] < 2 or not np.all(np.isfinite(observed)) or not np.all(np.isfinite(nulls)):
        raise ValueError("joint null inputs must be finite with at least two children per parent")
    rng = np.random.default_rng(seed)
    selections = rng.integers(0, nulls.shape[1], size=(replicates, len(observed)))
    parent_indices = np.broadcast_to(np.arange(len(observed)), selections.shape)
    joint = np.median(nulls[parent_indices, selections], axis=1)
    aggregate = float(np.median(observed))
    upper = float((1 + np.sum(joint >= aggregate)) / (replicates + 1))
    lower = float((1 + np.sum(joint <= aggregate)) / (replicates + 1))
    two_sided = min(1.0, 2.0 * min(upper, lower))
    median_null = float(np.median(joint))
    null_scale = float(1.4826 * np.median(np.abs(joint - median_null)))
    return {
        "observed_population_statistic": aggregate,
        "joint_null_median": median_null,
        "observed_minus_joint_null": aggregate - median_null,
        "joint_null_robust_scale": null_scale,
        "robust_standardized_effect": (aggregate - median_null)
        / max(null_scale, np.finfo(float).eps),
        "upper_tail_p": upper,
        "lower_tail_p": lower,
        "two_sided_p": two_sided,
        "parent_count": len(observed),
        "joint_null_replicates": replicates,
        "children_flattened": False,
        "joint_null_values": [float(value) for value in joint],
    }


def modal_residual_trace(field: FloatArray, mode_counts: list[int]) -> FloatArray:
    values = np.asarray(field, dtype=np.float64)
    if values.ndim != 2 or not np.all(np.isfinite(values)):
        raise ValueError("modal residual diagnostic requires a finite 2D scalar field")
    centered = values - float(np.mean(values))
    power = np.sort((np.abs(np.fft.rfft2(centered)) ** 2).ravel())[::-1]
    total = max(float(np.sum(power)), np.finfo(float).eps)
    return np.asarray(
        [float(np.sum(power[count:]) / total) + np.finfo(float).eps for count in mode_counts]
    )


def _minimum_audit(trace: FloatArray, coordinates: list[int]) -> dict[str, Any]:
    values = np.asarray(trace, dtype=np.float64)
    minimum = float(np.min(values))
    tolerance = max(np.finfo(float).eps * 16.0, abs(minimum) * 1e-12)
    indices = np.flatnonzero(np.isclose(values, minimum, rtol=0.0, atol=tolerance))
    selected = [coordinates[int(index)] for index in indices]
    return {
        "minimum_coordinates": selected,
        "tie": len(selected) > 1,
        "boundary_minimum": bool(indices[0] == 0 or indices[-1] == len(values) - 1),
        "first_interior_pinning": bool(1 in indices),
        "last_interior_pinning": bool(len(values) - 2 in indices),
    }


def aggregate_modal_trace_audit(
    parent_traces: FloatArray,
    null_child_traces: FloatArray,
    coordinates: list[int],
    *,
    replicates: int = 999,
    seed: int = 300,
) -> dict[str, Any]:
    parents = np.asarray(parent_traces, dtype=np.float64)
    nulls = np.asarray(null_child_traces, dtype=np.float64)
    if parents.ndim != 2 or nulls.ndim != 3:
        raise ValueError("expected parent-by-coordinate and parent-by-child-by-coordinate traces")
    if nulls.shape[0] != parents.shape[0] or nulls.shape[2] != parents.shape[1]:
        raise ValueError("parent/null trace shapes do not align")
    observed = np.median(parents, axis=0)
    rng = np.random.default_rng(seed)
    choices = rng.integers(0, nulls.shape[1], size=(replicates, len(parents)))
    parent_indices = np.broadcast_to(np.arange(len(parents)), choices.shape)
    joint = np.median(nulls[parent_indices, choices, :], axis=1)
    audit = _minimum_audit(observed, coordinates)
    per_parent = [_minimum_audit(row, coordinates) for row in parents]
    return {
        "operator": "MODAL_RESIDUAL_DIAGNOSTIC_NOT_TLD_CLOSURE",
        "coordinates": coordinates,
        "observed_population_trace": [float(value) for value in observed],
        "joint_null_trace_count": replicates,
        "joint_null_traces": [[float(value) for value in row] for row in joint],
        "population_minimum_audit": audit,
        "per_parent_minimum_audits": per_parent,
        "null_children_flattened": False,
        "midpoint_penalty": None,
    }


def curvature_audit_v2(
    parent_traces: FloatArray,
    joint_null_traces: FloatArray,
    coordinates: list[int],
    *,
    bootstrap_samples: int = 999,
    seed: int = 300,
) -> dict[str, Any]:
    parents = np.asarray(parent_traces, dtype=np.float64)
    nulls = np.asarray(joint_null_traces, dtype=np.float64)
    observed = np.median(parents, axis=0)
    if parents.ndim != 2 or nulls.ndim != 2 or parents.shape[1] != len(coordinates):
        raise ValueError("curvature inputs must align on coordinates")
    if len(coordinates) < 5 or not np.all(observed > 0):
        raise ValueError("curvature requires at least five positive trace points")

    def curvature(trace: FloatArray) -> FloatArray:
        logged = np.log(trace)
        return -(logged[2:] - 2.0 * logged[1:-1] + logged[:-2])

    observed_curvature = curvature(observed)
    scale = float(1.4826 * np.median(np.abs(np.log(observed) - np.median(np.log(observed)))))
    if scale <= np.finfo(float).eps or np.ptp(observed_curvature) <= np.finfo(float).eps:
        return {
            "status": "REJECTED_FLAT_OR_TIED_TRACE",
            "selected_elbow": None,
            "candidate_elbows": [],
            "first_interior_pinning": False,
            "last_interior_pinning": False,
            "bootstrap_stability": None,
        }
    peak = float(np.max(observed_curvature))
    tolerance = max(abs(peak) * 1e-12, np.finfo(float).eps * 16.0)
    tied = np.flatnonzero(np.isclose(observed_curvature, peak, rtol=0.0, atol=tolerance))
    candidates = [coordinates[int(index) + 1] for index in np.argsort(observed_curvature)[::-1][:3]]
    selected = None if len(tied) != 1 else coordinates[int(tied[0]) + 1]
    null_peaks = np.asarray([np.max(curvature(row)) for row in nulls])
    null_median = float(np.median(null_peaks))
    null_scale = float(1.4826 * np.median(np.abs(null_peaks - null_median)))
    rng = np.random.default_rng(seed)
    bootstrap_selected: list[int | None] = []
    for _ in range(bootstrap_samples):
        sample = parents[rng.integers(0, len(parents), len(parents))]
        sample_curvature = curvature(np.median(sample, axis=0))
        sample_peak = float(np.max(sample_curvature))
        sample_ties = np.flatnonzero(
            np.isclose(sample_curvature, sample_peak, rtol=0.0, atol=tolerance)
        )
        bootstrap_selected.append(
            None if len(sample_ties) != 1 else coordinates[int(sample_ties[0]) + 1]
        )
    stability = (
        None
        if selected is None
        else float(np.mean(np.asarray(bootstrap_selected, dtype=object) == selected))
    )
    return {
        "status": "REJECTED_TIED_ELBOW" if selected is None else "COMPUTED_INTERIOR_ONLY",
        "selected_elbow": selected,
        "candidate_elbows": candidates,
        "multiple_elbows_reported": True,
        "curvature": [float(value) for value in observed_curvature],
        "relative_prominence": peak / max(scale, np.finfo(float).eps),
        "null_standardized_prominence": (peak - null_median)
        / max(null_scale, np.finfo(float).eps),
        "first_interior_pinning": selected == coordinates[1],
        "last_interior_pinning": selected == coordinates[-2],
        "tied_peak": selected is None,
        "bootstrap_unit": "PARENT",
        "bootstrap_samples": bootstrap_samples,
        "bootstrap_stability": stability,
        "elbow_is_T_e": False,
        "elbow_is_winner_N": False,
    }


def extract_path_sequence(embedding: PathEmbedding) -> FloatArray:
    values = np.asarray(embedding.values, dtype=np.float64)
    if embedding.representation == "ONE_DIMENSIONAL_COORDINATE_FIELD":
        if values.ndim != 1:
            raise ValueError("1D path representation requires a vector")
        return values.copy()
    if embedding.representation == "ONE_BY_M_SCALAR_FIELD":
        if values.ndim != 2 or values.shape[0] != 1:
            raise ValueError("1xM path representation requires one row")
        return values[0].copy()
    if embedding.representation != "PATH_GRAPH":
        raise ValueError("unregistered path representation")
    adjacency = np.asarray(embedding.adjacency, dtype=np.float64)
    if adjacency.shape != (len(values), len(values)) or not np.allclose(adjacency, adjacency.T):
        raise ValueError("path graph adjacency must be aligned and undirected")
    neighbors = [list(np.flatnonzero(row > 0)) for row in adjacency]
    endpoints = [index for index, row in enumerate(neighbors) if len(row) == 1]
    if len(endpoints) != 2 or any(len(row) not in {1, 2} for row in neighbors):
        raise ValueError("graph is not a simple path")
    order = [min(endpoints)]
    previous = -1
    while len(order) < len(values):
        choices = [node for node in neighbors[order[-1]] if node != previous]
        if len(choices) != 1:
            raise ValueError("path graph traversal is ambiguous")
        previous, current = order[-1], choices[0]
        if current in order:
            raise ValueError("path graph contains a cycle")
        order.append(current)
    return values[np.asarray(order)]


def point_cloud_winding_number(coordinates: FloatArray) -> float:
    """Compute the signed winding of an ordered closed planar point path."""

    points = np.asarray(coordinates, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 4:
        raise ValueError("winding number requires at least four ordered planar points")
    centered = points - np.mean(points, axis=0, keepdims=True)
    if np.any(np.linalg.norm(centered, axis=1) <= np.finfo(float).eps):
        raise ValueError("winding path cannot pass through its registered center")
    angles = np.arctan2(centered[:, 1], centered[:, 0])
    closed = np.concatenate((angles, angles[:1]))
    differences = np.diff(closed)
    wrapped = (differences + np.pi) % (2.0 * np.pi) - np.pi
    return float(np.sum(wrapped) / (2.0 * np.pi))


def point_cloud_winding_coherence(coordinates: FloatArray) -> float:
    """Combine winding with ordered-path efficiency to reject shuffled-ring decoys."""

    points = np.asarray(coordinates, dtype=np.float64)
    winding = abs(point_cloud_winding_number(points))
    centered = points - np.mean(points, axis=0, keepdims=True)
    radius = float(np.median(np.linalg.norm(centered, axis=1)))
    closed = np.vstack((points, points[:1]))
    path_length = float(np.sum(np.linalg.norm(np.diff(closed, axis=0), axis=1)))
    efficiency = min(
        1.0,
        2.0 * np.pi * radius / max(path_length, np.finfo(float).eps),
    )
    return min(1.0, winding) * efficiency


def path_tld_closure(embedding: PathEmbedding, n_values: range = range(7, 14)) -> dict[str, Any]:
    sequence = extract_path_sequence(embedding)
    result = score_ladder(sequence, n_values).to_dict()
    return {
        "operator": "CANONICAL_TLD_CHI_RMS_CLOSURE_VIA_LOSSLESS_PATH_PROJECTION",
        "representation": embedding.representation,
        "information_loss": "NONE",
        "commutative": True,
        "score": result,
    }


def line_porosity(mask: BoolArray, *, directions: list[tuple[int, int]]) -> dict[str, Any]:
    support = np.asarray(mask, dtype=bool)
    if support.ndim != 2 or not directions:
        raise ValueError("line porosity requires a 2D support and registered directions")
    occupancies: dict[str, float] = {}
    for dy, dx in directions:
        if (dy, dx) == (0, 0):
            raise ValueError("line direction cannot be zero")
        samples: list[float] = []
        for y in range(support.shape[0]):
            for x in range(support.shape[1]):
                yy, xx = y, x
                values: list[bool] = []
                while 0 <= yy < support.shape[0] and 0 <= xx < support.shape[1]:
                    values.append(bool(support[yy, xx]))
                    yy += dy
                    xx += dx
                if len(values) >= 4:
                    samples.append(float(np.mean(values)))
        occupancies[f"{dy},{dx}"] = max(samples, default=0.0)
    return {
        "maximum_directional_occupancy": max(occupancies.values()),
        "minimum_directional_occupancy": min(occupancies.values()),
        "directional_occupancy": occupancies,
        "directional_channel_count": sum(value >= 0.75 for value in occupancies.values()),
    }


def ball_porosity(mask: BoolArray, *, radii: list[int]) -> dict[str, Any]:
    """Estimate finite-grid occupancy/porosity without assigning theorem authority."""

    support = np.asarray(mask, dtype=bool)
    if support.ndim != 2 or not radii or any(radius < 1 for radius in radii):
        raise ValueError("ball porosity requires a 2D support and positive radii")
    rows: list[dict[str, float | int]] = []
    y_grid, x_grid = np.mgrid[: support.shape[0], : support.shape[1]]
    for radius in radii:
        occupancies: list[float] = []
        for y in range(support.shape[0]):
            for x in range(support.shape[1]):
                inside = (y_grid - y) ** 2 + (x_grid - x) ** 2 <= radius**2
                occupancies.append(float(np.mean(support[inside])))
        rows.append(
            {
                "radius": radius,
                "maximum_occupancy": max(occupancies),
                "median_missing_fraction": float(1.0 - np.median(occupancies)),
                "minimum_missing_fraction": float(1.0 - max(occupancies)),
            }
        )
    return {
        "estimator": "FINITE_GRID_CIRCULAR_NEIGHBORHOOD_DIAGNOSTIC",
        "scale_rows": rows,
        "theorem_authority": False,
    }


def dual_concentration_operator_norm(
    spatial_support: BoolArray,
    spectral_support: BoolArray,
    *,
    iterations: int = 64,
) -> float:
    x_mask = np.asarray(spatial_support, dtype=bool)
    y_mask = np.asarray(spectral_support, dtype=bool)
    if x_mask.shape != y_mask.shape or x_mask.ndim != 2:
        raise ValueError("dual concentration supports must share a 2D grid")
    vector = x_mask.astype(np.complex128)
    norm = np.linalg.norm(vector)
    if norm <= np.finfo(float).eps:
        return 0.0
    vector /= norm
    for _ in range(iterations):
        transformed = np.fft.fft2(vector, norm="ortho")
        transformed *= y_mask
        candidate = np.fft.ifft2(transformed, norm="ortho")
        candidate *= x_mask
        norm = np.linalg.norm(candidate)
        if norm <= np.finfo(float).eps:
            return 0.0
        vector = candidate / norm
    transformed = np.fft.fft2(vector, norm="ortho") * y_mask
    return float(np.linalg.norm(transformed))


def fup_applicability_gate(
    *,
    spatial_support_defined: bool,
    spectral_support_defined: bool,
    transform_registered: bool,
    scale_registered: bool,
    domain_justified: bool,
) -> dict[str, Any]:
    checks = {
        "spatial_support_defined": spatial_support_defined,
        "spectral_support_defined": spectral_support_defined,
        "transform_registered": transform_registered,
        "scale_registered": scale_registered,
        "domain_justified": domain_justified,
    }
    return {
        "applicable": all(checks.values()),
        "checks": checks,
        "claim_authority": "OPTIONAL_DIAGNOSTIC_NOT_TORUS_CONFIRMATION",
    }
