#!/usr/bin/env python3
"""Attempt path-normalized numerical replays of published TLD notebooks.

The published notebooks were authored for a flat Google Colab ``/content``
workspace.  This runner changes only that filesystem prefix, suppresses upload
widgets/package-install magics, and executes in a fresh temporary directory.
Receipts never claim byte-exact notebook execution or a locked environment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "external_cache" / "v0.4.0-lineage"
ZENODO_RELEASES = CACHE / "zenodo-releases"
ZENODO_EXTRACTED = CACHE / "zenodo-extracted"
OUT = ROOT / "studies" / "v0.4.0" / "reproduction" / "executed_notebooks"
RAW_OUT = ROOT / "studies" / "v0.4.0" / "reproduction" / "raw_outputs"

RELEASES = [
    ("I", "18080090", range(13, 15)),
    ("II", "18080855", range(15, 18)),
    ("III", "18082659", range(18, 21)),
    ("IV", "18098646", range(21, 25)),
    ("V", "18103642", range(25, 26)),
    ("VI", "18112594", range(26, 27)),
    ("VII", "18143682", range(27, 29)),
    ("VIII", "18181963", range(29, 31)),
    ("IX", "18188063", range(31, 34)),
    ("X", "18193915", range(34, 38)),
    ("XI", "18200172", range(38, 41)),
    ("XII", "18205906", range(41, 42)),
    ("XIII", "18206361", range(42, 43)),
    ("XIV", "18209905", range(43, 45)),
]
NUMBER_TO_RELEASE = {
    number: (roman, record_id) for roman, record_id, numbers in RELEASES for number in numbers
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def notebook_number(path: Path) -> int | None:
    import re

    if "25A" in path.name.upper():
        return None
    match = re.search(r"Notebook[_ ]?(\d+)", path.name, re.I)
    return int(match.group(1)) if match else None


def published_notebooks() -> dict[int, Path]:
    found: dict[int, list[Path]] = {}
    for base in (ZENODO_RELEASES, ZENODO_EXTRACTED):
        for path in base.rglob("*.ipynb"):
            number = notebook_number(path)
            if number is not None:
                found.setdefault(number, []).append(path)
    return {
        number: sorted(
            paths, key=lambda path: ("zenodo-releases" not in str(path), len(str(path)))
        )[0]
        for number, paths in found.items()
    }


def copy_inputs(record_id: str, work: Path) -> list[str]:
    candidates: list[tuple[Path, bool]] = []
    direct = ZENODO_RELEASES / record_id
    if direct.exists():
        candidates.extend((path, False) for path in direct.rglob("*") if path.is_file())
    for directory in ZENODO_EXTRACTED.glob(f"{record_id}_*"):
        input_archive = any(token in directory.name.lower() for token in ("input", "domain"))
        candidates.extend((path, input_archive) for path in directory.rglob("*") if path.is_file())

    copied: list[str] = []
    by_name: dict[str, str] = {}
    input_tokens = (
        "input",
        "domain",
        "target",
        "lock",
        "gate",
        "perturb",
        "registry",
        "requirement",
    )
    outcome_tokens = (
        "output",
        "audit",
        "surface",
        "endpoint",
        "summary",
        "score",
        "winner",
        "null_distribution",
    )
    for source, from_input_archive in sorted(candidates, key=lambda item: str(item[0])):
        if source.suffix.lower() == ".ipynb":
            continue
        lower = source.name.lower()
        if not from_input_archive and not any(token in lower for token in input_tokens):
            continue
        if not from_input_archive and any(token in lower for token in outcome_tokens):
            continue
        source_hash = digest(source)
        if source.name in by_name and by_name[source.name] != source_hash:
            # Keep the first immutable release member.  The conflict remains
            # explicit instead of selecting by an observed notebook outcome.
            continue
        target = work / source.name
        if not target.exists():
            shutil.copy2(source, target)
        by_name[source.name] = source_hash
        copied.append(source.name)
    return sorted(set(copied))


def normalize_notebook(source: Path, work: Path) -> tuple[Any, list[int]]:
    notebook = nbformat.read(source, as_version=4)
    suppressed: list[int] = []
    prefix = work.as_posix()
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue
        text = cell.source.replace("/content", prefix)
        lines = []
        suppressed_cell = False
        for line in text.splitlines():
            stripped = line.lstrip()
            if stripped.startswith(("!pip ", "%pip ", "!apt ")):
                lines.append("# suppressed by path-normalized replay: " + line)
                suppressed_cell = True
            elif "from google.colab import files" in line or "files.upload()" in line:
                lines.append("# suppressed by path-normalized replay: " + line)
                suppressed_cell = True
            else:
                lines.append(line)
        cell.source = "\n".join(lines)
        cell.execution_count = None
        cell.outputs = []
        if suppressed_cell:
            suppressed.append(index)
    return notebook, suppressed


def replay(number: int, source: Path, timeout: int, receipt_suffix: str) -> dict[str, Any]:
    roman, record_id = NUMBER_TO_RELEASE[number]
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=f"tld-n{number:02d}-") as temporary:
        work = Path(temporary)
        copied = copy_inputs(record_id, work)
        before = {
            path.relative_to(work).as_posix(): digest(path)
            for path in work.rglob("*")
            if path.is_file()
        }
        notebook, suppressed = normalize_notebook(source, work)
        status = "PASS"
        error: dict[str, str] | None = None
        try:
            NotebookClient(
                notebook,
                timeout=timeout,
                kernel_name="python3",
                resources={"metadata": {"path": str(work)}},
                allow_errors=False,
            ).execute()
        except Exception as exc:  # noqa: BLE001 - receipt preserves exact class/message
            status = "BLOCKED"
            error = {"type": type(exc).__name__, "message": str(exc)[-4000:]}

        generated = []
        persisted_root = (
            RAW_OUT / f"notebook_{number:02d}{f'_{receipt_suffix}' if receipt_suffix else ''}"
        )
        for path in sorted(work.rglob("*"), key=lambda item: str(item)):
            if not path.is_file():
                continue
            relative = path.relative_to(work).as_posix()
            value = digest(path)
            if relative not in before or before[relative] != value:
                persisted = persisted_root / relative
                persisted.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, persisted)
                generated.append(
                    {
                        "name": relative,
                        "size_bytes": path.stat().st_size,
                        "sha256": value,
                        "persisted_path": persisted.relative_to(ROOT).as_posix(),
                    }
                )
        executed_count = sum(
            1
            for cell in notebook.cells
            if cell.cell_type == "code" and cell.execution_count is not None
        )
        return {
            "schema_version": "tfs-v040-notebook-replay-receipt-v1",
            "notebook": number,
            "release": roman,
            "record_id": record_id,
            "source_sha256": digest(source),
            "source_file": source.name,
            "replay_class": "PATH_NORMALIZED_NUMERICAL_REPLAY_NOT_EXACT_ENVIRONMENT_REPLAY",
            "path_change_only": True,
            "outcome_exposed_release_outputs_admitted_as_inputs": False,
            "valid_for_independent_reproduction": True,
            "upload_or_install_cells_suppressed": suppressed,
            "input_files_flattened": copied,
            "input_count": len(copied),
            "status": status,
            "error": error,
            "executed_code_cell_count": executed_count,
            "generated_or_changed_outputs": generated,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "claim_authority": "REPRODUCTION_DIAGNOSTIC_ONLY",
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("notebooks", nargs="+", type=int)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--receipt-suffix", default="")
    args = parser.parse_args()
    sources = published_notebooks()
    OUT.mkdir(parents=True, exist_ok=True)
    for number in args.notebooks:
        if number not in sources:
            raise SystemExit(f"Notebook {number} is not available as published source")
        receipt = replay(number, sources[number], args.timeout, args.receipt_suffix)
        suffix = f"_{args.receipt_suffix}" if args.receipt_suffix else ""
        target = OUT / f"notebook_{number:02d}_replay_receipt{suffix}.json"
        target.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"Notebook {number}: {receipt['status']} ({receipt['elapsed_seconds']} s)")


if __name__ == "__main__":
    main()
