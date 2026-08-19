from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from torusbrot.tld.forensic import (
    POSTHOC,
    _exact_two_sided,
    _exact_upper,
    _matrix_scores,
    _synthetic_series,
    block_persistence,
    closure_error,
    contract_semantic_audit,
    operator_construct_audit,
    rolling_persistence,
)


def test_one_sided_and_two_sided_separation_are_distinct() -> None:
    assert _exact_upper(12, 12) == 1 / 4096
    assert _exact_two_sided(12, 0) == 2 / 4096


def test_opposite_sign_consensus_is_explicitly_posthoc() -> None:
    assert POSTHOC == "POST_HOC_DIAGNOSTIC_ONLY"
    assert _exact_upper(0, 12) == 1.0
    assert _exact_two_sided(0, 12) < 0.001


def test_block_phase_can_change_magnitude_without_changing_direction() -> None:
    rng = np.random.default_rng(4)
    values = np.sin(np.arange(1461) / 12) + rng.normal(0, 0.2, 1461)
    scores = [block_persistence(values, 9, phase) for phase in range(9)]
    assert all(math.isfinite(score) for score in scores)
    assert np.std(scores) > 0
    assert len({np.sign(score) for score in scores}) == 1


def test_matrix_score_matches_scalar_reference() -> None:
    rng = np.random.default_rng(8)
    matrix = rng.normal(size=(5, 1461))
    vectorized = _matrix_scores(matrix, 10, 3)
    scalar = np.asarray([block_persistence(row, 10, 3) for row in matrix])
    assert np.allclose(vectorized, scalar, atol=1e-12)


def test_rolling_and_nonoverlapping_windows_are_not_conflated() -> None:
    values = np.sin(np.arange(1461) / 21) + np.arange(1461) / 1461
    assert not math.isclose(
        block_persistence(values, 14), rolling_persistence(values, 14), abs_tol=1e-6
    )


def test_synthetic_ar_and_burst_fixtures_are_deterministic() -> None:
    left = _synthetic_series("ar1", 0.6, 365, np.random.default_rng(22))
    right = _synthetic_series("ar1", 0.6, 365, np.random.default_rng(22))
    burst = _synthetic_series("bursty_episodes", 0.6, 365, np.random.default_rng(22))
    assert np.array_equal(left, right)
    assert not np.array_equal(left, burst)


def test_closure_error_prefers_exact_period() -> None:
    values = np.tile(np.arange(9, dtype=float), 200)
    errors = {n_value: closure_error(values, n_value) for n_value in range(4, 15)}
    assert min(errors, key=errors.get) == 9


def test_operator_construct_audit_rejects_short_tld_i_ladder(tmp_path: Path) -> None:
    target = tmp_path / "targets.csv"
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["value", "sigma"])
        writer.writeheader()
        writer.writerows({"value": index / 10, "sigma": 0.1} for index in range(61))
    _, rows, adjudication = operator_construct_audit(target)
    assert not any(row["eligible_under_v021_minimum_30_blocks"] for row in rows)
    assert adjudication["classification"] == "NARROW_POSITIVE_PERSISTENCE_PROXY"


def test_contract_audit_finds_closure_gap_and_winner_ambiguity() -> None:
    root = Path(__file__).resolve().parents[1]
    matrix, declared, _ = contract_semantic_audit(root)
    assert declared[0]["field"] == "closure_local_p_less_equal"
    assert next(row for row in matrix if row["field"] == "winner_N_study")["status"] == "AMBIGUOUS"


def test_forensic_critic_rejects_all_thirty_mutations() -> None:
    root = Path(__file__).resolve().parents[1] / "studies" / "v0.2.2-negative-result-forensic"
    rows = [json.loads(line) for line in (root / "forensic_mutation_results.jsonl").read_text().splitlines()]
    assert len(rows) == 30
    assert all(row["rejected"] and row["actual_issue_code"] for row in rows)


def test_parent_dependence_warning_is_published() -> None:
    root = Path(__file__).resolve().parents[1] / "studies" / "v0.2.2-negative-result-forensic"
    audit = json.loads((root / "nested_parent_model_audit.json").read_text(encoding="utf-8"))
    assert audit["classification"] == "ONE_CITY_LEVEL_PARENT_WITH_SENSOR_REPLICATES"
    assert audit["v021_registered_parent_count_rewritten"] is False


def test_perturbation_redundancy_and_te_semantics_are_published() -> None:
    root = Path(__file__).resolve().parents[1] / "studies" / "v0.2.2-negative-result-forensic"
    scale = json.loads((root / "S_e_condition_independence_audit.json").read_text())
    semantics = json.loads((root / "T_e_semantic_adjudication.json").read_text())
    assert scale["calibration_scaling_median_canonical_rmse"] < 0.005
    assert semantics["classification"] == "T_E_IS_COARSE_GRAINING_SCALE_NOT_TIME"
