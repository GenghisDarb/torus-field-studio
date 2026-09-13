from dataclasses import replace

import numpy as np
import pytest
from numpy.testing import assert_allclose
from torusbrot.geometry.v2 import GeometryKind, TypedGeometry, typed_projection_scores
from torusbrot.metrology.temporal import temporal_diagnostics
from torusbrot.metrology.v1 import (
    Hierarchy,
    RectilinearVectorField,
    circulation,
    derivatives,
    field_from_coordinate_mesh,
    frame_at,
    nondimensionalize,
    reflect_y,
    regional_summary,
    reorder,
    resample_bilinear,
    rotate90,
)


def field(x=None, y=None):
    x = np.arange(5) * 2.0 if x is None else np.asarray(x, dtype=float)
    y = np.arange(5) * 0.5 if y is None else np.asarray(y, dtype=float)
    xx, yy = np.meshgrid(x, y)
    return RectilinearVectorField(
        np.stack((-yy, xx), axis=-1),
        x,
        y,
        np.ones(xx.shape, dtype=bool),
        "m",
        "m/s",
        Hierarchy("synthetic", "analytic", "one"),
        "SOLID_ROTATION",
    )


def test_legacy_scientific_counterexamples_remain_reproducible():
    f = field()
    old = TypedGeometry(
        GeometryKind.VECTOR_FIELD_2D,
        f.values,
        mask=f.mask,
        component_names=("u", "v"),
        projection_id="legacy",
    )
    assert typed_projection_scores(old)["signed_mean_curl"] == 2.5
    assert_allclose(derivatives(f).curl, 2)
    values = np.zeros_like(f.values)
    values[..., 0] = 1
    mask = f.mask.copy()
    mask[2, 2] = False
    assert typed_projection_scores(replace(old, values=values, mask=mask))[
        "curl_energy"
    ] == pytest.approx(1 / 48)
    corrected = derivatives(replace(f, values=values, mask=mask))
    assert np.isnan(corrected.curl[2, 1])
    assert np.isnan(corrected.curl[1, 2])
    assert_allclose(corrected.curl[corrected.support], 0, atol=1e-15)
    assert_allclose(corrected.divergence[corrected.support], 0, atol=1e-15)


def test_nonuniform_coordinates_quadratic_exact_and_units():
    f = field([0, 0.2, 0.9, 2.0, 5.0], [-1, -0.3, 0.2, 2.2])
    xx, yy = np.meshgrid(f.x, f.y)
    f = replace(f, values=np.stack((xx**2 - yy, yy**2 + xx), axis=-1))
    result = derivatives(f)
    assert_allclose(result.curl, 2, atol=3e-14)
    assert_allclose(result.divergence, 2 * xx + 2 * yy, atol=3e-14)
    millimeters = replace(
        f,
        x=f.x * 1000,
        y=f.y * 1000,
        values=f.values * 1000,
        coordinate_unit="mm",
        velocity_unit="mm/s",
    )
    assert_allclose(derivatives(millimeters).curl, result.curl, atol=3e-14)
    assert_allclose(
        nondimensionalize(millimeters, length_m=2, speed_m_per_s=3).values,
        nondimensionalize(f, length_m=2, speed_m_per_s=3).values,
    )
    assert_allclose(
        derivatives(nondimensionalize(f, length_m=2, speed_m_per_s=3)).curl,
        result.curl * 2 / 3,
        atol=3e-14,
    )
    assert result.derivative_unit == "s^-1"


def test_transformations_rotation_reflection_reordering_translation():
    f = field()
    mask = f.mask.copy()
    mask[1, 2] = False
    f = replace(f, mask=mask)
    original = derivatives(f)
    rotated = derivatives(rotate90(f))
    reflected = derivatives(reflect_y(f))
    reordered = derivatives(reorder(f, reverse_x=True, reverse_y=True))
    assert_allclose(rotated.curl, original.curl.T, atol=1e-13, equal_nan=True)
    assert np.array_equal(rotated.support, original.support.T)
    assert_allclose(reflected.curl, -original.curl, atol=1e-13, equal_nan=True)
    assert_allclose(reflected.divergence, original.divergence, atol=1e-13, equal_nan=True)
    assert_allclose(reordered.curl, original.curl[::-1, ::-1], equal_nan=True)
    assert_allclose(
        derivatives(replace(f, x=f.x + 91, y=f.y - 48)).curl,
        original.curl,
        atol=1e-13,
        equal_nan=True,
    )


def test_circulation_regional_area_and_cancellation():
    f = field()
    loop = (
        [(0, i) for i in range(5)]
        + [(j, 4) for j in range(1, 5)]
        + [(4, i) for i in range(3, -1, -1)]
        + [(j, 0) for j in range(3, 0, -1)]
    )
    observed = circulation(f, loop)
    assert observed["circulation"] == pytest.approx(32)
    assert observed["signed_loop_area"] == pytest.approx(16)
    summary = regional_summary(derivatives(f))
    assert summary["net_vorticity_integral"] == pytest.approx(32)
    assert summary["cancellation_fraction"] == 0
    g = field(np.linspace(-1, 1, 21), np.linspace(-1, 1, 21))
    xx, yy = np.meshgrid(g.x, g.y)
    paired = replace(g, values=np.stack((np.zeros_like(xx), xx**2), axis=-1))
    mixed = regional_summary(derivatives(paired))
    assert mixed["positive_vorticity_integral"] > 0
    assert mixed["negative_vorticity_integral"] < 0
    assert mixed["cancellation_fraction"] == pytest.approx(1)
    mask = f.mask.copy()
    mask[0, 0] = False
    assert circulation(replace(f, mask=mask), loop)["circulation"] is None


