from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "studies" / "v0.3.0-field-selection"


def load(name: str) -> object:
    return json.loads((SELECTION / name).read_text(encoding="utf-8"))


def test_candidate_selection_is_outcome_blind_and_method_bound() -> None:
    scores = load("candidate_scores.json")
    receipt = load("selected_candidate_receipt.json")
    assert isinstance(scores, dict)
    assert isinstance(receipt, dict)
    assert scores["outcome_data_used"] is False
    assert receipt["raw_measurement_archive_accessed"] is False
    assert receipt["candidate_id"] == "wind_farm_scanning_lidar_wakes"
    assert receipt["selected_method"] == "METHOD_C_EVIDENCE_VECTOR_NONBINARY"
    assert receipt["candidate_substitution_after_dataset_freeze"] == "FORBIDDEN"
    assert receipt["method_freeze_commit"] == "827b3394c0ce8ed414ca57d8e77ef1aaf1a72b1c"


def test_candidate_score_bounds_ranking_and_automatic_exclusions() -> None:
    scores = load("candidate_scores.json")
    assert isinstance(scores, dict)
    maxima = scores["dimension_maxima"]
    eligible = []
    for row in scores["scores"]:
        assert row["subtotal"] == sum(row["dimensions"].values())
        for dimension, maximum in maxima.items():
            assert 0 <= row["dimensions"][dimension] <= maximum
        assert row["automatic_penalty"] == -100 * len(row["automatic_exclusions"])
        assert row["eligible"] is (not row["automatic_exclusions"])
        if row["eligible"]:
            eligible.append(row)
    assert eligible[0]["candidate_id"] == scores["selected_candidate_id"]
    assert eligible[0]["subtotal"] > eligible[1]["subtotal"]


def test_selected_source_plan_has_fail_closed_custody() -> None:
    plan = load("selected_candidate_source_plan.json")
    exposure = load("prior_exposure_audit.json")
    assert isinstance(plan, dict)
    assert isinstance(exposure, dict)
    assert plan["acquisition_authorized_only_after_dataset_freeze_push"] is True
    assert plan["primary_measurement_archive"] == "Multiple Wake.zip"
    assert all("published_md5" in item for item in plan["required_files"])
    assert "never substitute" in plan["failure_policy"]
    assert exposure["selected_candidate"]["prior_outcome_exposure"] is False
