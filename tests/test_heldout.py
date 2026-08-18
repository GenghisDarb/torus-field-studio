from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
from tld_fixtures import read_members, resign_bundle
from torusbrot.audit import audit_bundle
from torusbrot.domains.beijing_pm25 import (
    EXPECTED_DAYS,
    EXPECTED_HOURS,
    ParentSource,
    _null_permutations,
    canonicalize,
    sha256_file,
    write_json,
)
from torusbrot.tld.heldout.study import (
    _coarse_scores,
    _exact_sign_p,
    _holm,
    authorize_scored_run,
)
from torusbrot.tld.heldout.verification import _mutations, _protocol_issues


def test_daily_canonicalization_preserves_missing_values() -> None:
    values = np.arange(EXPECTED_HOURS, dtype=np.float64) % 100
    values[:7] = np.nan
    timestamps = tuple(
        datetime(2013, 3, 1) + timedelta(hours=index) for index in range(EXPECTED_HOURS)
    )
    canonical, audit = canonicalize(values, timestamps)
    assert len(canonical) == EXPECTED_DAYS
    assert math.isnan(canonical[0])
    assert audit["eligible_daily_count"] == EXPECTED_DAYS - 1
    assert np.count_nonzero(np.isfinite(canonical)) == EXPECTED_DAYS - 1


def test_parent_local_permutations_are_deterministic_and_stratified() -> None:
    timestamps = tuple(
        datetime(2013, 3, 1) + timedelta(hours=index) for index in range(EXPECTED_HOURS)
    )
    parent = ParentSource(
        station="Aotizhongxin",
        member="fixture.csv",
        member_sha256="0" * 64,
        member_bytes=1,
        raw_values=np.ones(EXPECTED_HOURS),
        raw_text=tuple("1" for _ in range(EXPECTED_HOURS)),
        timestamps_local=timestamps,
        source_order_valid=True,
        duplicate_count=0,
        invalid_value_count=0,
    )
    left = _null_permutations(parent, 0)
    right = _null_permutations(parent, 0)
    assert np.array_equal(left, right)
    assert left.shape == (127, EXPECTED_DAYS)
    march_2013 = np.arange(31)
    assert set(left[0, march_2013]) == set(march_2013)
    assert not np.array_equal(left[0], np.arange(EXPECTED_DAYS))


def test_separation_math_keeps_endpoints_distinct() -> None:
    t = np.linspace(0.0, 12.0, EXPECTED_DAYS)
    matrix = np.vstack((np.sin(t), np.random.default_rng(7).normal(size=EXPECTED_DAYS)))
    scores = _coarse_scores(matrix, 6)
    assert np.isfinite(scores).all()
    assert _exact_sign_p(12, 12) == pytest.approx(1 / 4096)
    adjusted = _holm({6: 1 / 4096, 7: 0.2, 8: 0.5})
    assert adjusted[6] == pytest.approx(3 / 4096)
    assert set(adjusted) == {6, 7, 8}


def test_all_registered_mutations_fail_closed() -> None:
    base = {
        "null_parent_matches": True,
        "null_in_observed_metrics": False,
        "ladder_order_frozen": True,
        "primary_n_min": 6,
        "winner_relabelled_te": False,
        "te_consistent": True,
        "se_source": "persistence",
        "failure_ledger_complete": True,
        "all_parents_preserved": True,
        "seed_frozen": True,
        "perturbations_registered": True,
        "all_files_manifested": True,
        "source_sha256": "d1b9261c54132f04c374f762f1e5e512af19f95c95fd6bfa1e8ac7e927e3b0b8",
        "global_null_pool": False,
        "ordering_selected_after_outcomes": False,
        "window_selected_after_outcomes": False,
        "claim_tld_derived": False,
        "tld_gates_complete": True,
        "externally_validated": False,
        "claim_14_unique": False,
        "specificity_gate": True,
        "interpolation_as_observation": False,
        "torus_tot_conflated": False,
        "analytic_evidence": False,
        "negative_parent_removed": False,
        "thresholds_frozen": True,
        "dataset_id": "uci-beijing-multisite-air-quality-pm25",
    }
    assert _protocol_issues(base) == []
    registry, results = _mutations(base)
    assert len(registry) == len(results) == 25
    assert all(result["rejected"] for result in results)


