from __future__ import annotations

import json

import numpy as np
import pytest
from torusbrot.phase.v2 import (
    O2Element,
    covariant_phase_links,
    integrated_autocorrelation,
    lag_block_bootstrap,
    lagged_phase_association,
    o2_action,
    o2_compose,
    o2_loop_monodromy,
    o2_power,
    sampled_winding,
    segment_phase_surrogate,
    temporal_cross_spectrum,
)


def test_four_sample_winding_counterexample_to_product_argument() -> None:
    z = np.exp(1j*np.array([0, np.pi/2, np.pi, -np.pi/2]))
    result = sampled_winding(z)
    assert result["winding"] == 1
    assert result["continuous_winding"] is None
    assert result["scalar_link_product_real"] == pytest.approx(1)
    assert result["scalar_link_product_imag"] == pytest.approx(0, abs=1e-14)
    # The obsolete proposed estimator returns zero on this exact +1 loop.
    old = np.angle(np.prod(np.roll(z, -1)*np.conjugate(z)))/(2*np.pi)
    assert old == pytest.approx(0, abs=1e-14)
    assert old != pytest.approx(result["winding"])


@pytest.mark.parametrize("sign", [-2, -1, 0, 1, 2])
def test_winding_orientation_global_phase_and_units(sign: int) -> None:
    z = np.exp(1j*sign*np.linspace(0, 2*np.pi, 33, endpoint=False))
    for scale in [1e-250, 1.0, 1e250]:
        result = sampled_winding(z*scale*np.exp(1j*2.7), amplitude_noise_bound=scale*.01,
                                 sampling_admissible=True)
        assert result["winding"] == sign
        assert result["continuous_winding"] == sign
    assert sampled_winding(z[::-1])["winding"] == -sign
    assert sampled_winding(np.conjugate(z))["winding"] == -sign


def test_missing_amplitude_and_near_branch_abstain_without_filling() -> None:
    z = np.array([1, 1j, -1, -1j], dtype=complex)
    assert sampled_winding(z, mask=[True, False, True, True])["winding"] is None
    z[1] = 0
    result = sampled_winding(z)
    assert result["phase_unidentifiable_sample_count"] == 1
    assert result["winding"] is None
    assert sampled_winding([1, -1, 1j])["reason"] == "BRANCH_UNCERTAINTY_OR_ALIASING"
    assert sampled_winding([1, 1j, -1, -1j], amplitude_noise_bound=.8)["winding"] is None
    assert sampled_winding([1, 1j, -1, -1j], amplitude_noise_bound=1)["winding"] is None


def test_sampling_alias_is_unidentifiable_from_endpoints() -> None:
    theta = np.linspace(0, 2*np.pi, 8, endpoint=False)
    assert np.allclose(np.exp(1j*theta), np.exp(1j*9*theta))
    assert sampled_winding(np.exp(1j*9*theta))["winding"] == 1
    assert sampled_winding(np.exp(1j*9*theta))["continuous_winding"] is None
    # At sufficient resolution the true +9 continuous lift is recoverable.
    fine = np.linspace(0, 2*np.pi, 64, endpoint=False)
    assert sampled_winding(np.exp(1j*9*fine), sampling_admissible=True)["winding"] == 9


def test_local_gauge_changes_scalar_winding_but_covariant_links_transform() -> None:
    theta = np.linspace(0, 2*np.pi, 12, endpoint=False)
    z = np.exp(1j*theta)
    alpha = -theta
    transformed = z*np.exp(1j*alpha)
    assert sampled_winding(z)["winding"] == 1
    assert sampled_winding(transformed)["winding"] == 0
    transport = np.exp(1j*np.full(len(z), .13))
    transformed_transport = transport*np.exp(1j*(alpha-np.roll(alpha, -1)))
    assert np.allclose(covariant_phase_links(z, transport),
                       covariant_phase_links(transformed, transformed_transport))


def test_random_phase_nonzero_winding_is_not_specific_structure() -> None:
    rng = np.random.default_rng(901)
    winding = [sampled_winding(np.exp(1j*rng.uniform(-np.pi, np.pi, 16)))["winding"]
               for _ in range(200)]
    assert sum(w != 0 for w in winding) > 50


