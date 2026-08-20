# ruff: noqa: E501 -- protocol identifiers and mutation labels are intentionally explicit.
from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from torusbrot.models import canonical_json

ROOT = Path(__file__).resolve().parents[1]
HELDOUT = ROOT / "studies" / "v0.3.0-recovery" / "heldout"
MATERIALIZATION = HELDOUT / "materialization"
PREREGISTRATION = HELDOUT / "preregistration"
AUTHORIZATION = HELDOUT / "authorization"
EXECUTION = HELDOUT / "execution"
OUTPUT = HELDOUT / "verification"
RUN_ID = "pinball-heldout-e9e3d7666b2b10cb"
SOURCE_SHA256 = "5819f9071c3b3b0b856934602b5e7b487852abe0e0a3a5b1b62eae17720d822f"
ROOT_SEED = 20260820
NULL_CHILDREN = 127
JOINT_REPLICATES = 999
TOLERANCE = 1e-12


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path)
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(path)
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value, pretty=True))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(canonical_json(row) for row in rows))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derived_seed(label: str) -> int:
    digest = hashlib.sha256(f"{ROOT_SEED}:{label}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def close(left: Any, right: Any, *, tolerance: float = TOLERANCE) -> bool:
    try:
        return bool(np.isclose(float(left), float(right), rtol=0.0, atol=tolerance))
    except (TypeError, ValueError):
        return False


def load_state() -> dict[str, Any]:
    return {
        "source_pairs": read_jsonl(MATERIALIZATION / "paired_acquisition_registry.jsonl"),
        "authorization": read_json(AUTHORIZATION / "scored_execution_authorization.json"),
        "claim": read_json(EXECUTION / "claim_adjudication.json"),
        "protocol": read_json(EXECUTION / "protocol_audit.json"),
        "receipt": read_json(EXECUTION / "execution_receipt.json"),
        "manifest": read_json(EXECUTION / "execution_manifest.json"),
        "attempt": read_json(EXECUTION / "execution_attempt.json"),
        "access": read_json(EXECUTION / "field_value_access_receipt.json"),
        "joint": read_json(EXECUTION / "joint_null_evidence.json"),
        "acquisitions": read_jsonl(EXECUTION / "acquisition_evidence.jsonl"),
        "acquisition_nulls": read_jsonl(EXECUTION / "acquisition_null_children.jsonl"),
        "pairs": read_jsonl(EXECUTION / "pair_evidence.jsonl"),
        "pair_nulls": read_jsonl(EXECUTION / "pair_null_children.jsonl"),
    }


def independent_joint(observed: np.ndarray, children: np.ndarray, channel: str) -> dict[str, Any]:
    rng = np.random.default_rng(derived_seed(f"joint-null:{channel}"))
    selections = rng.integers(0, NULL_CHILDREN, size=(JOINT_REPLICATES, 28))
    parents = np.broadcast_to(np.arange(28), selections.shape)
    joint = np.median(children[parents, selections], axis=1)
    observed_statistic = float(np.median(observed))
    null_median = float(np.median(joint))
    robust_scale = float(1.4826 * np.median(np.abs(joint - null_median)))
    return {
        "observed": observed_statistic,
        "null_median": null_median,
        "q025": float(np.quantile(joint, 0.025)),
        "q975": float(np.quantile(joint, 0.975)),
        "difference": observed_statistic - null_median,
        "robust_scale": robust_scale,
        "standardized": (observed_statistic - null_median) / max(robust_scale, np.finfo(float).eps),
        "values": joint,
    }


def protocol_issues(state: dict[str, Any], *, verify_files: bool = False) -> list[str]:
    issues: list[str] = []

    def require(condition: bool, code: str) -> None:
        if not condition:
            issues.append(code)

    authorization = state["authorization"]
    scope = authorization.get("authorization_scope", {})
    receipt = state["receipt"]
    manifest = state["manifest"]
    claim = state["claim"]
    protocol = state["protocol"]
    attempt = state["attempt"]
    access = state["access"]
    source_pairs = state["source_pairs"]
    acquisitions = state["acquisitions"]
    acquisition_nulls = state["acquisition_nulls"]
    pairs = state["pairs"]
    pair_nulls = state["pair_nulls"]
    joint = state["joint"]
    require(scope.get("permitted_scored_executions") == 1, "V001_AUTHORIZATION_LIMIT")
    require(receipt.get("scored_execution_count") == 1, "V002_EXECUTION_COUNT")
    require(receipt.get("second_scored_execution_permitted") is False, "V003_SECOND_EXECUTION_FIREWALL")
    require(attempt.get("attempt_number") == 1 and attempt.get("permitted_attempts") == 1, "V004_ATTEMPT_SENTINEL")
    require(access.get("values_previously_read_for_scoring") is False, "V005_PREVIOUS_SCORE_ACCESS")
    require(manifest.get("source_sha256") == SOURCE_SHA256, "V006_SOURCE_SHA256")
    require(manifest.get("run_id") == RUN_ID and receipt.get("run_id") == RUN_ID, "V007_RUN_ID")
    require(len(source_pairs) == 28 and len(pairs) == 28, "V008_PAIR_COUNT")
    require(len(acquisitions) == 56 and len(acquisition_nulls) == 56, "V009_ACQUISITION_COUNT")
    require(len(pair_nulls) == 28, "V010_PAIR_NULL_COUNT")
    expected_outcomes = {
        "GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY",
        "GEOMETRY_INDEXED_TLD_HELDOUT_EXECUTION_BLOCKED",
        "GEOMETRY_INDEXED_TLD_HELDOUT_INVALIDATED_BY_PROTOCOL",
    }
    require(claim.get("scientific_outcome") in expected_outcomes, "V011_CLAIM_OUTCOME")
    require("POSITIVE" not in str(claim.get("scientific_outcome")) and "NEGATIVE" not in str(claim.get("scientific_outcome")), "V012_BINARY_LABEL")
    require(claim.get("TLD_DERIVED") == "BLOCKED", "V013_TLD_DERIVED")
    require(claim.get("EXTERNALLY_VALIDATED") is False, "V014_EXTERNAL_VALIDATION")
    require(str(claim.get("T_e", "")).startswith("NOT_APPLICABLE"), "V015_T_E_FIREWALL")
    require(str(claim.get("S_e", "")).startswith("NOT_APPLICABLE"), "V016_S_E_FIREWALL")
    require(str(claim.get("winner_N", "")).startswith("NOT_APPLICABLE"), "V017_WINNER_N_FIREWALL")
    require(claim.get("binary_threshold_applied") is False, "V018_THRESHOLD_FIREWALL")
    require(protocol.get("p_value_computed") is False and joint.get("binary_threshold_applied") is False, "V019_P_VALUE_FIREWALL")
    require(protocol.get("winner_selection_performed") is False, "V020_WINNER_SELECTION")
    require(protocol.get("rotation_equivariance") == "PASS", "V021_ROTATION_STATUS")
    acquisition_by_member = {row.get("member"): row for row in acquisitions}
    null_by_member = {row.get("member"): row for row in acquisition_nulls}
    pair_by_id = {row.get("pair_id"): row for row in pairs}
    pair_null_by_id = {row.get("pair_id"): row for row in pair_nulls}
    require(len(acquisition_by_member) == 56 and len(null_by_member) == 56, "V022_MEMBER_UNIQUENESS")
    require(len(pair_by_id) == 28 and len(pair_null_by_id) == 28, "V023_PAIR_UNIQUENESS")
    observed_by_channel: dict[str, list[float]] = {}
    null_by_channel: dict[str, list[list[float]]] = {}
    for source_pair in source_pairs:
        pair_id = source_pair["pair_id"]
        if pair_id not in pair_by_id or pair_id not in pair_null_by_id:
            continue
        row = pair_by_id[pair_id]
        null_row = pair_null_by_id[pair_id]
        actuated_member = source_pair["actuated_member"]
        reference_member = source_pair["reference_member"]
        if actuated_member not in acquisition_by_member or reference_member not in acquisition_by_member:
            issues.append(f"V024_PAIR_MEMBER_MISSING:{pair_id}")
            continue
        actuated = acquisition_by_member[actuated_member]
        reference = acquisition_by_member[reference_member]
        for projection in ("P01", "P02"):
            expected_delta = row.get(f"{projection}_pair_delta", {})
            actual_left = actuated.get(f"{projection}_channels", {})
            actual_right = reference.get(f"{projection}_channels", {})
            if set(expected_delta) != set(actual_left) or set(expected_delta) != set(actual_right):
                issues.append(f"V025_{projection}_CHANNEL_SET:{pair_id}")
                continue
            for channel, value in expected_delta.items():
                recomputed = float(actual_left[channel] - actual_right[channel])
                if not close(value, recomputed):
                    issues.append(f"V026_{projection}_PAIR_DELTA:{pair_id}:{channel}")
        if actuated_member not in null_by_member or reference_member not in null_by_member:
            issues.append(f"V027_NULL_MEMBER_MISSING:{pair_id}")
            continue
        actuated_null = null_by_member[actuated_member].get("samples_by_channel", {})
        reference_null = null_by_member[reference_member].get("samples_by_channel", {})
        saved_null_delta = null_row.get("null_child_pair_deltas_by_channel", {})
        for channel, observed_delta in row.get("P01_pair_delta", {}).items():
            left = actuated_null.get(channel, [])
            right = reference_null.get(channel, [])
            saved = saved_null_delta.get(channel, [])
            if len(left) != NULL_CHILDREN or len(right) != NULL_CHILDREN or len(saved) != NULL_CHILDREN:
                issues.append(f"V028_NULL_CHILD_COUNT:{pair_id}:{channel}")
                continue
            recomputed_null = np.asarray(left, dtype=np.float64) - np.asarray(right, dtype=np.float64)
            if not np.allclose(recomputed_null, np.asarray(saved), rtol=0.0, atol=TOLERANCE):
                issues.append(f"V029_NULL_PAIR_DELTA:{pair_id}:{channel}")
            observed_by_channel.setdefault(channel, []).append(float(observed_delta))
            null_by_channel.setdefault(channel, []).append([float(value) for value in recomputed_null])
        rotation = actuated.get("perturbations", {}).get("PERT01_ROTATE_90_WITH_COORDINATES_COMPONENTS_AND_MASK", {})
        reference_rotation = reference.get("perturbations", {}).get("PERT01_ROTATE_90_WITH_COORDINATES_COMPONENTS_AND_MASK", {})
        if rotation.get("status") != "PASS" or reference_rotation.get("status") != "PASS":
            issues.append(f"V030_ROTATION_FAILURE:{pair_id}")
    require(set(observed_by_channel) == set(joint.get("channels", {})), "V031_JOINT_CHANNEL_SET")
    for channel, saved in joint.get("channels", {}).items():
        if channel not in observed_by_channel:
            continue
        if (
            len(observed_by_channel[channel]) != 28
            or len(null_by_channel.get(channel, [])) != 28
            or any(len(row) != NULL_CHILDREN for row in null_by_channel[channel])
        ):
            issues.append(f"V032_JOINT_INPUT_SHAPE:{channel}")
            continue
        independent = independent_joint(
            np.asarray(observed_by_channel[channel], dtype=np.float64),
            np.asarray(null_by_channel[channel], dtype=np.float64),
            channel,
        )
        comparisons = {
            "observed": saved.get("within_campaign_observed_median_pair_delta"),
            "null_median": saved.get("joint_null_median"),
            "q025": saved.get("joint_null_q025"),
            "q975": saved.get("joint_null_q975"),
            "difference": saved.get("observed_minus_joint_null_median"),
            "robust_scale": saved.get("joint_null_robust_scale"),
            "standardized": saved.get("robust_standardized_effect"),
        }
        if any(not close(comparisons[name], independent[name]) for name in comparisons):
            issues.append(f"V033_JOINT_SUMMARY:{channel}")
        saved_values = np.asarray(saved.get("joint_null_values", []), dtype=np.float64)
        if len(saved_values) != JOINT_REPLICATES or not np.array_equal(saved_values, independent["values"]):
            issues.append(f"V034_JOINT_VALUES:{channel}")
        if saved.get("p_value_computed") is not False or saved.get("binary_threshold_applied") is not False:
            issues.append(f"V035_JOINT_BINARY_FIELD:{channel}")
    if verify_files:
        for artifact in manifest.get("artifacts", []):
            name = artifact.get("name")
            path = EXECUTION / str(name)
            if not path.is_file() or sha256_file(path) != artifact.get("sha256"):
                issues.append(f"V036_MANIFEST_HASH:{name}")
        require(receipt.get("manifest_sha256") == sha256_file(EXECUTION / "execution_manifest.json"), "V037_MANIFEST_RECEIPT")
    return sorted(set(issues))


def mutations() -> list[tuple[str, str, Callable[[dict[str, Any]], None]]]:
    return [
        (
            "M01_SECOND_SCORED_EXECUTION",
            "increase the scored execution count to two",
            lambda state: state["receipt"].update(scored_execution_count=2),
        ),
        (
            "M02_BINARY_POSITIVE_LABEL",
            "replace the nonbinary outcome with a TLD-positive label",
            lambda state: state["claim"].update(scientific_outcome="GEOMETRY_INDEXED_TLD_POSITIVE"),
        ),
        (
            "M03_TLD_DERIVED",
            "promote the blocked TLD_DERIVED field",
            lambda state: state["claim"].update(TLD_DERIVED="DERIVED"),
        ),
        (
            "M04_MANUFACTURE_T_E",
            "replace the inapplicable T_e endpoint with a numeric value",
            lambda state: state["claim"].update(T_e=4),
        ),
        (
            "M05_MANUFACTURE_S_E",
            "replace the inapplicable S_e endpoint with geometric scale",
            lambda state: state["claim"].update(S_e=2),
        ),
        (
            "M06_MANUFACTURE_WINNER_N",
            "replace the inapplicable winner_N endpoint with a numeric value",
            lambda state: state["claim"].update(winner_N=10),
        ),
        (
            "M07_ENABLE_P_VALUE",
            "mark a joint channel as a hypothesis-test p-value",
            lambda state: next(iter(state["joint"]["channels"].values())).update(p_value_computed=True),
        ),
        (
            "M08_DROP_PAIR",
            "remove one frozen pair from the reported evidence",
            lambda state: state["pairs"].pop(),
        ),
        (
            "M09_CORRUPT_PAIR_DELTA",
            "change a reported P01 pair delta",
            lambda state: next(iter(state["pairs"][0]["P01_pair_delta"]))
            and state["pairs"][0]["P01_pair_delta"].update(
                {
                    next(iter(state["pairs"][0]["P01_pair_delta"])): 999.0,
                }
            ),
        ),
        (
            "M10_DROP_NULL_CHILD",
            "remove one acquisition-local null child",
            lambda state: next(iter(state["acquisition_nulls"][0]["samples_by_channel"].values())).pop(),
        ),
        (
            "M11_CORRUPT_SOURCE_HASH",
            "replace the frozen source SHA-256",
            lambda state: state["manifest"].update(source_sha256="0" * 64),
        ),
        (
            "M12_FAIL_ROTATION",
            "replace the registered equivariance pass with failure",
            lambda state: state["acquisitions"][0]["perturbations"][
                "PERT01_ROTATE_90_WITH_COORDINATES_COMPONENTS_AND_MASK"
            ].update(status="FAIL"),
        ),
    ]


def main() -> None:
    state = load_state()
    baseline_issues = protocol_issues(state, verify_files=True)
    mutation_rows = []
    for mutation_id, description, apply_mutation in mutations():
        mutated = copy.deepcopy(state)
        apply_mutation(mutated)
        issues = protocol_issues(mutated)
        mutation_rows.append(
            {
                "mutation_id": mutation_id,
                "description": description,
                "detected": bool(issues),
                "detected_issue_codes": issues,
            }
        )
    verification = {
        "schema_version": "1.0.0",
        "run_id": RUN_ID,
        "status": "PASS" if not baseline_issues and all(row["detected"] for row in mutation_rows) else "FAIL",
        "production_runner_imported": False,
        "raw_hdf5_field_values_reopened": False,
        "verification_inputs": "saved acquisition channels, null children, pair evidence, manifests, contracts, and claim artifacts",
        "pair_deltas_independently_recomputed": True,
        "null_child_pair_deltas_independently_recomputed": True,
        "joint_999_replicate_summaries_independently_recomputed": True,
        "baseline_disagreements": baseline_issues,
        "disagreement_count": len(baseline_issues),
        "mutation_count": len(mutation_rows),
        "mutations_detected": sum(row["detected"] for row in mutation_rows),
        "second_scored_execution_performed": False,
        "scored_execution_count": 1,
        "scientific_outcome_unchanged": state["claim"]["scientific_outcome"],
        "TLD_DERIVED": "BLOCKED",
        "EXTERNALLY_VALIDATED": False,
    }
    write_json(OUTPUT / "independent_verification.json", verification)
    write_jsonl(OUTPUT / "mutation_results.jsonl", mutation_rows)
    write_json(
        OUTPUT / "verification_receipt.json",
        {
            "schema_version": "1.0.0",
            "run_id": RUN_ID,
            "status": verification["status"],
            "disagreement_count": len(baseline_issues),
            "mutation_count": len(mutation_rows),
            "mutations_detected": verification["mutations_detected"],
            "raw_hdf5_field_values_reopened": False,
            "second_scored_execution_performed": False,
            "scored_execution_count": 1,
        },
    )
    print(json.dumps(verification, indent=2, sort_keys=True))
    if verification["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
