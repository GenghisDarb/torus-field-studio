from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies" / "v0.3.0-method-freeze"
FILES = (
    "method_candidate_registry.json",
    "method_selection_loss.json",
    "calibration_preregistration.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    lines = [f"{sha256(STUDY / name)}  {name}" for name in FILES]
    (STUDY / "calibration_preregistration_SHA256SUMS.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("Frozen geometry calibration preregistration checksums.")


if __name__ == "__main__":
    main()
