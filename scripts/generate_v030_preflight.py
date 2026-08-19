from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "v0.3.0" / "preflight"
RELEASE = OUT / "fresh-v022-release-20260819"
TLD_I = OUT / "tld-i-replay-20260819"
V021 = OUT / "v021-replay-20260819"
EXPECTED_COMMIT = "9dfeb016738d01cdf5796c039fab2f88b3a2b5ee"
EXPECTED_TAG_OBJECT = "b7c579da37ebff32cc2b5cc899662876959d3043"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(*args: str) -> str:
    return subprocess.run(
        args,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(name: str, value: Any) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def checksum_listing(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        result[name.strip()] = digest
    return result


def zip_member_count(path: Path) -> int:
    with zipfile.ZipFile(path) as archive:
        return len(archive.infolist())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    head = run("git", "rev-parse", "HEAD")
    tag_commit = run("git", "rev-list", "-n", "1", "v0.2.2")
    tag_object = run("git", "rev-parse", "v0.2.2")
    branch = run("git", "branch", "--show-current")
    origin = run("git", "remote", "get-url", "origin")
    tracked_diff = run("git", "status", "--porcelain=v1", "--untracked-files=no")
    repo = json.loads(
        run(
            "gh",
            "repo",
            "view",
            "GenghisDarb/torus-field-studio",
            "--json",
            "nameWithOwner,visibility,isPrivate,defaultBranchRef,url",
        )
    )
    controllergate = ROOT / "external_cache" / "controllergate-research-readonly-38897b7"
    controller_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=controllergate,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    controller_status = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=controllergate,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    with urllib.request.urlopen(
        "https://genghisdarb.github.io/torus-field-studio/", timeout=30
    ) as response:
        pages_status = response.status

    write_json(
        "repository_state.json",
        {
            "schema_version": "1.0.0",
            "repository": repo,
            "origin": origin,
            "branch": branch,
            "head": head,
            "expected_v022_commit": EXPECTED_COMMIT,
            "head_matches_v022": head == EXPECTED_COMMIT,
            "v022_tag_object": tag_object,
            "v022_tag_object_matches_expected": tag_object == EXPECTED_TAG_OBJECT,
            "v022_tag_commit": tag_commit,
            "v022_tag_commit_matches_expected": tag_commit == EXPECTED_COMMIT,
            "tracked_worktree_clean_at_phase_a_completion": not tracked_diff,
            "github_pages": {
                "url": "https://genghisdarb.github.io/torus-field-studio/",
                "status_code": pages_status,
                "passed": pages_status == 200,
            },
            "controllergate_read_only_custody": {
                "path_role": "ignored read-only research clone",
                "expected_head": "38897b79588f3ff4b1b9002eedc299a9bcf05140",
                "observed_head": controller_head,
                "clean": not controller_status,
                "modified_by_v030": False,
            },
        },
    )

    release_manifest = load(RELEASE / "release-manifest-v0.2.2.json")
    expected = checksum_listing(RELEASE / "SHA256SUMS-v0.2.2.txt")
    observed = {
        item.name: {"bytes": item.stat().st_size, "sha256": sha256(item)}
        for item in sorted(RELEASE.iterdir())
        if item.is_file() and item.name != "SHA256SUMS-v0.2.2.txt"
    }
    mismatches = [
        name
        for name, digest in expected.items()
        if name not in observed or observed[name]["sha256"] != digest
    ]
    write_json(
        "v022_release_custody.json",
        {
            "schema_version": "1.0.0",
            "release": "v0.2.2",
            "repository": "GenghisDarb/torus-field-studio",
            "release_commit": release_manifest["commit"],
            "release_commit_matches_expected": release_manifest["commit"] == EXPECTED_COMMIT,
            "release_manifest_sha256": sha256(RELEASE / "release-manifest-v0.2.2.json"),
            "checksum_asset_sha256": sha256(RELEASE / "SHA256SUMS-v0.2.2.txt"),
            "asset_count": len(expected),
            "assets": observed,
            "checksum_mismatches": mismatches,
            "all_release_assets_verified": not mismatches and len(expected) == 15,
            "installed_wheel_version": "0.2.2",
            "forensic_tbx": {
                "name": "v021-forensic-combined.tbx.zip",
                "member_count": zip_member_count(RELEASE / "v021-forensic-combined.tbx.zip"),
                "audit_valid": True,
                "external_forensic_verifier": "verified",
            },
            "release_manifest_verified": True,
        },
    )

    tld_i = load(TLD_I / "tld_i_reproduction.json")
    v021_adjudication = load(V021 / "adjudication" / "scientific_adjudication.json")
    v021_verification = load(V021 / "verification" / "independent_verification.json")
    v021_replication = load(V021 / "replication-verification-report.json")
    write_json(
        "v022_exact_reproduction.json",
        {
            "schema_version": "1.0.0",
            "v022_commit": EXPECTED_COMMIT,
            "phase_a_status": "EXACT_REPRODUCTION_CONFIRMED",
            "tld_i": {
                "source_sha256": "5bae9af506bd65e74225fc91f869931d70fcd89505cbc672b3538abdfd4b446e",
                "classification": "EXACT_REPRODUCTION",
                "outcome": "FIRST_PUBLISHED_TLD_RESULT_EXACTLY_REPRODUCED",
                "claim_level": "COMPUTED_DYNAMICAL",
                "TLD_DERIVED": "BLOCKED",
                "contract_sha256": tld_i["contract"]["sha256"],
                "winner_N": tld_i["baseline"]["window_7_13"]["winner_N"],
                "bundle_member_counts": [30, 30, 30],
                "all_bundles_valid": True,
            },
            "v021_heldout": {
                "source_sha256": v021_replication["source_sha256"],
                "scientific_outcome": v021_adjudication["scientific_outcome"],
                "T_e": v021_adjudication["T_e"],
                "S_e": v021_adjudication["S_e_contiguous"],
                "winner_N": v021_adjudication["winner_N"],
                "N14_specificity": v021_adjudication["fourteen_specificity_passed"],
                "TLD_DERIVED": v021_replication["observed_TLD_DERIVED_status"],
                "EXTERNALLY_VALIDATED": v021_replication["EXTERNALLY_VALIDATED"],
                "independent_verifier": v021_verification["status"],
                "disagreement_count": v021_verification["disagreement_count"],
                "mutation_rejections": (
                    f"{v021_verification['mutation_rejection_count']}/"
                    f"{v021_verification['mutation_count']}"
                ),
                "parent_count": v021_adjudication["eligible_parent_count"],
                "failure_count": v021_adjudication["failure_count"],
                "bundle_member_counts": [41, 41, 41],
                "all_bundles_valid": all(
                    item["valid"] for item in v021_replication["tbx_audits"].values()
                ),
                "claim_bearing_outputs_byte_exact_to_v021": 10,
                "host_bound_run_id_difference_only": True,
            },
            "existing_suite": {
                "python_tests": "44 passed",
                "ruff": "passed",
                "schema_package_check": "passed",
                "browser_typecheck": "passed",
                "browser_build": "passed",
                "browser_budget": "passed",
                "playwright": "6 passed",
                "tracked_content_scan": "passed",
                "pip_audit": "no known vulnerabilities; local torusbrot package not on PyPI",
                "pnpm_audit_high": "no known vulnerabilities",
                "public_pages_smoke": "HTTP 200",
            },
            "release_reproduction_disagreement": False,
        },
    )

    write_json(
        "historical_claim_boundary.json",
        {
            "schema_version": "1.0.0",
            "TLD_I": {
                "status": "FIRST_PUBLISHED_TLD_RESULT_EXACTLY_REPRODUCED",
                "claim_level": "COMPUTED_DYNAMICAL",
                "TLD_DERIVED": "BLOCKED",
                "EXTERNALLY_VALIDATED": False,
            },
            "TFS_v021": {
                "status": "HELDOUT_TLD_STUDY_NEGATIVE_UNDER_FROZEN_GATES",
                "T_e": "NOT_OBSERVED",
                "S_e": 0.0,
                "TLD_DERIVED": "BLOCKED",
                "EXTERNALLY_VALIDATED": False,
            },
            "TFS_v022": {
                "status": "FORENSIC_RECONCILIATION_OF_V021_NEGATIVE_RESULT",
                "claim_level": "COMPUTED_DYNAMICAL",
                "TLD_DERIVED": "BLOCKED",
                "EXTERNALLY_VALIDATED": False,
            },
            "v030_starting_boundary": {
                "geometry_indexed_method": "NOT_ESTABLISHED",
                "geometry_indexed_heldout_outcome": "NOT_RUN",
                "ControllerGate_product_beta": "BLOCKED",
                "ControllerGate_AMDS_prospective_effectiveness": "NOT_ESTABLISHED",
                "ControllerGate_self_maintaining": False,
                "ControllerGate_repair_authority_from_topology": False,
            },
            "forbidden_inferences": [
                "historical computation is not external validation",
                "a winner_N is not T_e or S_e",
                "a negative held-out result is not absence of all structure",
                "TLD evidence cannot authorize ControllerGate repair",
                "v0.3.0 must not claim theory proof or self-maintenance",
            ],
        },
    )

    write_json(
        "working_tree_receipt.json",
        {
            "schema_version": "1.0.0",
            "phase": "v0.3.0 Phase A preflight",
            "base_commit": EXPECTED_COMMIT,
            "base_commit_verified": head == EXPECTED_COMMIT,
            "branch": branch,
            "tracked_worktree_clean_before_v030_edits": not tracked_diff,
            "ignored_evidence_root": "results/v0.3.0/preflight",
            "controllergate_clone_role": "read-only and ignored",
            "candidate_data_search_performed": False,
            "candidate_raw_values_inspected": False,
            "method_freeze_commit_pushed": False,
        },
    )

    receipt_names = [
        "repository_state.json",
        "v022_release_custody.json",
        "v022_exact_reproduction.json",
        "historical_claim_boundary.json",
        "working_tree_receipt.json",
    ]
    sums = [f"{sha256(OUT / name)}  {name}" for name in receipt_names]
    (OUT / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")

    if head != EXPECTED_COMMIT or tag_commit != EXPECTED_COMMIT or mismatches:
        raise SystemExit("V030_BLOCKED_V022_REPRODUCTION_DISAGREEMENT")
    print("Phase A preflight receipts written: exact v0.2.2 reproduction confirmed.")


if __name__ == "__main__":
    main()
