from __future__ import annotations

import argparse
import hashlib
import json
import warnings
import zipfile
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from torusbrot import DomainPack, LocalBrotRun
from torusbrot.models import GridSpec, canonical_json

ROOT = Path(__file__).parents[1]


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {
            info.filename: archive.read(info) for info in archive.infolist() if not info.is_dir()
        }


def write_entries(path: Path, entries: list[tuple[str, bytes]]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in entries:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload)


def rebuild(members: dict[str, bytes], manifest: dict) -> list[tuple[str, bytes]]:
    members = {name: payload for name, payload in members.items() if name != "manifest.json"}
    sums = "".join(
        f"{sha256(payload)}  {name}\n"
        for name, payload in sorted(members.items())
        if name != "audit/SHA256SUMS.txt"
    )
    members["audit/SHA256SUMS.txt"] = sums.encode()
    manifest["files"] = [
        {"path": name, "sha256": sha256(payload), "bytes": len(payload)}
        for name, payload in sorted(members.items())
    ]
    return [("manifest.json", canonical_json(manifest, pretty=True)), *sorted(members.items())]


def semantic_case(
    base: dict[str, bytes],
    mutation: Callable[[dict[str, bytes], dict], None],
) -> list[tuple[str, bytes]]:
    members = dict(base)
    manifest = json.loads(members.pop("manifest.json"))
    mutation(members, manifest)
    return rebuild(members, manifest)


def generate_corpus(output: Path) -> dict[str, str]:
    output.mkdir(parents=True, exist_ok=True)
    domain = DomainPack.load(ROOT / "examples/tld-parent-null/domain.json")
    run = LocalBrotRun.from_file(ROOT / "examples/tld-parent-null/run-spec.json")
    run.specification = replace(run.specification, grid=GridSpec(width=8, height=6))
    valid_path = output / "valid-reference.tbx.zip"
    run.execute(domain).export_tbx(valid_path)
    base = read_members(valid_path)
    expectations: dict[str, str] = {valid_path.name: "VALID"}

    unlisted = [*base.items(), ("extra.txt", b"unmanifested")]
    write_entries(output / "unlisted-member.tbx.zip", unlisted)
    expectations["unlisted-member.tbx.zip"] = "MANIFEST_UNLISTED_MEMBER"

    traversal = [*base.items(), ("../escape.txt", b"blocked")]
    write_entries(output / "path-traversal.tbx.zip", traversal)
    expectations["path-traversal.tbx.zip"] = "ARCHIVE_PATH_INVALID"

    duplicate = list(base.items()) + [("run_spec.json", base["run_spec.json"])]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        write_entries(output / "duplicate-member.tbx.zip", duplicate)
    expectations["duplicate-member.tbx.zip"] = "ARCHIVE_DUPLICATE_MEMBER"

    def forge_verifier(members: dict[str, bytes], _manifest: dict) -> None:
        claim = json.loads(members["claim_boundary.json"])
        claim["independent_verifier_status"] = "independently_verified"
        members["claim_boundary.json"] = canonical_json(claim, pretty=True)

    def remove_point(members: dict[str, bytes], _manifest: dict) -> None:
        table = json.loads(members["tables/field_points.json"])
        table["points"].pop()
        members["tables/field_points.json"] = canonical_json(table)

    def change_run_id(_members: dict[str, bytes], manifest: dict) -> None:
        manifest["run_id"] = "run-forged0000000"

    def add_nonfinite(members: dict[str, bytes], _manifest: dict) -> None:
        table = json.loads(members["tables/field_points.json"])
        table["points"][0]["NSS"] = "__NONFINITE__"
        payload = (json.dumps(table, sort_keys=True, separators=(",", ":")) + "\n").encode()
        members["tables/field_points.json"] = payload.replace(b'"__NONFINITE__"', b"1e999")

    semantic_cases = {
        "forged-verifier.tbx.zip": (forge_verifier, "VERIFIER_RECEIPT_MISSING"),
        "grid-count.tbx.zip": (remove_point, "GRID_POINT_COUNT_MISMATCH"),
        "run-id.tbx.zip": (change_run_id, "RUN_ID_MISMATCH"),
        "nonfinite-metric.tbx.zip": (add_nonfinite, "JSON_NONFINITE"),
    }
    for name, (mutation, expected) in semantic_cases.items():
        write_entries(output / name, semantic_case(base, mutation))
        expectations[name] = expected
    (output / "expectations.json").write_bytes(canonical_json(expectations, pretty=True))
    return expectations


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate hostile TBX interoperability fixtures")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    expectations = generate_corpus(args.output)
    print(f"Generated {len(expectations)} fixtures in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
