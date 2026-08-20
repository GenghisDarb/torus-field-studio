from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "studies" / "v0.3.0-recovery"


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_method_v1_and_dataset_v1_are_append_only_superseded() -> None:
    method = _json(RECOVERY / "supersession" / "method_freeze_v1_status.json")
    dataset = _json(RECOVERY / "supersession" / "dataset_freeze_v1_status.json")
    assert set(method["statuses"]) == {
        "SUPERSEDED_FOR_FUTURE_CONFIRMATORY_USE",
        "PRESERVED_FOR_REPRODUCTION",
        "NOT_DELETED",
        "NOT_REWRITTEN",
    }
    assert "NONCONFIRMATORY_METHOD_DEVELOPMENT_PILOT_ONLY" in dataset["statuses"]
    assert "THRESHOLD_CALIBRATION_FORBIDDEN" in dataset["statuses"]


def test_parent_policy_has_no_universal_fixed_eight_rule() -> None:
    design = _json(RECOVERY / "design" / "statistical_unit_contract_v2.json")
    frozen = _json(RECOVERY / "freeze" / "frozen_parent_design_policy_v2.json")
    assert design["universal_minimum_parent_count"] is None
    assert frozen["universal_minimum_parent_count"] is None
    assert frozen["old_v1_eight_parent_gate"] == "PRESERVED_UNMODIFIED_HISTORICAL_ONLY"
    assert frozen["unknown_hierarchy_credit"] == "NONE"


def test_v2_freeze_is_instrumented_evidence_vector_only() -> None:
    method = _json(RECOVERY / "freeze" / "frozen_method_v2.json")
    gate = _json(RECOVERY / "freeze" / "method_v2_acceptance_gate.json")
    assert method["method_id"] == "METHOD_V2_C_EVIDENCE_VECTOR"
    assert method["required_name"] == "INSTRUMENTED_EVIDENCE_VECTOR"
    assert method["predictive_TLD_discriminator"] is False
    assert method["EXTERNALLY_VALIDATED"] is False
    assert method["TLD_DERIVED_default"] == "BLOCKED"
    assert gate["evidence_vector_pass"] is True
    assert gate["binary_pass"] is False
    assert gate["hierarchical_pass"] is False


def test_raw_verifier_and_bridge_pass_without_disagreement() -> None:
    verification = _json(RECOVERY / "verification" / "independent_raw_recomputation.json")
    bridge = _json(RECOVERY / "bridge" / "geometry_tld_bridge_adjudication.json")
    assert verification["production_endpoint_CSV_used_as_primary_evidence"] is False
    assert verification["raw_realizations_recomputed"] >= 600
    assert verification["unexplained_disagreement_count"] == 0
    assert verification["mutation_count"] >= 45
    assert verification["mutations_rejected"] == verification["mutation_count"]
    assert bridge["status"] == "PASS_LOSSLESS_PATH_CHANNEL_ONLY"
    assert bridge["exact_commutative_pass_count"] == 3


def test_freeze_checksums_cover_and_match_every_frozen_contract() -> None:
    checksum_file = RECOVERY / "freeze" / "method_v2_SHA256SUMS.txt"
    rows = [line.split("  ", 1) for line in checksum_file.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 11
    for expected, name in rows:
        actual = hashlib.sha256((checksum_file.parent / name).read_bytes()).hexdigest()
        assert actual == expected
