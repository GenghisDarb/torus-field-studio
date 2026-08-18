from __future__ import annotations

import argparse
import json
from pathlib import Path

from torusbrot.models import canonical_json
from torusbrot.tld.bundle import FORBIDDEN_CLAIMS, HISTORICAL_LANE
from torusbrot.tld.modern import MODERN_LANE
from torusbrot.tld.verification import verify_historical_result


def write(path: Path, value) -> None:
    path.write_bytes(canonical_json(value, pretty=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="Write TLD I claim-boundary receipts")
    parser.add_argument("--historical-result", required=True)
    parser.add_argument("--modern-result", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    historical = json.loads(Path(args.historical_result).read_text(encoding="utf-8"))
    modern = json.loads(Path(args.modern_result).read_text(encoding="utf-8"))
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    historical_blockers = [
        "alpha=0.02 mean_return_steps exceeds the preregistered maximum",
        "alpha=0.02 p90_flips exceeds the preregistered maximum",
        "preregistration document says 400 healing steps; Notebook 13 executes 300",
        "T_e and S_e were not computed",
        "self-reproduction is not external validation",
    ]
    write(
        root / "historical_claim_adjudication.json",
        {
            "schema_version": "1.0.0",
            "lane": HISTORICAL_LANE,
            "reproduction_classification": "EXACT_REPRODUCTION",
            "high_level_outcome": "FIRST_PUBLISHED_TLD_RESULT_EXACTLY_REPRODUCED",
            "claim_level": "COMPUTED_DYNAMICAL",
            "TLD_DERIVED_STATUS": "BLOCKED",
            "externally_validated": False,
            "blockers": historical_blockers,
        },
    )
    write(
        root / "modern_claim_adjudication.json",
        {
            "schema_version": "1.0.0",
            "lane": MODERN_LANE,
            "claim_level": modern["claim_level"],
            "TLD_DERIVED_STATUS": modern["TLD_DERIVED_STATUS"],
            "externally_validated": False,
            "criteria": modern["criteria"],
            "endpoint_applicability": modern["endpoint_applicability"],
            "blockers": modern["blockers"],
        },
    )
    write(root / "forbidden_claims.json", {"forbidden_claims": FORBIDDEN_CLAIMS})
    receipt = verify_historical_result(historical)
    write(
        root / "claim_boundary_audit.json",
        {
            "schema_version": "1.0.0",
            "valid": receipt["status"] == "verified"
            and modern["TLD_DERIVED_STATUS"] == "BLOCKED"
            and modern["externally_validated"] is False,
            "independent_verifier": receipt,
            "historical_claim_ceiling": "COMPUTED_DYNAMICAL",
            "modern_claim_level": modern["claim_level"],
            "external_validation_forbidden": True,
            "forbidden_claims_present": len(FORBIDDEN_CLAIMS),
        },
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
