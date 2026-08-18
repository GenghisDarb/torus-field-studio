"""Custody-preserving adapter for Zenodo record 18080090."""

from __future__ import annotations

import hashlib
import json
import shutil
import stat
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from ..tld.contracts import TLD_I_ARCHIVE_MD5, TLD_I_ARCHIVE_SHA256, TLD_I_DOI

DOWNLOAD_URL = "https://zenodo.org/records/18080090/files/TORUS_Zenodo_v1.zip?download=1"
MAX_MEMBERS = 1000
MAX_MEMBER_BYTES = 100 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024
MAX_RATIO = 1000.0


def hash_file(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_tld_i(destination: str | Path) -> dict[str, Any]:
    target = Path(destination)
    if target.exists():
        raise ValueError(f"Refusing to overwrite existing source archive: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(DOWNLOAD_URL, timeout=60) as response, target.open("xb") as output:
        shutil.copyfileobj(response, output)
    return validate_archive(target)


def _member_path(info: zipfile.ZipInfo) -> PurePosixPath:
    name = info.filename
    path = PurePosixPath(name)
    if (
        not name
        or "\\" in name
        or "\x00" in name
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise ValueError(f"ARCHIVE_PATH_INVALID: {name!r}")
    return path


def validate_archive(source: str | Path) -> dict[str, Any]:
    archive = Path(source)
    md5 = hash_file(archive, "md5")
    sha256 = hash_file(archive, "sha256")
    if md5 != TLD_I_ARCHIVE_MD5 or sha256 != TLD_I_ARCHIVE_SHA256:
        raise ValueError("SOURCE_IDENTITY_MISMATCH: Zenodo archive digest")
    total = 0
    names: set[str] = set()
    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        if len(infos) > MAX_MEMBERS:
            raise ValueError("ARCHIVE_MEMBER_LIMIT")
        for info in infos:
            path = _member_path(info)
            normalized = path.as_posix().rstrip("/").casefold()
            if normalized in names:
                raise ValueError(f"ARCHIVE_DUPLICATE_MEMBER: {info.filename}")
            names.add(normalized)
            if info.flag_bits & 1:
                raise ValueError(f"ARCHIVE_ENCRYPTED_MEMBER: {info.filename}")
            mode = info.external_attr >> 16
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError(f"ARCHIVE_SPECIAL_MEMBER: {info.filename}")
            if info.file_size > MAX_MEMBER_BYTES:
                raise ValueError(f"ARCHIVE_MEMBER_SIZE_LIMIT: {info.filename}")
            total += info.file_size
            if info.file_size / max(info.compress_size, 1) > MAX_RATIO:
                raise ValueError(f"ARCHIVE_COMPRESSION_RATIO_LIMIT: {info.filename}")
        if total > MAX_TOTAL_BYTES:
            raise ValueError("ARCHIVE_TOTAL_SIZE_LIMIT")
        if bundle.testzip() is not None:
            raise ValueError("ARCHIVE_CRC_FAILURE")
    return {
        "valid": True,
        "doi": TLD_I_DOI,
        "md5": md5,
        "sha256": sha256,
        "member_count": len(names),
        "uncompressed_bytes": total,
    }


def extract_tld_i(source: str | Path, destination: str | Path) -> Path:
    validate_archive(source)
    target = Path(destination)
    if target.exists():
        raise ValueError(f"Fresh quarantine target already exists: {target}")
    target.mkdir(parents=True)
    root = target.resolve()
    with zipfile.ZipFile(source) as bundle:
        for info in bundle.infolist():
            path = _member_path(info)
            output = root.joinpath(*path.parts).resolve()
            if not output.is_relative_to(root):
                raise ValueError(f"ARCHIVE_PATH_INVALID: {info.filename}")
            if info.is_dir():
                output.mkdir(parents=True, exist_ok=True)
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(info) as input_stream, output.open("xb") as output_stream:
                    shutil.copyfileobj(input_stream, output_stream)
    release_root = target / "TORUS_Zenodo_v1"
    if not release_root.is_dir():
        raise ValueError("SOURCE_LAYOUT_INVALID: TORUS_Zenodo_v1 root missing")
    return release_root


def validate_release_source(source: str | Path) -> dict[str, Any]:
    """Validate either the canonical archive or an extracted canonical release tree."""
    path = Path(source)
    if path.is_file():
        return validate_archive(path)
    release_root = path / "TORUS_Zenodo_v1" if (path / "TORUS_Zenodo_v1").is_dir() else path
    inputs = release_root / "data_inputs"
    required = (
        "targets_baseline.csv",
        "targets_metadata_template.csv",
        "targets_metadata_addon.csv",
    )
    missing = [name for name in required if not (inputs / name).is_file()]
    if missing:
        raise ValueError(f"SOURCE_LAYOUT_INVALID: missing {', '.join(missing)}")
    notebooks = sorted(release_root.rglob("*Notebook*1[34]*.ipynb"))
    if len(notebooks) != 2:
        raise ValueError("SOURCE_LAYOUT_INVALID: confirmatory Notebooks 13 and 14 not found")
    hashes = {name: hash_file(inputs / name, "sha256") for name in required}
    for notebook in notebooks:
        try:
            document = json.loads(notebook.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"SOURCE_NOTEBOOK_INVALID: {notebook.name}") from error
        if not isinstance(document.get("cells"), list):
            raise ValueError(f"SOURCE_NOTEBOOK_INVALID: {notebook.name}")
    return {
        "valid": True,
        "doi": TLD_I_DOI,
        "source_kind": "extracted_release",
        "release_root": str(release_root),
        "input_sha256": hashes,
        "confirmatory_notebooks": [notebook.name for notebook in notebooks],
    }
