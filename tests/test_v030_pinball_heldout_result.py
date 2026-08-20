from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELDOUT = ROOT / "studies" / "v0.3.0-recovery" / "heldout"
EXECUTION = HELDOUT / "execution"
VERIFICATION = HELDOUT / "verification"


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


def test_exactly_one_execution_is_preserved_and_manifested() -> None:
    attempt = load(EXECUTION, "execution_attempt.json")
    access = load(EXECUTION, "field_value_access_receipt.json")
    receipt = load(EXECUTION, "execution_receipt.json")
    manifest = load(EXECUTION, "execution_manifest.json")
    assert attempt["attempt_number"] == 1
    assert attempt["permitted_attempts"] == 1
    assert attempt["created_before_field_value_access"] is True
    assert attempt["implementation_commit"] == (
        "a40663cfa7611af5085c40408a067fc61477f610"
    )
    assert access["values_previously_read_for_scoring"] is False
    assert receipt["status"] == "PASS_ONE_SCORED_EXECUTION_PRESERVED"
    assert receipt["scored_execution_count"] == 1
    assert receipt["second_scored_execution_permitted"] is False
    assert manifest["scored_execution_count"] == 1
    assert manifest["second_scored_execution_permitted"] is False
    for artifact in manifest["artifacts"]:
        assert isinstance(artifact, dict)
        path = EXECUTION / str(artifact["name"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
    assert receipt["manifest_sha256"] == hashlib.sha256(
        (EXECUTION / "execution_manifest.json").read_bytes()
    ).hexdigest()


def test_all_acquisitions_pairs_nulls_scales_and_perturbations_are_reported() -> None:
    acquisitions = load_jsonl(EXECUTION, "acquisition_evidence.jsonl")
    acquisition_nulls = load_jsonl(EXECUTION, "acquisition_null_children.jsonl")
    pairs = load_jsonl(EXECUTION, "pair_evidence.jsonl")
    pair_nulls = load_jsonl(EXECUTION, "pair_null_children.jsonl")
    assert len(acquisitions) == 56
    assert len(acquisition_nulls) == 56
    assert len(pairs) == 28
    assert len(pair_nulls) == 28
    assert [row["p"] for row in pairs] == [round(-2.8 + 0.2 * index, 1) for index in range(28)]
    for row in acquisitions:
        assert row["projection_audit"]["snapshot_axis"] == 0
        assert row["projection_audit"]["fill_performed"] is False
        assert row["projection_audit"]["interpolation_performed"] is False
        assert row["projection_audit"]["observed_grid_cells"] >= 16
        assert set(row["perturbations"]) == {
            "PERT01_ROTATE_90_WITH_COORDINATES_COMPONENTS_AND_MASK",
            "PERT02_MASK_DROPOUT_5_PERCENT",
            "PERT03_RELATIVE_COMPONENT_NOISE_1_PERCENT",
            "PERT04_ANTI_ALIASED_SCALE_2X",
        }
        assert row["perturbations"][
            "PERT01_ROTATE_90_WITH_COORDINATES_COMPONENTS_AND_MASK"
        ]["status"] == "PASS"
        assert [scale["ell_cells"] for scale in row["scale_views"]] == [1, 2, 4]
        assert all(scale["S_e"] == "NOT_APPLICABLE" for scale in row["scale_views"])
    for row in acquisition_nulls:
        assert row["children"] == 127
        assert all(len(values) == 127 for values in row["samples_by_channel"].values())


def test_joint_summary_is_nonbinary_and_complete() -> None:
    joint = load(EXECUTION, "joint_null_evidence.json")
    assert set(joint["channels"]) == {
        "curl_coherence",
        "curl_energy",
        "divergence_energy",
        "signed_mean_curl",
        "u_neighbor_coherence",
        "v_neighbor_coherence",
    }
    assert joint["binary_threshold_applied"] is False
    assert joint["multiple_testing_family"] == "NONE"
    assert joint["population_generalization"] is False
    for row in joint["channels"].values():
        assert row["joint_null_replicates"] == 999
        assert len(row["joint_null_values"]) == 999
        assert row["p_value_computed"] is False
        assert row["binary_threshold_applied"] is False


def test_claim_cannot_escape_the_nonbinary_method_ceiling() -> None:
    claim = load(EXECUTION, "claim_adjudication.json")
    protocol = load(EXECUTION, "protocol_audit.json")
    assert claim["scientific_outcome"] == (
        "GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY"
    )
    assert claim["positive_negative_TLD_classification"] == (
        "NOT_PERFORMED_FORBIDDEN_BY_METHOD_FREEZE"
    )
    assert claim["TLD_DERIVED"] == "BLOCKED"
    assert claim["EXTERNALLY_VALIDATED"] is False
    assert str(claim["T_e"]).startswith("NOT_APPLICABLE")
    assert str(claim["S_e"]).startswith("NOT_APPLICABLE")
    assert str(claim["winner_N"]).startswith("NOT_APPLICABLE")
    assert protocol["p_value_computed"] is False
    assert protocol["winner_selection_performed"] is False
    assert protocol["second_scored_execution_attempted"] is False


def test_independent_verifier_has_zero_disagreements_and_catches_mutations() -> None:
    verification = load(VERIFICATION, "independent_verification.json")
    receipt = load(VERIFICATION, "verification_receipt.json")
    mutations = load_jsonl(VERIFICATION, "mutation_results.jsonl")
    assert verification["status"] == "PASS"
    assert verification["production_runner_imported"] is False
    assert verification["raw_hdf5_field_values_reopened"] is False
    assert verification["second_scored_execution_performed"] is False
    assert verification["disagreement_count"] == 0
    assert verification["mutation_count"] == 12
    assert verification["mutations_detected"] == 12
    assert len(mutations) == 12
    assert all(row["detected"] is True for row in mutations)
    assert receipt["scored_execution_count"] == 1
