from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from torusbrot.adapters.zenodo_tld_i import extract_tld_i, validate_release_source
from torusbrot.models import canonical_json
from torusbrot.tld.reproduce import reproduce_tld_i
from torusbrot.tld.verification import verify_historical_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a raw cross-platform TLD I summary")
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = Path(args.source)
    with tempfile.TemporaryDirectory(prefix="tld-ci-source-") as temporary:
        if source.is_file():
            root = extract_tld_i(source, Path(temporary) / "release")
        else:
            root = Path(str(validate_release_source(source)["release_root"]))
        result = reproduce_tld_i(root)
    verification = verify_historical_result(result)
    summary = {
        "contract_sha256": result["contract"]["sha256"],
        "input_hashes": result["input_hashes"],
        "baseline": result["baseline"],
        "core": result["notebook13"]["core"],
        "alpha_sweep": result["notebook13"]["alpha_sweep"],
        "preregistration": result["notebook13"]["preregistration"],
        "trace_summary": result["notebook14"]["trace_summary"],
        "transition_counts": result["notebook14"]["transition_counts"],
        "operating_envelope": result["notebook14"]["operating_envelope"],
        "verification_checks": verification["checks"],
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_json(summary, pretty=True))
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
