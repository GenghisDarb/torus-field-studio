from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from torusbrot.audit import audit_bundle


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, required=True)
    args = parser.parse_args()
    assets = args.assets.resolve()
    errors: list[str] = []
    for line in (assets / "SHA256SUMS-v0.2.2.txt").read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        path = assets / name
        if not path.is_file() or sha256(path) != expected:
            errors.append(f"ASSET_HASH_MISMATCH:{name}")
    bundle = assets / "v021-forensic-combined.tbx.zip"
    audit = audit_bundle(bundle)
    if not audit.valid:
        errors.extend(audit.errors)
    report = json.loads((assets / "v021-negative-result-forensic-report.json").read_text())
    if report.get("V021_PRIMARY_RESULT") != "HELDOUT_TLD_STUDY_NEGATIVE_UNDER_FROZEN_GATES":
        errors.append("V021_PRIMARY_RESULT_REWRITTEN")
    if report.get("TLD_DERIVED") != "BLOCKED":
        errors.append("CLAIM_LEVEL_ESCALATION")
    if report.get("EXTERNALLY_VALIDATED") is not False:
        errors.append("EXTERNAL_VALIDATION_FORGED")
    result = {"status": "verified" if not errors else "failed", "errors": errors}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
