from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".csv", ".json", ".jsonl", ".md", ".txt"}
METHOD = ROOT / "studies" / "v0.3.0-method-freeze"
MATERIALIZATION = ROOT / "studies" / "v0.3.0-field-assay" / "materialization"


def normalize(path: Path) -> None:
    raw = path.read_bytes()
    canonical = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    if canonical != raw:
        path.write_bytes(canonical)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_lf(path: Path, value: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(value)


def replace_hash(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old != new:
        if old not in text:
            raise SystemExit(f"Expected embedded hash not found in {path}: {old}")
        write_lf(path, text.replace(old, new))


def main() -> None:
    for directory in (
        ROOT / "studies" / "v0.3.0-source-audit",
        METHOD,
        ROOT / "studies" / "v0.3.0-field-selection",
        ROOT / "studies" / "v0.3.0-field-assay",
    ):
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                normalize(path)

    preregistration = METHOD / "calibration_preregistration.json"
    calibration = METHOD / "method_calibration_results.json"
    frozen_method = METHOD / "frozen_revised_method.json"
    verification = METHOD / "independent_method_verification.json"
    calibration_value = json.loads(calibration.read_text(encoding="utf-8"))
    old_preregistration_hash = calibration_value["preregistration_sha256"]
    new_preregistration_hash = sha256(preregistration)
    replace_hash(calibration, old_preregistration_hash, new_preregistration_hash)
    replace_hash(frozen_method, old_preregistration_hash, new_preregistration_hash)
    frozen_value = json.loads(frozen_method.read_text(encoding="utf-8"))
    old_verification_hash = frozen_value["independent_verification_sha256"]
    new_verification_hash = sha256(verification)
    replace_hash(frozen_method, old_verification_hash, new_verification_hash)

    method_names = [
        line.split(maxsplit=1)[1]
        for line in (METHOD / "method_freeze_SHA256SUMS.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    write_lf(
        METHOD / "method_freeze_SHA256SUMS.txt",
        "\n".join(f"{sha256(METHOD / name)}  {name}" for name in method_names) + "\n",
    )
    post_push = METHOD / "method_freeze_post_push_receipt.json"
    post_push_value = json.loads(post_push.read_text(encoding="utf-8"))
    post_push_value["independent_verification_sha256"] = new_verification_hash
    post_push_value["method_freeze_checksums_sha256"] = sha256(
        METHOD / "method_freeze_SHA256SUMS.txt"
    )
    post_push_value["source_checksums_sha256"] = sha256(METHOD / "SHA256SUMS_SOURCE.txt")
    write_lf(post_push, json.dumps(post_push_value, indent=2, sort_keys=True) + "\n")
    materialization_names = sorted(
        path.name
        for path in MATERIALIZATION.iterdir()
        if path.is_file() and path.name != "SHA256SUMS_INPUTS.txt"
    )
    write_lf(
        MATERIALIZATION / "SHA256SUMS_INPUTS.txt",
        "\n".join(
            f"{sha256(MATERIALIZATION / name)}  {name}"
            for name in materialization_names
        )
        + "\n",
    )


if __name__ == "__main__":
    main()
