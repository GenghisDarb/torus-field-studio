#!/usr/bin/env python3
"""Generate temporal metrology and the conservative v0.4.0 no-method freeze."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies" / "v0.4.0"
CALIBRATION = STUDY / "calibration"
TEMPORAL = STUDY / "temporal"
FREEZE = STUDY / "freeze"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def integral_autocorrelation_time(values: np.ndarray) -> float:
    centered = np.asarray(values, dtype=np.float64) - float(np.mean(values))
    n = len(centered)
    transform = np.fft.rfft(centered, n=2 * n)
    autocovariance = np.fft.irfft(transform * np.conjugate(transform))[:n]
    if autocovariance[0] <= np.finfo(float).eps:
        return 1.0
    correlation = autocovariance / autocovariance[0]
    positive = correlation[1:]
    stop = np.flatnonzero(positive <= 0.0)
    limit = int(stop[0]) if len(stop) else min(len(positive), n // 4)
    return max(1.0, float(1.0 + 2.0 * np.sum(positive[:limit])))


def dominant_period(values: np.ndarray, dt: float = 1.0) -> float:
    centered = values - float(np.mean(values))
    power = np.abs(np.fft.rfft(centered)) ** 2
    power[0] = 0.0
    frequencies = np.fft.rfftfreq(len(values), dt)
    index = int(np.argmax(power))
    return float(1.0 / frequencies[index]) if frequencies[index] > 0.0 else math.inf


def stationarity_score(values: np.ndarray) -> float:
    midpoint = len(values) // 2
    scale = max(float(np.std(values)), np.finfo(float).eps)
    return float(abs(np.mean(values[:midpoint]) - np.mean(values[midpoint:])) / scale)


def change_point_score(values: np.ndarray) -> float:
    centered = values - float(np.mean(values))
    scale = max(float(np.std(values)) * math.sqrt(len(values)), np.finfo(float).eps)
    return float(np.max(np.abs(np.cumsum(centered))) / scale)


def temporal_rows() -> list[dict[str, Any]]:
    rows = []
    for archive in sorted((CALIBRATION / "raw_realizations").glob("SYN_*.npz")):
        with np.load(archive, allow_pickle=False) as data:
            if "temporal_left" not in data:
                continue
            left = np.asarray(data["temporal_left"], dtype=np.float64)
            right = np.asarray(data["temporal_right"], dtype=np.float64)
        iats = np.asarray([integral_autocorrelation_time(row) for row in left])
        component_right_iats = np.asarray([integral_autocorrelation_time(row) for row in right])
        periods = np.asarray([dominant_period(row) for row in left])
        vorticity_proxy_iats = np.asarray(
            [integral_autocorrelation_time(np.gradient(row)) for row in left]
        )
        stationarity = np.asarray([stationarity_score(row) for row in left])
        changes = np.asarray([change_point_score(row) for row in left])
        phase_lag = []
        for x, y in zip(left, right, strict=True):
            cross = np.fft.rfft(y - np.mean(y)) * np.conjugate(np.fft.rfft(x - np.mean(x)))
            cross[0] = 0.0
            phase_lag.append(float(np.angle(cross[int(np.argmax(np.abs(cross)))])))
        block = max(1, int(round(float(np.median(iats)))))
        block_means = (
            left[:, : (left.shape[1] // block) * block].reshape(len(left), -1, block).mean(axis=2)
        )
        iid_se = float(np.std(left) / math.sqrt(left.size))
        block_se = float(np.std(block_means) / math.sqrt(block_means.size))
        rows.append(
            {
                "family_id": archive.stem,
                "sampling_interval": 1.0,
                "acquisition_duration": float(left.shape[1] - 1),
                "replicate_count": len(left),
                "median_integral_autocorrelation_time": float(np.median(iats)),
                "median_component_right_autocorrelation_time": float(
                    np.median(component_right_iats)
                ),
                "median_vorticity_proxy_autocorrelation_time": float(
                    np.median(vorticity_proxy_iats)
                ),
                "median_dominant_spectral_period": float(np.median(periods)),
                "convective_time": "NOT_APPLICABLE_SYNTHETIC",
                "eddy_turnover_proxy": "NOT_APPLICABLE_SYNTHETIC",
                "pair_temporal_overlap": "NOT_APPLICABLE_INDEPENDENT_SYNTHETIC_PARENTS",
                "effective_temporal_degrees_of_freedom": float(np.median(left.shape[1] / iats)),
                "block_length": block,
                "block_to_iid_se_ratio": block_se / max(iid_se, np.finfo(float).eps),
                "subsampled_dominant_period_dt2": float(
                    np.median([dominant_period(row[::2], dt=2.0) for row in left])
                ),
                "circular_phase_lag_resultant": float(
                    abs(np.mean(np.exp(1j * np.asarray(phase_lag))))
                ),
                "median_stationarity_half_mean_score": float(np.median(stationarity)),
                "median_change_point_cusum_score": float(np.median(changes)),
            }
        )
    return rows


def main() -> None:
    TEMPORAL.mkdir(parents=True, exist_ok=True)
    FREEZE.mkdir(parents=True, exist_ok=True)
    contract = {
        "schema_version": "TemporalDependenceAuditV1",
        "hierarchy": [
            "nested snapshots",
            "within-acquisition temporal support",
            "independent acquisitions",
            "paired blocks",
            "campaigns",
            "systems",
        ],
        "permitted_uses": [
            "estimator uncertainty",
            "block length",
            "null construction",
            "descriptive dynamics",
        ],
        "forbidden_use": "decorrelated frames may not increase system, campaign, acquisition, or population-parent count",
        "three_turnover_universal_rule": False,
        "estimators_frozen_before_field_diagnostic": True,
    }
    write_json(TEMPORAL / "temporal_dependence_contract.json", contract)
    write_json(
        TEMPORAL / "decorrelation_estimators.json",
        {
            "integral_autocorrelation_time": "1 + 2*sum positive-lag sample ACF until first nonpositive lag",
            "effective_temporal_degrees_of_freedom": "sample_count / integral_autocorrelation_time; descriptive uncertainty only",
            "dominant_spectral_period": "maximum non-DC periodogram bin",
            "component_autocorrelation": "calculated independently per registered component",
            "vorticity_autocorrelation": "same estimator on signed vorticity or declared temporal proxy",
            "block_bootstrap_length": "rounded median integral autocorrelation time, minimum one sample",
            "stationarity": "absolute first-half versus second-half mean difference divided by full standard deviation",
            "change_point": "maximum standardized absolute cumulative centered sum",
            "convective_time": "D/U only when D and U are source-registered physical quantities",
            "vortex_shedding_period": "reported only when an identifiable spectral peak and source interpretation agree",
        },
    )
    rows = temporal_rows()
    write_csv(
        TEMPORAL / "synthetic_validation.csv",
        rows,
        list(rows[0]),
    )
    write_json(
        TEMPORAL / "v030_pinball_diagnostic.json",
        {
            "status": "NOT_EXECUTED_AFTER_NO_METHOD_GATE",
            "reason": "the prompt permits outcome-exposed diagnostic replay only after an established method freeze; no method was established",
            "source_role": "OUTCOME_EXPOSED_V030_DIAGNOSTIC_ONLY",
            "sampling_interval_seconds": 1.0 / 120.0,
            "snapshots_per_acquisition": 1794,
            "acquisition_duration_seconds": 1793.0 / 120.0,
            "cylinder_diameter_m": 0.03,
            "stream_velocity_m_per_s": 0.31,
            "convective_time_D_over_U_seconds": 0.03 / 0.31,
            "integral_autocorrelation_time": "NOT_CALCULATED_METHOD_GATE_CLOSED",
            "vortex_shedding_period": "NOT_CALCULATED_METHOD_GATE_CLOSED",
            "pair_temporal_overlap": "UNKNOWN_FROM_FROZEN_DEPOSIT",
            "acquisition_gap_distribution": "UNKNOWN_FROM_FROZEN_DEPOSIT",
            "parent_hierarchy": {
                "systems": 1,
                "campaign_independence": "UNKNOWN",
                "paired_acquisition_blocks": 28,
                "acquisitions": 56,
                "snapshots": "NESTED_NEVER_POPULATION_PARENTS",
                "cells": "NESTED_NEVER_POPULATION_PARENTS",
            },
        },
    )
    write_json(
        TEMPORAL / "wind_pilot_diagnostic.json",
        {
            "status": "NOT_EXECUTED_AFTER_NO_METHOD_GATE",
            "source_role": "OUTCOME_EXPOSED_NONCONFIRMATORY_ENGINEERING_PILOT",
            "reason": "no established phase/orientation method exists",
            "frozen_hierarchy": {
                "facility_campaigns": 1,
                "condition_acquisitions": 4,
                "same_yaw_repeated_acquisitions": 0,
                "coupled_lidar_modalities": 2,
                "nested_synchronized_samples": True,
                "condition_acquisitions_exchangeable": False,
            },
            "temporal_phase_applicability": "BLOCKED_NO_REGISTERED_TIME_AXIS_IN_FROZEN_PILOT_PROJECTIONS",
            "population_aggregation": False,
        },
    )
    write_json(
        TEMPORAL / "forbidden_independence_promotions.json",
        {
            "forbidden": [
                "frames -> independent acquisitions",
                "decorrelated frames -> independent population parents",
                "cells -> independent systems",
                "modalities -> independent parents",
                "paired blocks -> independent systems",
                "one campaign -> population generalization",
            ]
        },
    )

    calibration = json.loads((CALIBRATION / "calibration_summary.json").read_text(encoding="utf-8"))
    freeze_receipt_path = FREEZE / "method_freeze_commit_receipt.json"
    freeze_commit = (
        json.loads(freeze_receipt_path.read_text(encoding="utf-8"))["commit"]
        if freeze_receipt_path.exists()
        else "RECORDED_BY_FOLLOWUP_RECEIPT_AFTER_ENCLOSING_COMMIT"
    )
    candidates = json.loads(
        (CALIBRATION / "preregistration" / "candidate_family.json").read_text(encoding="utf-8")
    )
    rejection = {
        "PHASE_V3_A_SIGNED_VECTOR_BASELINE": "REJECTED_AS_COMPLETE_METHOD_NO_FROZEN_MATCHED_NULL_DECISION_OR_TYPE_I_CALIBRATION",
        "PHASE_V3_B_U1_LOCAL_HOLONOMY": "REJECTED_PURE_VERTEX_LINK_HOLONOMY_TRIVIAL_AND_LOCAL_GAUGE_GATE_FAILS",
        "PHASE_V3_C_O2_PARITY_MONODROMY": "REJECTED_AS_COMPLETE_METHOD_REQUIRES_EXPLICIT_TRANSITION_DATA_AND_CANNOT_INFER_IT",
        "PHASE_V3_D_TEMPORAL_CROSS_SPECTRUM": "REJECTED_AS_COMPLETE_METHOD_NULL_STATIONARITY_IRREGULAR_SAMPLING_AND_INSTRUMENT_GATES_FAIL",
        "PHASE_V3_E_DISCRETE_EXTERIOR_CALCULUS_OPTIONAL": "REJECTED_UNIMPLEMENTED_OPTIONAL_CANDIDATE",
        "NO_PHASE_METHOD_ESTABLISHED": "SELECTED_CONSERVATIVE_STOP",
    }
    write_json(
        FREEZE / "method_candidate_registry.json",
        {
            "candidates": [
                {**row, "post_calibration_status": rejection[row["candidate_id"]]}
                for row in candidates["candidates"]
            ],
            "bounded_family": True,
        },
    )
    selection_loss = json.loads(
        (CALIBRATION / "preregistration" / "method_selection_loss.json").read_text(encoding="utf-8")
    )
    write_json(
        FREEZE / "method_selection_loss.json",
        {
            **selection_loss,
            "source_sha256": digest(CALIBRATION / "preregistration" / "method_selection_loss.json"),
        },
    )
    gates = [
        ("source_and_lineage_custody", "PASS_WITH_RECORDED_HISTORICAL_EXCEPTIONS"),
        ("TLD_lineage_reconciliation", "FAIL_FOR_TLD_DERIVATION"),
        ("mathematical_consistency", "FAIL_FOR_COMPLETE_BOUNDED_COMBINATION"),
        ("type_I_control_with_uncertainty", "FAIL_NO_FROZEN_SELECTIVE_RULE"),
        ("adequate_power", "FAIL_OPERATOR_RECOGNITION_IS_NOT_CLASSIFIER_POWER"),
        ("low_false_sign_rate", "FAIL_NOT_NULL_CALIBRATED"),
        ("low_false_parity_rate", "PASS_EXPLICIT_O2_SYNTHETIC_ONLY"),
        ("period_specificity", "PASS_SYNTHETIC_BLIND_LANE_ONLY"),
        ("no_14_28_privilege", "PASS"),
        ("valid_nulls", "FAIL_INCOMPLETE_BY_CANDIDATE"),
        ("gauge_invariance", "FAIL_U1_LOCAL_GAUGE"),
        ("representation_equivariance", "PASS_FOR_TESTED_SUBSET_ONLY"),
        ("temporal_dependence_policy", "PASS_POLICY_SYNTHETIC_VALIDATION"),
        ("parent_hierarchy", "PASS"),
        ("instrument_sensitivity", "FAIL_NO_POWER_OVER_DECLARED_INSTRUMENT_RANGE"),
        ("mask_boundary_robustness", "FAIL_ABSTENTION_ONLY_NO_POWER"),
        ("independent_raw_recomputation", "FAIL_NOT_COMPLETED_FOR_COMBINED_METHOD"),
        ("mutation_rejection", "FAIL_NOT_COMPLETED_FOR_COMBINED_METHOD"),
        ("claim_source_quarantine", "PASS"),
        ("semantic_firewalls", "PASS"),
    ]
    write_json(
        FREEZE / "method_acceptance_gate.json",
        {
            "all_gates_pass": False,
            "gates": [{"gate": gate, "status": status} for gate, status in gates],
            "selected_method": "NO_PHASE_ORIENTATION_METHOD_ESTABLISHED",
            "heldout_legal": False,
        },
    )
    write_json(
        FREEZE / "frozen_phase_orientation_method.json",
        {
            "status": "NO_PHASE_ORIENTATION_METHOD_ESTABLISHED",
            "selected_method": "NO_PHASE_ORIENTATION_METHOD_ESTABLISHED",
            "scientific_outcome": "V040_PHASE_ORIENTATION_METHOD_NOT_ESTABLISHED",
            "operator_implementation_sha256": digest(
                ROOT / "python" / "torusbrot" / "phase" / "v1.py"
            ),
            "calibration_summary_sha256": digest(CALIBRATION / "calibration_summary.json"),
            "calibration_manifest_sha256": digest(CALIBRATION / "SHA256SUMS.txt"),
            "method_freeze_commit": freeze_commit,
            "untouched_heldout_phase_sensitive_outcomes_accessed": False,
            "real_candidate_selected": False,
            "TLD_DERIVED": "BLOCKED",
            "EXTERNALLY_VALIDATED": False,
        },
    )
    write_json(
        FREEZE / "frozen_nulls.json",
        {
            "status": "NO_COMPLETE_NULL_SUITE_FROZEN",
            "diagnostic_nulls": [
                "amplitude/spectrum-preserving phase randomization",
                "signed-curl noise/domain baseline",
                "explicit O2 transition controls",
            ],
            "claim_bearing_selective_null": None,
        },
    )
    write_json(
        FREEZE / "frozen_projections.json",
        {
            "diagnostic_only": [
                "registered planar vector -> local signed curl",
                "registered complex grid -> global-offset-invariant wrapped winding",
                "explicit O2 edge transitions -> determinant parity",
                "regular paired time signals -> cross spectrum",
            ],
            "claim_bearing_combination": None,
        },
    )
    write_json(
        FREEZE / "frozen_temporal_policy.json",
        {**contract, "synthetic_family_count": len(rows)},
    )
    write_json(
        FREEZE / "frozen_parent_policy.json",
        {
            "highest_available_independent_unit_controls_inference": True,
            "frames_cells_modalities_are_nested_by_default": True,
            "decorrelation_never_promotes_population_parent_count": True,
            "single_system_claim_ceiling": "SYSTEM_SPECIFIC_DESCRIPTIVE",
        },
    )
    period_design = json.loads(
        (CALIBRATION / "preregistration" / "blind_period_design.json").read_text(encoding="utf-8")
    )
    write_json(
        FREEZE / "frozen_period_search.json",
        {
            "period_family": period_design["period_family"],
            "privileged_scoring_terms": [],
            "blind_synthetic_accuracy": calibration["period_scan"]["accuracy"],
            "targeted_14_28_authority": "BLOCKED_NO_INDEPENDENT_THEORY_SOURCE",
            "heldout_period_search_authority": "NONE_NO_METHOD",
        },
    )
    write_json(
        FREEZE / "frozen_claim_boundary.json",
        {
            "maximum_claim": "BOUNDED_SYNTHETIC_OPERATOR_DIAGNOSTICS_WITH_NO_ESTABLISHED_PHASE_ORIENTATION_METHOD",
            "forbidden": [
                "real candidate selection",
                "heldout execution",
                "U1 parity",
                "Klein-bottle detection",
                "universal 14/28 law",
                "spinor claim from ordinary fields",
                "TLD_DERIVED",
                "external validation",
                "TORUS confirmation",
            ],
            "T_e": "NOT_APPLICABLE",
            "S_e": "NOT_APPLICABLE",
            "winner_N": "NOT_APPLICABLE",
            "TLD_DERIVED": "BLOCKED",
            "EXTERNALLY_VALIDATED": False,
        },
    )
    write_json(
        FREEZE / "exact_blockers.json",
        {
            "blockers": calibration["hard_gate_failures"],
            "absence_of_untouched_heldout_outcomes": True,
            "next_phase_prohibited": "PHASE_K_AND_L_THROUGH_Q",
        },
    )
    for directory in (TEMPORAL, FREEZE):
        files = [
            path
            for path in directory.rglob("*")
            if path.is_file() and path.name != "SHA256SUMS.txt"
        ]
        (directory / "SHA256SUMS.txt").write_text(
            "".join(
                f"{digest(path)}  {path.relative_to(directory).as_posix()}\n"
                for path in sorted(files)
            ),
            encoding="utf-8",
            newline="\n",
        )
    print(
        json.dumps(
            {
                "temporal_synthetic_families": len(rows),
                "selected_method": "NO_PHASE_ORIENTATION_METHOD_ESTABLISHED",
                "heldout_legal": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
