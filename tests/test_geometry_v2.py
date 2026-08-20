from __future__ import annotations

import numpy as np
import pytest
from torusbrot.geometry.v2 import (
    GeometryKind,
    PathEmbedding,
    TypedGeometry,
    aggregate_modal_trace_audit,
    anti_alias_downsample_2d,
    ball_porosity,
    curvature_audit_v2,
    dual_concentration_operator_norm,
    extract_path_sequence,
    fup_applicability_gate,
    joint_parent_null_distribution,
    line_porosity,
    modal_residual_trace,
    path_tld_closure,
    point_cloud_winding_coherence,
    point_cloud_winding_number,
    reflect_vector_field_y,
    rotate_vector_field_90,
    typed_projection_scores,
    validate_typed_geometry,
)


def _grid(size: int = 4) -> np.ndarray:
    y, x = np.mgrid[:size, :size]
    return np.stack((x, y), axis=-1).astype(np.float64)


def test_vector_rotation_transforms_coordinates_components_mask_and_metadata() -> None:
    values = np.zeros((4, 4, 2), dtype=np.float64)
    values[..., 0] = 1.0
    mask = np.ones((4, 4), dtype=bool)
    mask[0, 0] = False
    geometry = TypedGeometry(
        kind=GeometryKind.VECTOR_FIELD_2D,
        values=values,
        coordinates=_grid(),
        mask=mask,
        component_names=("east", "north"),
        orientation="east-north",
        projection_id="vector-native",
    )

    rotated = rotate_vector_field_90(geometry)

    assert np.allclose(rotated.values[..., 0], 0.0)
    assert np.allclose(rotated.values[..., 1], 1.0)
    assert np.array_equal(rotated.mask, np.rot90(mask, k=-1))
    moved_coordinates = np.rot90(_grid(), k=-1)
    assert np.allclose(rotated.coordinates[..., 0], -moved_coordinates[..., 1])
    assert np.allclose(rotated.coordinates[..., 1], moved_coordinates[..., 0])
    assert rotated.orientation == "rot90(east-north)"


def test_vector_rotation_preserves_signed_curl_under_proper_rotation() -> None:
    coordinates = _grid(7)
    values = np.empty((7, 7, 2), dtype=np.float64)
    values[..., 0] = -coordinates[..., 1]
    values[..., 1] = coordinates[..., 0]
    geometry = TypedGeometry(
        kind=GeometryKind.VECTOR_FIELD_2D,
        values=values,
        coordinates=coordinates,
        component_names=("east", "north"),
        orientation="east-north",
        projection_id="solid-body-rotation",
    )

    original = typed_projection_scores(geometry)
    rotated = typed_projection_scores(rotate_vector_field_90(geometry))

    assert rotated["signed_mean_curl"] == pytest.approx(original["signed_mean_curl"])
    assert rotated["curl_energy"] == pytest.approx(original["curl_energy"])
    assert rotated["divergence_energy"] == pytest.approx(original["divergence_energy"])


def test_vector_reflection_changes_signed_normal_component() -> None:
    values = np.dstack((np.full((3, 3), 2.0), np.full((3, 3), 3.0)))
    geometry = TypedGeometry(
        kind=GeometryKind.VECTOR_FIELD_2D,
        values=values,
        coordinates=_grid(3),
        component_names=("east", "north"),
        projection_id="vector-native",
    )
    reflected = reflect_vector_field_y(geometry)
    assert np.all(reflected.values[..., 0] == 2.0)
    assert np.all(reflected.values[..., 1] == -3.0)
    assert np.all(reflected.coordinates[..., 1] <= 0.0)


def test_mask_is_preserved_without_mean_fill_and_downsample_is_antialiased() -> None:
    values = np.arange(16, dtype=np.float64).reshape(4, 4)
    values[0, 0] = np.nan
    mask = np.ones((4, 4), dtype=bool)
    mask[0, 0] = False
    geometry = TypedGeometry(
        kind=GeometryKind.SCALAR_FIELD_2D,
        values=values,
        mask=mask,
        projection_id="scalar-native",
    )
    reduced = anti_alias_downsample_2d(geometry)
    assert reduced.mask is not None and bool(reduced.mask[0, 0])
    assert reduced.values[0, 0] == pytest.approx((1.0 + 4.0 + 5.0) / 3.0)
    assert reduced.values[1, 1] == pytest.approx((10.0 + 11.0 + 14.0 + 15.0) / 4.0)


