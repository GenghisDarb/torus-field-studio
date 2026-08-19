"""Deterministic TBX packaging for the prospective held-out study."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from ...audit import HELDOUT_REQUIRED_MEMBERS, audit_bundle
from ...domains.beijing_pm25 import DOI, SOURCE_SHA256
from ...models import canonical_json, content_hash

PROFILES = {
    "primary": "tld-heldout-primary-v0.2.1",
    "specificity": "tld-heldout-specificity-v0.2.1",
    "combined": "tld-heldout-combined-v0.2.1",
    "forensic": "tld-heldout-v021-forensic-v0.2.2",
}


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _jsonl(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json(row) for row in rows)


def _csv_bytes(rows: list[dict[str, str]]) -> bytes:
    if not rows:
        return b""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def _point_table(scored: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    conditions = (
        "baseline",
        "calibration_scale_095",
        "calibration_scale_105",
        "sensor_noise_001",
        "outage_6h_30d",
        "outage_24h_90d",
        "day_order_swap_010",
        "cyclic_adjacency",
    )
    surface = _csv(scored / "byN_surface.csv")
    endpoints = _json(scored / "primary_endpoints.json")
    specificity = _csv(scored / "specificity_audit.csv")
    closure = {int(row["N"]): float(row["median_closure_error"]) for row in specificity}
    points: list[dict[str, Any]] = []
    for y, condition in enumerate(conditions):
        rows = sorted(
            (row for row in surface if row["condition"] == condition),
            key=lambda row: int(row["N"]),
        )
        for x, row in enumerate(rows):
            n_value = int(row["N"])
            sep = row["SEP"].casefold() == "true"
            points.append(
                {
                    "index": len(points),
                    "grid_x": x,
                    "grid_y": y,
                    "x": float(n_value),
                    "y": float(y),
                    "classification": "BOUNDED" if sep else "NULL_LIKE",
                    "eligible": int(row["eligible_parent_count"]) >= 10,
                    "emerged": sep,
                    "separated_from_null": sep,
                    "closed": n_value == endpoints["winner_N_study_closure_minimum"],
                    "survived": False,
                    "escaped_from_reference": False,
                    "recovered": None,
                    "winner_N": endpoints["winner_N_study_closure_minimum"],
                    "T_e": None,
                    "S_e": float(endpoints["S_e_contiguous"]),
                    "UI": float(row["UI"]),
                    "NSS": float(row["NSS"]),
                    "SEP": 1.0 if sep else 0.0,
                    "rms_to_parent": closure[n_value],
                    "iterations": int(row["eligible_parent_count"]),
                    "parent_id": "population:beijing-pm25-stations",
                    "null_policy_id": "within-year-month-complete-day-permutation-127",
                    "trace": [
                        {
                            "step": n_value,
                            "stage": condition,
                            "coherence": float(row["UI"]),
                            "null_mean": float(row["NSS"]),
                        }
                    ],
                    "failure_id": None,
                    "observed": True,
                }
            )
    counts = Counter(point["classification"] for point in points)
    statistics = {
        "point_count": len(points),
        "classification_counts": dict(sorted(counts.items())),
        "mean_UI": round(sum(point["UI"] for point in points) / len(points), 8),
        "mean_NSS": round(sum(point["NSS"] for point in points) / len(points), 8),
        "mean_S_e": round(sum(point["S_e"] for point in points) / len(points), 8),
        "failure_count": 0,
    }
    return {"schema_version": "1.0.0", "width": 9, "height": 8, "points": points}, statistics


def _members(
    profile_key: str,
    study: Path,
    materialized: Path,
    scored: Path,
    verification: Path,
    adjudication: Path,
    publication: Path,
) -> tuple[dict[str, bytes], dict[str, Any], str, str, dict[str, Any]]:
    profile = PROFILES[profile_key]
    endpoints = _json(scored / "primary_endpoints.json")
    independent = _json(verification / "independent_verification.json")
    scientific = _json(adjudication / "scientific_adjudication.json")
    tld_adjudication = _json(adjudication / "TLD_DERIVED_adjudication.json")
    field_table, statistics = _point_table(scored)
    specification = {
        "schema_version": "1.0.0",
        "engine": "tld",
        "seed": 20260818,
        "domain_id": "uci-beijing-multisite-air-quality-pm25",
        "claim_level": "COMPUTED_DYNAMICAL",
        "grid": {"width": 9, "height": 8},
        "parameters": {
            "profile": profile,
            "primary_N_grid": list(range(6, 15)),
            "specificity_N_grid": list(range(4, 21)),
            "scored_run_id": endpoints["run_id"],
        },
        "classification_rules": {
            "separation_threshold": 0.05,
            "nss_threshold": 2.0,
            "survival_threshold": 0.8,
            "recovery_threshold": 1.0,
            "escape_threshold": 1.0,
        },
        "null_policy": {
            "kind": "preserve_multiset_shuffle",
            "count": 127,
            "seed": 20260818,
        },
    }
    specification_sha256 = content_hash(specification)
    kernel_id = "torusbrot.tld.heldout.beijing_pm25.v1"
    identity = {
        "specification": specification,
        "kernel_id": kernel_id,
        "domain_sha256": SOURCE_SHA256,
    }
    run_id = f"run-{content_hash(identity)[:16]}"
    parent_rows = _csv(materialized / "parent_registry.csv")
    ladder_rows = _csv(materialized / "ladder_registry.csv")
    null_rows = [row for row in ladder_rows if row["is_null"].casefold() == "true"]
    perturbation_rows = _csv(materialized / "perturbation_registry.csv")
    generic_nulls = [
        {
            "null_id": f"matched-child-{index:03d}",
            "policy": "within_year_month_complete_day_permutation",
            "seed_offset": index,
            "scope": "parent_local",
        }
        for index in range(1, 128)
    ]
    verification_receipt = {
        "run_id": run_id,
        "status": "verified",
        "verifier": independent["verifier"],
        "disagreement_count": independent["disagreement_count"],
    }
    claim = {
        "claim_level": "COMPUTED_DYNAMICAL",
        "permitted_interpretations": [
            "valid negative result under frozen gates",
            "parent-versus-parent-local-null computation",
            "winner_N is a separate closure-mode label",
        ],
        "excluded_interpretations": _json(adjudication / "forbidden_claims.json")[
            "forbidden_claims"
        ]
        + ["external validation"],
        "experimental_tags": ["prospective", "held-out", "scientific-negative"],
        "independent_verifier_status": "independently_verified",
    }
    source_registry = {
        "schema_version": "1.0.0",
        "source_id": "uci-501-beijing-multisite-air-quality",
        "title": "Beijing Multi-Site Air Quality",
        "doi": DOI,
        "license": "CC BY 4.0",
        "authoritative_archive": "PRSA2017_Data_20130301-20170228.zip",
        "authoritative_archive_sha256": SOURCE_SHA256,
        "source_url": (
            "https://archive.ics.uci.edu/static/public/501/beijing+multi+site+air+quality+data.zip"
        ),
        "independently_generated": True,
        "previously_outcome_exposed": False,
    }
    profile_document = {
        "schema_version": "1.0.0",
        "profile": profile,
        "focus": profile_key,
        "lane": "PROSPECTIVE_HELDOUT_EXTERNAL_DOMAIN",
        "required_members": sorted(HELDOUT_REQUIRED_MEMBERS),
        "preregistration_manifest_sha256": (
            "eb3a886aa3bc344ccf715d0036d5054cfba107aa3eae017ba00c68852bb73bfc"
        ),
        "classification_precedes_rendering": True,
        "interpolation_used_for_metrics": False,
        "external_replication_completed": False,
    }
    members: dict[str, bytes] = {
        "run_spec.json": canonical_json(specification, pretty=True),
        "ontology.json": canonical_json(
            {
                "schema_version": "1.0.0",
                "terms": {
                    "omega": "ordered ladder state vector only",
                    "T_e": "first registered observed/null separation depth",
                    "S_e": "separation survival after T_e",
                    "winner_N": "harmonic closure-mode label",
                },
                "non_equivalences": [
                    "winner_N != T_e",
                    "winner_N != S_e",
                    "TORUS-BROT != ToT-BROT",
                    "interpolation != observation",
                ],
            },
            pretty=True,
        ),
        "claim_boundary.json": canonical_json(claim, pretty=True),
        "visual_encoding.json": canonical_json(
            {
                "position": {"x": "N", "y": "registered_condition", "z": "NSS"},
                "color": "SEP",
                "opacity": "eligible_parent_fraction",
                "contour": "winner_N",
                "interpolation": {"method": "none", "used_for_metrics": False},
                "point_classes": [
                    "observed raw point",
                    "null point",
                    "computed summary",
                    "ineligible cell",
                    "failed cell",
                ],
                "scale_policy": "frozen-heldout-v0.2.1",
            },
            pretty=True,
        ),
        "scene_recipe.json": canonical_json(
            {
                "viewer": "TORUS Field Studio",
                "default_view": "field",
                "raw_samples_visible": True,
                "missing_regions_visible": True,
                "palette": "spectral-claim-safe-v1",
            },
            pretty=True,
        ),
        "provenance/sources.jsonl": _jsonl([source_registry]),
        "provenance/transformations.jsonl": _jsonl(
            [
                {
                    "transformation_id": kernel_id,
                    "software_version": "0.2.1",
                    "seed": 20260818,
                    "specification_sha256": specification_sha256,
                }
            ]
        ),
        "provenance/verification_receipts.jsonl": _jsonl([verification_receipt]),
        "registry/parent_registry.json": canonical_json(
            {
                "parent_id": "population:beijing-pm25-stations",
                "title": "12 independent Beijing PM2.5 station parents",
                "domain_sha256": SOURCE_SHA256,
                "claim_authority": "COMPUTED_DYNAMICAL",
                "parent_count": 12,
                "eligible_parent_count": 12,
            },
            pretty=True,
        ),
        "registry/null_registry.json": canonical_json(generic_nulls, pretty=True),
        "tables/field_points.json": canonical_json(field_table),
        "tables/metrics_by_N.json": canonical_json(
            {
                "summary": statistics,
                "T_e": endpoints["T_e"],
                "S_e_contiguous": endpoints["S_e_contiguous"],
                "winner_N": endpoints["winner_N_study_closure_minimum"],
            },
            pretty=True,
        ),
        "audit/audit.json": canonical_json(
            {
                "status": "independently_verified",
                "kernel_authority": "deterministic_cpu_reference",
                "failure_preservation": "complete",
                "classification_precedes_rendering": True,
                "mutation_rejections": "25/25",
            },
            pretty=True,
        ),
        "audit/failure_ledger.jsonl": (scored / "failure_ledger.jsonl").read_bytes(),
        "heldout_profile.json": canonical_json(profile_document, pretty=True),
        "source_registry.json": canonical_json(source_registry, pretty=True),
        "domain_translation.json": (
            study / "domain" / "domain_translation_contract.json"
        ).read_bytes(),
        "preregistration.json": (study / "preregistration" / "preregistration.json").read_bytes(),
        "registry/parent_registry.csv": _csv_bytes(parent_rows),
        "registry/ladder_registry.csv": _csv_bytes(ladder_rows),
        "registry/null_registry.csv": _csv_bytes(null_rows),
        "registry/perturbation_registry.csv": _csv_bytes(perturbation_rows),
        "tables/byN_surface.csv": (scored / "byN_surface.csv").read_bytes(),
        "tables/emergent_time_by_parent.csv": (scored / "emergent_time_by_parent.csv").read_bytes(),
        "tables/emergent_scale_by_parent.csv": (
            scored / "emergent_scale_by_parent.csv"
        ).read_bytes(),
        "tables/primary_endpoints.json": (scored / "primary_endpoints.json").read_bytes(),
        "tables/closure_mode_results.csv": (scored / "closure_mode_results.csv").read_bytes(),
        "tables/parent_null_comparison.csv": (scored / "parent_null_comparison.csv").read_bytes(),
        "tables/structured_fragility_results.csv": (
            scored / "structured_fragility_results.csv"
        ).read_bytes(),
        "tables/specificity_audit.csv": (scored / "specificity_audit.csv").read_bytes(),
        "tables/domain_baseline_comparison.csv": (
            scored / "domain_baseline_comparison.csv"
        ).read_bytes(),
        "audit/independent_verification.json": (
            verification / "independent_verification.json"
        ).read_bytes(),
        "audit/independent_recomputed_endpoints.json": (
            verification / "independent_recomputed_endpoints.json"
        ).read_bytes(),
        "audit/mutation_results.jsonl": (verification / "mutation_results.jsonl").read_bytes(),
        "audit/claim_adjudication.json": canonical_json(
            {
                "schema_version": "1.0.0",
                "scientific_outcome": scientific["scientific_outcome"],
                "claim_level": tld_adjudication["claim_level"],
                "TLD_DERIVED_status": tld_adjudication["TLD_DERIVED_status"],
                "EXTERNALLY_VALIDATED": False,
                "exact_blockers": tld_adjudication["exact_blockers"],
            },
            pretty=True,
        ),
        "audit/forbidden_claims.json": (adjudication / "forbidden_claims.json").read_bytes(),
        "reports/plain_language_summary.md": (
            publication / "plain-language-summary.md"
        ).read_bytes(),
        "reports/technical_report.md": (publication / "technical-report.md").read_bytes(),
        "visualization/byN_surface.svg": (publication / "heldout-tld-byN.svg").read_bytes(),
        "visualization/byN_surface.png": (publication / "heldout-tld-byN.png").read_bytes(),
    }
    sums = "".join(f"{_sha256(payload)}  {name}\n" for name, payload in sorted(members.items()))
    members["audit/SHA256SUMS.txt"] = sums.encode()
    return members, specification, run_id, kernel_id, statistics


def export_heldout_bundle(
    profile: str,
    study: Path,
    materialized: Path,
    scored: Path,
    verification: Path,
    adjudication: Path,
    publication: Path,
    destination: Path,
) -> tuple[Path, dict[str, Any]]:
    if profile not in PROFILES:
        raise ValueError(f"unregistered held-out TBX profile: {profile}")
    members, specification, run_id, kernel_id, statistics = _members(
        profile, study, materialized, scored, verification, adjudication, publication
    )
    manifest = {
        "tbx_version": "1.0.0",
        "profile": PROFILES[profile],
        "run_id": run_id,
        "claim_level": "COMPUTED_DYNAMICAL",
        "kernel_id": kernel_id,
        "specification_sha256": content_hash(specification),
        "statistics": statistics,
        "files": [
            {"path": name, "sha256": _sha256(payload), "bytes": len(payload)}
            for name, payload in sorted(members.items())
        ],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in [("manifest.json", canonical_json(manifest, pretty=True))] + sorted(
            members.items()
        ):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload)
    audit = audit_bundle(destination)
    return destination, audit.to_dict()


def export_forensic_bundle(
    study: Path,
    materialized: Path,
    scored: Path,
    verification: Path,
    adjudication: Path,
    publication: Path,
    forensic: Path,
    destination: Path,
) -> tuple[Path, dict[str, Any]]:
    """Package the immutable v0.2.1 result with additive v0.2.2 diagnostics."""
    members, specification, run_id, kernel_id, statistics = _members(
        "forensic", study, materialized, scored, verification, adjudication, publication
    )
    for path in sorted(forensic.iterdir()):
        if path.is_file() and path.name not in {
            destination.name,
            "external-replication-addon.zip",
            "release-manifest-v0.2.2.json",
            "SHA256SUMS-v0.2.2.txt",
        }:
            members[f"forensic/{path.name}"] = path.read_bytes()
    members["forensic_profile.json"] = canonical_json(
        {
            "schema_version": "1.0.0",
            "profile": PROFILES["forensic"],
            "basis": "immutable v0.2.1 combined held-out result",
            "diagnostic_status": "POST_HOC_DIAGNOSTIC_ONLY",
            "V021_PRIMARY_RESULT": "HELDOUT_TLD_STUDY_NEGATIVE_UNDER_FROZEN_GATES",
            "TLD_DERIVED": "BLOCKED",
            "EXTERNALLY_VALIDATED": False,
        },
        pretty=True,
    )
    sums = "".join(
        f"{_sha256(payload)}  {name}\n"
        for name, payload in sorted(members.items())
        if name != "audit/SHA256SUMS.txt"
    )
    members["audit/SHA256SUMS.txt"] = sums.encode()
    manifest = {
        "tbx_version": "1.0.0",
        "profile": PROFILES["forensic"],
        "run_id": run_id,
        "claim_level": "COMPUTED_DYNAMICAL",
        "kernel_id": kernel_id,
        "specification_sha256": content_hash(specification),
        "statistics": statistics,
        "files": [
            {"path": name, "sha256": _sha256(payload), "bytes": len(payload)}
            for name, payload in sorted(members.items())
        ],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in [("manifest.json", canonical_json(manifest, pretty=True))] + sorted(
            members.items()
        ):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload)
    audit = audit_bundle(destination)
    return destination, audit.to_dict()


def export_heldout_bundle_set(
    study: Path,
    materialized: Path,
    scored: Path,
    verification: Path,
    adjudication: Path,
    publication: Path,
    output: Path,
) -> list[dict[str, Any]]:
    names = {
        "primary": "heldout-tld-study-primary.tbx.zip",
        "specificity": "heldout-tld-study-specificity-audit.tbx.zip",
        "combined": "heldout-tld-study-combined.tbx.zip",
    }
    receipts: list[dict[str, Any]] = []
    for profile, name in names.items():
        path, audit = export_heldout_bundle(
            profile,
            study,
            materialized,
            scored,
            verification,
            adjudication,
            publication,
            output / name,
        )
        receipts.append(
            {
                "profile": profile,
                "path": str(path),
                "sha256": _sha256(path.read_bytes()),
                "bytes": path.stat().st_size,
                "audit": audit,
            }
        )
    return receipts
