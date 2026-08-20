from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELDOUT = ROOT / "studies" / "v0.3.0-recovery" / "heldout"
MATERIALIZATION = HELDOUT / "materialization"
PREREGISTRATION = HELDOUT / "preregistration"


def load(directory: Path, name: str) -> dict[str, object]:
    value = json.loads((directory / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def load_jsonl(directory: Path, name: str) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (directory / name).read_text(encoding="utf-8").splitlines()
        if line
    ]


def test_materialization_is_hash_verified_and_outcome_blind() -> None:
    custody = load(MATERIALIZATION, "source_custody.json")
    receipt = load(MATERIALIZATION, "source_materialization_receipt.json")
    structures = load_jsonl(MATERIALIZATION, "hdf5_structure_registry.jsonl")
    assert custody["status"] == "PASS"
    assert custody["published_size_bytes"] == 1_333_197_134
    assert custody["verified_md5"] == "6629a8e110b1682b9361de37d8be4afb"
    assert custody["verified_sha256"] == (
        "5819f9071c3b3b0b856934602b5e7b487852abe0e0a3a5b1b62eae17720d822f"
    )
    assert custody["raw_field_values_read"] is False
    assert custody["field_statistics_computed"] is False
    assert receipt["hdf5_values_read"] is False
    assert receipt["scored_execution_authorized"] is False
    assert len(structures) == 57
    assert all(row["field_values_read"] is False for row in structures)
    assert all(row["snapshot_axis"] == 0 for row in structures)
    assert all(set(row["datasets"]) == {"U", "V", "X", "Y"} for row in structures)


def test_exact_pair_hierarchy_is_frozen_without_population_promotion() -> None:
    pairs = load_jsonl(MATERIALIZATION, "paired_acquisition_registry.jsonl")
    hierarchy = load(PREREGISTRATION, "parent_campaign_hierarchy.json")
    effective = load(PREREGISTRATION, "effective_sample_method.json")
    assert len(pairs) == 28
    assert len({row["actuated_member"] for row in pairs}) == 28
    assert len({row["reference_member"] for row in pairs}) == 28
    assert all(row["reference_reused"] is False for row in pairs)
    assert [row["p"] for row in pairs if row["spatial_grid_shape_match"] is False] == [
        2.0,
        2.2,
        2.6,
    ]
    assert all(
        row["pairwise_cell_alignment"]
        == "FORBIDDEN_COMPARE_ACQUISITION_LEVEL_CHANNELS_ONLY"
        for row in pairs
    )
    assert sorted(row["p"] for row in pairs) == [
        round(-2.8 + 0.2 * index, 1) for index in range(28)
    ]
    assert hierarchy["campaign_count"] == "UNKNOWN_NO_SCORE"
    assert hierarchy["paired_acquisition_blocks"] == 28
    assert hierarchy["acquisition_files"] == 56
    assert hierarchy["auxiliary_unpaired_acquisitions"] == 1
    assert hierarchy["cross_file_cell_alignment"] == "FORBIDDEN"
    assert hierarchy["spatial_grid_shape_mismatch_pairs"] == [
        {"p": 2.0, "pair_id": "PAIR_25"},
        {"p": 2.2, "pair_id": "PAIR_26"},
        {"p": 2.6, "pair_id": "PAIR_28"},
    ]
    assert effective["effective_population_parent_count"] == 1
    assert effective["population_sign_test"] == "FORBIDDEN"


def test_preregistration_manifest_is_complete_and_deterministic() -> None:
    manifest = load(PREREGISTRATION, "preregistration_manifest.json")
    assert manifest["status"] == "FROZEN_PENDING_COMMIT_AND_PUSH"
    assert manifest["outcome_data_used"] is False
    assert manifest["field_values_read"] is False
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    assert len(artifacts) == 19
    for artifact in artifacts:
        assert isinstance(artifact, dict)
        path = PREREGISTRATION / str(artifact["name"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]


def test_single_execution_and_projection_contracts_are_frozen() -> None:
    run = load(PREREGISTRATION, "run_contract.json")
    projections = load_jsonl(PREREGISTRATION, "projection_registry.jsonl")
    nulls = load_jsonl(PREREGISTRATION, "null_registry.jsonl")
    assert run["scored_execution_limit"] == 1
    assert run["scored_executions_completed"] == 0
    assert run["execution_authorized"] is False
    assert run["outcome_data_used_during_preregistration"] is False
    assert [row["projection_id"] for row in projections] == [
        "P01_REGISTERED_TEMPORAL_MEAN_VECTOR_FIELD",
        "P02_REGISTERED_SPATIOTEMPORAL_VECTOR_FLUCTUATIONS",
    ]
    assert projections[0]["silent_time_average"] is False
    assert nulls[0]["children_per_acquisition"] == 127
    assert nulls[0]["joint_aggregate_replicates"] == 999
    assert nulls[0]["global_child_pool"] == "FORBIDDEN"


def test_claim_and_endpoint_firewalls_forbid_binary_tld_interpretation() -> None:
    boundary = load(PREREGISTRATION, "claim_boundary.json")
    endpoints = load(PREREGISTRATION, "endpoint_applicability.json")
    scales = load(PREREGISTRATION, "geometric_scale_registry.json")
    closure = load(PREREGISTRATION, "closure_objective.json")
    outcomes = boundary["permitted_outcomes"]
    assert isinstance(outcomes, list)
    assert set(outcomes) == {
        "GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY",
        "GEOMETRY_INDEXED_TLD_HELDOUT_EXECUTION_BLOCKED",
        "GEOMETRY_INDEXED_TLD_HELDOUT_INVALIDATED_BY_PROTOCOL",
    }
    assert not any("POSITIVE" in outcome or "NEGATIVE" in outcome for outcome in outcomes)
    assert boundary["TLD_DERIVED"] == "BLOCKED"
    assert boundary["EXTERNALLY_VALIDATED"] is False
    assert boundary["ToT_BROT"] == "FORBIDDEN"
    assert str(endpoints["T_e"]).startswith("NOT_APPLICABLE")
    assert str(endpoints["S_e"]).startswith("NOT_APPLICABLE")
    assert str(endpoints["winner_N"]).startswith("NOT_APPLICABLE")
    assert str(scales["S_e"]).startswith("NOT_APPLICABLE")
    assert closure["winner_N"] == "NOT_APPLICABLE"
