"""Deterministic TLD TBX materialization with explicit historical claim boundaries."""

from __future__ import annotations

import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from ..models import canonical_json, content_hash
from .contracts import TLD_I_DOI, HistoricalTldIContract
from .provenance import tld_i_source_registry
from .verification import verify_historical_result

HISTORICAL_LANE = "HISTORICAL_PUBLISHED_RELEASE_REPRODUCTION"
FORBIDDEN_CLAIMS = [
    "TORUS Theory proven",
    "14 uniquely established by this reproduction",
    "physical law derived",
    "external validation",
    "cross-domain universality",
    "observer-state effect",
    "cosmological time or length derived",
    "ToT-BROT validated",
    "ToT-BULB validated",
    "causal physical mechanism established beyond the computational system",
]
TLD_MEMBERS = {
    "source_registry.json",
    "preregistration_contract.json",
    "tld_profile.json",
    "registry/ladder_registry.json",
    "registry/control_or_null_registry.json",
    "tables/tld_endpoint_table.json",
    "tables/baseline_scores.json",
    "tables/alpha_sweep.json",
    "tables/core_alpha_compare.json",
    "tables/preregistration_results.json",
    "tables/trajectories.jsonl",
    "tables/transition_counts.json",
    "tables/operating_envelope.json",
    "audit/independent_verification.json",
    "audit/claim_adjudication.json",
}


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _jsonl(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json(row) for row in rows)


def _domain_pack(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "domain_id": "torus-tld-i-baseline-v1",
        "doi": TLD_I_DOI,
        "source_input": "targets_baseline.csv",
        "source_sha256": result["input_hashes"]["targets_baseline.csv"],
        "row_order": "source_csv_order",
        "rows": [
            {
                "index": index,
                "family": row["family"],
                "label": row["codata_name"],
                "value": float(row["value"]),
                "sigma": float(row["sigma"]),
            }
            for index, row in enumerate(result["input_rows"])
        ],
        "canonicalization": "none; preserve source scalar bytes and row order",
        "ladderization": "omega=natural_log(value); sigma_omega=sigma/value",
        "adjacency_topology": "ordered_path",
        "units": "dimensionless",
        "duplicate_policy": "preserve source rows",
        "missing_value_policy": "reject",
        "claim_authority": "COMPUTED_DYNAMICAL",
        "license": "MIT",
    }


def _endpoints(result: dict[str, Any]) -> dict[str, Any]:
    rows = [
        {
            "endpoint_id": "baseline-closure",
            "lane": HISTORICAL_LANE,
            "condition": {"sweep": [2, 30]},
            "winner_N": result["baseline"]["sweep_2_30"]["winner_N"],
            "T_e": None,
            "S_e": None,
            "metrics": {
                "chi": result["baseline"]["sweep_2_30"]["chi"],
                "margin": result["baseline"]["sweep_2_30"]["margin"],
                "winner_rms": result["baseline"]["sweep_2_30"]["winner_rms"],
            },
            "eligible": True,
            "failure_id": None,
        }
    ]
    for row in result["notebook13"]["alpha_sweep"]:
        rows.append(
            {
                "endpoint_id": f"alpha-{row['alpha_heal']}",
                "lane": HISTORICAL_LANE,
                "condition": {"alpha_heal": row["alpha_heal"]},
                "winner_N": None,
                "T_e": None,
                "S_e": None,
                "metrics": {
                    key: row[key]
                    for key in (
                        "escape_rate",
                        "return_rate_given_escape",
                        "mean_return_steps",
                        "mean_flips",
                        "p90_flips",
                    )
                },
                "eligible": True,
                "failure_id": None,
            }
        )
    return {"schema_version": "1.0.0", "rows": rows}


def _endpoint_field(
    result: dict[str, Any], parent_id: str
) -> tuple[int, int, list[dict[str, Any]]]:
    metric_names = ("escape_rate", "return_rate_given_escape", "mean_return_steps", "p90_flips")
    conditions = result["notebook13"]["alpha_sweep"]
    points = []
    for grid_y, metric_name in enumerate(metric_names):
        for grid_x, row in enumerate(conditions):
            recovered = row["return_rate_given_escape"] >= 0.95
            points.append(
                {
                    "index": len(points),
                    "grid_x": grid_x,
                    "grid_y": grid_y,
                    "x": float(row["alpha_heal"]),
                    "y": float(grid_y),
                    "classification": "RECOVERED" if recovered else "ESCAPED",
                    "eligible": True,
                    "emerged": False,
                    "separated_from_null": False,
                    "closed": False,
                    "survived": False,
                    "escaped_from_reference": True,
                    "recovered": recovered,
                    "winner_N": None,
                    "T_e": None,
                    "S_e": None,
                    "UI": None,
                    "NSS": None,
                    "SEP": None,
                    "rms_to_parent": None,
                    "iterations": int(row["trials"]),
                    "parent_id": parent_id,
                    "null_policy_id": (
                        "historical-alpha-zero-control"
                        if row["alpha_heal"] == 0
                        else "historical-no-matched-null"
                    ),
                    "failure_id": None,
                    "observed": True,
                    "phase": f"endpoint:{metric_name}",
                    "trial_id": None,
                    "alpha": float(row["alpha_heal"]),
                    "t": None,
                    "trace": [],
                }
            )
    return len(conditions), len(metric_names), points


