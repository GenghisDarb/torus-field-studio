from __future__ import annotations

import numpy as np
import pytest
from torusbrot.phase.v1 import (
    O2Element,
    blind_period_scan,
    o2_compose,
    o2_inverse,
    o2_loop_monodromy,
    temporal_cross_spectrum,
    u1_plaquette_metrics,
    vector_chirality_metrics,
)


def test_signed_vector_detects_local_cancellation() -> None:
    y, x = np.mgrid[-1:1:41j, -1:1:41j]
    left = np.stack((-y, x), axis=-1)
    right = np.stack((y, -x), axis=-1)
    field = np.where((x < 0)[..., None], left, right)
    result = vector_chirality_metrics(field)
    assert result["positive_fraction"] > 0.4
    assert result["negative_fraction"] > 0.4
    assert result["chirality_cancellation_ratio"] < 0.2


def test_u1_winding_is_global_offset_invariant_and_holonomy_telescopes() -> None:
    y, x = np.mgrid[-1:1:65j, -1:1:65j]
    field = (x + 1j * y).astype(np.complex128)
    mask = np.abs(field) > 0.08
    first = u1_plaquette_metrics(field, mask)
    second = u1_plaquette_metrics(field * np.exp(1j * 1.234), mask)
    assert first["signed_winding_sum"] == second["signed_winding_sum"]
    assert first["scalar_derived_link_product_max_error_from_unity"] < 1e-12
    assert first["arbitrary_local_gauge_invariant"] == 0


def test_o2_group_inverse_and_reflection_parity() -> None:
    element = O2Element(0.7, -1)
    identity = o2_compose(element, o2_inverse(element))
    assert identity.theta == pytest.approx(0.0)
    assert identity.s == 1
    one = o2_loop_monodromy([O2Element(0.2, 1), O2Element(0.4, -1)])
    two = o2_loop_monodromy([O2Element(0.2, -1), O2Element(0.4, -1)])
    assert one["orientation_class"] == "REVERSING"
    assert two["orientation_class"] == "PRESERVING"


def test_temporal_phase_and_blind_period() -> None:
    t = np.arange(1024, dtype=np.float64)
    left = np.cos(2.0 * np.pi * t / 16.0)
    right = np.cos(2.0 * np.pi * t / 16.0 + np.pi / 2.0)
    spectrum = temporal_cross_spectrum(left, right, dt=1.0, segment_length=256)
    assert spectrum["dominant_period"] == pytest.approx(16.0)
    assert spectrum["cross_phase"] == pytest.approx(np.pi / 2.0, abs=5e-6)
    scan = blind_period_scan(left, [14, 15, 16, 18, 20])
    assert scan["winner_period"] == 16
    assert scan["period_family"] == [14, 15, 16, 18, 20]
