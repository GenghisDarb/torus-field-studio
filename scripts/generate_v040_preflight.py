#!/usr/bin/env python3
"""Write the immutable v0.3.0 custody receipts required by the v0.4.0 study.

This script records observations from the fresh release download and clean-room
consumer environments created on 2026-08-21.  It deliberately does not execute
the held-out scorer and cannot create a second scored execution.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "studies" / "v0.4.0" / "preflight"

STARTING_MAIN = "abe12e1da964c8902978ac7460028975f1f0324d"
TAG_OBJECT = "c86ad35049dac249824b52deab8ffc041a084646"
PR_HEAD = "a572681c868f2df68ed938586ef0e79ac2d9d1db"

ASSETS = [
    (
        "controllergate-read-only-transfer-v0.3.0.zip",
        4171,
        "72f2418fa41617c7e41bad6996ab8fdffd3236506c04442139371c995c888e52",
    ),
    (
        "geometry-method-v2-combined-v0.3.0.tbx.zip",
        2348284,
        "09a2015f87a91013efca575014d4ea364bb9019038d94606938423e75ba9538b",
    ),
    (
        "geometry-method-v2-specification.md",
        3878,
        "2443f28dfdb9faf5ef47eabcc062514533f15f7bc095ea41e63888b685c9903e",
    ),
    (
        "heldout-fluidic-pinball-v0.3.0.tbx.zip",
        2336898,
        "11b1808584331829ff490db38c1294d4fdc0c616b71feb2a7e5fb0ae19d46c5d",
    ),
    (
        "method-calibration-v2.tbx.zip",
        76833,
        "5328c905614506c22828038e670d40bcd5135bede1f11e4f8256a6b4369d3200",
    ),
    (
        "method-v2-calibration-v0.3.0.zip",
        63104,
        "62687cc6a6e126729b98d2992ddc3c211f98c78842dbb30f3bcaecc37e733e97",
    ),
    (
        "release-manifest-v0.3.0.json",
        3364,
        "4e09ce551951ea2d8cdb1e9c5757c7063bb04b4a8058455ee70da3d0aed9f58e",
    ),
    (
        "representation-equivariance-v2.tbx.zip",
        14521,
        "22e141dcd757dd250355c3196573179cd8c16606bfc28b899970b220dbff38bb",
    ),
    (
        "sbom-v0.3.0.spdx.json",
        288890,
        "0e0bd73fa315d1d8107309ba334200c0852c5e94217a13d3773dd02388e49031",
    ),
    (
        "SHA256SUMS-v0.3.0.txt",
        1588,
        "87c15962e5f2c11ea3a738d582b57d88aef4243eac71854d9f7842918ed63b4d",
    ),
    (
        "torusbrot-0.3.0.tar.gz",
        171807,
        "50b3d53bbc6bebe6cb9f43542fdb3335cdc555b057a16df42b2d33e4a3dea293",
    ),
    (
        "torusbrot-0.3.0-py3-none-any.whl",
        176383,
        "644c03617d0b7e9a84cdbf7631a3d8b618db40f4bdf347efbb3ab80bd1531ad2",
    ),
    (
        "v0.3.0-plain-language-report.md",
        1511,
        "56d83cdff1ffe18f40d9b91fc9556e261ff94e53372873b04b770aaa1a6316eb",
    ),
    (
        "v0.3.0-replication-package.zip",
        5770215,
        "ba24bc514cbca961c9532ba3891966f964a04d8e9e42d0dec8a988d2faf1868f",
    ),
    (
        "v0.3.0-technical-report.md",
        5163,
        "2fb5d1b32dbf1519769f53eee5d58b023efcfa700a4769b21cd5cbd93b29acb1",
    ),
    (
        "wind-farm-engineering-pilot-v0.3.0.zip",
        210877,
        "8be8feab13e1f3edf5646f8aece03043abef1e4def8610448777999c9e8358f4",
    ),
    (
        "wind-farm-pilot-v0.3.0.tbx.zip",
        203196,
        "e2be775fa9e77e1544d3202e64ed1282f4e695fbc27855b037b5159e7b549c84",
    ),
]


def write_json(name: str, value: object) -> None:
    (OUT / name).write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    common = {
        "schema_version": "tfs-v040-v030-custody-v1",
        "audit_date_utc": "2026-08-21",
        "evidence_kind": "fresh_download_and_independent_recomputation",
    }

    write_json(
        "v030_repository_state.json",
        {
            **common,
            "repository": "GenghisDarb/torus-field-studio",
            "repository_url": "https://github.com/GenghisDarb/torus-field-studio",
            "visibility": "PUBLIC",
            "default_branch": "main",
            "local_authoritative_path": str(ROOT),
            "starting_main": STARTING_MAIN,
            "origin_main": STARTING_MAIN,
            "v030_tag_object": TAG_OBJECT,
            "v030_tag_commit": STARTING_MAIN,
            "pr_5": {
                "state": "MERGED",
                "head": PR_HEAD,
                "merge_commit": STARTING_MAIN,
                "url": "https://github.com/GenghisDarb/torus-field-studio/pull/5",
            },
            "audit_branch": "agent/v0.4.0-phase-orientation-tld",
            "tracked_tree_clean_before_v040_writes": True,
            "ignored_runtime_outputs_only": True,
            "package_version": "0.3.0",
            "public_pages": "https://genghisdarb.github.io/torus-field-studio/",
        },
    )

    write_json(
        "v030_release_custody.json",
        {
            **common,
            "release_url": "https://github.com/GenghisDarb/torus-field-studio/releases/tag/v0.3.0",
            "published_at": "2026-08-20T17:25:38Z",
            "is_draft": False,
            "is_prerelease": False,
            "asset_count": len(ASSETS),
            "fresh_download_count": len(ASSETS),
            "github_digest_matches": len(ASSETS),
            "local_sha256_matches": len(ASSETS),
            "sha256sums_entries_verified": 16,
            "release_manifest": "PASS",
            "sbom": {"status": "PASS", "spdx_version": "SPDX-2.3"},
            "assets": [
                {
                    "name": name,
                    "size_bytes": size,
                    "sha256": digest,
                    "github_digest_match": True,
                    "fresh_local_digest_match": True,
                }
                for name, size, digest in ASSETS
            ],
        },
    )

    write_json(
        "v030_exact_reproduction.json",
        {
            **common,
            "status": "EXACT_WITHIN_FROZEN_NUMERICAL_TOLERANCE",
            "fresh_consumer_environments": {
                "wheel": {"install": "PASS", "reported_version": "0.3.0"},
                "sdist": {
                    "install": "PASS",
                    "reported_version": "0.3.0",
                    "member_count": 166,
                },
            },
            "tbx_audits": {
                "passed": 5,
                "failed": 0,
                "hashes": {
                    "geometry_combined": "09a2015f87a91013efca575014d4ea364bb9019038d94606938423e75ba9538b",
                    "heldout": "11b1808584331829ff490db38c1294d4fdc0c616b71feb2a7e5fb0ae19d46c5d",
                    "calibration": "5328c905614506c22828038e670d40bcd5135bede1f11e4f8256a6b4369d3200",
                    "representation": "22e141dcd757dd250355c3196573179cd8c16606bfc28b899970b220dbff38bb",
                    "wind_pilot": "e2be775fa9e77e1544d3202e64ed1282f4e695fbc27855b037b5159e7b549c84",
                },
            },
            "installed_wheel_replication": {
                "status": "PASS",
                "tbx_count": 5,
                "recorded_scored_executions": 1,
                "new_scored_executions": 0,
                "raw_disagreements": 0,
            },
            "independent_raw_hdf5_verifier": {
                "script": "scripts/verify_v030_pinball_raw.py",
                "production_result_tables_used_as_primary_evidence": False,
                "acquisitions_recomputed": 56,
                "unique_pairs": 28,
                "acquisition_local_null_children": 7112,
                "joint_replicates_per_channel": 999,
                "raw_disagreements": 0,
                "new_scored_execution": False,
                "claim_changed": False,
            },
            "tests": {
                "python": {"collected": 118, "passed": 118, "failed": 0},
                "browser_e2e": {"collected": 8, "passed": 8, "failed": 0},
            },
            "frozen_identities": {
                "method": "METHOD_V2_C_EVIDENCE_VECTOR",
                "public_name": "INSTRUMENTED_EVIDENCE_VECTOR",
                "method_freeze": "dcaeb72b29fc0d32b002d9b5de0809b13f2ed272",
                "candidate_freeze": "590f6ea5896d3813c3a0a673e108381a4e3d87da",
                "preregistration": "a8e3cba766bd8b160fc9b8074086a48fb7aceceb",
                "authorization": "77624c6cd56fbdbe3b83a240898884ad9ab67442",
                "single_scored_execution": "4edb89d724dae0aac8b4ed15e48018a8681dbfd0",
                "run_id": "pinball-heldout-e9e3d7666b2b10cb",
            },
        },
    )

    write_json(
        "v030_claim_boundary.json",
        {
            **common,
            "scientific_outcome": "GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY",
            "method_role": "measurement_instrument_not_universal_classifier",
            "TLD_DERIVED": "BLOCKED",
            "EXTERNALLY_VALIDATED": False,
            "TORUS_confirmation": "FORBIDDEN",
            "ToT_BROT": "FORBIDDEN",
            "binary_positive_negative_classification": "NOT_PERFORMED_AND_FORBIDDEN_BY_METHOD_V2_FREEZE",
            "endpoint_applicability": {
                "T_e": "NOT_APPLICABLE_NO_OPERATION_DEPTH_AXIS",
                "S_e": "NOT_APPLICABLE_NO_CALIBRATED_PERSISTENCE_ENDPOINT",
                "winner_N": "NOT_APPLICABLE_NO_CANONICAL_PATH_CLOSURE_AXIS",
            },
            "inferential_hierarchy": {
                "physical_systems": 1,
                "deposit_level_clusters": 1,
                "paired_acquisition_blocks": 28,
                "snapshots": "nested_within_acquisition",
                "spatial_cells": "nested_within_snapshot_and_acquisition",
                "campaign_independence": "UNKNOWN",
                "population_generalization_credit": False,
                "population_sign_test": False,
            },
        },
    )

    write_json(
        "v030_public_pages_reconciliation.json",
        {
            **common,
            "pages_url": "https://genghisdarb.github.io/torus-field-studio/",
            "downloaded_combined_tbx_sha256": "09a2015f87a91013efca575014d4ea364bb9019038d94606938423e75ba9538b",
            "release_combined_tbx_sha256": "09a2015f87a91013efca575014d4ea364bb9019038d94606938423e75ba9538b",
            "byte_identity": True,
            "tbx_audit": "PASS",
            "browser_smoke": "PASS",
            "browser_e2e": "8/8_PASS",
            "console_errors": 0,
        },
    )

    checksums = []
    for path in sorted(OUT.glob("*.json"), key=lambda item: item.name):
        checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (OUT / "SHA256SUMS.txt").write_text(
        "\n".join(checksums) + "\n", encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