def _trace_field(
    result: dict[str, Any], parent_id: str
) -> tuple[int, int, list[dict[str, Any]], list[dict[str, Any]]]:
    width = 561
    summaries = result["notebook14"]["trace_summary"]
    traces_by_trial: dict[int, list[dict[str, Any]]] = {}
    for row in result["notebook14"]["traces"]:
        traces_by_trial.setdefault(int(row["trial_id"]), []).append(row)
    points = []
    failures = []
    for grid_y, summary in enumerate(summaries):
        trial_id = int(summary["trial_id"])
        failure_id = f"not-observed-after-terminal-trial-{trial_id}"
        failures.append(
            {
                "failure_id": failure_id,
                "category": "NOT_OBSERVED_AFTER_TERMINAL",
                "stage": "visual_materialization",
                "message": (
                    "Grid cells after the registered terminal event are explicit missing cells, "
                    "not interpolated observations."
                ),
                "grid_x": None,
                "grid_y": grid_y,
                "coordinate": None,
                "recoverable": False,
            }
        )
        by_timeline = {}
        escape_steps = int(summary["escape_steps"] or 0)
        for row in traces_by_trial[trial_id]:
            timeline = int(row["t"])
            if row["phase"] == "heal":
                timeline += escape_steps
            by_timeline[timeline] = row
        for grid_x in range(width):
            row = by_timeline.get(grid_x)
            if row is None:
                points.append(
                    {
                        "index": len(points),
                        "grid_x": grid_x,
                        "grid_y": grid_y,
                        "x": float(grid_x),
                        "y": float(summary["alpha_heal"]),
                        "classification": "UNRESOLVED",
                        "eligible": False,
                        "emerged": False,
                        "separated_from_null": False,
                        "closed": False,
                        "survived": False,
                        "escaped_from_reference": False,
                        "recovered": None,
                        "winner_N": None,
                        "T_e": None,
                        "S_e": None,
                        "UI": None,
                        "NSS": None,
                        "SEP": None,
                        "rms_to_parent": None,
                        "iterations": 0,
                        "parent_id": parent_id,
                        "null_policy_id": "historical-no-matched-null",
                        "failure_id": failure_id,
                        "observed": False,
                        "phase": None,
                        "trial_id": trial_id,
                        "alpha": float(summary["alpha_heal"]),
                        "t": None,
                        "trace": [],
                    }
                )
                continue
            closed = int(row["winner_N"]) == 10 and float(row["margin"]) >= float(
                result["baseline"]["window_7_13"]["margin"]
            )
            recovered = row["phase"] == "heal" and closed
            classification = (
                "RECOVERED"
                if recovered
                else "BOUNDED"
                if row["phase"] == "start" or closed
                else "ESCAPED"
            )
            points.append(
                {
                    "index": len(points),
                    "grid_x": grid_x,
                    "grid_y": grid_y,
                    "x": float(grid_x),
                    "y": float(row["alpha_heal"]),
                    "classification": classification,
                    "eligible": True,
                    "emerged": False,
                    "separated_from_null": False,
                    "closed": closed,
                    "survived": False,
                    "escaped_from_reference": row["phase"] != "start",
                    "recovered": recovered,
                    "winner_N": int(row["winner_N"]),
                    "T_e": None,
                    "S_e": None,
                    "UI": None,
                    "NSS": None,
                    "SEP": None,
                    "rms_to_parent": None,
                    "iterations": grid_x,
                    "parent_id": parent_id,
                    "null_policy_id": "historical-no-matched-null",
                    "failure_id": None,
                    "observed": True,
                    "phase": row["phase"],
                    "trial_id": trial_id,
                    "alpha": float(row["alpha_heal"]),
                    "t": int(row["t"]),
                    "trace": [
                        {
                            "step": grid_x,
                            "stage": row["phase"],
                            "coherence": float(row["margin"]),
                            "magnitude": float(row["chi"]),
                        }
                    ],
                }
            )
    return width, len(summaries), points, failures


