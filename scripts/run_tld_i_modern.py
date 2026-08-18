from __future__ import annotations

import argparse
import json
from pathlib import Path

from torusbrot.models import canonical_json
from torusbrot.schema_validation import validate_with_schema
from torusbrot.tld.modern import ModernTldIContract, execute_modern_extension


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the frozen TLD I modern compliance extension")
    parser.add_argument("--source", required=True)
    parser.add_argument("--historical-result", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    declared = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    expected = ModernTldIContract()
    if declared != expected.to_dict():
        raise ValueError("MODERN_CONTRACT_IDENTITY_MISMATCH")
    errors = validate_with_schema("tld-run-contract", declared)
    if errors:
        raise ValueError("MODERN_CONTRACT_SCHEMA_INVALID: " + "; ".join(errors))
    historical = json.loads(Path(args.historical_result).read_text(encoding="utf-8"))
    result = execute_modern_extension(args.source, historical, expected)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_json(result, pretty=True))
    print(
        json.dumps(
            {
                "output": str(target),
                "claim_level": result["claim_level"],
                "TLD_DERIVED_STATUS": result["TLD_DERIVED_STATUS"],
                "blockers": result["blockers"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
