from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies" / "v0.3.0-method-freeze"
EXPECTED_COMMIT = "827b3394c0ce8ed414ca57d8e77ef1aaf1a72b1c"
EXPECTED_SUBJECT = "Freeze geometry-indexed TLD method on synthetic and historical controls"


def run(*args: str) -> str:
    return subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> Any:
    return json.loads((STUDY / name).read_text(encoding="utf-8"))


def main() -> None:
    head = run("git", "rev-parse", "HEAD")
    subject = run("git", "show", "-s", "--format=%s", EXPECTED_COMMIT)
    remote_line = run(
        "git",
        "ls-remote",
        "origin",
        "refs/heads/agent/v0.3.0-geometry-indexed-tld",
    )
    remote_commit = remote_line.split()[0]
    if head != EXPECTED_COMMIT or remote_commit != EXPECTED_COMMIT or subject != EXPECTED_SUBJECT:
        raise SystemExit("Method-freeze local/remote custody mismatch")
    acceptance = load("method_acceptance_gate.json")
    source_lines = [
        line
        for line in (STUDY / "SHA256SUMS_SOURCE.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rejected = {
        method_id: method["blockers"]
        for method_id, method in acceptance["methods"].items()
        if not method["accepted"]
    }
    receipt = {
        "schema_version": "1.0.0",
        "branch": "agent/v0.3.0-geometry-indexed-tld",
        "method_freeze_commit": EXPECTED_COMMIT,
        "commit_subject": subject,
        "remote_origin_commit": remote_commit,
        "local_remote_match": True,
        "selected_method": acceptance["selected_method"],
        "rejected_methods_and_exact_blockers": rejected,
        "method_freeze_checksums_sha256": sha256(STUDY / "method_freeze_SHA256SUMS.txt"),
        "source_checksums_sha256": sha256(STUDY / "SHA256SUMS_SOURCE.txt"),
        "source_hash_count": len(source_lines),
        "independent_verification_sha256": sha256(STUDY / "independent_method_verification.json"),
        "independent_verification_status": load("independent_method_verification.json")["status"],
        "external_heldout_field_outcome_at_freeze": "ABSENT",
        "candidate_dataset_search_before_push": False,
        "candidate_raw_values_inspected_before_push": False,
        "metadata_only_candidate_discovery_now_authorized": True,
        "binary_TLD_field_classification_authorized": False,
    }
    (STUDY / "method_freeze_post_push_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Recorded pushed method freeze {EXPECTED_COMMIT}.")


if __name__ == "__main__":
    main()