def export_tld_bundle(result: dict[str, Any], profile: str, destination: str | Path) -> Path:
    if profile not in {"notebook13", "notebook14", "combined"}:
        raise ValueError(f"Unknown TLD bundle profile: {profile}")
    # JSON object keys are strings on disk. Normalize before hashing or materializing so a
    # freshly computed result and the same result loaded from JSON produce identical bytes.
    result = json.loads(canonical_json(result))
    verification = verify_historical_result(result)
    if verification["status"] != "verified":
        raise ValueError("Independent TLD verifier rejected the production result")
    parent = result["registries"]["parents"][0]
    parent_id = parent["ladder_id"]
    if profile == "notebook13":
        width, height, points = _endpoint_field(result, parent_id)
        failures: list[dict[str, Any]] = []
        tbx_profile = "tld-i-historical-v1"
    else:
        width, height, points, failures = _trace_field(result, parent_id)
        tbx_profile = "tld-i-combined-v1" if profile == "combined" else "tld-i-historical-v1"
    classifications = Counter(point["classification"] for point in points)
    statistics = {
        "point_count": len(points),
        "classification_counts": dict(sorted(classifications.items())),
        "mean_UI": None,
        "mean_NSS": None,
        "mean_S_e": None,
        "failure_count": len(failures),
    }
    contract = HistoricalTldIContract()
    run_spec = {
        "schema_version": "1.0.0",
        "engine": "tld",
        "seed": contract.seed,
        "domain_id": "torus-tld-i-baseline-v1",
        "claim_level": "COMPUTED_DYNAMICAL",
        "grid": {"width": width, "height": height},
        "parameters": {
            "doi": TLD_I_DOI,
            "lane": HISTORICAL_LANE,
            "profile": profile,
            "historical_contract_sha256": contract.sha256,
        },
        "classification_rules": {},
        "null_policy": {"kind": "none", "count": 0, "seed": contract.seed},
    }
    specification_sha256 = content_hash(run_spec)
    kernel_id = "torusbrot.tld_i.historical.v1"
    domain = _domain_pack(result)
    domain_sha256 = content_hash(domain)
    identity = {
        "specification": run_spec,
        "kernel_id": kernel_id,
        "domain_sha256": domain_sha256,
    }
    run_id = f"run-{content_hash(identity)[:16]}"
    source_registry = tld_i_source_registry(result["input_hashes"])
    preregistration = {
        "schema_version": "1.0.0",
        "contract_sha256": contract.sha256,
        "criteria": result["notebook13"]["preregistration"],
        "passed": sum(result["notebook13"]["preregistration"].values()),
        "failed": sum(not value for value in result["notebook13"]["preregistration"].values()),
    }
    blockers = [
        "Notebook 13 alpha=0.02 mean_return_steps exceeds the preregistered maximum",
        "Notebook 13 alpha=0.02 p90_flips exceeds the preregistered maximum",
        "The preregistration document declares 400 healing steps while Notebook 13 executes 300",
        "The historical alpha=0 control is not a modern matched structural null family",
        "Self-reproduction is not external validation",
    ]
    claim_adjudication = {
        "schema_version": "1.0.0",
        "lane": HISTORICAL_LANE,
        "claim_level": "COMPUTED_DYNAMICAL",
        "tld_derived_status": "BLOCKED",
        "externally_validated": False,
        "blockers": blockers,
        "forbidden_claims": FORBIDDEN_CLAIMS,
    }
    endpoint_table = _endpoints(result)
    required = sorted(TLD_MEMBERS)
    members = {
        "run_spec.json": canonical_json(run_spec, pretty=True),
        "ontology.json": canonical_json(
            {
                "schema_version": "1.0.0",
                "terms": {
                    "omega": "ordered ladder state",
                    "winner_N": "harmonic closure-mode label",
                    "T_e": "first registered observed/null separation depth",
                    "S_e": "persistence after emergence",
                },
                "non_equivalences": [
                    "winner_N != T_e",
                    "winner_N != S_e",
                    "interpolation != observation",
                    "TORUS-BROT != ToT-BROT",
                ],
            },
            pretty=True,
        ),
        "claim_boundary.json": canonical_json(
            {
                "claim_level": "COMPUTED_DYNAMICAL",
                "permitted_interpretations": [
                    "exact reproduction of the published computational outputs",
                    "registered structural escape, recovery, and ringing diagnostics",
                ],
                "excluded_interpretations": FORBIDDEN_CLAIMS,
                "experimental_tags": [HISTORICAL_LANE, "PUBLISHED_SOURCE_REPRODUCTION"],
                "independent_verifier_status": "independently_verified",
            },
            pretty=True,
        ),
        "visual_encoding.json": canonical_json(
            {
                "position": {"x": "registered step or alpha", "y": "trial or endpoint"},
                "color": "classification",
                "interpolation": {"method": "nearest", "used_for_metrics": False},
                "raw_samples_visible": True,
                "missing_cells_visible": True,
            },
            pretty=True,
        ),
        "scene_recipe.json": canonical_json(
            {
                "viewer": "TORUS Field Studio",
                "default_view": "field",
                "raw_samples_visible": True,
                "missing_regions_visible": True,
                "historical_and_modern_lanes_visually_distinct": True,
            },
            pretty=True,
        ),
        "source_registry.json": canonical_json(source_registry, pretty=True),
        "preregistration_contract.json": canonical_json(preregistration, pretty=True),
        "tld_profile.json": canonical_json(
            {
                "schema_version": "1.0.0",
                "profile": tbx_profile,
                "lane": HISTORICAL_LANE,
                "required_members": required,
                "classification_precedes_rendering": True,
                "interpolation_used_for_metrics": False,
            },
            pretty=True,
        ),
        "provenance/sources.jsonl": _jsonl([source_registry]),
        "provenance/transformations.jsonl": _jsonl(
            [
                {
                    "transformation_id": kernel_id,
                    "software_version": "0.2.1",
                    "seed": contract.seed,
                    "specification_sha256": specification_sha256,
                    "notebook_imported": False,
                }
            ]
        ),
        "provenance/verification_receipts.jsonl": _jsonl(
            [
                {
                    "run_id": run_id,
                    "status": "verified",
                    "verifier": verification["verifier"],
                    "result_sha256": verification["result_sha256"],
                }
            ]
        ),
        "registry/parent_registry.json": canonical_json(
            {
                "parent_id": parent_id,
                "domain_id": domain["domain_id"],
                "domain_sha256": domain_sha256,
                "claim_authority": "COMPUTED_DYNAMICAL",
            },
            pretty=True,
        ),
        "registry/ladder_registry.json": canonical_json(
            {"schema_version": "1.0.0", "ladders": result["registries"]["ladders"]},
            pretty=True,
        ),
        "registry/control_or_null_registry.json": canonical_json(
            result["registries"]["controls"], pretty=True
        ),
        "registry/null_registry.json": canonical_json([], pretty=True),
        "tables/field_points.json": canonical_json(
            {"schema_version": "1.0.0", "width": width, "height": height, "points": points}
        ),
        "tables/metrics_by_N.json": canonical_json(
            {"baseline": result["baseline"], "summary": statistics}, pretty=True
        ),
        "tables/tld_endpoint_table.json": canonical_json(endpoint_table, pretty=True),
        "tables/baseline_scores.json": canonical_json(result["baseline"], pretty=True),
        "tables/alpha_sweep.json": canonical_json(result["notebook13"]["alpha_sweep"], pretty=True),
        "tables/core_alpha_compare.json": canonical_json(result["notebook13"]["core"], pretty=True),
        "tables/preregistration_results.json": canonical_json(preregistration, pretty=True),
        "tables/trajectories.jsonl": _jsonl(result["notebook14"]["traces"]),
        "tables/transition_counts.json": canonical_json(
            result["notebook14"]["transition_counts"], pretty=True
        ),
        "tables/operating_envelope.json": canonical_json(
            result["notebook14"]["operating_envelope"], pretty=True
        ),
        "audit/audit.json": canonical_json(
            {
                "status": "independently_verified",
                "failure_preservation": "complete",
                "classification_precedes_rendering": True,
                "uncomputed_T_e_and_S_e_are_null": True,
            },
            pretty=True,
        ),
        "audit/failure_ledger.jsonl": _jsonl(failures),
        "audit/independent_verification.json": canonical_json(verification, pretty=True),
        "audit/claim_adjudication.json": canonical_json(claim_adjudication, pretty=True),
    }
    sums = "".join(f"{_sha256(payload)}  {path}\n" for path, payload in sorted(members.items()))
    members["audit/SHA256SUMS.txt"] = sums.encode()
    manifest = {
        "tbx_version": "1.0.0",
        "profile": tbx_profile,
        "run_id": run_id,
        "claim_level": "COMPUTED_DYNAMICAL",
        "kernel_id": kernel_id,
        "specification_sha256": specification_sha256,
        "statistics": statistics,
        "files": [
            {"path": path, "sha256": _sha256(payload), "bytes": len(payload)}
            for path, payload in sorted(members.items())
        ],
    }
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, payload in [
            ("manifest.json", canonical_json(manifest, pretty=True)),
            *sorted(members.items()),
        ]:
            info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload)
    return target


def export_historical_bundle_set(result: dict[str, Any], destination: str | Path) -> list[Path]:
    root = Path(destination)
    return [
        export_tld_bundle(
            result, "notebook13", root / "tld-i-notebook13-historical-reproduction.tbx.zip"
        ),
        export_tld_bundle(
            result, "notebook14", root / "tld-i-notebook14-historical-diagnostics.tbx.zip"
        ),
        export_tld_bundle(
            result, "combined", root / "tld-i-combined-historical-reproduction.tbx.zip"
        ),
    ]
