"""Execute mathematical counterexamples; development evidence, never field scoring."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from torusbrot.phase import v2


def main() -> None:
    output = Path(__file__).resolve().parent
    z = np.exp(1j*np.array([0, np.pi/2, np.pi, -np.pi/2]))
    theta = np.linspace(0, 2*np.pi, 16, endpoint=False)
    rng = np.random.default_rng(901)
    random_phase = np.exp(1j*rng.uniform(-np.pi, np.pi, (200, 16)))
    t = np.arange(4096)*.1
    x, y = np.cos(2*np.pi*t/1.6), np.sin(2*np.pi*t/1.6)
    permutation = np.random.default_rng(30).permutation(len(t))
    surrogate = np.asarray(v2.segment_phase_surrogate(y, segment_length=128, seed=991))
    noise = np.random.default_rng(338).normal(size=16384)
    for i in range(1, len(noise)):
        noise[i] += .7*noise[i-1]
    raw = output / "mathematical_inputs.npz"
    np.savez_compressed(raw, loop=z, theta=theta, random_phase=random_phase,
                        time=t, left=x, right=y, permutation=permutation,
                        surrogate=surrogate, ar1=noise)
    periods = []
    for period in [7.25, 13, 14, 15, 27, 28, 29]:
        time = np.arange(4096)*period/16
        spectrum = v2.temporal_cross_spectrum(np.cos(2*np.pi*time/period),
                                             np.cos(2*np.pi*time/period+.7), time,
                                             frequency_index=8)
        periods.append({"supplied_period": period, "estimated_period": spectrum["dominant_period"],
                        "phase": spectrum["cross_phase"]})
    before = v2.lagged_phase_association(x, y, t)
    after = v2.lagged_phase_association(x[permutation], y[permutation], t)
    results = {
        "status": "EXECUTED", "evidence_lane": "DEVELOPMENT_MATHEMATICAL_COUNTEREXAMPLES",
        "execution_command": "python studies/v0.4.0/reviewed/math/run_audit.py",
        "numpy_version": np.__version__,
        "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "kernel_sha256": hashlib.sha256(Path(v2.__file__).read_bytes()).hexdigest(),
        "pure_loop": v2.sampled_winding(z),
        "local_gauge": {"original": v2.sampled_winding(np.exp(1j*theta))["winding"],
                        "local_frame_changed": v2.sampled_winding(np.ones(16))["winding"]},
        "noise_branch_abstention": v2.sampled_winding(z, amplitude_noise_bound=.8),
        "missing_abstention": v2.sampled_winding(z, mask=[True, False, True, True]),
        "random_phase_null": {"independent_loop_count": 200,
                              "nonzero_count": sum(v2.sampled_winding(a)["winding"] != 0
                                                   for a in random_phase)},
        "fixed_o2_no_go": [{"theta": angle, "s": s, "fourteenth_parity":
                            v2.o2_power(v2.O2Element(angle, s), 14).s}
                           for angle in [.0, .7, np.pi/7] for s in [-1, 1]],
        "imposed_fourteenth_reflection": v2.o2_loop_monodromy(
            [v2.O2Element(0, 1)]*13+[v2.O2Element(0, -1)],
            transition_provenance="SUPPLIED_MODEL_TRANSITION_MAPS"),
        "unannotated_scalar_orientation": v2.o2_loop_monodromy(
            None, transition_provenance="SCALAR_ENDPOINTS"),
        "periods": periods,
        "temporal": {
            "ordered": before, "permuted": after,
            "reversed": v2.lagged_phase_association(x[::-1], y[::-1], t),
            "frame_median_original": float(np.median(x*x+y*y)),
            "frame_median_permuted": float(np.median((x*x+y*y)[permutation])),
            "coherence": v2.temporal_cross_spectrum(x, y, t, frequency_index=8,
                                                    window="boxcar"),
            "surrogate_coherence": v2.temporal_cross_spectrum(x, surrogate, t,
                                                              frequency_index=8, window="boxcar"),
            "block_uncertainty_sensitivity": [v2.lag_block_bootstrap(
                x, y, t, lag=1, block_length=b, replicates=100, seed=74,
                stationarity_assumed=True) for b in [16, 32, 64]],
            "iat_ar1": v2.integrated_autocorrelation(
                noise, np.arange(len(noise))*.05, max_lag=128,
                applicability="STATIONARY_SHORT_MEMORY_NONOSCILLATORY"),
            "iat_oscillatory": v2.integrated_autocorrelation(
                x, t, max_lag=128, applicability="STATIONARY_SHORT_MEMORY_NONOSCILLATORY"),
        },
        "claim_boundaries": {"TLD_DERIVED": False, "external_replication": False,
                             "preferred_14_28": False, "physical_nonorientability": False},
    }
    destination = output / "mathematical_results.json"
    destination.write_text(json.dumps(results, indent=2, sort_keys=True, allow_nan=False)+"\n",
                           encoding="utf-8")
    print(json.dumps({"status": "EXECUTED", "result_file": destination.name,
                      "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                      "random_null_nonzero": results["random_phase_null"],
                      "lag_before": before["value"], "lag_after": after["value"]}))


if __name__ == "__main__":
    main()