def test_derivative_convergence_including_crop_boundaries():
    errors = []
    for n in (17, 33, 65):
        f = field(np.linspace(-1, 1, n), np.linspace(-1, 1, n))
        xx, yy = np.meshgrid(f.x, f.y)
        f = replace(f, values=np.stack((np.zeros_like(xx), xx**3), axis=-1))
        result = derivatives(f)
        errors.append(np.max(np.abs(result.curl - 3 * xx**2)))
        crop = replace(
            f, x=f.x[3:-3], y=f.y[3:-3], values=f.values[3:-3, 3:-3], mask=f.mask[3:-3, 3:-3]
        )
        assert (
            np.max(np.abs(derivatives(crop).curl - 3 * xx[3:-3, 3:-3] ** 2)) <= errors[-1] * 1.001
        )
    assert np.all(np.asarray(errors[:-1]) / errors[1:] > 3.99)


def test_coordinate_propagation_time():
    f = field()
    temporal = replace(
        f,
        values=np.stack([f.values, f.values * 2]),
        mask=np.stack([f.mask, f.mask]),
        time=np.array([0.0, 0.25]),
        time_unit="s",
    )
    result = derivatives(temporal)
    assert_allclose(result.curl[0], 2)
    assert_allclose(result.curl[1], 4)
    assert np.array_equal(frame_at(temporal, 1).x, f.x)
    assert_allclose(derivatives(frame_at(temporal, 1)).curl, 4)
    with pytest.raises(ValueError, match="chronological"):
        replace(temporal, time=np.array([0.25, 0.0]))


def test_raw_mesh_axes_resolved_from_coordinates():
    f = field()
    xx, yy = np.meshgrid(f.x, f.y)
    resolved = field_from_coordinate_mesh(
        values=f.values.transpose(1, 0, 2),
        x_mesh=xx.T,
        y_mesh=yy.T,
        mask=f.mask.T,
        coordinate_unit="m",
        velocity_unit="m/s",
        hierarchy=f.hierarchy,
        projection_id="TRANSPOSED_SOURCE",
    )
    assert_allclose(derivatives(resolved).curl, 2)
    with pytest.raises(ValueError, match="nonrectilinear"):
        field_from_coordinate_mesh(
            values=f.values,
            x_mesh=xx + yy / 10,
            y_mesh=yy,
            mask=f.mask,
            coordinate_unit="m",
            velocity_unit="m/s",
            hierarchy=f.hierarchy,
            projection_id="NOT_A_RASTER",
        )


def test_temporal_diagnostics_sensitive_to_order_and_gaps():
    t = np.arange(256) / 64
    u = np.sin(2 * np.pi * 4 * t)
    signals = np.stack((u, np.roll(u, 2), u * 2), axis=-1)
    original = temporal_diagnostics(signals, t, replicates=20)
    permuted = temporal_diagnostics(
        signals[np.random.default_rng(41).permutation(len(t))], t, replicates=20
    )
    assert original["signals"]["u"]["dominant_fft_frequency_hz"] == pytest.approx(4)
    assert original["signals"]["u"]["acf"][1] > 0.9
    assert abs(permuted["signals"]["u"]["acf"][1]) < 0.2
    assert original["independent_system_count_added"] == 0
    bad = t.copy()
    bad[100:] += 0.1
    with pytest.raises(ValueError, match="gaps"):
        temporal_diagnostics(signals, bad)


def test_resampling_has_declared_error_and_never_manufactures_observations():
    f = field(np.linspace(0, 1, 9), np.linspace(0, 1, 9))
    out = resample_bilinear(f, np.linspace(0, 1, 17), np.linspace(0, 1, 17), error_bound=1e-14)
    assert "NOT_OBSERVATIONS" in out.provenance
    assert_allclose(derivatives(out).curl, 2, atol=3e-14)
    xx, yy = np.meshgrid(f.x, f.y)
    quadratic = replace(f, values=np.stack((xx**2, yy**2), axis=-1))
    out = resample_bilinear(
        quadratic, np.linspace(0, 1, 17), np.linspace(0, 1, 17), error_bound=1 / 256
    )
    x2, y2 = np.meshgrid(out.x, out.y)
    assert np.max(np.abs(out.values - np.stack((x2**2, y2**2), axis=-1))) <= 1 / 256
    mask = f.mask.copy()
    mask[4, 4] = False
    out = resample_bilinear(replace(f, mask=mask), out.x, out.y, error_bound=0)
    assert not out.mask[8, 8]
    assert np.all(np.isnan(out.values[~out.mask]))


@pytest.mark.parametrize(
    "change",
    [
        {"coordinate_unit": "pixel"},
        {"velocity_unit": "s"},
        {"geometry_kind": "CURVILINEAR"},
        {"component_basis": "POLAR"},
        {"orientation": "unknown"},
        {"boundary": "zero-pad"},
        {"x": np.array([0, 1, 1, 2, 3])},
        {"projection_id": ""},
    ],
)
def test_invalid_semantics_rejected(change):
    with pytest.raises(ValueError):
        replace(field(), **change)
