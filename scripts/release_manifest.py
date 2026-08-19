from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(directory: Path, version: str, commit: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / f"release-manifest-{version}.json"
    sums_path = directory / f"SHA256SUMS-{version}.txt"
    excluded = {manifest_path.name, sums_path.name}
    assets = [
        path for path in sorted(directory.iterdir()) if path.is_file() and path.name not in excluded
    ]
    manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "release": version,
        "commit": commit,
        "scientific_outcome": "HELDOUT_TLD_STUDY_NEGATIVE_UNDER_FROZEN_GATES",
        "claim_level": "COMPUTED_DYNAMICAL",
        "TLD_DERIVED_status": "BLOCKED",
        "EXTERNALLY_VALIDATED": False,
        "assets": [
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in assets
        ],
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    sum_assets = assets + [manifest_path]
    sums_path.write_text(
        "".join(f"{sha256_file(path)}  {path.name}\n" for path in sorted(sum_assets)),
        encoding="utf-8",
        newline="\n",
    )
    return manifest_path


def verify_manifest(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    directory = path.parent
    if manifest.get("EXTERNALLY_VALIDATED") is not False:
        raise ValueError("release manifest may not self-assert external validation")
    if manifest.get("TLD_DERIVED_status") != "BLOCKED":
        raise ValueError("release manifest claim boundary mismatch")
    declared = {item["name"]: item for item in manifest.get("assets", [])}
    if len(declared) != len(manifest.get("assets", [])):
        raise ValueError("duplicate release asset declaration")
    for name, item in declared.items():
        candidate = directory / name
        if not candidate.is_file():
            raise ValueError(f"release asset missing: {name}")
        if candidate.stat().st_size != item["bytes"]:
            raise ValueError(f"release asset size mismatch: {name}")
        if sha256_file(candidate) != item["sha256"]:
            raise ValueError(f"release asset hash mismatch: {name}")
    sums = directory / f"SHA256SUMS-{manifest['release']}.txt"
    for line in sums.read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        if sha256_file(directory / name) != expected:
            raise ValueError(f"release checksum mismatch: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify a release manifest")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("directory", type=Path)
    build.add_argument("--version", required=True)
    build.add_argument("--commit", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("manifest", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        path = build_manifest(args.directory.resolve(), args.version, args.commit)
        verify_manifest(path)
        print(path)
    else:
        verify_manifest(args.manifest.resolve())
        print(f"verified: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
