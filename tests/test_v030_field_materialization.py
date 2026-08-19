from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "studies" / "v0.3.0-field-assay" / "materialization"


def load(name: str) -> object:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_materialization_is_complete_without_claim_metrics() -> None:
    receipt = load("materialization_receipt.json")
    contamination = load("contamination_prevention.json")
    parents = (OUT / "parent_registry.jsonl").read_text(encoding="utf-8").splitlines()
    assert isinstance(receipt, dict)
    assert isinstance(contamination, dict)
    assert receipt["status"] == "PASS_WITH_DOCUMENTED_WARNINGS"
    assert receipt["parent_count"] == 4
    assert receipt["claim_metrics_computed"] is False
    assert contamination["dataset_frozen_before_raw_access"] is True
    assert len(parents) == 4


def test_field_units_and_parent_limitations_are_explicit() -> None:
    coordinate = load("coordinate_integrity.json")
    parent = load("parent_independence_precheck.json")
    scout = load("scout_eligibility.json")
    assert isinstance(coordinate, dict)
    assert isinstance(parent, dict)
    assert isinstance(scout, dict)
    assert coordinate["native_unit_attributes"] is False
    assert coordinate["status"] == "PASS_WITH_CROSS_SOURCE_UNIT_PROVENANCE"
    assert parent["effective_parent_count_for_frozen_assay"] == 4
    assert parent["binary_sensitivity_adequate"] is False
    assert scout["claim_ceiling"] == "NONBINARY_EVIDENCE_VECTOR_ONLY"


def test_materialization_input_checksums_are_current() -> None:
    for line in (OUT / "SHA256SUMS_INPUTS.txt").read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        actual = hashlib.sha256((OUT / name).read_bytes()).hexdigest()
        assert actual == expected
