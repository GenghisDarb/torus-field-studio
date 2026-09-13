#!/usr/bin/env python3
"""Build the v0.4.0 TLD I-XIV / Notebook 1-44 custody registries.

The script consumes only read-only, ignored caches populated from the immutable
Zenodo records and the hash-custodied historical recovery bundle.  It does not
execute notebooks or promote descriptive text to executable evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "external_cache" / "v0.4.0-lineage"
ZENODO_META = CACHE / "zenodo-metadata"
ZENODO_RELEASES = CACHE / "zenodo-releases"
ZENODO_EXTRACTED = CACHE / "zenodo-extracted"
HISTORICAL = CACHE / "historical-architecture-bundle"
OUT = ROOT / "studies" / "v0.4.0" / "lineage"


RELEASES = [
    ("I", "18080090", [13, 14]),
    ("II", "18080855", [15, 16, 17]),
    ("III", "18082659", [18, 19, 20]),
    ("IV", "18098646", [21, 22, 23, 24]),
    ("V", "18103642", [25]),
    ("VI", "18112594", [26]),
    ("VII", "18143682", [27, 28]),
    ("VIII", "18181963", [29, 30]),
    ("IX", "18188063", [31, 32, 33]),
    ("X", "18193915", [34, 35, 36, 37]),
    ("XI", "18200172", [38, 39, 40]),
    ("XII", "18205906", [41]),
    ("XIII", "18206361", [42]),
    ("XIV", "18209905", [43, 44]),
]
NUMBER_TO_RELEASE = {
    notebook: (roman, record_id)
    for roman, record_id, notebooks in RELEASES
    for notebook in notebooks
}

PRE_RELEASE = {
    1: ("Baseline Ladder Construction", "Construct the ordered baseline ladder."),
    2: ("Deterministic Closure Sweep", "Find interior versus edge RMS minima."),
    3: ("Null Model Introduction", "Compare ordered ladders with shuffled nulls."),
    4: ("Controller and Pipeline Variants", "Test representation and trend artifacts."),
    5: ("Emergence Diagnostics", "Track separation onset rather than closure alone."),
    6: ("Full Null and Monte Carlo", "Stress closure under uncertainty; only partially completed."),
    7: ("Pilot Basin Verification", "Triage candidate interior basins with analytic solvers."),
    8: ("Standalone Basin Confirmation", "Confirm MC versus null contrast independently."),
    9: ("Escalated Validation", "Concentrate the reported MC basin at N=10."),
    10: ("Artifact Falsification", "Test expanded N, order, and rung removal."),
    11: ("Kernel Discovery", "Identify load-bearing rungs and pairwise interactions."),
    12: (
        "Coupling Map and Kernel Comparison",
        "Compare the load-bearing kernel across three frozen pipelines.",
    ),
}

OPERATOR_PATTERNS = {
    "absolute_value": re.compile(r"\b(?:np\.)?abs\s*\(|absolute", re.I),
    "signed_difference": re.compile(r"\b(?:np\.)?diff\s*\(|signed", re.I),
    "complex_amplitude_or_phase": re.compile(r"\bcomplex\b|np\.angle|phase|exp\s*\([^\n]*1j", re.I),
    "orientation": re.compile(r"orientation|orientable", re.I),
    "cyclic_adjacency": re.compile(r"cyclic|np\.roll", re.I),
    "reflection": re.compile(r"reflect|mirror", re.I),
    "conjugation": re.compile(r"conjugat|\.conj\s*\(", re.I),
    "winding": re.compile(r"winding", re.I),
    "curl_or_vorticity": re.compile(r"curl|vorticity", re.I),
    "divergence": re.compile(r"divergence", re.I),
    "holonomy": re.compile(r"holonomy", re.I),
    "monodromy": re.compile(r"monodromy", re.I),
    "parity": re.compile(r"parity", re.I),
    "chirality": re.compile(r"chirality|chiral", re.I),
    "double_cover": re.compile(r"double[- ]cover", re.I),
    "mobius_or_klein": re.compile(r"m[oö]bius|klein", re.I),
    "U1": re.compile(r"\bU\s*\(\s*1\s*\)|\bU1\b", re.I),
    "O2": re.compile(r"\bO\s*\(\s*2\s*\)|\bO2\b", re.I),
    "Z2": re.compile(r"\bZ\s*2\b|ℤ2", re.I),
    "spinor": re.compile(r"spinor", re.I),
    "berry_phase": re.compile(r"berry", re.I),
    "chern_class": re.compile(r"chern|\bc1\b", re.I),
    "stiefel_whitney": re.compile(r"stiefel|\bw1\b", re.I),
}

ENDPOINT_PATTERNS = {
    "winner_N": re.compile(r"winner_?N|consensus_?N|harmonic mode", re.I),
    "T_e_historical": re.compile(r"T_hat|max separated N|emergent time", re.I),
    "S_e_historical": re.compile(r"S_hat|AUC_SEP|emergent scale|survival", re.I),
    "UI": re.compile(r"universality index|\bUI\b"),
    "NSS": re.compile(r"null[- ]separation|\bNSS\b", re.I),
    "SEP": re.compile(r"\bSEP\b|separat(?:e|ion)", re.I),
}

NULL_PATTERNS = {
    "shuffle_or_permutation": re.compile(r"shuffle|permut", re.I),
    "cyclic_shift": re.compile(r"cyclic.?shift|np\.roll", re.I),
    "matched_parent_null": re.compile(r"matched.?null|parent_ladder_id|null children", re.I),
    "bootstrap": re.compile(r"bootstrap", re.I),
    "phase_randomization": re.compile(r"phase.?scrambl|phase.?random", re.I),
}

PERTURBATION_PATTERNS = {
    "order_mutation": re.compile(r"order.?mutation|permut|shuffle", re.I),
    "entropy_jitter": re.compile(r"entropy.?jitter", re.I),
    "topology": re.compile(r"topology|cyclic|linear", re.I),
    "resonance": re.compile(r"resonance", re.I),
    "participation": re.compile(r"participation|rung", re.I),
    "compound": re.compile(r"compound|hyb:", re.I),
    "value_noise": re.compile(r"noise|jitter|monte.?carlo", re.I),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()  # noqa: S324 - archive identity only


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def source_text(cell: dict[str, Any]) -> str:
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else str(source)


def write_jsonl(name: str, rows: Iterable[dict[str, Any]]) -> None:
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    (OUT / name).write_text(text, encoding="utf-8", newline="\n")


def notebook_number(path: Path) -> int | None:
    if "25A" in path.name.upper():
        return None
    match = re.search(r"Notebook[_ ]?(\d+)", path.name, re.I)
    return int(match.group(1)) if match else None


def notebook_paths() -> dict[int, Path]:
    candidates: defaultdict[int, list[Path]] = defaultdict(list)
    for base in (ZENODO_RELEASES, ZENODO_EXTRACTED):
        for path in base.rglob("*.ipynb"):
            number = notebook_number(path)
            if number is not None:
                candidates[number].append(path)
    selected: dict[int, Path] = {}
    for number, paths in candidates.items():
        hashes = {sha256(path) for path in paths}
        if len(hashes) != 1:
            raise RuntimeError(f"conflicting public bytes for Notebook {number}: {paths}")
        selected[number] = sorted(
            paths, key=lambda path: ("zenodo-releases" not in str(path), len(str(path)))
        )[0]
    return selected


def inspect_notebook(path: Path) -> dict[str, Any]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    cells = notebook.get("cells", [])
    code_cells = [cell for cell in cells if cell.get("cell_type") == "code"]
    markdown_cells = [cell for cell in cells if cell.get("cell_type") == "markdown"]
    executed = [cell for cell in code_cells if cell.get("execution_count") is not None]
    errors: list[dict[str, Any]] = []
    aborted_cells: list[int] = []
    for index, cell in enumerate(cells):
        info = cell.get("metadata", {}).get("executionInfo", {})
        if info.get("status") == "aborted":
            aborted_cells.append(index)
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                errors.append(
                    {
                        "cell_index": index,
                        "ename": output.get("ename"),
                        "evalue": output.get("evalue"),
                    }
                )
    title = path.stem
    for cell in markdown_cells:
        for line in source_text(cell).splitlines():
            if line.lstrip().startswith("#"):
                title = line.lstrip("# ").strip()
                break
        if title != path.stem:
            break
    return {
        "document": notebook,
        "title": title,
        "cell_count": len(cells),
        "code_cell_count": len(code_cells),
        "markdown_cell_count": len(markdown_cells),
        "executed_code_cell_count": len(executed),
        "unexecuted_code_cell_count": len(code_cells) - len(executed),
        "embedded_error_outputs": errors,
        "aborted_cell_indices": aborted_cells,
    }


def public_file_url(record_id: str, key: str) -> str:
    from urllib.parse import quote

    return f"https://zenodo.org/records/{record_id}/files/{quote(key)}?download=1"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    paths = notebook_paths()
    expected = set(range(13, 45))
    if set(paths) != expected:
        raise RuntimeError(f"public notebook coverage mismatch: {sorted(set(paths) ^ expected)}")

    metadata: dict[str, dict[str, Any]] = {}
    for _, record_id, _ in RELEASES:
        metadata[record_id] = json.loads(
            (ZENODO_META / f"{record_id}.json").read_text(encoding="utf-8")
        )

    notebook_records: list[dict[str, Any]] = []
    inspections: dict[int, dict[str, Any]] = {}
    for number in range(1, 13):
        title, purpose = PRE_RELEASE[number]
        source_kind = "HASH_CUSTODIED_TECHNICAL_LEDGER"
        classification = "SUMMARY_ONLY"
        exact_executable = False
        if number == 12:
            source_kind = "EXECUTABLE_JSON_EMBEDDED_IN_HASH_CUSTODIED_LEDGER"
            classification = "SEMANTICALLY_RECOVERABLE"
            exact_executable = True
        notebook_records.append(
            {
                "notebook": number,
                "release": "PRE_RELEASE" if number < 12 else "PRE_RELEASE_TO_I_BRIDGE",
                "title": title,
                "purpose": purpose,
                "source_authority": "D",
                "source_kind": source_kind,
                "source_location": "historical recovery bundle",
                "public": False,
                "sha256": None,
                "inputs": ["targets_baseline.csv"] if number != 2 else ["Notebook 1 omega vector"],
                "N_r_ell_axes": {"N": "historical ladder harmonic search", "r": None, "ell": None},
                "exactly_executable": exact_executable,
                "exactly_reproduced": False,
                "recovery_classification": classification,
                "safe_for_public_redistribution": False,
                "claim_authority": "DESCRIPTIVE_ONLY",
            }
        )

    for number in range(13, 45):
        path = paths[number]
        inspection = inspect_notebook(path)
        inspections[number] = inspection
        roman, record_id = NUMBER_TO_RELEASE[number]
        notebook_records.append(
            {
                "notebook": number,
                "release": roman,
                "title": inspection["title"],
                "source_authority": "A",
                "source_kind": "IMMUTABLE_PUBLISHED_EXECUTABLE_NOTEBOOK",
                "source_location": {
                    "record": f"https://zenodo.org/records/{record_id}",
                    "local_ignored_cache": rel(path),
                },
                "public": True,
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
                "cell_counts": {
                    key: inspection[key]
                    for key in (
                        "cell_count",
                        "code_cell_count",
                        "markdown_cell_count",
                        "executed_code_cell_count",
                        "unexecuted_code_cell_count",
                    )
                },
                "embedded_error_outputs": inspection["embedded_error_outputs"],
                "aborted_cell_indices": inspection["aborted_cell_indices"],
                "N_r_ell_axes": {
                    "N": "historical harmonic/recursion grid; inspect notebook lock",
                    "r": "not a separately typed Field Studio operation-depth axis",
                    "ell": None,
                },
                "exactly_executable": True,
                "exactly_reproduced": number in {13, 14},
                "recovery_classification": "EXACTLY_REPRODUCIBLE",
                "safe_for_public_redistribution": True,
                "license": "MIT",
                "claim_authority": "CODE_AND_OUTPUT_SUBJECT_TO_CURRENT_LEXICON",
            }
        )

    release_records: list[dict[str, Any]] = []
    input_records: list[dict[str, Any]] = []
    source_authority: list[dict[str, Any]] = []
    source_sums: dict[str, str] = {}
    for roman, record_id, notebooks in RELEASES:
        record = metadata[record_id]
        files = record.get("files", [])
        materialized = 0
        for item in files:
            local = ZENODO_RELEASES / record_id / item["key"]
            local_ok = local.exists() and md5(local) == item["checksum"].removeprefix("md5:")
            if local_ok:
                materialized += 1
                source_sums[rel(local)] = sha256(local)
            if re.search(r"input|domain|target|lock|gate|perturb|registry", item["key"], re.I):
                input_records.append(
                    {
                        "release": roman,
                        "record_id": record_id,
                        "name": item["key"],
                        "size_bytes": item["size"],
                        "published_md5": item["checksum"].removeprefix("md5:"),
                        "public_url": public_file_url(record_id, item["key"]),
                        "local_byte_verification": "PASS"
                        if local_ok
                        else "PUBLICLY_LOCATED_NOT_MATERIALIZED",
                        "authority": "A",
                        "role": "release_input_or_contract",
                    }
                )
        release_records.append(
            {
                "release": roman,
                "identity": f"TLD_{roman}",
                "record_id": record_id,
                "doi": record["metadata"]["doi"],
                "record_url": f"https://zenodo.org/records/{record_id}",
                "title": record["metadata"]["title"],
                "public": True,
                "license": "MIT",
                "notebooks": notebooks,
                "asset_count": len(files),
                "total_size_bytes": sum(item["size"] for item in files),
                "locally_md5_verified_assets": materialized,
                "large_public_assets_not_materialized": [
                    {
                        "name": item["key"],
                        "size_bytes": item["size"],
                        "published_md5": item["checksum"].removeprefix("md5:"),
                    }
                    for item in files
                    if item["size"] > 10_000_000
                    and not (ZENODO_RELEASES / record_id / item["key"]).exists()
                ],
                "source_status": "IMMUTABLE_PUBLIC_RELEASE_LOCATED",
                "claim_boundary": "RELEASE_CLAIMS_REQUIRE_CODE_OUTPUT_LEXICON_RECONCILIATION",
            }
        )
        source_authority.append(
            {
                "source_id": f"ZENODO_{record_id}",
                "authority": "A",
                "kind": "published_executable_source_and_release_artifacts",
                "identity": record["metadata"]["doi"],
                "public": True,
                "use": "primary executable and immutable release evidence",
            }
        )

    manifest = json.loads((HISTORICAL / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    for entry in manifest["entries"]:
        path = HISTORICAL / "sources" / entry["filename"]
        if sha256(path) != entry["sha256"] or path.stat().st_size != entry["size_bytes"]:
            raise RuntimeError(f"historical bundle mismatch: {entry['filename']}")
        source_sums[rel(path)] = entry["sha256"]
        authority = "C" if entry["role"] == "tld_semantic_lock" else "D"
        if "chat" in entry["role"]:
            authority = "E"
        source_authority.append(
            {
                "source_id": f"HISTORICAL_{entry['sha256'][:12]}",
                "authority": authority,
                "kind": entry["role"],
                "identity": entry["sha256"],
                "public": False,
                "use": "semantic lock"
                if authority == "C"
                else "descriptive or development context only",
                "promotion_prohibited": authority in {"D", "E"},
            }
        )

    for number, path in paths.items():
        source_sums[rel(path)] = sha256(path)

    operator_rows: list[dict[str, Any]] = []
    endpoint_rows: list[dict[str, Any]] = []
    null_rows: list[dict[str, Any]] = []
    perturbation_rows: list[dict[str, Any]] = []
    for number, inspection in inspections.items():
        for cell_index, cell in enumerate(inspection["document"].get("cells", [])):
            if cell.get("cell_type") not in {"code", "markdown"}:
                continue
            for line_index, line in enumerate(source_text(cell).splitlines(), start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                snippet = stripped[:300]
                for category, pattern in OPERATOR_PATTERNS.items():
                    if pattern.search(stripped):
                        operator_rows.append(
                            {
                                "notebook": number,
                                "release": NUMBER_TO_RELEASE[number][0],
                                "category": category,
                                "cell_index": cell_index,
                                "cell_type": cell.get("cell_type"),
                                "source_line": line_index,
                                "exact_code_or_equation": snippet,
                                "authority": "A",
                                "sign_preserved": category
                                in {"signed_difference", "curl_or_vorticity"},
                                "phase_preserved": category
                                in {
                                    "complex_amplitude_or_phase",
                                    "conjugation",
                                    "winding",
                                    "holonomy",
                                },
                                "historically_executed": cell.get("execution_count") is not None,
                                "prospectively_validated": False,
                                "claim_authority": "HISTORICAL_OPERATOR_ONLY",
                            }
                        )
                for endpoint, pattern in ENDPOINT_PATTERNS.items():
                    if pattern.search(stripped):
                        endpoint_rows.append(
                            {
                                "notebook": number,
                                "release": NUMBER_TO_RELEASE[number][0],
                                "endpoint": endpoint,
                                "cell_index": cell_index,
                                "source_line": line_index,
                                "snippet": snippet,
                                "authority": "A",
                                "current_semantics_required": True,
                            }
                        )
                for family, pattern in NULL_PATTERNS.items():
                    if pattern.search(stripped):
                        null_rows.append(
                            {
                                "notebook": number,
                                "release": NUMBER_TO_RELEASE[number][0],
                                "family": family,
                                "cell_index": cell_index,
                                "source_line": line_index,
                                "snippet": snippet,
                                "authority": "A",
                                "parent_match_requires_manual_audit": True,
                            }
                        )
                for family, pattern in PERTURBATION_PATTERNS.items():
                    if pattern.search(stripped):
                        perturbation_rows.append(
                            {
                                "notebook": number,
                                "release": NUMBER_TO_RELEASE[number][0],
                                "family": family,
                                "cell_index": cell_index,
                                "source_line": line_index,
                                "snippet": snippet,
                                "authority": "A",
                                "outcome_blindness_requires_contract_audit": True,
                            }
                        )

    failures: list[dict[str, Any]] = [
        {
            "failure_id": "PRE_RELEASE_NOTEBOOKS_1_11_SOURCE_NOT_FOUND",
            "scope": "Notebooks 1-11",
            "classification": "SOURCE_NOT_FOUND",
            "preserved": True,
            "effect": "results remain descriptive; no executable-result inference permitted",
        },
        {
            "failure_id": "NOTEBOOK_12_NOT_IMMUTABLY_PUBLISHED",
            "scope": "Notebook 12",
            "classification": "SEMANTICALLY_RECOVERABLE",
            "preserved": True,
            "effect": "embedded JSON is executable context but not promoted to authority A/B",
        },
        {
            "failure_id": "NOTEBOOK_13_PREREG_GATES_NOT_ALL_PASS",
            "scope": "Notebook 13",
            "classification": "KNOWN_NEGATIVE_RESULT",
            "evidence": "historical output reports ALPHA_ON_OK=False and RINGING_OK=False at alpha=0.02",
            "preserved": True,
        },
        {
            "failure_id": "NOTEBOOK_34_PRIME_GAPS_MISCLASSIFIED",
            "scope": "Notebook 34",
            "classification": "PREDICTIVE_FAILURE",
            "preserved": True,
        },
        {
            "failure_id": "NOTEBOOK_36_RANDOM_CONTROL_SEPARATED",
            "scope": "Notebook 36",
            "classification": "BASELINE_FALSE_POSITIVE_RISK",
            "preserved": True,
        },
        {
            "failure_id": "NOTEBOOK_40_SINGLE_PARENT_BASELINE",
            "scope": "Notebook 40",
            "classification": "PARENT_MODEL_WEAKNESS",
            "preserved": True,
            "effect": "not clean causal proof",
        },
        {
            "failure_id": "NOTEBOOK_41_44_T_HAT_MAXN_SEMANTIC_MISMATCH",
            "scope": "Notebooks 41-44",
            "classification": "SUPERSEDED_ENDPOINT_SEMANTICS",
            "preserved": True,
            "effect": "historical max-N outputs cannot be relabeled as current minimum-onset T_e",
        },
        {
            "failure_id": "NOTEBOOK_44_EEG_BASELINE_PARITY",
            "scope": "Notebook 44 EEG baseline",
            "classification": "BASELINE_PARITY_FAILURE",
            "mismatched_N_rows": 9,
            "total_N_rows": 9,
            "cosmo_mismatches": 0,
            "gw_mismatches": 0,
            "preserved": True,
            "effect": "EEG compound conclusions blocked pending documented migration or exact reconciliation",
        },
    ]
    for number, inspection in inspections.items():
        for error in inspection["embedded_error_outputs"]:
            failures.append(
                {
                    "failure_id": f"NOTEBOOK_{number}_EMBEDDED_ERROR_CELL_{error['cell_index']}",
                    "scope": f"Notebook {number}",
                    "classification": "PUBLISHED_EMBEDDED_EXECUTION_ERROR",
                    "error": error,
                    "preserved": True,
                }
            )
        if inspection["aborted_cell_indices"]:
            failures.append(
                {
                    "failure_id": f"NOTEBOOK_{number}_ABORTED_CELLS",
                    "scope": f"Notebook {number}",
                    "classification": "PUBLISHED_ABORTED_EXECUTION",
                    "cell_indices": inspection["aborted_cell_indices"],
                    "preserved": True,
                }
            )

    translations = [
        {
            "legacy": "Omega/omega used as emergence depth or time",
            "current": "T_e only when the locked minimum-onset definition is actually computed",
            "rule": "omega is permanently reserved for the ordered ladder state vector",
        },
        {"legacy": "closure scale", "current": "winner_N", "rule": "not S_e"},
        {"legacy": "emergent scale", "current": "S_e", "rule": "persistence/survival only"},
        {
            "legacy": "historical T_hat_maxN",
            "current": "historical maximum separated N",
            "rule": "preserve raw field; never relabel as current minimum-onset T_e",
        },
        {
            "legacy": "ToT-BROT describing the existing single-ladder dual",
            "current": "TORUS-BROT",
            "rule": "unless explicitly coupled/interlocked tori",
        },
        {
            "legacy": "winner_N as time or physical scale",
            "current": "harmonic/closure mode label",
            "rule": "no physical meaning by default",
        },
        {
            "legacy": "edge winner",
            "current": "possible null attractor or grid-boundary result",
            "rule": "not new physics without independent evidence",
        },
    ]

    write_jsonl("tld_release_registry.jsonl", release_records)
    write_jsonl("tld_notebook_registry.jsonl", notebook_records)
    write_jsonl("tld_input_registry.jsonl", input_records)
    write_jsonl("tld_operator_lineage.jsonl", operator_rows)
    write_jsonl("tld_endpoint_lineage.jsonl", endpoint_rows)
    write_jsonl("tld_null_lineage.jsonl", null_rows)
    write_jsonl("tld_perturbation_lineage.jsonl", perturbation_rows)
    write_jsonl("tld_known_failure_ledger.jsonl", failures)
    write_jsonl("tld_semantic_translation.jsonl", translations)
    write_jsonl("tld_source_authority.jsonl", source_authority)
    (OUT / "SHA256SUMS_SOURCE.txt").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(source_sums.items())),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