def test_o2_composition_action_and_even_fixed_step_no_go() -> None:
    rng = np.random.default_rng(91)
    for _ in range(100):
        a, b = [O2Element(float(rng.uniform(-np.pi, np.pi)), int(rng.choice([-1, 1])))
                for _ in range(2)]
        z = complex(rng.normal(), rng.normal())
        assert o2_action(o2_compose(a, b), z) == pytest.approx(o2_action(a, o2_action(b, z)))
        assert o2_power(a, 14).s == 1
        assert o2_power(a, 28).s == 1
        reflection = O2Element(a.theta, -1)
        assert o2_power(reflection, 2).theta == pytest.approx(0, abs=1e-14)
    assert 14*np.pi/7 == pytest.approx(2*np.pi)
    assert 28*np.pi/7 == pytest.approx(4*np.pi)
    assert o2_action(O2Element(np.pi, 1), 1+2j) == pytest.approx(-1-2j)


def test_o2_requires_observed_transition_and_imposed_fourteenth_step_is_disclosed() -> None:
    assert o2_loop_monodromy(None, transition_provenance="SCALAR_ENDPOINTS")["parity"] is None
    steps = [O2Element(0, 1)]*13 + [O2Element(0, -1)]
    result = o2_loop_monodromy(steps, transition_provenance="SUPPLIED_MODEL_TRANSITION_MAPS")
    assert result["parity"] == -1
    assert result["reflection_count"] == 1
    assert result["physical_nonorientable_space_established"] is False
    # The same real scalar observation is unchanged by identity and conjugation.
    assert o2_action(O2Element(0, 1), 1) == o2_action(O2Element(0, -1), 1)


@pytest.mark.parametrize("period", [7.25, 13, 14, 15, 27, 28, 29])
def test_temporal_frequency_measures_physical_units_without_14_privilege(period: float) -> None:
    # Same physical period, sampling interval adjusted independently of labels.
    dt = period/16
    t = np.arange(4096)*dt
    x = np.cos(2*np.pi*t/period)
    y = np.cos(2*np.pi*t/period+.7)
    result = temporal_cross_spectrum(x, y, t, segment_length=128, frequency_index=8)
    assert result["dominant_period"] == pytest.approx(period)
    assert result["cross_phase"] == pytest.approx(.7, abs=1e-12)
    assert result["magnitude_squared_coherence"] == pytest.approx(1)
    milliseconds = temporal_cross_spectrum(x, y, t*1000, segment_length=128, frequency_index=8,
                                          time_unit="ms")
    assert milliseconds["dominant_period"] == pytest.approx(period*1000)
    assert milliseconds["coherence"] == pytest.approx(result["coherence"], nan_ok=True)


def test_cross_spectrum_direct_fourier_reference_and_scale_invariance() -> None:
    rng = np.random.default_rng(82)
    x = rng.normal(size=1024)
    y = .6*x + rng.normal(size=1024)
    t = np.arange(1024)*.125
    result = temporal_cross_spectrum(x, y, t, segment_length=64, window="boxcar",
                                     frequency_index=4)
    # Direct DFT at one registered bin independently of FFT implementation.
    kernel = np.exp(-2j*np.pi*4*np.arange(64)/64)
    xs, ys = x.reshape(-1, 64), y.reshape(-1, 64)
    a, b = (xs-xs.mean(axis=1)[:, None])@kernel, (ys-ys.mean(axis=1)[:, None])@kernel
    expected = abs(np.mean(np.conjugate(a)*b))**2/(np.mean(abs(a)**2)*np.mean(abs(b)**2))
    assert result["magnitude_squared_coherence"] == pytest.approx(expected)
    scaled = temporal_cross_spectrum(x*1e-200, y*1e200, t, segment_length=64, window="boxcar",
                                     frequency_index=4)
    assert scaled["magnitude_squared_coherence"] == pytest.approx(expected)
    assert scaled["cross_phase"] == pytest.approx(result["cross_phase"])
    json.dumps(scaled, allow_nan=False)


def test_zero_time_gaps_and_single_segment_do_not_claim_phase() -> None:
    t = np.arange(256, dtype=float)
    result = temporal_cross_spectrum(np.zeros(256), np.ones(256), t)
    assert result["status"] == "INDETERMINATE"
    assert result["cross_phase"] is None
    with pytest.raises(ValueError, match="two nonoverlapping"):
        temporal_cross_spectrum(t, t, t, segment_length=256)
    t[20:] += 1
    with pytest.raises(ValueError, match="irregular"):
        temporal_cross_spectrum(np.ones(256), np.ones(256), t)


