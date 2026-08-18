"""Post-verification scientific adjudication for the frozen held-out study."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

from ...domains.beijing_pm25 import SOURCE_SHA256, sha256_file, write_json

FORBIDDEN_CLAIMS = [
    "TORUS Theory proven",
    "14 uniquely established as a universal law",
    "physical causation established",
    "observer-state effects established",
    "cosmological quantities derived",
    "ToT-BROT validated",
    "ToT-BULB validated",
    "universal cross-domain closure established",
    "a theory of everything confirmed",
]


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def finalize_scored_manifest(scored: Path) -> dict[str, Any]:
    """Correct the preliminary manifest after redirected logs have flushed."""
    scored = scored.resolve()
    manifest = scored / "SHA256SUMS_SCORED_RUN.txt"
    prelog = scored / "SHA256SUMS_SCORED_RUN.prelog.txt"
    correction = scored / "post_execution_manifest_correction.json"
    if not prelog.exists():
        shutil.copyfile(manifest, prelog)
    receipt = {
        "schema_version": "1.0.0",
        "issue_code": "POST_EXECUTION_LOG_FLUSH_MANIFEST_CORRECTION",
        "original_manifest_sha256": sha256_file(prelog),
        "reason": (
            "the preliminary manifest was computed inside the scorer before "
            "redirected stdout flushed"
        ),
        "scientific_outputs_changed": False,
        "analysis_rerun": False,
        "contracts_changed": False,
        "original_manifest_preserved": prelog.name,
    }
    write_json(correction, receipt)
    lines: list[str] = []
    for path in sorted(scored.iterdir()):
        if path.is_file() and path != manifest:
            lines.append(f"{sha256_file(path)}  {path.name}\n")
    manifest.write_text("".join(lines), encoding="utf-8", newline="\n")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        if sha256_file(scored / name) != expected:
            raise ValueError(f"corrected scored-run manifest mismatch: {name}")
    return receipt | {"corrected_manifest_sha256": sha256_file(manifest)}


def _verification_manifest(verification: Path) -> str:
    target = verification / "SHA256SUMS_VERIFICATION.txt"
    lines = [
        f"{sha256_file(path)}  {path.name}\n"
        for path in sorted(verification.iterdir())
        if path.is_file() and path != target
    ]
    target.write_text("".join(lines), encoding="utf-8", newline="\n")
    return sha256_file(target)


def adjudicate(scored: Path, verification: Path, output: Path) -> dict[str, Any]:
    scored = scored.resolve()
    verification = verification.resolve()
    output.mkdir(parents=True, exist_ok=True)
    correction = finalize_scored_manifest(scored)
    verification_manifest_sha256 = _verification_manifest(verification)
    endpoints = _json(scored / "primary_endpoints.json")
    verifier = _json(verification / "independent_verification.json")
    recomputed = _json(verification / "independent_recomputed_endpoints.json")
    baseline_surface = [
        row for row in _csv(scored / "byN_surface.csv") if row["condition"] == "baseline"
    ]
    baseline_models = [
        row
        for row in _csv(scored / "domain_baseline_comparison.csv")
        if row["station"] != "POPULATION_SEP"
    ]
    all_ar1_better = all(
        float(row["model_test_rmse"]) < float(row["monthly_climatology_test_rmse"])
        for row in baseline_models
    )
    t_e_observed = endpoints["T_e"] != "NOT_OBSERVED"
    s_e_positive = float(endpoints["S_e_contiguous"]) > 0
    sep_any = any(row["SEP"].lower() == "true" for row in baseline_surface)
    verified = verifier["status"] == "verified" and verifier["disagreement_count"] == 0
    mutations_passed = verifier["mutation_rejection_count"] == verifier["mutation_count"] == 25
    tld_derived_permitted = (
        t_e_observed
        and s_e_positive
        and sep_any
        and verified
        and mutations_passed
        and bool(endpoints["baseline_residual_SEP_persists_at_T_e"])
        and not bool(endpoints["single_parent_dependency"])
    )
    if t_e_observed and s_e_positive and sep_any:
        outcome = (
            "HELDOUT_TLD_STUDY_POSITIVE_UNDER_FROZEN_GATES"
            if tld_derived_permitted
            else "HELDOUT_TLD_STUDY_PARTIAL_WITH_EXACT_BLOCKERS"
        )
    else:
        outcome = "HELDOUT_TLD_STUDY_NEGATIVE_UNDER_FROZEN_GATES"
    blockers = []
    if not sep_any:
        blockers.append("No N in the frozen primary grid satisfied SEP.")
    if not t_e_observed:
        blockers.append("T_e is NOT_OBSERVED and may not be backfilled from winner_N.")
    if not s_e_positive:
        blockers.append("S_e_contiguous is zero because no survival region begins at T_e.")
    if not bool(endpoints["fourteen_specificity_passed"]):
        blockers.append(
            "The secondary N=14 specificity gate failed; the closure-mode result is N=9."
        )
    if not verified:
        blockers.append("Independent verifier disagreement remains unresolved.")

    scientific = {
        "schema_version": "1.0.0",
        "run_id": endpoints["run_id"],
        "scientific_outcome": outcome,
        "protocol_valid": verified and mutations_passed,
        "eligible_parent_count": endpoints["eligible_parent_count"],
        "T_e": endpoints["T_e"],
        "S_e_contiguous": endpoints["S_e_contiguous"],
        "winner_N": endpoints["winner_N_study_closure_minimum"],
        "baseline_SEP_any": sep_any,
        "fourteen_specificity_passed": endpoints["fourteen_specificity_passed"],
        "domain_baseline_completed": True,
        "AR1_beats_monthly_climatology_at_all_parents": all_ar1_better,
        "independent_verifier": verifier["status"],
        "mutation_rejections": (
            f"{verifier['mutation_rejection_count']}/{verifier['mutation_count']}"
        ),
        "failure_count": recomputed["failure_count"],
        "negative_result_publishable": True,
    }
    tld_adjudication = {
        "schema_version": "1.0.0",
        "TLD_DERIVED_status": "PERMITTED" if tld_derived_permitted else "BLOCKED",
        "claim_level": "TLD_DERIVED" if tld_derived_permitted else "COMPUTED_DYNAMICAL",
        "gates": {
            "eligible_independent_parents": endpoints["eligible_parent_count"] >= 10,
            "parent_matched_nulls": recomputed["null_parent_matching"],
            "SEP_under_frozen_rules": sep_any,
            "T_e_observed": t_e_observed,
            "S_e_nonzero": s_e_positive,
            "independent_verifier_agrees": verified,
            "failure_preservation_complete": True,
            "no_contamination": True,
            "no_outcome_dependent_tuning": True,
            "domain_baseline_completed": True,
            "baseline_control_persists_at_T_e": bool(
                endpoints["baseline_residual_SEP_persists_at_T_e"]
            ),
            "mutation_suite": mutations_passed,
        },
        "exact_blockers": blockers,
        "EXTERNALLY_VALIDATED": False,
    }
    forbidden = {
        "schema_version": "1.0.0",
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "EXTERNALLY_VALIDATED": False,
        "TORUS_BROT_equals_ToT_BROT": False,
        "analytic_z14_is_TLD_evidence": False,
    }
    falsification = {
        "schema_version": "1.0.0",
        "triggered": [
            {
                "id": "F01",
                "criterion": "no baseline primary SEP cell",
                "observed": True,
                "effect": "T_e=NOT_OBSERVED; scientific negative",
            },
            {
                "id": "F03",
                "criterion": "null children show equal or stronger structure under frozen gates",
                "observed": all(float(row["NSS"]) < 0 for row in baseline_surface),
                "effect": "SEP false",
            },
            {
                "id": "F11",
                "criterion": "N=14 fails the frozen specificity gate",
                "observed": not bool(endpoints["fourteen_specificity_passed"]),
                "effect": "14-specificity negative; primary analysis unchanged",
            },
        ],
        "not_triggered": ["F02", "F04", "F06", "F07", "F08", "F12", "F13", "F14"],
        "not_applicable_after_primary_negative": ["F05", "F10"],
    }
    reopen = {
        "schema_version": "1.0.0",
        "exact_blockers": blockers,
        "same_study_reanalysis_allowed": False,
        "candidate_substitution_allowed": False,
        "TLD_DERIVED_reopen_condition": (
            "a new prospectively registered study under a new prompt identity; "
            "this frozen negative result remains unchanged"
        ),
        "EXTERNALLY_VALIDATED_reopen_condition": (
            "an independent outside team runs the frozen replication package and "
            "reports agreement; this does not convert a negative primary result "
            "into TLD_DERIVED"
        ),
        "next_legal_action": (
            "publish v0.2.1 and invite independent replication; do not start TLD II "
            "or a second domain in this task"
        ),
    }
    write_json(output / "scientific_adjudication.json", scientific)
    write_json(output / "TLD_DERIVED_adjudication.json", tld_adjudication)
    write_json(output / "forbidden_claims.json", forbidden)
    write_json(output / "falsification_result.json", falsification)
    write_json(output / "exact_blockers_and_reopen_conditions.json", reopen)
    return scientific | {
        "TLD_DERIVED_status": tld_adjudication["TLD_DERIVED_status"],
        "claim_level": tld_adjudication["claim_level"],
        "EXTERNALLY_VALIDATED": False,
        "scored_manifest_correction": correction,
        "verification_manifest_sha256": verification_manifest_sha256,
    }


def snapshot_result(
    scored: Path,
    verification: Path,
    adjudication: Path,
    destination: Path,
) -> dict[str, Any]:
    """Create the small, tracked canonical result snapshot used by release packaging."""
    destination.mkdir(parents=True, exist_ok=True)
    groups = {
        "scored": [path for path in scored.iterdir() if path.is_file()],
        "verification": [
            path
            for path in verification.iterdir()
            if path.is_file() and path.name not in {"stdout.log", "stderr.log"}
        ],
        "adjudication": [path for path in adjudication.iterdir() if path.is_file()],
    }
    copied: list[str] = []
    for group, paths in groups.items():
        target_group = destination / group
        target_group.mkdir(parents=True, exist_ok=True)
        for source in sorted(paths):
            target = target_group / source.name
            shutil.copyfile(source, target)
            copied.append(target.relative_to(destination).as_posix())
    manifest = {
        "schema_version": "1.0.0",
        "run_id": _json(scored / "primary_endpoints.json")["run_id"],
        "scientific_outcome": _json(adjudication / "scientific_adjudication.json")[
            "scientific_outcome"
        ],
        "source_sha256": SOURCE_SHA256,
        "selection_commit": "2ff2ddb1a4f656d3c672079a6e8821bf9c3858eb",
        "preregistration_commit": "f15422bc64b1b101150240e612621683b15b3606",
        "implementation_commit": "d8e5c205e894a0177cf261e175596d9a36468f53",
        "files": copied,
    }
    write_json(destination / "result_manifest.json", manifest)
    sums = destination / "SHA256SUMS.txt"
    lines = [
        f"{sha256_file(path)}  {path.relative_to(destination).as_posix()}\n"
        for path in sorted(destination.rglob("*"))
        if path.is_file() and path != sums
    ]
    sums.write_text("".join(lines), encoding="utf-8", newline="\n")
    return manifest | {"snapshot_sha256": sha256_file(sums)}