def test_authorization_is_one_time_and_hash_bound(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    study = repository / "studies" / "heldout-v0.2.1"
    materialized = tmp_path / "materialized"
    materialized.mkdir()
    write_json(
        materialized / "materialization_receipt.json",
        {"ready_for_scored_run_authorization": True},
    )
    write_json(
        materialized / "contamination_prevention_audit.json",
        {"observed_metrics_computed": False},
    )
    lines = []
    for name in ("materialization_receipt.json", "contamination_prevention_audit.json"):
        lines.append(f"{sha256_file(materialized / name)}  {name}\n")
    (materialized / "SHA256SUMS_INPUTS.txt").write_text(
        "".join(lines), encoding="utf-8", newline="\n"
    )
    output = tmp_path / "scored"
    receipt = authorize_scored_run(
        materialized,
        study,
        output,
        preregistration_commit="f15422bc64b1b101150240e612621683b15b3606",
        implementation_commit="fixture",
    )
    assert receipt["authorization_status"] == "AUTHORIZED_FOR_EXACTLY_ONE_SCORED_EXECUTION"
    with pytest.raises(ValueError, match="already authorized"):
        authorize_scored_run(
            materialized,
            study,
            output,
            preregistration_commit="f15422bc64b1b101150240e612621683b15b3606",
            implementation_commit="fixture",
        )


def test_independent_verifier_does_not_import_production_endpoints() -> None:
    repository = Path(__file__).resolve().parents[1]
    source = (
        repository / "python" / "torusbrot" / "tld" / "heldout" / "verification.py"
    ).read_text(encoding="utf-8")
    assert "from .study import" not in source
    assert 'production_endpoint_functions_imported": False' in source
    json.loads(
        (
            repository / "studies" / "heldout-v0.2.1" / "preregistration" / "frozen_thresholds.json"
        ).read_text(encoding="utf-8")
    )


def test_public_heldout_bundle_is_auditable_and_semantic_mutations_fail(
    tmp_path: Path,
) -> None:
    repository = Path(__file__).resolve().parents[1]
    source = (
        repository
        / "apps"
        / "studio"
        / "public"
        / "examples"
        / "heldout-tld-study-combined.tbx.zip"
    )
    report = audit_bundle(source)
    assert report.valid, report.errors
    assert report.checked_files == 41

    members = read_members(source)
    endpoints = json.loads(members["tables/primary_endpoints.json"])
    endpoints["T_e"] = 9
    members["tables/primary_endpoints.json"] = (
        json.dumps(endpoints, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    )
    changed = resign_bundle(tmp_path / "winner-as-te.tbx.zip", members)
    assert "HELDOUT_TE_MISMATCH" in audit_bundle(changed).issue_codes

    members = read_members(source)
    adjudication = json.loads(members["audit/claim_adjudication.json"])
    adjudication["EXTERNALLY_VALIDATED"] = True
    members["audit/claim_adjudication.json"] = (
        json.dumps(adjudication, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    )
    changed = resign_bundle(tmp_path / "external-validation.tbx.zip", members)
    assert "HELDOUT_EXTERNAL_VALIDATION_FORBIDDEN" in audit_bundle(changed).issue_codes


def test_external_replication_package_is_hash_bound_and_outcome_blind() -> None:
    repository = Path(__file__).resolve().parents[1]
    replication = repository / "replication"
    for line in (replication / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        assert sha256_file(replication / relative) == expected
    inventory = json.loads(
        (replication / "expected_artifact_inventory.json").read_text(encoding="utf-8")
    )
    assert inventory["required_bundle_count"] == 3
    assert inventory["external_validation_must_remain_false_until_outside_report"] is True
    assert "expected_scientific_outcome" not in inventory
    verifier = (replication / "verify.py").read_text(encoding="utf-8")
    assert "HELDOUT_TLD_STUDY_POSITIVE_UNDER_FROZEN_GATES" not in verifier