def test_silent_dimensional_collapse_and_vector_magnitude_are_rejected() -> None:
    with pytest.raises(ValueError, match="requires \\(y, x\\)"):
        validate_typed_geometry(
            TypedGeometry(
                kind=GeometryKind.SCALAR_FIELD_2D,
                values=np.ones((2, 4, 4)),
                projection_id="illegal-time-average",
            )
        )
    with pytest.raises(ValueError, match="registered component names"):
        validate_typed_geometry(
            TypedGeometry(
                kind=GeometryKind.VECTOR_FIELD_2D,
                values=np.ones((4, 4, 2)),
                projection_id="illegal-magnitude",
            )
        )


def test_volume_spatiotemporal_and_multicomponent_handlers_remain_typed() -> None:
    scalar_volume = TypedGeometry(
        kind=GeometryKind.SCALAR_VOLUME_3D,
        values=np.arange(48, dtype=np.float64).reshape(3, 4, 4),
        projection_id="scalar-volume",
    )
    assert "depth_lag1_slice_mean" in typed_projection_scores(scalar_volume)

    time = np.asarray([0.0, 0.5, 1.0])
    spatiotemporal = TypedGeometry(
        kind=GeometryKind.SPATIOTEMPORAL_SCALAR,
        values=np.arange(48, dtype=np.float64).reshape(3, 4, 4),
        time=time,
        projection_id="time-native",
    )
    assert "temporal_lag1_frame_mean" in typed_projection_scores(spatiotemporal)

    components = np.stack(
        (
            np.arange(16, dtype=np.float64).reshape(4, 4),
            np.arange(16, dtype=np.float64).reshape(4, 4) ** 2,
        ),
        axis=-1,
    )
    multicomponent = TypedGeometry(
        kind=GeometryKind.MULTICOMPONENT_SINGLE_SYSTEM,
        values=components,
        component_names=("a", "b"),
        projection_id="components-native",
    )
    scores = typed_projection_scores(multicomponent)
    assert "component:a:neighbor_coherence" in scores
    assert "component:b:neighbor_coherence" in scores
    assert "cross_component_correlation:a:b" in scores


def test_weighted_and_directed_graph_handlers_retain_edge_semantics() -> None:
    weighted = TypedGeometry(
        kind=GeometryKind.WEIGHTED_GRAPH,
        values=np.asarray([[0.0, 0.2, 0.0], [0.2, 0.0, 0.7], [0.0, 0.7, 0.0]]),
        projection_id="weighted-native",
    )
    directed = TypedGeometry(
        kind=GeometryKind.DIRECTED_GRAPH,
        values=np.asarray([[0.0, 1.0, 0.0], [0.0, 0.0, 2.0], [0.5, 0.0, 0.0]]),
        projection_id="directed-native",
    )
    assert typed_projection_scores(weighted)["total_absolute_edge_weight"] == pytest.approx(1.8)
    assert typed_projection_scores(directed)["weighted_reciprocity"] == pytest.approx(0.0)


def test_irregular_points_use_coordinates_and_mask_directly() -> None:
    geometry = TypedGeometry(
        kind=GeometryKind.IRREGULAR_POINT_FIELD,
        values=np.asarray([0.0, 1.0, 1.5, 2.0]),
        coordinates=np.asarray([[0.0, 0.0], [0.2, 0.1], [1.0, 0.7], [2.0, 1.9]]),
        mask=np.asarray([True, True, True, False]),
        projection_id="irregular-native",
    )
    scores = typed_projection_scores(geometry)
    assert set(scores) == {"coordinate_anisotropy", "nearest_neighbor_value_coherence"}

    theta = np.linspace(0.0, 2.0 * np.pi, 32, endpoint=False)
    ring = np.column_stack((np.cos(theta), np.sin(theta)))
    assert point_cloud_winding_number(ring) == pytest.approx(1.0)
    assert point_cloud_winding_number(ring[::-1]) == pytest.approx(-1.0)
    assert point_cloud_winding_coherence(ring) > 0.99
    shuffled = ring[np.random.default_rng(3).permutation(len(ring))]
    assert point_cloud_winding_coherence(shuffled) < 0.8


def test_joint_null_uses_parent_matched_aggregate_replicates() -> None:
    observed = np.asarray([1.0, 2.0, 3.0, 4.0])
    nulls = np.asarray(
        [[0.1, 0.2, 0.3], [0.5, 0.6, 0.7], [1.0, 1.1, 1.2], [1.5, 1.6, 1.7]]
    )
    result = joint_parent_null_distribution(observed, nulls, replicates=999, seed=3)
    assert result["children_flattened"] is False
    assert result["parent_count"] == 4
    assert len(result["joint_null_values"]) == 999
    with pytest.raises(ValueError, match="at least 999"):
        joint_parent_null_distribution(observed, nulls, replicates=998)