def test_time_reversal_and_permutation_change_lag_information_not_frame_median() -> None:
    t = np.arange(2048)*.1
    x, y = np.cos(2*np.pi*t/1.6), np.sin(2*np.pi*t/1.6)
    original = lagged_phase_association(x, y, t)["value"]
    reversed_value = lagged_phase_association(x[::-1], y[::-1], t)["value"]
    assert reversed_value == pytest.approx(-original)
    permutation = np.random.default_rng(30).permutation(len(t))
    shuffled = lagged_phase_association(x[permutation], y[permutation], t)["value"]
    assert abs(shuffled) < .1*abs(original)
    assert np.median(x*x+y*y) == np.median((x*x+y*y)[permutation])


def test_segment_surrogate_preserves_spectrum_and_destroys_coherent_phase() -> None:
    t = np.arange(8192, dtype=float)
    x, y = np.cos(2*np.pi*t/16), np.cos(2*np.pi*t/16+.5)
    surrogate = np.asarray(segment_phase_surrogate(y, segment_length=128, seed=991))
    assert np.allclose(abs(np.fft.rfft(y.reshape(-1, 128), axis=1)),
                       abs(np.fft.rfft(surrogate.reshape(-1, 128), axis=1)), atol=1e-12)
    result = temporal_cross_spectrum(x, surrogate, t, window="boxcar", frequency_index=8)
    assert result["magnitude_squared_coherence"] < .15


def test_phase_uncertainty_requires_registered_bin_and_explicit_segment_assumption() -> None:
    rng = np.random.default_rng(710)
    t = np.arange(4096)
    x = rng.normal(size=len(t))
    y = .8*x + rng.normal(size=len(t))*.2
    with pytest.raises(ValueError, match="registered bin"):
        temporal_cross_spectrum(x, y, t, bootstrap_replicates=200)
    result = temporal_cross_spectrum(x, y, t, frequency_index=4, independent_segments=True,
                                     bootstrap_replicates=200)
    uncertainty = result["phase_uncertainty"]
    assert uncertainty["status"] == "CONDITIONAL_BOOTSTRAP"
    assert uncertainty["lower_offset_radians"] < uncertainty["upper_offset_radians"]
    assert result["independent_physical_system_count"] is None


def test_lag_block_uncertainty_is_conditional_and_changes_with_block_length() -> None:
    rng = np.random.default_rng(728)
    t = np.arange(1024)
    x, y = rng.normal(size=(2, len(t)))
    assert lag_block_bootstrap(x, y, t, lag=1, block_length=16, replicates=100, seed=0,
                              stationarity_assumed=False)["status"] == "NOT_APPLICABLE"
    intervals = [lag_block_bootstrap(x, y, t, lag=1, block_length=b, replicates=100, seed=0,
                                    stationarity_assumed=True) for b in [8, 16, 32]]
    assert all(a["lower"] < a["upper"] for a in intervals)
    assert len({a["upper"]-a["lower"] for a in intervals}) == 3
    assert all(a["population_generalization"] is False for a in intervals)


def test_iat_convention_and_oscillatory_limit() -> None:
    rng = np.random.default_rng(338)
    x = rng.normal(size=16384)
    for i in range(1, len(x)):
        x[i] += .7*x[i-1]
    t = np.arange(len(x))*.05
    assert integrated_autocorrelation(x, t, max_lag=128)["tau_factor"] is None
    result = integrated_autocorrelation(x, t, max_lag=128,
                                        applicability="STATIONARY_SHORT_MEMORY_NONOSCILLATORY")
    assert result["tau_factor"] == pytest.approx((1+.7)/(1-.7), rel=.3)
    assert result["independent_system_count"] is None
    oscillatory = integrated_autocorrelation(np.cos(t), t, max_lag=256,
                                             applicability="STATIONARY_SHORT_MEMORY_NONOSCILLATORY")
    assert oscillatory["tau_factor"] is None
    assert oscillatory["reason"] == "STRONG_NEGATIVE_LOBE_USE_OSCILLATORY_MODEL"


def test_finite_components_with_overflowing_modulus_abstain() -> None:
    result = sampled_winding(np.full(4, complex(1.7e308, 1.7e308)))
    assert result["winding"] is None
    assert result["valid_sample_count"] == 0
    assert result["phase_unidentifiable_sample_count"] == 4
