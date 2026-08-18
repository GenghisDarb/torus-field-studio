from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from torusbrot.audit import audit_bundle

SOURCE_SHA256 = "d1b9261c54132f04c374f762f1e5e512af19f95c95fd6bfa1e8ac7e927e3b0b8"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify an outside held-out-study attempt")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    package = Path(__file__).resolve().parent
    inventory = load_json(package / "expected_artifact_inventory.json")
    errors: list[str] = []

    if sha256_file(args.source) != SOURCE_SHA256:
        errors.append("SOURCE_SHA256_MISMATCH")
    for line in (package / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        if sha256_file(package / relative) != expected:
            errors.append(f"REPLICATION_PACKAGE_HASH_MISMATCH:{relative}")
    for relative in inventory["required_files"]:
        if not (output / relative).is_file():
            errors.append(f"EXPECTED_ARTIFACT_MISSING:{relative}")

    verifier_path = output / "verification/independent_verification.json"
    adjudication_path = output / "adjudication/TLD_DERIVED_adjudication.json"
    scientific_path = output / "adjudication/scientific_adjudication.json"
    verifier = load_json(verifier_path) if verifier_path.is_file() else {}
    adjudication = load_json(adjudication_path) if adjudication_path.is_file() else {}
    scientific = load_json(scientific_path) if scientific_path.is_file() else {}
    if verifier.get("status") != "verified" or verifier.get("disagreement_count") != 0:
        errors.append("INDEPENDENT_VERIFIER_DISAGREEMENT")
    if verifier.get("mutation_count") != 25 or verifier.get("mutation_rejection_count") != 25:
        errors.append("MUTATION_REJECTION_INCOMPLETE")
    if adjudication.get("EXTERNALLY_VALIDATED") is not False:
        errors.append("EXTERNAL_VALIDATION_SELF_ASSERTED")

    audits: dict[str, dict[str, Any]] = {}
    bundle_dir = output / "bundles"
    for name in (
        "heldout-tld-study-primary.tbx.zip",
        "heldout-tld-study-specificity-audit.tbx.zip",
        "heldout-tld-study-combined.tbx.zip",
    ):
        path = bundle_dir / name
        if path.is_file():
            result = audit_bundle(path)
            audits[name] = {
                "valid": result.valid,
                "issue_codes": list(result.issue_codes),
                "sha256": sha256_file(path),
            }
            if not result.valid:
                errors.append(f"TBX_AUDIT_FAILED:{name}")

    report = {
        "schema_version": "1.0.0",
        "verification_status": "verified" if not errors else "failed",
        "errors": errors,
        "source_sha256": sha256_file(args.source),
        "run_id": scientific.get("run_id"),
        "observed_scientific_outcome": scientific.get("scientific_outcome"),
        "observed_TLD_DERIVED_status": adjudication.get("TLD_DERIVED_status"),
        "EXTERNALLY_VALIDATED": False,
        "independent_verifier": {
            "status": verifier.get("status"),
            "disagreement_count": verifier.get("disagreement_count"),
            "mutation_rejections": (
                f"{verifier.get('mutation_rejection_count')}/{verifier.get('mutation_count')}"
            ),
        },
        "tbx_audits": audits,
    }
    target = output / "replication-verification-report.json"
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
