"""Preflight, quarantine, and inventory the public TORUS Ladder Dynamics I archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import shutil
import stat
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_DOI = "10.5281/zenodo.18080090"
EXPECTED_TITLE = (
    "TORUS Ladder Dynamics I: Structural Escape, Damped Healing, and Ringing Diagnostics"
)
EXPECTED_ARCHIVE = "TORUS_Zenodo_v1.zip"
EXPECTED_MD5 = "25f26f78bf6c73df1e551983af518e9a"
MAX_MEMBERS = 1_000
MAX_MEMBER_BYTES = 100 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024
MAX_COMPRESSION_RATIO = 1_000.0


def digest(path: Path, algorithm: str = "sha256") -> str:
    result = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def digest_bytes(data: bytes, algorithm: str = "sha256") -> str:
    return hashlib.new(algorithm, data).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def display_path(path: Path) -> str:
    resolved = path.resolve()
    repository = Path.cwd().resolve()
    if resolved.is_relative_to(repository):
        return f"<REPOSITORY>/{resolved.relative_to(repository).as_posix()}"
    user_home = Path.home().resolve()
    if resolved.is_relative_to(user_home):
        return f"<USER_HOME>/{resolved.relative_to(user_home).as_posix()}"
    return str(resolved)


def canonical_member(info: zipfile.ZipInfo) -> PurePosixPath:
    name = info.filename
    if not name or "\\" in name or "\x00" in name:
        raise ValueError(f"ARCHIVE_PATH_INVALID: {name!r}")
    if name.startswith(("/", "//")) or re.match(r"^[A-Za-z]:", name):
        raise ValueError(f"ARCHIVE_PATH_INVALID: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"ARCHIVE_PATH_INVALID: {name!r}")
    return path


def member_role(name: str) -> str:
    lowered = name.casefold()
    if lowered.endswith("/"):
        return "directory"
    if "/data_inputs/" in lowered:
        return "source_input"
    if "/data_outputs_notebook" in lowered:
        return "published_generated_output"
    if lowered.endswith(".ipynb"):
        return "confirmatory_notebook"
    if lowered.endswith("license.txt"):
        return "license"
    if lowered.endswith("citation.cff"):
        return "citation"
    if "/env/" in lowered:
        return "environment"
    if "/integrity/" in lowered:
        return "integrity"
    if "/docs/" in lowered:
        return "documentation"
    return "other"


def notebook_number(name: str) -> int | None:
    lowered = name.casefold()
    if not lowered.endswith(".ipynb"):
        return None
    match = re.search(r"(?:notebook\s*_?|notebook_)(13|14)\b", lowered)
    return int(match.group(1)) if match else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--quarantine", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--local-copy", action="append", type=Path, default=[])
    args = parser.parse_args()

    archive = args.archive.resolve(strict=True)
    record_path = args.record.resolve(strict=True)
    quarantine = args.quarantine.resolve()
    receipts = args.receipts.resolve()
    if quarantine.exists():
        raise RuntimeError(f"Fresh quarantine target already exists: {quarantine}")
    receipts.mkdir(parents=True, exist_ok=True)

    record = json.loads(record_path.read_text(encoding="utf-8"))
    if record.get("doi") != EXPECTED_DOI:
        raise RuntimeError(f"Zenodo DOI mismatch: {record.get('doi')}")
    if record.get("metadata", {}).get("title") != EXPECTED_TITLE:
        raise RuntimeError("Zenodo title mismatch")
    record_archive = next(
        (item for item in record.get("files", []) if item["key"] == EXPECTED_ARCHIVE), None
    )
    if not record_archive:
        raise RuntimeError(f"Zenodo record does not list {EXPECTED_ARCHIVE}")

    archive_md5 = digest(archive, "md5")
    archive_sha256 = digest(archive)
    if archive_md5 != EXPECTED_MD5 or record_archive.get("checksum") != f"md5:{EXPECTED_MD5}":
        raise RuntimeError(f"Zenodo archive MD5 mismatch: {archive_md5}")
    if archive.stat().st_size != record_archive.get("size"):
        raise RuntimeError("Zenodo archive byte-size mismatch")

    member_rows: list[dict[str, Any]] = []
    total_bytes = 0
    normalized_names: set[str] = set()
    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        if len(infos) > MAX_MEMBERS:
            raise RuntimeError("ARCHIVE_MEMBER_LIMIT")
        for info in infos:
            path = canonical_member(info)
            normalized = path.as_posix().rstrip("/").casefold()
            if normalized in normalized_names:
                raise RuntimeError(f"ARCHIVE_DUPLICATE_MEMBER: {info.filename}")
            normalized_names.add(normalized)
            if info.flag_bits & 0x1:
                raise RuntimeError(f"ARCHIVE_ENCRYPTED_MEMBER: {info.filename}")
            mode = info.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise RuntimeError(f"ARCHIVE_SPECIAL_MEMBER: {info.filename}")
            if info.file_size > MAX_MEMBER_BYTES:
                raise RuntimeError(f"ARCHIVE_MEMBER_SIZE_LIMIT: {info.filename}")
            total_bytes += info.file_size
            ratio = info.file_size / max(info.compress_size, 1)
            if ratio > MAX_COMPRESSION_RATIO:
                raise RuntimeError(f"ARCHIVE_COMPRESSION_RATIO_LIMIT: {info.filename}")
            member_rows.append(
                {
                    "path": path.as_posix(),
                    "bytes": info.file_size,
                    "compressed_bytes": info.compress_size,
                    "compression_ratio": ratio,
                    "zip_crc32": f"{info.CRC:08x}",
                    "role": member_role(info.filename),
                }
            )
        if total_bytes > MAX_TOTAL_BYTES:
            raise RuntimeError("ARCHIVE_TOTAL_SIZE_LIMIT")
        bad_member = bundle.testzip()
        if bad_member is not None:
            raise RuntimeError(f"ARCHIVE_CRC_FAILURE: {bad_member}")

        quarantine.mkdir(parents=True)
        root = quarantine.resolve()
        for info in infos:
            path = canonical_member(info)
            destination = root.joinpath(*path.parts).resolve()
            if not destination.is_relative_to(root):
                raise RuntimeError(f"ARCHIVE_PATH_INVALID: {info.filename}")
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, destination.open("xb") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)

    notebook_text: dict[int, str] = {}
    confirmatory_notebooks: dict[int, str] = {}
    for row in member_rows:
        number = notebook_number(row["path"])
        if number is None:
            continue
        notebook_path = quarantine.joinpath(*PurePosixPath(row["path"]).parts)
        notebook_text[number] = notebook_path.read_text(encoding="utf-8")
        confirmatory_notebooks[number] = row["path"]
    if set(confirmatory_notebooks) != {13, 14}:
        raise RuntimeError(
            f"Expected confirmatory notebooks 13 and 14, found {confirmatory_notebooks}"
        )

    for row in member_rows:
        path = quarantine.joinpath(*PurePosixPath(row["path"]).parts)
        if row["role"] == "directory":
            row.update(
                {
                    "md5": None,
                    "sha256": None,
                    "media_type": "inode/directory",
                    "used_by_notebook13": False,
                    "used_by_notebook14": False,
                    "generated_output": False,
                    "source_input": False,
                    "license_citation_relationship": "archive_container",
                }
            )
            continue
        basename = path.name
        row.update(
            {
                "md5": digest(path, "md5"),
                "sha256": digest(path),
                "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                "used_by_notebook13": basename in notebook_text[13]
                or "notebook13" in row["path"].casefold(),
                "used_by_notebook14": basename in notebook_text[14]
                or "notebook14" in row["path"].casefold(),
                "generated_output": row["role"] == "published_generated_output",
                "source_input": row["role"] == "source_input",
                "license_citation_relationship": (
                    "governing_license"
                    if row["role"] == "license"
                    else "preferred_citation"
                    if row["role"] == "citation"
                    else "covered_by_archive_license_and_citation"
                ),
            }
        )

    required_roles = {"license", "citation", "environment"}
    present_roles = {row["role"] for row in member_rows}
    if not required_roles.issubset(present_roles):
        raise RuntimeError(
            f"Archive lacks required custody metadata: {required_roles - present_roles}"
        )

    local_rows: list[dict[str, Any]] = []
    file_rows = [row for row in member_rows if row["sha256"]]
    by_basename: dict[str, list[dict[str, Any]]] = {}
    for row in file_rows:
        by_basename.setdefault(PurePosixPath(row["path"]).name.casefold(), []).append(row)
    for candidate in args.local_copy:
        resolved = candidate.resolve(strict=True)
        candidate_sha256 = digest(resolved)
        matches = by_basename.get(resolved.name.casefold(), [])
        exact = next((row for row in matches if row["sha256"] == candidate_sha256), None)
        classification = (
            "exact_duplicate" if exact else "modified_descendant" if matches else "unrelated"
        )
        local_rows.append(
            {
                "path": display_path(resolved),
                "bytes": resolved.stat().st_size,
                "md5": digest(resolved, "md5"),
                "sha256": candidate_sha256,
                "classification": classification,
                "matching_archive_member": exact["path"] if exact else None,
                "same_name_archive_members": [row["path"] for row in matches],
            }
        )

    record_receipt = {
        "record_id": record["id"],
        "doi": record["doi"],
        "title": record["metadata"]["title"],
        "publication_date": record["metadata"].get("publication_date"),
        "resource_type": record["metadata"].get("resource_type"),
        "license": record["metadata"].get("license"),
        "creators": record["metadata"].get("creators"),
        "record_url": record.get("links", {}).get("self_html"),
        "api_url": record.get("links", {}).get("self"),
        "files": [
            {"name": item["key"], "bytes": item["size"], "checksum": item["checksum"]}
            for item in record["files"]
        ],
        "retrieved_at": datetime.now(UTC).isoformat(),
        "raw_record_sha256": digest(record_path),
    }
    archive_identity = {
        "archive": EXPECTED_ARCHIVE,
        "bytes": archive.stat().st_size,
        "md5": archive_md5,
        "sha256": archive_sha256,
        "zenodo_md5_verified": True,
        "member_count": len(member_rows),
        "file_member_count": len(file_rows),
        "uncompressed_bytes": total_bytes,
        "preflight": {
            "passed": True,
            "canonical_relative_paths": True,
            "no_duplicate_members": True,
            "no_encrypted_members": True,
            "no_symlinks_or_devices": True,
            "crc_test_passed": True,
            "limits": {
                "max_members": MAX_MEMBERS,
                "max_member_bytes": MAX_MEMBER_BYTES,
                "max_total_bytes": MAX_TOTAL_BYTES,
                "max_compression_ratio": MAX_COMPRESSION_RATIO,
            },
        },
        "quarantine": display_path(quarantine),
    }
    output_names = {
        number: sorted(
            PurePosixPath(row["path"]).name
            for row in member_rows
            if row["role"] == "published_generated_output"
            and f"notebook{number}" in row["path"].casefold()
        )
        for number in (13, 14)
    }
    usage_plan = {
        "historical_lane": "HISTORICAL_PUBLISHED_RELEASE_REPRODUCTION",
        "confirmatory_notebooks": confirmatory_notebooks,
        "published_outputs": output_names,
        "source_inputs": sorted(row["path"] for row in member_rows if row["source_input"]),
        "execution_order": [confirmatory_notebooks[13], confirmatory_notebooks[14]],
        "notebook14_depends_on_notebook13_outputs": any(
            PurePosixPath(row["path"]).name in notebook_text[14]
            for row in member_rows
            if "data_outputs_notebook13" in row["path"]
        ),
        "exploratory_notebooks_1_through_12_used_as_evidence": False,
        "source_of_truth": "downloaded Zenodo record bytes",
        "vendoring_policy": (
            "archive remains ignored; commit only registry, hashes, fetch logic, and lawful small "
            "derived fixtures"
        ),
    }
    duplicate_audit = {
        "search_scope": [
            r"C:\Dev",
            r"C:\Users\<USER>\Documents",
            r"C:\Users\<USER>\Desktop",
            r"C:\Users\<USER>\Downloads",
            r"C:\Users\<USER>\OneDrive\Documents",
        ],
        "archive_copy_found": False,
        "notebook_copy_found": False,
        "candidate_count": len(local_rows),
        "candidates": local_rows,
        "public_download_is_source_of_truth": True,
    }

    write_json(receipts / "zenodo_record.json", record_receipt)
    write_json(receipts / "archive_identity.json", archive_identity)
    (receipts / "member_manifest.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in member_rows), encoding="utf-8"
    )
    write_json(receipts / "local_duplicate_audit.json", duplicate_audit)
    write_json(receipts / "source_usage_plan.json", usage_plan)

    checksum_lines = [f"{archive_sha256}  {EXPECTED_ARCHIVE}"]
    checksum_lines.append(f"{digest(record_path)}  zenodo_record_api.json")
    checksum_lines.extend(
        f"{row['sha256']}  quarantine/{row['path']}" for row in member_rows if row["sha256"]
    )
    (receipts / "SHA256SUMS_SOURCE.txt").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "archive_identity": archive_identity,
                "usage_plan": usage_plan,
                "duplicates": duplicate_audit,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
