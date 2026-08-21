#!/usr/bin/env python3
"""Reconcile public TLD I-XIV code, outputs, failures, and fresh replay attempts."""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "external_cache" / "v0.4.0-lineage"
META = CACHE / "zenodo-metadata"
RELEASES = CACHE / "zenodo-releases"
EXTRACTED = CACHE / "zenodo-extracted"
LINEAGE = ROOT / "studies" / "v0.4.0" / "lineage"
OUT = ROOT / "studies" / "v0.4.0" / "reproduction"

RELEASE_MAP = [
    ("I", "18080090", "closure, structural escape, healing, anchoring, ringing"),
    ("II", "18080855", "mechanism, masks, structure-preserving nulls, operating limits"),
    ("III", "18082659", "invariance, brittleness, deformation thresholds, coherence"),
    ("IV", "18098646", "order mutation and recurrence-distribution guardrails"),
    ("V", "18103642", "calibrated recurrence gates and null prevalence"),
    ("VI", "18112594", "cyclic adjacency, topology-labelled effects, relational modes"),
    ("VII", "18143682", "parent-only cross-ladder matched-null inference"),
    ("VIII", "18181963", "cross-domain closure differentiation"),
    (
        "IX",
        "18188063",
        "outcome-blind features, registry-first ladders, exploratory topology/RPS/TORUS-BROT",
    ),
    ("X", "18193915", "frozen predictive gates and out-of-sample domains"),
    ("XI", "18200172", "deterministic perturbation preserve/collapse/induce contrasts"),
    ("XII", "18205906", "survival surfaces and historical emergent endpoint implementation"),
    ("XIII", "18206361", "comparative cross-domain survival geometry"),
    ("XIV", "18209905", "new categories and compound perturbations with baseline-parity audit"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()  # noqa: S324 - published identity only


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def load_replays() -> list[dict[str, Any]]:
    directory = OUT / "executed_notebooks"
    rows = []
    for path in sorted(directory.glob("notebook_*_replay_receipt*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        row["receipt_file"] = path.name
        row["valid_for_independent_reproduction"] = bool(
            row.get("valid_for_independent_reproduction", True)
            and not row.get("outcome_exposed_release_outputs_admitted_as_inputs", False)
        )
        rows.append(row)
    return rows


def xiv_baseline_parity() -> dict[str, Any]:
    directory = EXTRACTED / "18209905_outputs_XIV" / "outputs_XIV"
    with (directory / "byN_surface_43.csv").open(encoding="utf-8", newline="") as handle:
        rows43 = list(csv.DictReader(handle))
    with (directory / "byN_surface_44.csv").open(encoding="utf-8", newline="") as handle:
        rows44 = [row for row in csv.DictReader(handle) if row["family"] == "parent"]
    index43 = {(row["domain"], row["N"]): row for row in rows43}
    details = []
    for row in rows44:
        prior = index43[(row["domain"], row["N"])]
        match = all(prior[field] == row[field] for field in ("UI", "NSS", "sep"))
        details.append(
            {
                "domain": row["domain"],
                "N": int(row["N"]),
                "match": match,
                "notebook43": {field: prior[field] for field in ("UI", "NSS", "sep")},
                "notebook44": {field: row[field] for field in ("UI", "NSS", "sep")},
            }
        )
    domains = {}
    for domain in sorted({row["domain"] for row in details}):
        subset = [row for row in details if row["domain"] == domain]
        domains[domain] = {
            "rows": len(subset),
            "mismatches": sum(not row["match"] for row in subset),
            "pass": all(row["match"] for row in subset),
        }
    return {
        "schema_version": "tfs-v040-tld-xiv-baseline-parity-v1",
        "source_43_sha256": sha256(directory / "byN_surface_43.csv"),
        "source_44_sha256": sha256(directory / "byN_surface_44.csv"),
        "comparison_fields": ["UI", "NSS", "sep"],
        "domains": domains,
        "details": details,
        "status": "FAIL_EEG_ALL_N_ROWS" if not domains["EEG_VAR_MEDIAN"]["pass"] else "PASS",
        "claim_effect": "NOTEBOOK_44_EEG_COMPOUND_INTERPRETATION_BLOCKED",
    }


def output_registry() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    large_ix = Path.home() / "Downloads" / "Zenodo" / "rps_long_33.csv"
    for roman, record_id, _ in RELEASE_MAP:
        record = json.loads((META / f"{record_id}.json").read_text(encoding="utf-8"))
        for item in record["files"]:
            if not any(
                token in item["key"].lower()
                for token in (
                    "output",
                    "audit",
                    "surface",
                    "endpoint",
                    "summary",
                    "score",
                    "winner",
                    "null",
                    "rps",
                    "sha256",
                )
            ):
                continue
            local = RELEASES / record_id / item["key"]
            if item["key"] == "rps_long_33.csv" and large_ix.exists():
                local = large_ix
            verified = local.exists() and md5(local) == item["checksum"].removeprefix("md5:")
            rows.append(
                {
                    "release": roman,
                    "record_id": record_id,
                    "name": item["key"],
                    "published_md5": item["checksum"].removeprefix("md5:"),
                    "size_bytes": item["size"],
                    "local_byte_verification": "PASS"
                    if verified
                    else "PUBLICLY_LOCATED_NOT_MATERIALIZED",
                    "local_sha256": sha256(local) if verified else None,
                    "role": "published_output_or_audit",
                    "claim_authority": "OUTPUT_EVIDENCE_NOT_INDEPENDENT_REPRODUCTION",
                }
            )
    return rows


def claim_matrix() -> list[dict[str, Any]]:
    notes = {
        "I": (
            "exact TLD I path reproduced",
            "v0.3.0 imports the 1-D construct through lossless sequence representations",
        ),
        "II": (
            "published source/output plus fresh Notebook 15 path-normalized PASS",
            "no phase or orientation-reversal operator",
        ),
        "III": (
            "published source/output only in this audit",
            "deformation robustness is not parity",
        ),
        "IV": (
            "published source/output only in this audit",
            "return distributions are not physical time",
        ),
        "V": (
            "fresh Notebook 25 replay timed out at the frozen 180-second cell ceiling",
            "N=13/14 recurrence has high null prevalence in reported outputs",
        ),
        "VI": (
            "published source/output only in this audit",
            "cyclic adjacency is not an orientation bundle",
        ),
        "VII": (
            "published source/output only in this audit",
            "parent/null isolation is explicit but must not create extra parents",
        ),
        "VIII": (
            "published source/output only in this audit",
            "domain-specific winner_N values defeat pooled universality",
        ),
        "IX": (
            "Notebook 31 blocked on a missing historical domain-pack upload; other source/output exact",
            "TORUS-BROT/RPS remain exploratory",
        ),
        "X": (
            "published source/output; large domain-input archive publicly located",
            "mixed OOS results and a random-control separation remain visible",
        ),
        "XI": (
            "published source/output",
            "Notebook 40 single-parent baseline blocks clean causal proof",
        ),
        "XII": (
            "Notebook 41 timed out at the frozen 180-second cell ceiling",
            "historical T_hat_maxN is not current minimum-onset T_e",
        ),
        "XIII": (
            "published source/output with a published embedded error",
            "comparative behavior does not establish pooled universality",
        ),
        "XIV": (
            "exact source/output recovered; all 9 EEG baseline rows disagree between 43 and 44",
            "EEG compound claim blocked; COSMO and displayed GW baseline parity pass",
        ),
    }
    imported = {"I": "historical construct only"}
    return [
        {
            "release": roman,
            "historical_stage": stage,
            "what_code_computes": stage,
            "what_output_proves": notes[roman][0],
            "current_lexicon_allows": notes[roman][1],
            "field_studio_v030_imported": imported.get(roman, "not imported as canonical method"),
            "field_studio_still_lacks": "calibrated phase/orientation/parity inference",
            "TLD_DERIVED_phase_method": "BLOCKED",
        }
        for roman, _, stage in RELEASE_MAP
    ]


def main() -> None:
    for directory in (
        OUT / "reproduction_contracts",
        OUT / "environments",
        OUT / "executed_notebooks",
        OUT / "raw_outputs",
        OUT / "receipts",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    replays = load_replays()
    valid_replays = [row for row in replays if row["valid_for_independent_reproduction"]]
    parity = xiv_baseline_parity()
    outputs = output_registry()
    failures = read_jsonl(LINEAGE / "tld_known_failure_ledger.jsonl")
    for replay in valid_replays:
        if replay["status"] != "PASS":
            failures.append(
                {
                    "failure_id": f"NOTEBOOK_{replay['notebook']}_FRESH_REPLAY_BLOCKED",
                    "scope": f"Notebook {replay['notebook']}",
                    "classification": "ENVIRONMENT_OR_RUNTIME_BLOCKED",
                    "error_type": replay["error"]["type"],
                    "preserved": True,
                }
            )

    contract = {
        "schema_version": "tfs-v040-full-lineage-reproduction-contract-v1",
        "authority_order": ["A", "B", "C", "D", "E", "F"],
        "no_readme_to_executable_promotion": True,
        "no_output_to_independent_reproduction_promotion": True,
        "no_failure_suppression": True,
        "current_semantic_locks": {
            "omega": "ordered ladder state vector only",
            "winner_N": "harmonic/closure mode label only",
            "T_e": "minimum registered depth at first separation; not physical time",
            "S_e": "persistence/survival; not winner_N",
        },
        "fresh_replay_policy": "path changes only; no iteration/threshold/null/operator changes",
        "TLD_DERIVED": "BLOCKED",
    }
    write_json(OUT / "reproduction_contracts" / "full_lineage_contract.json", contract)

    environment = {
        "environment_id": "windows-python-3.13-path-normalized-replay",
        "python": "3.13",
        "original_colab_path_preserved_semantically": True,
        "path_normalization": "/content -> fresh temporary directory",
        "release_requirements": "minimum versions only; no complete historical lock files",
        "classification": "NOT_EXACT_ENVIRONMENT_REPRODUCTION",
    }
    write_jsonl(OUT / "environments" / "environment_registry.jsonl", [environment])
    write_jsonl(OUT / "executed_notebooks" / "execution_registry.jsonl", replays)
    write_jsonl(OUT / "raw_outputs" / "public_output_registry.jsonl", outputs)
    write_json(OUT / "receipts" / "tld_xiv_baseline_parity.json", parity)
    write_json(
        OUT / "receipts" / "source_custody_receipt.json",
        {
            "public_release_count": 14,
            "published_notebook_count": 32,
            "published_notebook_range": [13, 44],
            "pre_release_summary_only": list(range(1, 12)),
            "embedded_executable_not_immutably_published": [12],
            "published_output_or_audit_assets_freshly_downloaded_and_md5_verified": sum(
                record["local_byte_verification"] == "PASS" for record in outputs
            ),
            "large_ix_output_md5_verified": any(
                row["name"] == "rps_long_33.csv" and row["local_byte_verification"] == "PASS"
                for row in outputs
            ),
            "large_x_and_xiv_input_archives": "PUBLICLY_LOCATED_NOT_LOCALLY_DUPLICATED",
        },
    )

    summary = {
        "schema_version": "tfs-v040-tld-i-xiv-reproduction-summary-v1",
        "lineage_outcome": "FULL_TLD_I_XIV_LINEAGE_PARTIALLY_RECOVERED_WITH_BLOCKERS",
        "release_coverage": "14/14 immutable public releases located",
        "notebook_coverage": {
            "total": 44,
            "published_exact_source": 32,
            "embedded_executable_source": 1,
            "summary_only": 11,
        },
        "fresh_execution": {
            "tld_i_prior_exact_replay": True,
            "all_preserved_attempts": len(replays),
            "invalid_outcome_exposed_attempts": [
                row["receipt_file"]
                for row in replays
                if not row["valid_for_independent_reproduction"]
            ],
            "valid_path_normalized_attempts": len(valid_replays),
            "passes": [row["receipt_file"] for row in valid_replays if row["status"] == "PASS"],
            "blocked": [row["receipt_file"] for row in valid_replays if row["status"] != "PASS"],
        },
        "full_lineage_blockers": [
            "exact source files for pre-release Notebooks 1-11 were not found",
            "Notebook 12 is executable JSON embedded only in an authority-D ledger",
            "historical environments are minimum-version requirements, not complete locks",
            "published notebooks contain preserved error/aborted outputs",
            "Notebook 44 recomputation disagrees with Notebook 43 for all nine EEG baseline N rows",
        ],
        "method_authority_effect": {
            "TLD_DERIVED": "BLOCKED",
            "independent_phase_orientation_method_research": "MAY_CONTINUE_WITHOUT_TLD_DERIVATION",
            "reason": "the recovered lineage is sufficient to establish what TLD did not implement; it is insufficient to confer phase/parity authority",
        },
        "full_failure_count": len(failures),
    }
    write_json(OUT / "tld_i_xiv_reproduction_summary.json", summary)
    markdown = f"""# TLD I-XIV reproduction summary

Outcome: `{summary["lineage_outcome"]}`

All fourteen immutable Zenodo releases were located. Exact published notebook
source covers Notebooks 13-44; Notebook 12 survives as executable JSON embedded
in a hash-custodied authority-D ledger; Notebooks 1-11 remain summary-only.

The prior v0.3.0 TLD I replay remains exact. In this audit, one clean-input,
path-normalized Notebook 15 attempt passed without changing scientific
parameters and a repeated clean-input attempt reached the frozen 180-second
cell ceiling. The initial Notebook 15/25/31/41 attempts are preserved but
invalidated because their staging directory admitted outcome-exposed release
files. No claim relies on those attempts.

The strongest late-lineage blocker is Notebook 44 baseline parity: COSMO and GW
match Notebook 43 across all nine N rows, while EEG disagrees on all nine rows.
Therefore Notebook 44 EEG compound results are not clean validation evidence.

This recovery is sufficient to show that the historical lineage did not contain
a calibrated U(1), O(2)/Z2, spinor, parity, or orientation-bundle method. It is
not sufficient to label any new phase/orientation method `TLD_DERIVED`.
"""
    (OUT / "tld_i_xiv_reproduction_summary.md").write_text(
        markdown, encoding="utf-8", newline="\n"
    )
    write_jsonl(OUT / "claim_code_output_matrix.jsonl", claim_matrix())
    write_jsonl(OUT / "full_failure_ledger.jsonl", failures)

    files = [path for path in OUT.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt"]
    (OUT / "SHA256SUMS.txt").write_text(
        "".join(
            f"{sha256(path)}  {path.relative_to(OUT).as_posix()}\n"
            for path in sorted(files, key=lambda item: item.relative_to(OUT).as_posix())
        ),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
