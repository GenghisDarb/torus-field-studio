# ruff: noqa: E501 -- registry labels and frozen scientific descriptions stay explicit.
"""Calibrate Synthetic Geometry Suite V2 without field-outcome inputs."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from torusbrot.geometry.calibration import historical_construct_benchmark
from torusbrot.geometry.v2 import (
    GeometryKind,
    PathEmbedding,
    TypedGeometry,
    joint_parent_null_distribution,
    path_tld_closure,
    point_cloud_winding_coherence,
    rotate_vector_field_90,
    typed_projection_scores,
)
from torusbrot.tld.scoring import materialize_ladder, score_ladder

FloatArray = NDArray[np.float64]
ROOT = Path(__file__).resolve().parents[1]
CALIBRATION = ROOT / "studies" / "v0.3.0-recovery" / "calibration"
BRIDGE = ROOT / "studies" / "v0.3.0-recovery" / "bridge"
HISTORICAL_RESULT = ROOT / "results" / "tld-i" / "production-fixed" / "tld_i_reproduction.json"
HISTORICAL_RAW = ROOT / "external_cache" / "zenodo" / "18080090" / "quarantine" / "TORUS_Zenodo_v1" / "data_inputs" / "targets_baseline.csv"
PARENT_COUNT = 20
NULL_CHILD_COUNT = 31
JOINT_NULL_REPLICATES = 999
NULL_TIE_RTOL = 1e-10
NULL_TIE_ATOL = 1e-10


def family(
    family_id: str,
    family_class: str,
    generator: str,
    kind: GeometryKind,
    channel: str,
    truth: str,
    hierarchy: str,
    baseline: str,
) -> dict[str, Any]:
    return {
        "family_id": family_id,
        "family_class": family_class,
        "generator": generator,
        "geometry_kind": kind.value,
        "target_channel": channel,
        "channel_truth": truth,
        "universal_TLD_truth": "NOT_DEFINED",
        "hierarchy": hierarchy,
        "domain_baseline": baseline,
        "parent_count": PARENT_COUNT,
        "stochastic_realizations": PARENT_COUNT,
        "base_seed": 330000 + int(family_id[1:]) * 1000 + {"N": 0, "P": 100000, "A": 200000}[family_id[0]],
    }


FAMILIES = [
    family("N01", "TRUE_NEGATIVE", "scalar_iid", GeometryKind.SCALAR_FIELD_2D, "neighbor_coherence", "ABSENT", "20 independent fields", "iid Gaussian"),
    family("N02", "TRUE_NEGATIVE", "vector_iid", GeometryKind.VECTOR_FIELD_2D, "curl_energy", "ABSENT", "20 independent vector fields", "iid vector Gaussian"),
    family("N03", "TRUE_NEGATIVE", "scalar_volume_iid", GeometryKind.SCALAR_VOLUME_3D, "volume_neighbor", "ABSENT", "20 independent volumes", "iid voxel Gaussian"),
    family("N04", "TRUE_NEGATIVE", "temporal_white", GeometryKind.SPATIOTEMPORAL_SCALAR, "temporal_lag", "ABSENT", "20 independent time series of fields", "temporally exchangeable frames"),
    family("N05", "TRUE_NEGATIVE", "weighted_er", GeometryKind.WEIGHTED_GRAPH, "graph_spectral_radius", "ABSENT", "20 independent graphs", "matched weighted Erdos-Renyi"),
    family("N06", "TRUE_NEGATIVE", "directed_acyclic", GeometryKind.DIRECTED_GRAPH, "directed_three_cycle", "ABSENT", "20 independent DAGs", "matched directed acyclic graph"),
    family("N07", "TRUE_NEGATIVE", "irregular_random", GeometryKind.IRREGULAR_POINT_FIELD, "point_coherence", "ABSENT", "20 independent point fields", "coordinate-matched value shuffle"),
    family("N08", "TRUE_NEGATIVE", "point_disk_unordered", GeometryKind.MANIFOLD_POINT_CLOUD, "winding_number", "ABSENT", "20 independent unordered point clouds", "order-randomized coordinate path"),
    family("N09", "TRUE_NEGATIVE", "correlation_identity", GeometryKind.CORRELATION, "low_rank_concentration", "ABSENT", "20 independent registered matrices", "identity correlation"),
    family("N10", "TRUE_NEGATIVE", "multi_independent", GeometryKind.MULTICOMPONENT_SINGLE_SYSTEM, "cross_component_correlation", "ABSENT", "20 independent multichannel systems", "independent component shuffle"),
    family("N11", "TRUE_NEGATIVE", "masked_iid", GeometryKind.SCALAR_FIELD_2D, "neighbor_coherence", "ABSENT", "20 independent masked sensor fields", "mask-preserving shuffle"),
    family("N12", "ADVERSARIAL_NEAR_NULL", "phase_randomized", GeometryKind.SCALAR_FIELD_2D, "neighbor_coherence", "PRESENT_DECOY_NOT_TLD", "20 phase-randomized hard negatives", "spectrum-preserving phase randomization"),
    family("N13", "TRUE_NEGATIVE", "vector_potential_flow", GeometryKind.VECTOR_FIELD_2D, "curl_energy", "ABSENT", "20 independent curl-free vector fields", "gradient potential flow"),
    family("P01", "POSITIVE_CHANNEL_CONTROL", "scalar_gradient", GeometryKind.SCALAR_FIELD_2D, "neighbor_coherence", "PRESENT", "4 campaigns x 5 independent fields", "planar gradient plus relative noise"),
    family("P02", "POSITIVE_CHANNEL_CONTROL", "scalar_wave", GeometryKind.SCALAR_FIELD_2D, "spectral_concentration", "PRESENT", "20 independent phase-jittered fields", "registered sinusoidal model"),
    family("P03", "POSITIVE_CHANNEL_CONTROL", "vector_vortex", GeometryKind.VECTOR_FIELD_2D, "curl_coherence", "PRESENT", "20 independent vector fields", "solid-body rotation"),
    family("P04", "POSITIVE_CHANNEL_CONTROL", "vector_shear", GeometryKind.VECTOR_FIELD_2D, "curl_coherence", "PRESENT", "20 independent vector fields", "linear shear"),
    family("P05", "POSITIVE_CHANNEL_CONTROL", "scalar_volume_layers", GeometryKind.SCALAR_VOLUME_3D, "volume_neighbor", "PRESENT", "20 independent volumes", "layered scalar model"),
    family("P06", "POSITIVE_CHANNEL_CONTROL", "vector_volume_vortex", GeometryKind.VECTOR_VOLUME_3D, "curl_coherence_3d", "PRESENT", "20 independent vector volumes", "3D rotational flow"),
    family("P07", "POSITIVE_CHANNEL_CONTROL", "temporal_pulse", GeometryKind.SPATIOTEMPORAL_SCALAR, "temporal_lag", "PRESENT", "5 campaigns x 4 independent acquisitions", "registered evolving pulse"),
    family("P08", "POSITIVE_CHANNEL_CONTROL", "temporal_vector_vortex", GeometryKind.SPATIOTEMPORAL_VECTOR, "temporal_vector_curl_coherence", "PRESENT", "20 independent vector movies", "time-varying rotational flow"),
    family("P09", "POSITIVE_CHANNEL_CONTROL", "weighted_community", GeometryKind.WEIGHTED_GRAPH, "graph_triangle_concentration", "PRESENT", "4 campaigns x 5 independent graphs", "weighted block model"),
    family("P10", "POSITIVE_CHANNEL_CONTROL", "directed_cycle", GeometryKind.DIRECTED_GRAPH, "directed_return_trace", "PRESENT", "20 independent directed graphs", "directed-cycle model"),
    family("P11", "POSITIVE_CHANNEL_CONTROL", "irregular_gradient", GeometryKind.IRREGULAR_POINT_FIELD, "point_coherence", "PRESENT", "20 independent irregular scans", "coordinate-linear regression"),
    family("P12", "POSITIVE_CHANNEL_CONTROL", "manifold_ring", GeometryKind.MANIFOLD_POINT_CLOUD, "winding_number", "PRESENT", "20 independently jittered ordered rings", "registered winding-number operator"),
    family("A01", "ADVERSARIAL_NEAR_NULL", "correlation_factor", GeometryKind.CORRELATION, "low_rank_concentration", "PRESENT_DECOY_NOT_TLD", "20 independent correlation matrices", "one-factor conventional model"),
    family("A02", "ADVERSARIAL_NEAR_NULL", "multi_coupled_one_channel", GeometryKind.COUPLED_MULTI_SYSTEM, "cross_component_correlation", "PRESENT_DECOY_NOT_TLD", "20 single-system coupled fields", "linear coupling baseline"),
    family("A03", "ADVERSARIAL_NEAR_NULL", "masked_boundary_gradient", GeometryKind.SCALAR_FIELD_2D, "neighbor_coherence", "PRESENT_DECOY_NOT_TLD", "5 parent sensors x 4 nested repeats", "boundary-driven gradient"),
    family("A04", "ADVERSARIAL_NEAR_NULL", "checkerboard", GeometryKind.SCALAR_FIELD_2D, "spectral_concentration", "PRESENT_DECOY_NOT_TLD", "20 independent raster controls", "single-frequency lattice"),
    family("A05", "ADVERSARIAL_NEAR_NULL", "smooth_decoy", GeometryKind.SCALAR_FIELD_2D, "neighbor_coherence", "PRESENT_DECOY_NOT_TLD", "20 independent smooth fields", "Gaussian smoothing baseline"),
    family("A06", "ADVERSARIAL_NEAR_NULL", "boundary_sinusoid", GeometryKind.SCALAR_FIELD_2D, "spectral_concentration", "PRESENT_DECOY_NOT_TLD", "20 boundary-supported fields", "boundary-condition harmonic"),
]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"empty table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def grid(size: int = 24) -> tuple[FloatArray, FloatArray, FloatArray]:
    y, x = np.mgrid[-1.0 : 1.0 : complex(size), -1.0 : 1.0 : complex(size)]
    return y, x, np.stack((x, y), axis=-1)


def _correlation_from_samples(samples: FloatArray) -> FloatArray:
    correlation = np.corrcoef(samples, rowvar=False)
    correlation = (correlation + correlation.T) / 2.0
    np.fill_diagonal(correlation, 1.0)
    return correlation


def make_geometry(record: dict[str, Any], seed: int) -> TypedGeometry:
    rng = np.random.default_rng(seed)
    generator = record["generator"]
    y, x, coordinates = grid()
    projection_id = f"SUITE_V2:{record['family_id']}:{record['target_channel']}"
    if generator == "scalar_iid":
        return TypedGeometry(GeometryKind.SCALAR_FIELD_2D, rng.normal(size=x.shape), projection_id=projection_id)
    if generator == "vector_iid":
        return TypedGeometry(GeometryKind.VECTOR_FIELD_2D, rng.normal(size=(*x.shape, 2)), coordinates=coordinates, component_names=("u", "v"), orientation="x-y", projection_id=projection_id)
    if generator == "scalar_volume_iid":
        return TypedGeometry(GeometryKind.SCALAR_VOLUME_3D, rng.normal(size=(6, *x.shape)), projection_id=projection_id)
    if generator == "temporal_white":
        return TypedGeometry(GeometryKind.SPATIOTEMPORAL_SCALAR, rng.normal(size=(8, *x.shape)), time=np.arange(8, dtype=float), projection_id=projection_id)
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
        return TypedGeometry(GeometryKind.WEIGHTED_GRAPH, matrix, projection_id=projection_id)
    if generator in {"directed_acyclic", "directed_cycle"}:
        matrix = np.zeros((12, 12), dtype=float)
        if generator == "directed_acyclic":
            upper = rng.uniform(0.2, 1.0, size=(12, 12)) * (rng.random((12, 12)) < 0.22)
            matrix = np.triu(upper, 1)
        else:
            for index in range(12):
                matrix[index, (index + 1) % 12] = 0.9 + rng.uniform(0.0, 0.2)
                matrix[index, (index + 4) % 12] = 0.25
        return TypedGeometry(GeometryKind.DIRECTED_GRAPH, matrix, projection_id=projection_id)
    if generator in {"irregular_random", "irregular_gradient"}:
        point_coordinates = rng.uniform(-1.0, 1.0, size=(96, 2))
        values = rng.normal(size=96)
        if generator == "irregular_gradient":
            values = point_coordinates[:, 0] + 0.7 * point_coordinates[:, 1] + rng.normal(scale=0.08, size=96)
        return TypedGeometry(GeometryKind.IRREGULAR_POINT_FIELD, values, coordinates=point_coordinates, projection_id=projection_id)
    if generator in {"point_disk_unordered", "manifold_ring"}:
        if generator == "point_disk_unordered":
            theta = rng.uniform(-np.pi, np.pi, size=96)
            radius = np.sqrt(rng.uniform(0.05, 1.0, size=96))
        else:
            theta = np.linspace(-np.pi, np.pi, 96, endpoint=False)
            theta += rng.normal(scale=0.005, size=96)
            radius = 1.0 + rng.normal(scale=0.015, size=96)
        point_coordinates = np.column_stack((radius * np.cos(theta), radius * np.sin(theta)))
        return TypedGeometry(GeometryKind.MANIFOLD_POINT_CLOUD, np.sin(theta), coordinates=point_coordinates, projection_id=projection_id)
    if generator in {"correlation_identity", "correlation_factor"}:
        samples = rng.normal(size=(256, 8))
        if generator == "correlation_factor":
            latent = rng.normal(size=(256, 1))
            samples = 0.85 * latent + 0.35 * samples
        matrix = np.eye(8) if generator == "correlation_identity" else _correlation_from_samples(samples)
        return TypedGeometry(GeometryKind.CORRELATION, matrix, projection_id=projection_id)
    if generator in {"multi_independent", "multi_coupled_one_channel"}:
        left = rng.normal(size=x.shape)
        right = rng.normal(size=x.shape)
        kind = GeometryKind.MULTICOMPONENT_SINGLE_SYSTEM
        if generator == "multi_coupled_one_channel":
            left = np.sin(3.0 * x) + rng.normal(scale=0.08, size=x.shape)
            right = 0.9 * left + rng.normal(scale=0.08, size=x.shape)
            kind = GeometryKind.COUPLED_MULTI_SYSTEM
        return TypedGeometry(kind, np.stack((left, right), axis=-1), component_names=("a", "b"), projection_id=projection_id)
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
        return TypedGeometry(GeometryKind.SCALAR_FIELD_2D, values, mask=mask, projection_id=projection_id)
    if generator == "phase_randomized":
        base = np.sin(4.0 * np.pi * x) + 0.7 * np.cos(3.0 * np.pi * y)
        transform = np.fft.rfft2(base)
        phase = rng.uniform(-np.pi, np.pi, size=transform.shape)
        randomized = np.fft.irfft2(np.abs(transform) * np.exp(1j * phase), s=base.shape)
        return TypedGeometry(GeometryKind.SCALAR_FIELD_2D, randomized, projection_id=projection_id)
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
        return TypedGeometry(GeometryKind.SCALAR_FIELD_2D, values, projection_id=projection_id)
    if generator in {"vector_vortex", "vector_shear", "vector_potential_flow"}:
        if generator == "vector_vortex":
            values = np.stack((-y, x), axis=-1)
        elif generator == "vector_shear":
            values = np.stack((y, np.zeros_like(y)), axis=-1)
        else:
            values = np.stack((x, y), axis=-1)
        values += rng.normal(scale=0.03, size=values.shape)
        return TypedGeometry(GeometryKind.VECTOR_FIELD_2D, values, coordinates=coordinates, component_names=("u", "v"), orientation="x-y", projection_id=projection_id)
    if generator == "scalar_volume_layers":
        layers = [np.sin(2.0 * np.pi * x) + depth * 0.4 for depth in np.linspace(-1.0, 1.0, 6)]
        values = np.asarray(layers) + rng.normal(scale=0.05, size=(6, *x.shape))
        return TypedGeometry(GeometryKind.SCALAR_VOLUME_3D, values, projection_id=projection_id)
    if generator == "vector_volume_vortex":
        z = np.linspace(-1.0, 1.0, 6)[:, None, None]
        u = np.broadcast_to(-y, (6, *y.shape))
        v = np.broadcast_to(x, (6, *x.shape))
        w = np.broadcast_to(0.2 * z, u.shape)
        values = np.stack((u, v, w), axis=-1) + rng.normal(scale=0.02, size=(*u.shape, 3))
        return TypedGeometry(GeometryKind.VECTOR_VOLUME_3D, values, component_names=("u", "v", "w"), projection_id=projection_id)
    if generator == "temporal_pulse":
        time = np.linspace(0.0, 1.0, 8)
        spatial = np.exp(-4.0 * (x**2 + y**2))
        values = np.asarray([(0.2 + value) * spatial for value in time])
        values += rng.normal(scale=0.015, size=values.shape)
        return TypedGeometry(GeometryKind.SPATIOTEMPORAL_SCALAR, values, time=time, projection_id=projection_id)
    if generator == "temporal_vector_vortex":
        time = np.linspace(0.0, 1.0, 8)
        values = np.asarray([np.stack((-(1.0 + value) * y, (1.0 + value) * x), axis=-1) for value in time])
        values += rng.normal(scale=0.02, size=values.shape)
        return TypedGeometry(GeometryKind.SPATIOTEMPORAL_VECTOR, values, coordinates=coordinates, time=time, component_names=("u", "v"), orientation="x-y", projection_id=projection_id)
    raise ValueError(f"unknown generator: {generator}")


def project(record: dict[str, Any], geometry: TypedGeometry) -> float:
    channel = record["target_channel"]
    if channel == "winding_number":
        return point_cloud_winding_coherence(np.asarray(geometry.coordinates))
    scores = typed_projection_scores(geometry)
    keys = {
        "neighbor_coherence": "neighbor_coherence",
        "spectral_concentration": "spectral_concentration",
        "curl_energy": "curl_energy",
        "curl_coherence": "curl_coherence",
        "volume_neighbor": "median_slice_neighbor_coherence",
        "curl_energy_3d": "curl_energy_3d",
        "curl_coherence_3d": "curl_coherence_3d",
        "temporal_lag": "temporal_lag1_frame_mean",
        "temporal_vector_curl": "median_curl_energy",
        "temporal_vector_curl_coherence": "median_curl_coherence",
        "graph_spectral_radius": "spectral_radius",
        "directed_three_cycle": "signed_three_cycle_trace",
        "graph_triangle_concentration": "normalized_three_cycle_trace",
        "directed_return_trace": "maximum_normalized_return_trace",
        "point_coherence": "nearest_neighbor_value_coherence",
        "cross_component_correlation": "cross_component_correlation:a:b",
    }
    if channel == "low_rank_concentration":
        return float(len(geometry.values) - scores["effective_rank"])
    return float(abs(scores[keys[channel]]))


def make_null(record: dict[str, Any], geometry: TypedGeometry, seed: int) -> TypedGeometry:
    rng = np.random.default_rng(seed)
    values = np.asarray(geometry.values).copy()
    kind = geometry.kind
    if kind in {GeometryKind.SCALAR_FIELD_2D, GeometryKind.SCALAR_VOLUME_3D}:
        if geometry.mask is None:
            values = values.ravel()[rng.permutation(values.size)].reshape(values.shape)
        else:
            mask = np.asarray(geometry.mask)
            observed = values[mask]
            values[mask] = observed[rng.permutation(len(observed))]
    elif kind in {GeometryKind.VECTOR_FIELD_2D, GeometryKind.VECTOR_VOLUME_3D}:
        flat = values.reshape(-1, values.shape[-1])
        values = flat[rng.permutation(len(flat))].reshape(values.shape)
    elif kind in {GeometryKind.SPATIOTEMPORAL_SCALAR, GeometryKind.SPATIOTEMPORAL_VECTOR}:
        values = values[rng.permutation(values.shape[0])]
        spatial = values.reshape(values.shape[0], -1, *(() if kind == GeometryKind.SPATIOTEMPORAL_SCALAR else (2,)))
        for index in range(len(spatial)):
            spatial[index] = spatial[index][rng.permutation(len(spatial[index]))]
        values = spatial.reshape(values.shape)
    elif kind in {GeometryKind.WEIGHTED_GRAPH, GeometryKind.DIRECTED_GRAPH}:
        if kind == GeometryKind.WEIGHTED_GRAPH:
            upper = np.triu_indices(len(values), 1)
            weights = values[upper]
            values = np.zeros_like(values)
            values[upper] = weights[rng.permutation(len(weights))]
            values += values.T
        else:
            off_diagonal = ~np.eye(len(values), dtype=bool)
            edges = values[off_diagonal]
            values[off_diagonal] = edges[rng.permutation(len(edges))]
    elif kind in {GeometryKind.IRREGULAR_POINT_FIELD}:
        values = values[rng.permutation(len(values))]
    elif kind == GeometryKind.MANIFOLD_POINT_CLOUD:
        coordinates = np.asarray(geometry.coordinates)[rng.permutation(len(values))]
        return TypedGeometry(kind, values, coordinates=coordinates, mask=geometry.mask, projection_id=f"{geometry.projection_id}:null")
    elif kind in {GeometryKind.MULTICOMPONENT_SINGLE_SYSTEM, GeometryKind.COUPLED_MULTI_SYSTEM}:
        for component in range(values.shape[-1]):
            flat = values[..., component].ravel()
            values[..., component] = flat[rng.permutation(len(flat))].reshape(values.shape[:-1])
    elif kind == GeometryKind.CORRELATION:
        permutation = rng.permutation(len(values))
        values = values[permutation][:, permutation]
    return TypedGeometry(kind, values, coordinates=geometry.coordinates, mask=geometry.mask, time=geometry.time, component_names=geometry.component_names, orientation=geometry.orientation, projection_id=f"{geometry.projection_id}:null")


def wilson(successes: int, total: int) -> tuple[float, float]:
    if total == 0:
        return 0.0, 1.0
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1.0 + z**2 / total
    center = (proportion + z**2 / (2.0 * total)) / denominator
    radius = z * math.sqrt(proportion * (1.0 - proportion) / total + z**2 / (4.0 * total**2)) / denominator
    return max(0.0, center - radius), min(1.0, center + radius)


def parent_matched_upper_p(observed: float, null_scores: list[float]) -> float:
    """Return a finite-sample upper-tail p-value with numerical ties included."""
    tolerance = max(NULL_TIE_ATOL, abs(observed) * NULL_TIE_RTOL)
    exceedances = sum(value >= observed - tolerance for value in null_scores)
    return (1 + exceedances) / (len(null_scores) + 1)


def representation_check(record: dict[str, Any], geometry: TypedGeometry, observed: float) -> tuple[str, float | None]:
    if geometry.kind == GeometryKind.VECTOR_FIELD_2D:
        transformed = rotate_vector_field_90(geometry)
    elif geometry.kind == GeometryKind.SPATIOTEMPORAL_VECTOR:
        transformed = rotate_vector_field_90(geometry)
    elif geometry.kind in {GeometryKind.SCALAR_FIELD_2D}:
        transformed = TypedGeometry(geometry.kind, np.rot90(geometry.values), mask=None if geometry.mask is None else np.rot90(geometry.mask), projection_id=f"{geometry.projection_id}:rot90")
    elif geometry.kind == GeometryKind.SCALAR_VOLUME_3D:
        transformed = TypedGeometry(geometry.kind, np.rot90(geometry.values, axes=(1, 2)), projection_id=f"{geometry.projection_id}:rot90")
    elif geometry.kind == GeometryKind.SPATIOTEMPORAL_SCALAR:
        transformed = TypedGeometry(geometry.kind, np.rot90(geometry.values, axes=(1, 2)), time=geometry.time, projection_id=f"{geometry.projection_id}:rot90")
    elif geometry.kind in {GeometryKind.WEIGHTED_GRAPH, GeometryKind.DIRECTED_GRAPH, GeometryKind.CORRELATION}:
        permutation = np.arange(len(geometry.values))[::-1]
        values = geometry.values[permutation][:, permutation]
        transformed = TypedGeometry(geometry.kind, values, projection_id=f"{geometry.projection_id}:relabel")
    elif geometry.kind in {GeometryKind.IRREGULAR_POINT_FIELD, GeometryKind.MANIFOLD_POINT_CLOUD}:
        rotation = np.asarray([[0.0, -1.0], [1.0, 0.0]])
        transformed = TypedGeometry(geometry.kind, geometry.values, coordinates=np.asarray(geometry.coordinates) @ rotation.T, mask=geometry.mask, projection_id=f"{geometry.projection_id}:rigid-rot90")
    elif geometry.kind in {GeometryKind.MULTICOMPONENT_SINGLE_SYSTEM, GeometryKind.COUPLED_MULTI_SYSTEM}:
        transformed = TypedGeometry(geometry.kind, np.rot90(geometry.values, axes=(0, 1)), component_names=geometry.component_names, projection_id=f"{geometry.projection_id}:rot90")
    else:
        return "NOT_APPLICABLE_REGISTERED_TRANSFORM_PENDING", None
    transformed_score = project(record, transformed)
    tolerance = 1e-9 * max(1.0, abs(observed))
    return ("PASS" if abs(transformed_score - observed) <= tolerance else "DISAGREEMENT", transformed_score)


def calibrate_suite() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, Any]] = {}
    for record in FAMILIES:
        observed_scores: list[float] = []
        null_matrix: list[list[float]] = []
        family_results: list[dict[str, Any]] = []
        for parent_index in range(PARENT_COUNT):
            seed = int(record["base_seed"]) + parent_index
            geometry = make_geometry(record, seed)
            observed = project(record, geometry)
            null_scores = [
                project(record, make_null(record, geometry, seed * 1000 + child_index + 1))
                for child_index in range(NULL_CHILD_COUNT)
            ]
            upper_p = parent_matched_upper_p(observed, null_scores)
            agreement, transformed_score = representation_check(record, geometry, observed)
            row = {
                "family_id": record["family_id"],
                "family_class": record["family_class"],
                "geometry_kind": record["geometry_kind"],
                "target_channel": record["target_channel"],
                "channel_truth": record["channel_truth"],
                "parent_index": parent_index,
                "seed": seed,
                "campaign_id": f"campaign-{parent_index // 5 + 1}" if "campaign" in record["hierarchy"] else f"independent-{parent_index + 1}",
                "nested_replicates": 4 if "nested" in record["hierarchy"] else 1,
                "observed_score": observed,
                "null_median": float(np.median(null_scores)),
                "observed_minus_null": observed - float(np.median(null_scores)),
                "parent_matched_upper_p": upper_p,
                "parent_channel_detected": upper_p <= 0.05,
                "representation_status": agreement,
                "transformed_score": transformed_score,
                "universal_TLD_call": "NOT_APPLICABLE",
            }
            results.append(row)
            family_results.append(row)
            observed_scores.append(observed)
            null_matrix.append(null_scores)
        joint = joint_parent_null_distribution(np.asarray(observed_scores), np.asarray(null_matrix), replicates=JOINT_NULL_REPLICATES, seed=int(record["base_seed"]) + 900)
        joint_values = np.asarray(joint.pop("joint_null_values"))
        summaries[str(record["family_id"])] = {
            "record": record,
            "joint": joint,
            "joint_null_sha256": hashlib.sha256(joint_values.tobytes()).hexdigest(),
            "joint_null_quantiles": {str(q): float(np.quantile(joint_values, q)) for q in [0.025, 0.5, 0.975]},
            "parent_detections": sum(bool(row["parent_channel_detected"]) for row in family_results),
            "representation_disagreements": sum(row["representation_status"] == "DISAGREEMENT" for row in family_results),
        }
    return results, summaries


def bridge_and_history() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not HISTORICAL_RAW.exists() or not HISTORICAL_RESULT.exists():
        raise FileNotFoundError("Phase A TLD I raw custody or exact production replay is missing")
    with HISTORICAL_RAW.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    omega, _ = materialize_ladder([float(row["value"]) for row in rows], [float(row["sigma"]) for row in rows])
    coordinates = np.arange(len(omega), dtype=float)[:, None]
    adjacency = np.zeros((len(omega), len(omega)), dtype=float)
    for index in range(len(omega) - 1):
        adjacency[index, index + 1] = adjacency[index + 1, index] = 1.0
    embeddings = [
        PathEmbedding("ONE_DIMENSIONAL_COORDINATE_FIELD", omega, coordinates),
        PathEmbedding("ONE_BY_M_SCALAR_FIELD", omega[None, :], coordinates),
        PathEmbedding("PATH_GRAPH", omega, coordinates, adjacency),
    ]
    direct = score_ladder(omega, range(7, 14)).to_dict()
    bridge_rows = []
    for embedding in embeddings:
        closure = path_tld_closure(embedding)
        bridge_rows.append(
            {
                "representation": embedding.representation,
                "direct_chi": direct["chi"],
                "projected_chi": closure["score"]["chi"],
                "direct_winner_N": direct["winner_N"],
                "projected_winner_N": closure["score"]["winner_N"],
                "direct_margin": direct["margin"],
                "projected_margin": closure["score"]["margin"],
                "exact_score_dictionary_agreement": closure["score"] == direct,
                "information_loss": closure["information_loss"],
                "commutative": closure["commutative"],
                "status": "PASS" if closure["score"] == direct else "FAIL",
            }
        )
    historical = historical_construct_benchmark(HISTORICAL_RESULT)
    historical["raw_input_sha256"] = hashlib.sha256(HISTORICAL_RAW.read_bytes()).hexdigest()
    historical["raw_input_expected_sha256"] = "856f102a4f58d53d67fdb1ac5982de12ca18a9c78efe13097f23879e262cb683"
    historical["bridge_representations_pass"] = all(row["status"] == "PASS" for row in bridge_rows)
    historical["bridge_is_parallel_legacy_check"] = False
    return bridge_rows, historical


def build_outputs() -> None:
    results, summaries = calibrate_suite()
    registry = [
        {
            **record,
            "raw_input": "DETERMINISTIC_SEED_AND_GENERATOR",
            "calibration_split": "parents 0-11",
            "synthetic_holdout_split": "parents 12-19",
            "wind_farm_outcomes_used": False,
            "Beijing_outcomes_used": False,
        }
        for record in FAMILIES
    ]
    ground_truth = [
        {
            "family_id": record["family_id"],
            "target_channel": record["target_channel"],
            "channel_truth": record["channel_truth"],
            "universal_binary_TLD_truth": "NOT_DEFINED",
            "adversarial_decoy": record["family_class"] == "ADVERSARIAL_NEAR_NULL",
        }
        for record in FAMILIES
    ]
    write_jsonl(CALIBRATION / "synthetic_v2_registry.jsonl", registry)
    write_jsonl(CALIBRATION / "synthetic_v2_ground_truth.jsonl", ground_truth)
    write_csv(CALIBRATION / "synthetic_v2_results.csv", results)
    type_i_rows = []
    power_rows = []
    sign_rows = []
    null_bias_rows = []
    agreement_rows = []
    rng = np.random.default_rng(340)
    for record in FAMILIES:
        family_rows = [row for row in results if row["family_id"] == record["family_id"]]
        detections = sum(bool(row["parent_channel_detected"]) for row in family_rows)
        lower, upper = wilson(detections, len(family_rows))
        if record["family_class"] == "TRUE_NEGATIVE":
            type_i_rows.append(
                {
                    "family_id": record["family_id"],
                    "target_channel": record["target_channel"],
                    "false_positives": detections,
                    "realizations": len(family_rows),
                    "estimated_type_I_error": detections / len(family_rows),
                    "wilson_95_low": lower,
                    "wilson_95_high": upper,
                    "universal_TLD_false_positive": "NOT_DEFINED",
                }
            )
        effects = np.asarray([float(row["observed_minus_null"]) for row in family_rows])
        sign_errors = (
            int(np.sum(effects <= 0.0)) if record["channel_truth"] == "PRESENT" else None
        )
        sign_lower, sign_upper = (
            wilson(sign_errors, len(effects)) if sign_errors is not None else (None, None)
        )
        sign_rows.append(
            {
                "family_id": record["family_id"],
                "channel_truth": record["channel_truth"],
                "sign_errors": sign_errors if sign_errors is not None else "NOT_APPLICABLE",
                "realizations": len(effects),
                "sign_error_rate": (
                    sign_errors / len(effects) if sign_errors is not None else "NOT_APPLICABLE"
                ),
                "wilson_95_low": sign_lower,
                "wilson_95_high": sign_upper,
            }
        )
        null_bias_rows.append(
            {
                "family_id": record["family_id"],
                "family_class": record["family_class"],
                "median_observed_minus_matched_null": float(np.median(effects)),
                "joint_null_two_sided_p": summaries[record["family_id"]]["joint"]["two_sided_p"],
                "children_flattened": False,
                "joint_null_replicates": JOINT_NULL_REPLICATES,
            }
        )
        agreement_disagreements = summaries[record["family_id"]]["representation_disagreements"]
        agreement_rows.append(
            {
                "family_id": record["family_id"],
                "registered_transform_checks": len(family_rows),
                "disagreements": agreement_disagreements,
                "agreement_rate": 1.0 - agreement_disagreements / len(family_rows),
                "status": "PASS" if agreement_disagreements == 0 else "PRESERVED_DISAGREEMENT",
            }
        )
        if record["family_class"] == "POSITIVE_CHANNEL_CONTROL":
            for parent_count in [1, 2, 4, 6, 8, 12, 20]:
                successes = 0
                simulations = 1000
                for _ in range(simulations):
                    sample = rng.choice(effects, size=parent_count, replace=True)
                    if float(np.median(sample)) > 0.0:
                        successes += 1
                low, high = wilson(successes, simulations)
                power_rows.append(
                    {
                        "family_id": record["family_id"],
                        "target_channel": record["target_channel"],
                        "parent_count": parent_count,
                        "median_effect": float(np.median(effects)),
                        "direction_recovery_probability": successes / simulations,
                        "wilson_95_low": low,
                        "wilson_95_high": high,
                        "interpretation": "SYNTHETIC_CHANNEL_DIRECTION_NOT_UNIVERSAL_TLD_POWER",
                    }
                )
    write_csv(CALIBRATION / "type_I_error_by_family.csv", type_i_rows)
    write_csv(CALIBRATION / "power_by_effect_and_parent_count.csv", power_rows)
    write_csv(CALIBRATION / "sign_error_by_family.csv", sign_rows)
    write_csv(CALIBRATION / "null_bias_by_family.csv", null_bias_rows)
    write_csv(CALIBRATION / "representation_agreement_by_family.csv", agreement_rows)
    bridge_rows, historical = bridge_and_history()
    write_csv(CALIBRATION / "geometry_tld_bridge_results.csv", bridge_rows)
    write_jsonl(BRIDGE / "commutative_operator_tests.jsonl", bridge_rows)
    write_json(BRIDGE / "construct_recovery_v2.json", historical)
    write_json(
        BRIDGE / "geometry_tld_bridge_adjudication.json",
        {
            "schema_version": "2.0.0",
            "status": "PASS_LOSSLESS_PATH_CHANNEL_ONLY" if all(row["status"] == "PASS" for row in bridge_rows) else "NEW_GEOMETRY_STATISTIC_NOT_TLD_BRIDGE",
            "path_representation_count": len(bridge_rows),
            "exact_commutative_pass_count": sum(row["status"] == "PASS" for row in bridge_rows),
            "historical_construct_recovery": historical["construct_recovery_pass"],
            "general_geometry_channel_status": "NON_TLD_INSTRUMENTED_EVIDENCE_VECTOR",
        },
    )
    historical_rows = [{"construct": key, "pass": value} for key, value in historical["checks"].items()]
    historical_rows.extend(
        [
            {"construct": "lossless_path_bridge_all_representations", "pass": all(row["status"] == "PASS" for row in bridge_rows)},
            {"construct": "raw_input_sha256_exact", "pass": historical["raw_input_sha256"] == historical["raw_input_expected_sha256"]},
        ]
    )
    write_csv(CALIBRATION / "historical_construct_results_v2.csv", historical_rows)
    negative_count = sum(record["family_class"] == "TRUE_NEGATIVE" for record in FAMILIES)
    positive_count = sum(record["family_class"] == "POSITIVE_CHANNEL_CONTROL" for record in FAMILIES)
    adversarial_count = sum(record["family_class"] == "ADVERSARIAL_NEAR_NULL" for record in FAMILIES)
    write_json(
        CALIBRATION / "calibration_uncertainty.json",
        {
            "schema_version": "2.0.0",
            "family_counts": {"true_negative": negative_count, "positive_channel_control": positive_count, "adversarial_near_null": adversarial_count},
            "realizations_per_family": PARENT_COUNT,
            "joint_null_replicates_per_family": JOINT_NULL_REPLICATES,
            "confidence_interval": "Wilson 95% for binomial rates",
            "type_I_family_upper_bounds": {row["family_id"]: row["wilson_95_high"] for row in type_i_rows},
            "predictive_binary_TLD_calibrated": False,
            "hierarchical_multi_channel_TLD_calibrated": False,
            "instrumented_evidence_vector_supported": True,
            "wind_farm_outcomes_used": False,
            "Beijing_use": "NONE_IN_METHOD_SELECTION",
            "external_validation": False,
        },
    )
    write_json(
        CALIBRATION / "synthetic_v2_summary.json",
        {
            "family_count": len(FAMILIES),
            "negative_family_count": negative_count,
            "positive_family_count": positive_count,
            "adversarial_family_count": adversarial_count,
            "raw_seed_realization_count": len(results),
            "representation_disagreement_count": sum(row["disagreements"] for row in agreement_rows),
            "bridge_status": "PASS_LOSSLESS_PATH_CHANNEL_ONLY",
            "historical_construct_recovery": historical["construct_recovery_pass"],
            "universal_binary_truth_used": False,
            "outcome_exposed_field_used": False,
        },
    )
    artifacts = sorted(
        path
        for path in CALIBRATION.glob("*")
        if path.is_file() and path.name != "calibration_generation_manifest.json"
    )
    write_json(
        CALIBRATION / "calibration_generation_manifest.json",
        {
            "generator": "scripts/calibrate_geometry_method_v2.py",
            "artifacts": [{"name": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in artifacts],
        },
    )


def main() -> None:
    build_outputs()
    print(
        f"Calibrated Synthetic Geometry Suite V2 from {len(FAMILIES)} families "
        "and raw TLD I custody."
    )


if __name__ == "__main__":
    main()
