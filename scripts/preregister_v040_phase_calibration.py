#!/usr/bin/env python3
"""Freeze the bounded v0.4.0 phase/orientation synthetic calibration design."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "studies" / "v0.4.0" / "calibration"
PREREG = OUT / "preregistration"
SEED = 2026082104
REPLICATES = 96
PERIODS = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 24, 28, 32]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def seed(label: str) -> int:
    value = hashlib.sha256(f"{SEED}:{label}".encode()).digest()
    return int.from_bytes(value[:8], "big")


def main() -> None:
    candidates = [
        {
            "candidate_id": "PHASE_V3_A_SIGNED_VECTOR_BASELINE",
            "input": "registered real planar vector field",
            "target": "signed local vorticity/circulation and chirality domains",
            "parity": "reflection pseudoscalar only; no bundle monodromy",
            "status_before_calibration": "CANDIDATE",
        },
        {
            "candidate_id": "PHASE_V3_B_U1_LOCAL_HOLONOMY",
            "input": "registered nonzero complex grid",
            "target": "global-offset-invariant local phase winding",
            "parity": "not applicable",
            "status_before_calibration": "CANDIDATE_WITH_PURE_GAUGE_HOLONOMY_WARNING",
        },
        {
            "candidate_id": "PHASE_V3_C_O2_PARITY_MONODROMY",
            "input": "explicit registered O2 edge/chart transitions",
            "target": "loop reflection parity",
            "parity": "determinant product",
            "status_before_calibration": "CANDIDATE_REQUIRES_TRANSITION_DATA",
        },
        {
            "candidate_id": "PHASE_V3_D_TEMPORAL_CROSS_SPECTRUM",
            "input": "aligned regularly sampled component signals",
            "target": "dominant cross-phase and period",
            "parity": "not applicable",
            "status_before_calibration": "CANDIDATE",
        },
        {
            "candidate_id": "PHASE_V3_E_DISCRETE_EXTERIOR_CALCULUS_OPTIONAL",
            "input": "oriented mesh plus discrete connection",
            "target": "connection curvature/holonomy",
            "parity": "requires separate O2 transition data",
            "status_before_calibration": "NOT_IMPLEMENTED_OPTIONAL",
        },
        {
            "candidate_id": "NO_PHASE_METHOD_ESTABLISHED",
            "input": None,
            "target": "conservative stop",
            "parity": None,
            "status_before_calibration": "AVAILABLE_STOP",
        },
    ]
    write_json(PREREG / "candidate_family.json", {"bounded": True, "candidates": candidates})

    names = [
        "constant_complex_field",
        "iid_random_phase_fixed_amplitude",
        "smooth_phase_ramp",
        "single_u1_vortex",
        "vortex_antivortex_pair",
        "same_sign_vortex_pair",
        "counter_rotating_vector_vortices",
        "opposite_local_chirality_zero_global_mean",
        "standing_wave",
        "traveling_wave",
        "circularly_polarized_wave",
        "linearly_polarized_wave",
        "elliptically_polarized_wave",
        "phase_randomized_spectrum_preserving_field",
        "amplitude_randomized_phase_preserving_field",
        "mirrored_vector_field",
        "coordinate_rotated_equivalent_field",
        "time_reversed_wave",
        "director_field_pi_periodicity",
        "ordinary_vector_field_2pi_periodicity",
        "spinor_like_4pi_return",
        "mobius_strip_synthetic_section",
        "klein_bottle_chart_transition_section",
        "torus_orientable_double_cover_control",
        "orientation_preserving_u1_holonomy_without_parity",
        "o2_monodromy_one_reflection",
        "o2_monodromy_two_reflections",
        "boundary_truncated_vortex",
        "masked_singularity",
        "irregularly_sampled_phase_field",
        "spatiotemporal_vortex_shedding",
        "bursty_chirality_reversal",
        "one_channel_amplitude_decoy",
        "one_channel_phase_decoy",
        "nested_replicate_family",
        "multi_campaign_family",
        "instrument_limited_phase_family",
        "aliased_phase_family",
        "noise_only_signed_curl_family",
        "domain_baseline_explained_family",
    ]
    vector = {7, 8, 16, 17, 31, 32, 35, 36, 39, 40}
    complex_field = {1, 2, 3, 4, 5, 6, 14, 15, 28, 29, 30, 33, 34, 37, 38}
    temporal = {9, 10, 11, 12, 13, 18, 19, 20, 21, 31, 32, 37, 38}
    o2 = {22, 23, 24, 25, 26, 27}
    nulls = {1, 2, 14, 33, 39, 40}
    adversarial = {5, 8, 28, 29, 30, 35, 36, 37, 38, 40}
    registry = []
    truth = []
    for number, name in enumerate(names, 1):
        applicable = []
        if number in vector:
            applicable.append("SIGNED_VECTOR")
        if number in complex_field:
            applicable.append("U1_WINDING")
        if number in temporal:
            applicable.append("TEMPORAL_CROSS_SPECTRUM")
        if number in o2:
            applicable.append("O2_MONODROMY")
        registry.append(
            {
                "family_id": f"SYN_{number:02d}",
                "name": name,
                "replicates": REPLICATES,
                "seed": seed(f"SYN_{number:02d}"),
                "applicable_candidates": applicable,
                "lane": "D_NULL_ADVERSARIAL"
                if number in nulls | adversarial
                else "A_CHANNEL_IDENTIFICATION",
                "independent_parent_definition": "one generated realization",
                "nested_samples_are_not_parents": True,
            }
        )
        truth.append(
            {
                "family_id": f"SYN_{number:02d}",
                "truth_scope": "CHANNEL_SPECIFIC_NOT_UNIVERSAL_TLD_LABEL",
                "null_family": number in nulls,
                "adversarial_or_abstention_family": number in adversarial,
                "applicable_candidates": applicable,
            }
        )
    write_jsonl(OUT / "synthetic_registry.jsonl", registry)
    write_jsonl(OUT / "ground_truth_registry.jsonl", truth)

    cycle_rows = [
        {
            "period": period,
            "replicates": REPLICATES,
            "seed": seed(f"PERIOD_{period}"),
            "search_family": PERIODS,
        }
        for period in PERIODS
    ]
    write_json(
        PREREG / "blind_period_design.json",
        {
            "lanes": {
                "A": "blind period/monodromy identification",
                "B": "targeted 14/28; authority blocked absent independent theory source",
                "C": "neighboring-period specificity",
                "D": "null/adversarial controls",
            },
            "period_family": PERIODS,
            "privileged_scoring_terms": [],
            "cycles": cycle_rows,
        },
    )
    loss = {
        "schema_version": "tfs-v040-phase-selection-loss-v1",
        "frozen_before_outcomes": True,
        "confidence_method": "Wilson 95 percent interval",
        "familywise_type_I_upper_95_max": 0.05,
        "false_sign_upper_95_max": 0.05,
        "false_parity_upper_95_max": 0.05,
        "declared_power_lower_95_min": 0.80,
        "period_accuracy_lower_95_min": 0.80,
        "abstention_policy": "instrument-limited, inapplicable representation, or incomplete transition data must abstain",
        "hard_gates": [
            "mathematical consistency",
            "no 14/28 privilege",
            "valid matched null",
            "declared gauge invariance",
            "reflection/rotation equivariance",
            "time-reversal behavior",
            "mask/boundary and sampling policy",
            "parent hierarchy",
            "independent recomputation",
            "mutation rejection",
            "claim quarantine",
            "T_e/S_e/winner_N firewalls",
        ],
        "tie_break": "prefer fewer assumptions and narrower claim; otherwise abstain",
        "selection_options": [
            "PHASE_ORIENTATION_V1_CALIBRATED_SELECTIVE_CLASSIFIER",
            "PHASE_ORIENTATION_V1_HIERARCHICAL_MODEL",
            "PHASE_ORIENTATION_V1_CONFORMAL_DECISION_SET",
            "PHASE_ORIENTATION_V1_EVIDENCE_VECTOR_ONLY",
            "NO_PHASE_ORIENTATION_METHOD_ESTABLISHED",
        ],
    }
    write_json(PREREG / "method_selection_loss.json", loss)
    write_json(
        PREREG / "execution_contract.json",
        {
            "root_seed": SEED,
            "replicates_per_family": REPLICATES,
            "array_grid": [65, 65],
            "temporal_samples": 1024,
            "period_family": PERIODS,
            "scientific_parameters_may_change_after_execution": False,
            "outcome_exposed_v030_or_TLD_data_allowed": False,
            "raw_realization_storage": "compressed numeric arrays plus seed and semantic metadata",
        },
    )
    files = [path for path in PREREG.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt"]
    (PREREG / "SHA256SUMS.txt").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(PREREG).as_posix()}\n"
            for path in sorted(files)
        ),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
