from __future__ import annotations

import json
from pathlib import Path

from torusbrot.audit import audit_bundle

ROOT = Path(__file__).resolve().parent


def load(path: str) -> dict[str, object]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(path)
    return value


def main() -> int:
    bundles = sorted((ROOT / "tbx").glob("*.tbx.zip"))
    if len(bundles) != 5:
        raise SystemExit("V030_TBX_INVENTORY_MISMATCH")
    for bundle in bundles:
        report = audit_bundle(bundle)
        if not report.valid:
            raise SystemExit(f"{bundle.name}: {report.errors}")
    claim = load("heldout/execution/claim_adjudication.json")
    raw = load("heldout/raw_verification/independent_raw_recomputation.json")
    attempt = load("heldout/execution/execution_attempt.json")
    if claim.get("scientific_outcome") != (
        "GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY"
    ):
        raise SystemExit("V030_OUTCOME_MISMATCH")
    if claim.get("TLD_DERIVED") != "BLOCKED" or claim.get("EXTERNALLY_VALIDATED") is not False:
        raise SystemExit("V030_CLAIM_BOUNDARY_MISMATCH")
    if any(
        not str(claim.get(name, "")).startswith("NOT_APPLICABLE")
        for name in ("T_e", "S_e", "winner_N")
    ):
        raise SystemExit("V030_ENDPOINT_FIREWALL_MISMATCH")
    if raw.get("status") != "PASS" or raw.get("disagreement_count") != 0:
        raise SystemExit("V030_RAW_VERIFICATION_MISMATCH")
    if raw.get("new_scored_execution") is not False or raw.get("scored_execution_count") != 1:
        raise SystemExit("V030_EXECUTION_COUNT_MISMATCH")
    if attempt.get("attempt_number") != 1 or attempt.get("permitted_attempts") != 1:
        raise SystemExit("V030_EXECUTION_ATTEMPT_MISMATCH")
    print("v0.3.0 package verified: five TBXs, one scored execution, zero raw disagreements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
