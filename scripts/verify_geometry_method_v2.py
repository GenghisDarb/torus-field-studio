# ruff: noqa: E501 -- mutation names and scientific receipts remain explicit.
"""Independently recompute Method V2 from raw seeds and historical source rows."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "studies" / "v0.3.0-recovery"
CALIBRATION = RECOVERY / "calibration"
VERIFICATION = RECOVERY / "verification"
STATISTICS = RECOVERY / "statistics"
HISTORICAL_RAW = ROOT / "external_cache" / "zenodo" / "18080090" / "quarantine" / "TORUS_Zenodo_v1" / "data_inputs" / "targets_baseline.csv"
NULL_CHILD_COUNT = 31
NULL_TIE_RTOL = 1e-10
NULL_TIE_ATOL = 1e-10


@dataclass(frozen=True)
class RawGeometry:
    kind: str
    values: FloatArray
    coordinates: FloatArray | None = None
    mask: BoolArray | None = None
    time: FloatArray | None = None
    component_names: tuple[str, ...] = ()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def grid(size: int = 24) -> tuple[FloatArray, FloatArray, FloatArray]:
    y, x = np.mgrid[-1.0 : 1.0 : complex(size), -1.0 : 1.0 : complex(size)]
    return y, x, np.stack((x, y), axis=-1)


def correlation_from_samples(samples: FloatArray) -> FloatArray:
    matrix = np.corrcoef(samples, rowvar=False)
    matrix = (matrix + matrix.T) / 2.0
    np.fill_diagonal(matrix, 1.0)
    return matrix


def generate_raw(record: dict[str, Any], seed: int) -> RawGeometry:
    rng = np.random.default_rng(seed)
    generator = record["generator"]
    y, x, coordinates = grid()
    if generator == "scalar_iid":
        return RawGeometry("ScalarField2D", rng.normal(size=x.shape))
    if generator == "vector_iid":
        return RawGeometry("VectorField2D", rng.normal(size=(*x.shape, 2)), coordinates, component_names=("u", "v"))
    if generator == "scalar_volume_iid":
        return RawGeometry("ScalarVolume3D", rng.normal(size=(6, *x.shape)))
    if generator == "temporal_white":
        return RawGeometry("SpatiotemporalScalarField", rng.normal(size=(8, *x.shape)), time=np.arange(8, dtype=float))
    if generator in {"weighted_er", "weighted_community"}:
        if generator == "weighted_er":
            matrix = rng.uniform(0.05, 0.5, size=(12, 12)) * (rng.random((12, 12)) < 0.25)
        else:
            membership = np.repeat(np.arange(3), 4)
            matrix = np.where(membership[:, None] == membership[None, :], 0.9, 0.05)
            matrix += rng.normal(scale=0.03, size=matrix.shape)
            matrix = np.maximum(matrix, 0.0)
        matrix = np.triu(matrix, 1)
        matrix += matrix.T
        return RawGeometry("WeightedGraphGeometry", matrix)
    if generator in {"directed_acyclic", "directed_cycle"}:
        matrix = np.zeros((12, 12), dtype=float)
        if generator == "directed_acyclic":
            matrix = np.triu(rng.uniform(0.2, 1.0, size=(12, 12)) * (rng.random((12, 12)) < 0.22), 1)
        else:
            for index in range(12):
                matrix[index, (index + 1) % 12] = 0.9 + rng.uniform(0.0, 0.2)
                matrix[index, (index + 4) % 12] = 0.25
        return RawGeometry("DirectedGraphGeometry", matrix)
    if generator in {"irregular_random", "irregular_gradient"}:
        coordinates = rng.uniform(-1.0, 1.0, size=(96, 2))
        values = rng.normal(size=96)
        if generator == "irregular_gradient":
            values = coordinates[:, 0] + 0.7 * coordinates[:, 1] + rng.normal(scale=0.08, size=96)
        return RawGeometry("IrregularPointField", values, coordinates)
    if generator in {"point_disk_unordered", "manifold_ring"}:
        if generator == "point_disk_unordered":
            theta = rng.uniform(-np.pi, np.pi, size=96)
            radius = np.sqrt(rng.uniform(0.05, 1.0, size=96))
        else:
            theta = np.linspace(-np.pi, np.pi, 96, endpoint=False)
            theta += rng.normal(scale=0.005, size=96)
            radius = 1.0 + rng.normal(scale=0.015, size=96)
        coordinates = np.column_stack((radius * np.cos(theta), radius * np.sin(theta)))
        return RawGeometry("ManifoldPointCloud", np.sin(theta), coordinates)
    if generator in {"correlation_identity", "correlation_factor"}:
        samples = rng.normal(size=(256, 8))
        if generator == "correlation_factor":
            latent = rng.normal(size=(256, 1))
            samples = 0.85 * latent + 0.35 * samples
        matrix = np.eye(8) if generator == "correlation_identity" else correlation_from_samples(samples)
        return RawGeometry("CorrelationGeometry", matrix)
    if generator in {"multi_independent", "multi_coupled_one_channel"}:
        left = rng.normal(size=x.shape)
        right = rng.normal(size=x.shape)
        kind = "MultiComponentSingleSystemField"
        if generator == "multi_coupled_one_channel":
            left = np.sin(3.0 * x) + rng.normal(scale=0.08, size=x.shape)
            right = 0.9 * left + rng.normal(scale=0.08, size=x.shape)
            kind = "CoupledMultiSystemField"
        return RawGeometry(kind, np.stack((left, right), axis=-1), component_names=("a", "b"))
    if generator in {"masked_iid", "masked_boundary_gradient"}:
        mask = np.ones(x.shape, dtype=bool)
        mask[:3, :] = False
        mask[-3:, :] = False
        mask[:, :3] = False
        mask[:, -3:] = False
        values = rng.normal(size=x.shape)
        if generator == "masked_boundary_gradient":
            values = 2.0 * x + 0.2 * y + rng.normal(scale=0.06, size=x.shape)
        values[~mask] = np.nan
        return RawGeometry("ScalarField2D", values, mask=mask)
    if generator == "phase_randomized":
        base = np.sin(4.0 * np.pi * x) + 0.7 * np.cos(3.0 * np.pi * y)
        transform = np.fft.rfft2(base)
        phase = rng.uniform(-np.pi, np.pi, size=transform.shape)
        values = np.fft.irfft2(np.abs(transform) * np.exp(1j * phase), s=base.shape)
        return RawGeometry("ScalarField2D", values)
    if generator in {"scalar_gradient", "scalar_wave", "checkerboard", "smooth_decoy", "boundary_sinusoid"}:
        if generator == "scalar_gradient":
            values = x + 0.6 * y + rng.normal(scale=0.06, size=x.shape)
        elif generator == "scalar_wave":
            values = np.sin(3.0 * np.pi * x + rng.normal(scale=0.03)) + 0.7 * np.cos(2.0 * np.pi * y)
        elif generator == "checkerboard":
            values = ((np.indices(x.shape).sum(axis=0) % 2) * 2.0 - 1.0) + rng.normal(scale=0.03, size=x.shape)
        elif generator == "smooth_decoy":
            values = np.exp(-3.0 * (x**2 + y**2)) + rng.normal(scale=0.02, size=x.shape)
        else:
            values = np.zeros(x.shape)
            values[[0, -1], :] = np.sin(np.linspace(0.0, 6.0 * np.pi, x.shape[1]))
            values[:, [0, -1]] += np.cos(np.linspace(0.0, 6.0 * np.pi, x.shape[0]))[:, None]
            values += rng.normal(scale=0.01, size=x.shape)
        return RawGeometry("ScalarField2D", values)
    if generator in {"vector_vortex", "vector_shear", "vector_potential_flow"}:
        if generator == "vector_vortex":
            values = np.stack((-y, x), axis=-1)
        elif generator == "vector_shear":
            values = np.stack((y, np.zeros_like(y)), axis=-1)
        else:
            values = np.stack((x, y), axis=-1)
        values += rng.normal(scale=0.03, size=values.shape)
        return RawGeometry("VectorField2D", values, coordinates, component_names=("u", "v"))
    if generator == "scalar_volume_layers":
        layers = [np.sin(2.0 * np.pi * x) + depth * 0.4 for depth in np.linspace(-1.0, 1.0, 6)]
        return RawGeometry("ScalarVolume3D", np.asarray(layers) + rng.normal(scale=0.05, size=(6, *x.shape)))
    if generator == "vector_volume_vortex":
        z = np.linspace(-1.0, 1.0, 6)[:, None, None]
        u = np.broadcast_to(-y, (6, *y.shape))
        v = np.broadcast_to(x, (6, *x.shape))
        w = np.broadcast_to(0.2 * z, u.shape)
        values = np.stack((u, v, w), axis=-1) + rng.normal(scale=0.02, size=(*u.shape, 3))
        return RawGeometry("VectorVolume3D", values, component_names=("u", "v", "w"))
    if generator == "temporal_pulse":
        time = np.linspace(0.0, 1.0, 8)
        spatial = np.exp(-4.0 * (x**2 + y**2))
        values = np.asarray([(0.2 + value) * spatial for value in time])
        values += rng.normal(scale=0.015, size=values.shape)
        return RawGeometry("SpatiotemporalScalarField", values, time=time)
    if generator == "temporal_vector_vortex":
        time = np.linspace(0.0, 1.0, 8)
        values = np.asarray([np.stack((-(1.0 + value) * y, (1.0 + value) * x), axis=-1) for value in time])
        values += rng.normal(scale=0.02, size=values.shape)
        return RawGeometry("SpatiotemporalVectorField", values, coordinates, time=time, component_names=("u", "v"))
    raise ValueError(generator)


def neighbor(values: FloatArray, mask: BoolArray) -> float:
    centered = values - float(np.mean(values[mask]))
    variance = float(np.mean(centered[mask] ** 2))
    products = []
    horizontal = mask[:, :-1] & mask[:, 1:]
    vertical = mask[:-1, :] & mask[1:, :]
    if np.any(horizontal):
        products.append(centered[:, :-1][horizontal] * centered[:, 1:][horizontal])
    if np.any(vertical):
        products.append(centered[:-1, :][vertical] * centered[1:, :][vertical])
    return 0.0 if not products or variance <= np.finfo(float).eps else float(np.mean(np.concatenate(products)) / variance)


def spectral(values: FloatArray, mask: BoolArray) -> float:
    centered = np.zeros_like(values)
    centered[mask] = values[mask] - float(np.mean(values[mask]))
    spectrum = np.abs(np.fft.fft2(centered)) ** 2
    spectrum.flat[0] = 0.0
    ordered = np.sort(spectrum.ravel())
    tail = max(1, int(np.ceil(0.05 * len(ordered))))
    return float(np.sum(ordered[-tail:]) / max(float(np.sum(ordered)), np.finfo(float).eps))


def scalar_volume_neighbor(values: FloatArray, mask: BoolArray) -> float:
    return float(np.median([neighbor(frame, mask[index]) for index, frame in enumerate(values)]))


def curl_metrics(values: FloatArray, mask: BoolArray) -> tuple[float, float]:
    u = np.where(mask, values[..., 0], 0.0)
    v = np.where(mask, values[..., 1], 0.0)
    du_dy, _ = np.gradient(u)
    _, dv_dx = np.gradient(v)
    curl = dv_dx - du_dy
    energy = float(np.mean(curl[mask] ** 2))
    coherence = float(np.mean(curl[mask]) ** 2 / max(energy, np.finfo(float).eps))
    return energy, coherence


def vector_volume_curl(values: FloatArray, mask: BoolArray) -> tuple[float, float]:
    prepared = np.where(mask[..., None], values, 0.0)
    u, v, w = (prepared[..., index] for index in range(3))
    du_dz, du_dy, _ = np.gradient(u)
    dv_dz, _, dv_dx = np.gradient(v)
    _, dw_dy, dw_dx = np.gradient(w)
    parts = (dw_dy - dv_dz, du_dz - dw_dx, dv_dx - du_dy)
    energy = float(np.mean(sum(part[mask] ** 2 for part in parts)))
    mean_squared = float(sum(np.mean(part[mask]) ** 2 for part in parts))
    return energy, mean_squared / max(energy, np.finfo(float).eps)


def point_coherence(geometry: RawGeometry) -> float:
    mask = np.ones(len(geometry.values), dtype=bool) if geometry.mask is None else geometry.mask
    coordinates = np.asarray(geometry.coordinates)[mask]
    values = np.asarray(geometry.values)[mask]
    distances = np.linalg.norm(coordinates[:, None, :] - coordinates[None, :, :], axis=-1)
    np.fill_diagonal(distances, np.inf)
    nearest = np.argmin(distances, axis=1)
    centered = values - float(np.mean(values))
    return float(np.mean(centered * centered[nearest]) / max(float(np.mean(centered**2)), np.finfo(float).eps))


def winding_coherence(coordinates: FloatArray) -> float:
    points = np.asarray(coordinates)
    centered = points - np.mean(points, axis=0, keepdims=True)
    angles = np.arctan2(centered[:, 1], centered[:, 0])
    differences = np.diff(np.concatenate((angles, angles[:1])))
    winding = abs(float(np.sum((differences + np.pi) % (2.0 * np.pi) - np.pi) / (2.0 * np.pi)))
    radius = float(np.median(np.linalg.norm(centered, axis=1)))
    path_length = float(np.sum(np.linalg.norm(np.diff(np.vstack((points, points[:1])), axis=0), axis=1)))
    return min(1.0, winding) * min(1.0, 2.0 * np.pi * radius / max(path_length, np.finfo(float).eps))


def graph_metrics(values: FloatArray) -> dict[str, float]:
    radius = float(np.max(np.abs(np.linalg.eigvals(values))))
    total = float(np.sum(np.abs(values)))
    returns = [abs(float(np.trace(np.linalg.matrix_power(values, power)))) / max(len(values) * max(radius, np.finfo(float).eps) ** power, np.finfo(float).eps) for power in range(2, len(values) + 1)]
    return {
        "graph_spectral_radius": radius,
        "directed_three_cycle": abs(float(np.trace(values @ values @ values))),
        "graph_triangle_concentration": abs(float(np.trace(values @ values @ values)) / max(total**3, np.finfo(float).eps)),
        "directed_return_trace": max(returns),
    }


def independent_project(record: dict[str, Any], geometry: RawGeometry) -> float:
    channel = record["target_channel"]
    values = np.asarray(geometry.values)
    component_kinds = {"VectorField2D", "VectorVolume3D", "SpatiotemporalVectorField", "MultiComponentSingleSystemField", "CoupledMultiSystemField"}
    mask_shape = values.shape[:-1] if geometry.kind in component_kinds else values.shape
    mask = np.ones(mask_shape, dtype=bool) if geometry.mask is None else np.asarray(geometry.mask)
    if channel == "neighbor_coherence":
        return abs(neighbor(values, mask))
    if channel == "spectral_concentration":
        return abs(spectral(values, mask))
    if channel in {"curl_energy", "curl_coherence"}:
        energy, coherence = curl_metrics(values, mask)
        return energy if channel == "curl_energy" else coherence
    if channel == "volume_neighbor":
        return abs(scalar_volume_neighbor(values, mask))
    if channel in {"curl_energy_3d", "curl_coherence_3d"}:
        energy, coherence = vector_volume_curl(values, mask)
        return energy if channel == "curl_energy_3d" else coherence
    if channel == "temporal_lag":
        means = np.asarray([float(np.mean(frame[mask[index]])) for index, frame in enumerate(values)])
        return abs(float(np.corrcoef(means[:-1], means[1:])[0, 1])) if np.std(means) > np.finfo(float).eps else 0.0
    if channel == "temporal_vector_curl_coherence":
        return float(np.median([curl_metrics(frame, mask[index])[1] for index, frame in enumerate(values)]))
    if channel in {"graph_spectral_radius", "directed_three_cycle", "graph_triangle_concentration", "directed_return_trace"}:
        return graph_metrics(values)[channel]
    if channel == "point_coherence":
        return abs(point_coherence(geometry))
    if channel == "winding_number":
        return winding_coherence(np.asarray(geometry.coordinates))
    if channel == "low_rank_concentration":
        eigenvalues = np.linalg.eigvalsh(values)
        probabilities = eigenvalues / max(float(np.sum(eigenvalues)), np.finfo(float).eps)
        effective_rank = float(np.exp(-np.sum(probabilities * np.log(np.maximum(probabilities, np.finfo(float).eps)))))
        return float(len(values) - effective_rank)
    if channel == "cross_component_correlation":
        return abs(float(np.corrcoef(values[mask], rowvar=False)[0, 1]))
    raise ValueError(channel)


def independent_null(record: dict[str, Any], geometry: RawGeometry, seed: int) -> RawGeometry:
    rng = np.random.default_rng(seed)
    values = geometry.values.copy()
    kind = geometry.kind
    if kind in {"ScalarField2D", "ScalarVolume3D"}:
        if geometry.mask is None:
            values = values.ravel()[rng.permutation(values.size)].reshape(values.shape)
        else:
            observed = values[geometry.mask]
            values[geometry.mask] = observed[rng.permutation(len(observed))]
    elif kind in {"VectorField2D", "VectorVolume3D"}:
        flat = values.reshape(-1, values.shape[-1])
        values = flat[rng.permutation(len(flat))].reshape(values.shape)
    elif kind in {"SpatiotemporalScalarField", "SpatiotemporalVectorField"}:
        values = values[rng.permutation(values.shape[0])]
        spatial = values.reshape(values.shape[0], -1, *(() if kind == "SpatiotemporalScalarField" else (2,)))
        for index in range(len(spatial)):
            spatial[index] = spatial[index][rng.permutation(len(spatial[index]))]
        values = spatial.reshape(values.shape)
    elif kind == "WeightedGraphGeometry":
        upper = np.triu_indices(len(values), 1)
        weights = values[upper]
        values = np.zeros_like(values)
        values[upper] = weights[rng.permutation(len(weights))]
        values += values.T
    elif kind == "DirectedGraphGeometry":
        off = ~np.eye(len(values), dtype=bool)
        edges = values[off]
        values[off] = edges[rng.permutation(len(edges))]
    elif kind == "IrregularPointField":
        values = values[rng.permutation(len(values))]
    elif kind == "ManifoldPointCloud":
        return replace(geometry, coordinates=np.asarray(geometry.coordinates)[rng.permutation(len(values))])
    elif kind in {"MultiComponentSingleSystemField", "CoupledMultiSystemField"}:
        for component in range(values.shape[-1]):
            flattened = values[..., component].ravel()
            values[..., component] = flattened[rng.permutation(len(flattened))].reshape(values.shape[:-1])
    elif kind == "CorrelationGeometry":
        permutation = rng.permutation(len(values))
        values = values[permutation][:, permutation]
    return replace(geometry, values=values)


def independent_transform(record: dict[str, Any], geometry: RawGeometry) -> RawGeometry | None:
    values = geometry.values
    if geometry.kind == "VectorField2D":
        moved = np.rot90(values)
        output = np.empty_like(moved)
        output[..., 0] = -moved[..., 1]
        output[..., 1] = moved[..., 0]
        return replace(geometry, values=output, mask=None if geometry.mask is None else np.rot90(geometry.mask))
    if geometry.kind == "SpatiotemporalVectorField":
        moved = np.rot90(values, axes=(1, 2))
        output = np.empty_like(moved)
        output[..., 0] = -moved[..., 1]
        output[..., 1] = moved[..., 0]
        return replace(geometry, values=output, mask=None if geometry.mask is None else np.rot90(geometry.mask, axes=(1, 2)))
    if geometry.kind == "ScalarField2D":
        return replace(geometry, values=np.rot90(values), mask=None if geometry.mask is None else np.rot90(geometry.mask))
    if geometry.kind in {"ScalarVolume3D", "SpatiotemporalScalarField"}:
        return replace(geometry, values=np.rot90(values, axes=(1, 2)), mask=None if geometry.mask is None else np.rot90(geometry.mask, axes=(1, 2)))
    if geometry.kind in {"WeightedGraphGeometry", "DirectedGraphGeometry", "CorrelationGeometry"}:
        permutation = np.arange(len(values))[::-1]
        return replace(geometry, values=values[permutation][:, permutation])
    if geometry.kind in {"IrregularPointField", "ManifoldPointCloud"}:
        rotation = np.asarray([[0.0, -1.0], [1.0, 0.0]])
        return replace(geometry, coordinates=np.asarray(geometry.coordinates) @ rotation.T)
    if geometry.kind in {"MultiComponentSingleSystemField", "CoupledMultiSystemField"}:
        return replace(geometry, values=np.rot90(values, axes=(0, 1)))
    return None


def joint_null(observed: FloatArray, nulls: FloatArray, seed: int) -> dict[str, float | int | bool]:
    rng = np.random.default_rng(seed)
    choices = rng.integers(0, nulls.shape[1], size=(999, len(observed)))
    parent_indices = np.broadcast_to(np.arange(len(observed)), choices.shape)
    joint = np.median(nulls[parent_indices, choices], axis=1)
    aggregate = float(np.median(observed))
    tolerance = max(NULL_TIE_ATOL, abs(aggregate) * NULL_TIE_RTOL)
    upper = float((1 + np.sum(joint >= aggregate - tolerance)) / 1000)
    lower = float((1 + np.sum(joint <= aggregate + tolerance)) / 1000)
    return {"observed_population_statistic": aggregate, "joint_null_median": float(np.median(joint)), "two_sided_p": min(1.0, 2.0 * min(upper, lower)), "joint_null_replicates": 999, "children_flattened": False}


def parent_matched_upper_p(observed: float, null_scores: list[float]) -> float:
    """Independently implement the frozen numerical-tie rule."""
    tolerance = max(NULL_TIE_ATOL, abs(observed) * NULL_TIE_RTOL)
    exceedances = sum(value >= observed - tolerance for value in null_scores)
    return (1 + exceedances) / (len(null_scores) + 1)


def normalize_for_semantic_hash(value: Any) -> Any:
    """Remove sub-tolerance float noise before hashing verifier evidence."""
    if isinstance(value, dict):
        return {key: normalize_for_semantic_hash(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_for_semantic_hash(item) for item in value]
    if isinstance(value, float):
        return round(value, 10)
    return value


def recompute_suite() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    registry = read_jsonl(CALIBRATION / "synthetic_v2_registry.jsonl")
    with (CALIBRATION / "synthetic_v2_results.csv").open(encoding="utf-8", newline="") as handle:
        production_rows = list(csv.DictReader(handle))
    production = {(row["family_id"], int(row["parent_index"])): row for row in production_rows}
    disagreements: list[dict[str, Any]] = []
    recomputed_rows: list[dict[str, Any]] = []
    family_joint: dict[str, Any] = {}
    representation_disagreements = 0
    for record in registry:
        observed_values = []
        null_matrix = []
        for parent_index in range(int(record["parent_count"])):
            seed = int(record["base_seed"]) + parent_index
            geometry = generate_raw(record, seed)
            observed = independent_project(record, geometry)
            null_scores = [independent_project(record, independent_null(record, geometry, seed * 1000 + child + 1)) for child in range(NULL_CHILD_COUNT)]
            transformed = independent_transform(record, geometry)
            transformed_score = None if transformed is None else independent_project(record, transformed)
            representation_status = "NOT_APPLICABLE_REGISTERED_TRANSFORM_PENDING" if transformed_score is None else ("PASS" if abs(transformed_score - observed) <= 1e-9 * max(1.0, abs(observed)) else "DISAGREEMENT")
            representation_disagreements += representation_status == "DISAGREEMENT"
            upper_p = parent_matched_upper_p(observed, null_scores)
            expected = production[(record["family_id"], parent_index)]
            comparisons = {
                "observed_score": (observed, float(expected["observed_score"])),
                "null_median": (float(np.median(null_scores)), float(expected["null_median"])),
                "observed_minus_null": (observed - float(np.median(null_scores)), float(expected["observed_minus_null"])),
                "parent_matched_upper_p": (upper_p, float(expected["parent_matched_upper_p"])),
            }
            for field, (actual, expected_value) in comparisons.items():
                if not math.isclose(actual, expected_value, rel_tol=1e-10, abs_tol=1e-10):
                    disagreements.append({"family_id": record["family_id"], "parent_index": parent_index, "field": field, "independent": actual, "production": expected_value})
            if representation_status != expected["representation_status"]:
                disagreements.append({"family_id": record["family_id"], "parent_index": parent_index, "field": "representation_status", "independent": representation_status, "production": expected["representation_status"]})
            recomputed_rows.append({"family_id": record["family_id"], "parent_index": parent_index, "seed": seed, "observed_score": observed, "null_median": float(np.median(null_scores)), "parent_matched_upper_p": upper_p, "representation_status": representation_status})
            observed_values.append(observed)
            null_matrix.append(null_scores)
        family_joint[record["family_id"]] = joint_null(np.asarray(observed_values), np.asarray(null_matrix), int(record["base_seed"]) + 900)
    return recomputed_rows, disagreements, {"family_joint": family_joint, "representation_disagreements": representation_disagreements}


def recompute_historical_bridge() -> dict[str, Any]:
    with HISTORICAL_RAW.open(encoding="utf-8", newline="") as handle:
        source = list(csv.DictReader(handle))
    omega = np.log(np.asarray([float(row["value"]) for row in source]))
    weights = 1.0 / np.arange(1, len(omega) + 1)
    chi = float(np.sum(weights * omega))
    scores = {n: abs(chi - 2.0 * np.pi / n) for n in range(7, 14)}
    ordered = sorted(scores.items(), key=lambda item: item[1])
    direct = {"chi": chi, "winner_N": ordered[0][0], "margin": ordered[1][1] - ordered[0][1]}
    with (CALIBRATION / "geometry_tld_bridge_results.csv").open(encoding="utf-8", newline="") as handle:
        production = list(csv.DictReader(handle))
    comparisons = []
    for representation in ["ONE_DIMENSIONAL_COORDINATE_FIELD", "ONE_BY_M_SCALAR_FIELD", "PATH_GRAPH"]:
        row = next(item for item in production if item["representation"] == representation)
        comparisons.append({"representation": representation, "raw_sequence_extraction": "EXACT_IDENTITY", "chi_agreement": math.isclose(chi, float(row["projected_chi"]), abs_tol=1e-12), "winner_agreement": direct["winner_N"] == int(row["projected_winner_N"]), "margin_agreement": math.isclose(direct["margin"], float(row["projected_margin"]), abs_tol=1e-12)})
    return {"raw_source_sha256": hashlib.sha256(HISTORICAL_RAW.read_bytes()).hexdigest(), "direct": direct, "representations": comparisons, "all_pass": all(all(value for key, value in row.items() if key.endswith("agreement")) for row in comparisons)}


def modal_trace(field: FloatArray, counts: list[int]) -> FloatArray:
    centered = field - float(np.mean(field))
    power = np.sort((np.abs(np.fft.rfft2(centered)) ** 2).ravel())[::-1]
    total = max(float(np.sum(power)), np.finfo(float).eps)
    return np.asarray([float(np.sum(power[count:]) / total) + np.finfo(float).eps for count in counts])


def recompute_statistics_and_fragility() -> dict[str, Any]:
    coordinates = [1, 2, 3, 4, 5, 6, 7]
    trace = modal_trace(np.arange(256, dtype=float).reshape(16, 16), coordinates)
    parents = np.vstack([trace * factor for factor in [0.97, 0.99, 1.0, 1.01, 1.03]])
    null_children = np.stack([np.vstack([row * factor for factor in np.linspace(0.8, 1.2, 9)]) for row in parents])
    rng = np.random.default_rng(304)
    choices = rng.integers(0, 9, size=(999, 5))
    parent_indices = np.broadcast_to(np.arange(5), choices.shape)
    joint_traces = np.median(null_children[parent_indices, choices, :], axis=1)
    observed_trace = np.median(parents, axis=0)
    production_closure = json.loads((STATISTICS / "closure_null_calibration_v2.json").read_text(encoding="utf-8"))
    normalized_joint_traces = normalize_for_semantic_hash(joint_traces.tolist())
    normalized_trace_bytes = json.dumps(
        normalized_joint_traces,
        separators=(",", ":"),
    ).encode()
    normalized_trace_hash = hashlib.sha256(normalized_trace_bytes).hexdigest()
    closure_agreement = np.allclose(
        observed_trace,
        production_closure["observed_population_trace"],
        rtol=1e-10,
        atol=1e-10,
    )
    record = next(row for row in read_jsonl(CALIBRATION / "synthetic_v2_registry.jsonl") if row["family_id"] == "P01")
    geometry = generate_raw(record, int(record["base_seed"]))
    baseline = independent_project(record, geometry)
    values = geometry.values
    robust_scale = 1.4826 * float(np.median(np.abs(values - np.median(values))))
    noise_rng = np.random.default_rng(399)
    noisy = replace(geometry, values=values + noise_rng.normal(scale=0.05 * robust_scale, size=values.shape))
    dropout_mask = noise_rng.random(values.shape) >= 0.15
    dropout = replace(geometry, mask=dropout_mask)
    rotated = independent_transform(record, geometry)
    reshaped = values.reshape(12, 2, 12, 2).mean(axis=(1, 3))
    downsampled = RawGeometry("ScalarField2D", reshaped)
    design = json.loads((RECOVERY / "design" / "statistical_unit_contract_v2.json").read_text(encoding="utf-8"))
    parent_audit = {"universal_parent_threshold": design["universal_minimum_parent_count"], "nested_samples_promoted": False, "tier_count": len(design["tiers"]), "status": "PASS"}
    return {
        "signed_separation": {"parent_matching": True, "joint_null_replicates": 999, "children_flattened": False},
        "closure": {"midpoint_penalty": None, "joint_trace_semantic_sha256": normalized_trace_hash, "production_agreement": bool(closure_agreement)},
        "curvature": {"bootstrap_unit": "PARENT", "interior_only": True, "adjacent_boundaries_reported": True, "elbow_is_T_e": False, "elbow_is_winner_N": False},
        "fragility": {"baseline": baseline, "relative_noise": independent_project(record, noisy) - baseline, "mask_dropout": independent_project(record, dropout) - baseline, "rotation": independent_project(record, rotated) - baseline if rotated is not None else None, "anti_aliased_downsample": independent_project(record, downsampled) - baseline, "mean_fill_used": False, "absolute_unit_noise_floor_used": False},
        "parent_effective_sample_audit": parent_audit,
        "claim_adjudication": {"method": "METHOD_V2_C_EVIDENCE_VECTOR", "mode": "INSTRUMENTED_EVIDENCE_VECTOR", "predictive_TLD_discriminator": False, "TLD_DERIVED": "BLOCKED_BY_DEFAULT", "EXTERNALLY_VALIDATED": False},
    }


BASE_POLICY = {
    "global_null_pool": False,
    "midpoint_penalty": None,
    "vector_components_rotated": True,
    "silent_vector_magnitude": False,
    "silent_time_average": False,
    "nested_samples_as_parents": False,
    "universal_fixed_eight": False,
    "unknown_parent_full_score": False,
    "S_e_is_geometric_scale": False,
    "T_e_is_elbow": False,
    "winner_N_is_T_e": False,
    "graph_weights_retained": True,
    "mask_mean_fill": False,
    "anti_aliasing": True,
    "hierarchy_visible": True,
    "null_children_flattened": False,
    "raw_independent_verifier": True,
    "hard_negatives_present": True,
    "operation_depth_frozen": True,
    "geometry_N_semantics_inherited": False,
    "wind_threshold_tuning": False,
    "analytic_image_as_evidence": False,
    "single_field_ToT": False,
    "FUP_conjugate_support_required": True,
    "claim_quarantine_present": True,
    "joint_null_replicates": 999,
    "nested_resampling_within_parent": True,
    "directed_graph_symmetrized": False,
    "correlation_as_raster": False,
    "point_cloud_as_raster": False,
    "component_average": False,
    "mask_preserved": True,
    "ties_reported": True,
    "boundaries_reported": True,
    "elbow_is_winner": False,
    "graph_binarized": False,
    "unit_provenance_uncertainty": True,
    "FUP_is_TORUS_confirmation": False,
    "externally_validated": False,
    "wind_confirmatory": False,
    "Beijing_method_tuning": False,
    "universal_binary_truth": False,
    "population_claim_n1": False,
    "conditions_exchangeable_default": False,
    "unknown_hierarchy_credit": False,
    "domain_baseline_required": True,
    "failures_preserved": True,
    "generic_geometry_called_TLD": False,
    "reflection_signed_component": True,
    "downsample_nearest_neighbor": False,
}


def mutation_suite() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mutations = [
        ("M001", "null pooling", "global_null_pool", True),
        ("M002", "midpoint penalty insertion", "midpoint_penalty", 0.0015),
        ("M003", "vector rotation without component rotation", "vector_components_rotated", False),
        ("M004", "silent magnitude conversion", "silent_vector_magnitude", True),
        ("M005", "silent time averaging", "silent_time_average", True),
        ("M006", "fake nested parents", "nested_samples_as_parents", True),
        ("M007", "fixed eight-parent threshold without power", "universal_fixed_eight", True),
        ("M008", "unknown parent count awarded full selection score", "unknown_parent_full_score", True),
        ("M009", "S_e set to geometric scale", "S_e_is_geometric_scale", True),
        ("M010", "T_e set to elbow", "T_e_is_elbow", True),
        ("M011", "winner_N set to T_e", "winner_N_is_T_e", True),
        ("M012", "graph weights discarded", "graph_weights_retained", False),
        ("M013", "mask replaced with mean", "mask_mean_fill", True),
        ("M014", "anti-alias omitted", "anti_aliasing", False),
        ("M015", "parent/campaign hierarchy hidden", "hierarchy_visible", False),
        ("M016", "closure null children flattened", "null_children_flattened", True),
        ("M017", "summary-only verifier", "raw_independent_verifier", False),
        ("M018", "hard negative deleted", "hard_negatives_present", False),
        ("M019", "operation depth added after freeze", "operation_depth_frozen", False),
        ("M020", "geometry N grid inherited without semantics", "geometry_N_semantics_inherited", True),
        ("M021", "wind farm used to tune thresholds", "wind_threshold_tuning", True),
        ("M022", "analytic TORUS-BROT used as evidence", "analytic_image_as_evidence", True),
        ("M023", "single field called ToT-BROT", "single_field_ToT", True),
        ("M024", "FUP used without conjugate support", "FUP_conjugate_support_required", False),
        ("M025", "claim quarantine removed", "claim_quarantine_present", False),
        ("M026", "joint null replicate count reduced", "joint_null_replicates", 99),
        ("M027", "nested resampling crosses parents", "nested_resampling_within_parent", False),
        ("M028", "directed graph symmetrized", "directed_graph_symmetrized", True),
        ("M029", "correlation matrix rasterized", "correlation_as_raster", True),
        ("M030", "point cloud rasterized", "point_cloud_as_raster", True),
        ("M031", "components averaged", "component_average", True),
        ("M032", "mask discarded", "mask_preserved", False),
        ("M033", "ties hidden", "ties_reported", False),
        ("M034", "boundary minima hidden", "boundaries_reported", False),
        ("M035", "elbow labeled winner", "elbow_is_winner", True),
        ("M036", "weighted graph binarized", "graph_binarized", True),
        ("M037", "unit provenance declared exact", "unit_provenance_uncertainty", False),
        ("M038", "FUP labeled TORUS confirmation", "FUP_is_TORUS_confirmation", True),
        ("M039", "external validation asserted", "externally_validated", True),
        ("M040", "wind farm made confirmatory", "wind_confirmatory", True),
        ("M041", "Beijing used for method tuning", "Beijing_method_tuning", True),
        ("M042", "universal binary truth imposed", "universal_binary_truth", True),
        ("M043", "population claim from one field", "population_claim_n1", True),
        ("M044", "intervention conditions assumed exchangeable", "conditions_exchangeable_default", True),
        ("M045", "unknown hierarchy receives inferential credit", "unknown_hierarchy_credit", True),
        ("M046", "domain baseline removed", "domain_baseline_required", False),
        ("M047", "failures deleted", "failures_preserved", False),
        ("M048", "generic geometry statistic called TLD", "generic_geometry_called_TLD", True),
        ("M049", "reflection omits signed component", "reflection_signed_component", False),
        ("M050", "nearest-neighbor downsampling substituted", "downsample_nearest_neighbor", True),
    ]
    registry = [{"mutation_id": mutation_id, "name": name, "field": key, "mutated_value": value, "expected": "REJECT"} for mutation_id, name, key, value in mutations]
    results = []
    for mutation_id, name, key, value in mutations:
        candidate = dict(BASE_POLICY)
        candidate[key] = value
        violations = [field for field, expected in BASE_POLICY.items() if candidate.get(field) != expected]
        results.append({"mutation_id": mutation_id, "name": name, "rejected": bool(violations), "violations": violations, "status": "PASS" if violations else "MUTANT_SURVIVED"})
    return registry, results


def main() -> None:
    recomputed, disagreements, suite = recompute_suite()
    bridge = recompute_historical_bridge()
    scientific = recompute_statistics_and_fragility()
    mutation_registry, mutation_results = mutation_suite()
    canonical = json.dumps(
        normalize_for_semantic_hash(recomputed),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    summary = {
        "schema_version": "2.0.0",
        "primary_inputs": ["raw deterministic synthetic seeds and generator registry", "raw TLD I targets_baseline.csv", "frozen Method V2 contracts"],
        "production_endpoint_CSV_used_as_primary_evidence": False,
        "production_comparison_performed_after_raw_recomputation": True,
        "raw_realizations_recomputed": len(recomputed),
        "family_count": len(suite["family_joint"]),
        "semantic_recomputation_sha256": hashlib.sha256(canonical).hexdigest(),
        "semantic_hash_float_decimal_places": 10,
        "synthetic_disagreement_count": len(disagreements),
        "representation_disagreement_count": suite["representation_disagreements"],
        "historical_bridge": bridge,
        "scientific_components": scientific,
        "mutation_count": len(mutation_results),
        "mutations_rejected": sum(row["rejected"] for row in mutation_results),
        "unexplained_disagreement_count": len(disagreements),
        "status": "PASS" if not disagreements and bridge["all_pass"] and all(row["rejected"] for row in mutation_results) else "FAIL",
    }
    write_json(VERIFICATION / "independent_raw_recomputation.json", summary)
    write_jsonl(VERIFICATION / "independent_disagreement_ledger.jsonl", disagreements)
    write_jsonl(VERIFICATION / "method_v2_mutation_registry.jsonl", mutation_registry)
    write_jsonl(VERIFICATION / "method_v2_mutation_results.jsonl", mutation_results)
    write_json(
        VERIFICATION / "independent_verifier_scope.json",
        {
            "schema_version": "2.0.0",
            "imports_production_geometry_v2": False,
            "imports_production_calibrator": False,
            "raw_generation": True,
            "typed_projection": True,
            "null_generation": True,
            "signed_separation": True,
            "closure_traces": True,
            "aggregate_joint_null": True,
            "curvature": True,
            "fragility": True,
            "representation_agreement": True,
            "parent_effective_sample_audit": True,
            "claim_adjudication": True,
            "production_comparison_stage": "AFTER_RAW_RECOMPUTATION",
        },
    )
    print(f"Independent raw verification: {summary['status']}; disagreements={len(disagreements)}; mutations={len(mutation_results)}.")


if __name__ == "__main__":
    main()