def test_joint_null_counts_numerically_equivalent_statistics_as_ties() -> None:
    observed = np.asarray([6.0, 6.0, 6.0, 6.0])
    roundoff = np.asarray([-4e-12, 3e-12, -2e-12, 5e-12])
    nulls = np.repeat((observed + roundoff)[:, np.newaxis], 3, axis=1)

    result = joint_parent_null_distribution(observed, nulls, replicates=999, seed=4)

    assert result["upper_tail_p"] == 1.0
    assert result["lower_tail_p"] == 1.0
    assert result["two_sided_p"] == 1.0


def test_modal_trace_has_no_midpoint_penalty_and_reports_boundary_ties() -> None:
    field = np.arange(64, dtype=np.float64).reshape(8, 8)
    trace = modal_residual_trace(field, [1, 2, 3, 4, 5])
    assert np.all(np.diff(trace) <= 0.0)
    parents = np.vstack((trace, trace * 1.01, trace * 0.99))
    null_children = np.repeat(parents[:, np.newaxis, :], 3, axis=1)
    audit = aggregate_modal_trace_audit(
        parents, null_children, [1, 2, 3, 4, 5], replicates=999
    )
    assert audit["midpoint_penalty"] is None
    assert audit["population_minimum_audit"]["boundary_minimum"] is True
    assert audit["null_children_flattened"] is False


def test_curvature_rejects_flat_trace_and_keeps_semantic_firewall() -> None:
    parents = np.ones((4, 5), dtype=np.float64)
    nulls = np.ones((999, 5), dtype=np.float64)
    result = curvature_audit_v2(parents, nulls, [1, 2, 3, 4, 5])
    assert result["status"] == "REJECTED_FLAT_OR_TIED_TRACE"
    assert result["selected_elbow"] is None

    curved = np.asarray(
        [[1.0, 0.8, 0.2, 0.19, 0.18], [1.01, 0.79, 0.21, 0.18, 0.17]]
    )
    null_curves = np.repeat(np.asarray([[1.0, 0.8, 0.6, 0.4, 0.2]]), 999, axis=0)
    result = curvature_audit_v2(curved, null_curves, [1, 2, 3, 4, 5])
    assert result["bootstrap_unit"] == "PARENT"
    assert result["elbow_is_T_e"] is False
    assert result["elbow_is_winner_N"] is False


def test_exact_sequence_path_and_one_by_m_tld_bridge_commute() -> None:
    omega = np.asarray([0.12, 0.25, 0.18, 0.31, 0.11, 0.28, 0.22, 0.16])
    coordinates = np.arange(len(omega), dtype=np.float64)[:, np.newaxis]
    adjacency = np.zeros((len(omega), len(omega)), dtype=np.float64)
    for index in range(len(omega) - 1):
        adjacency[index, index + 1] = adjacency[index + 1, index] = 1.0
    embeddings = [
        PathEmbedding("ONE_DIMENSIONAL_COORDINATE_FIELD", omega, coordinates),
        PathEmbedding("ONE_BY_M_SCALAR_FIELD", omega[np.newaxis, :], coordinates),
        PathEmbedding("PATH_GRAPH", omega, coordinates, adjacency),
    ]
    extracted = [extract_path_sequence(item) for item in embeddings]
    assert all(np.array_equal(sequence, omega) for sequence in extracted)
    scores = [path_tld_closure(item)["score"] for item in embeddings]
    assert scores[0] == scores[1] == scores[2]


def test_fup_channel_is_separately_gated() -> None:
    blocked = fup_applicability_gate(
        spatial_support_defined=True,
        spectral_support_defined=False,
        transform_registered=True,
        scale_registered=True,
        domain_justified=True,
    )
    assert blocked["applicable"] is False
    assert blocked["claim_authority"] == "OPTIONAL_DIAGNOSTIC_NOT_TORUS_CONFIRMATION"
    support = np.eye(8, dtype=bool)
    ball = ball_porosity(support, radii=[1, 2])
    assert len(ball["scale_rows"]) == 2
    assert ball["theorem_authority"] is False
    porosity = line_porosity(support, directions=[(1, 0), (0, 1), (1, 1)])
    assert porosity["directional_channel_count"] >= 1
    operator_norm = dual_concentration_operator_norm(support, support)
    assert 0.0 <= operator_norm <= 1.0 + 1e-12
