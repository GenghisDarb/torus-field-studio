from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "studies" / "v0.3.0-recovery" / "candidate_selection"


def load(name: str) -> dict[str, object]:
    value = json.loads((SELECTION / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def load_jsonl(name: str) -> list[dict[str, object]]:
    lines = (SELECTION / name).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_structural_probe_is_outcome_blind_and_uses_no_field_payloads() -> None:
    probes = load_jsonl("candidate_structural_probe_registry.jsonl")
    pinball = next(row for row in probes if row["candidate_id"] == "actuated_fluidic_pinball_piv")
    assert pinball["inspection_mode"] == "METADATA_README_AND_ZIP_CENTRAL_DIRECTORY_ONLY"
    assert pinball["raw_hdf5_field_payload_accessed"] is False
    for forbidden in (
        "field_statistics_computed",
        "TLD_channels_computed",
        "closure_computed",
        "null_separation_computed",
        "source_power_computed",
        "outcome_informed_projection",
    ):
        assert pinball[forbidden] is False


def test_verified_hierarchy_does_not_promote_unknown_or_nested_counts() -> None:
    rows = load_jsonl("candidate_hierarchy_registry.jsonl")
    for row in rows:
        assert row["unknown_counts_awarded_full_score"] is False
        assert row["nested_samples_promoted_to_independent_parents"] is False
    pinball = next(row for row in rows if row["candidate_id"] == "actuated_fluidic_pinball_piv")
    assert pinball["independent_acquisition_count"]["value"] == 57
    assert pinball["same_condition_replicate_count"]["value"] == 28
    assert pinball["campaign_count"]["status"] == "UNKNOWN_NO_SCORE"


def test_candidate_scoring_is_separated_and_selects_tier_two_pinball() -> None:
    scores = load("candidate_scores_v2.json")
    receipt = load("selected_candidate_receipt_v2.json")
    assert scores["dimensions_separated"] is True
    assert scores["unknown_counts_receive_full_score"] is False
    assert scores["outcome_data_used"] is False
    maxima = scores["score_dimension_maxima"]
    assert isinstance(maxima, dict)
    for row in scores["scores"]:
        assert row["subtotal"] == sum(row["dimensions"].values())
        assert all(row["dimensions"][name] <= maximum for name, maximum in maxima.items())
    assert receipt["candidate_id"] == "actuated_fluidic_pinball_piv"
    assert receipt["selected_design_tier"] == 2
    assert receipt["outcome_data_used_for_selection"] is False
    assert receipt["raw_measurement_archive_accessed"] is False
    assert receipt["candidate_substitution_after_freeze_commit"] == "FORBIDDEN"


def test_wind_farm_cannot_reenter_confirmatory_selection() -> None:
    eligibility = load_jsonl("candidate_design_tier_eligibility.jsonl")
    wind = next(
        row
        for row in eligibility
        if row["candidate_id"] == "wind_farm_scanning_lidar_wakes"
    )
    assert wind["eligible"] is False
    assert wind["tier_name"] == "NONCONFIRMATORY_PILOT_ONLY"
    assert wind["TLD_DERIVED_default"] == "BLOCKED"
