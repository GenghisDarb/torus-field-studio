from __future__ import annotations

import hashlib
import json
import math
import zipfile
from pathlib import Path
from typing import Any

from torusbrot.models import canonical_json, content_hash
from torusbrot.tld.contracts import HistoricalTldIContract
from torusbrot.tld.endpoints import preregistration_results
from torusbrot.tld.verification import EXPECTED_INPUT_HASHES


def _score(values: list[float], candidates: range) -> dict[str, Any]:
    chi = sum(math.log(value) / index for index, value in enumerate(values, 1))
    ordered = sorted(
        ((number, abs(chi - 2 * math.pi / number)) for number in candidates),
        key=lambda item: item[1],
    )
    return {
        "chi": chi,
        "winner_N": ordered[0][0],
        "winner_rms": ordered[0][1],
        "runner_N": ordered[1][0],
        "runner_rms": ordered[1][1],
        "margin": ordered[1][1] - ordered[0][1],
        "rms_by_N": dict(ordered),
    }


def _summary(alpha: float, returned: int) -> dict[str, Any]:
    trials = 10
    escape_steps = [1] * trials
    return_steps = [100] * returned
    flips = [5] * trials
    return {
        "alpha_heal": alpha,
        "trials": trials,
        "escaped_count": trials,
        "returned_count": returned,
        "escape_rate": 1.0,
        "return_rate_given_escape": returned / trials,
        "mean_escape_steps": 1.0,
        "mean_return_steps": 100.0,
        "mean_flips": 5.0,
        "p90_flips": 5.0,
        "competitors": {},
        "raw": {
            "escape_steps": escape_steps,
            "return_steps": return_steps,
            "flips": flips,
        },
    }


def compact_tld_result() -> dict[str, Any]:
    values = [1.1, 1.2, 1.3, 1.4]
    rows = [
        {"family": "fixture", "codata_name": f"row-{index}", "value": value, "sigma": 0.01}
        for index, value in enumerate(values)
    ]
    contract = HistoricalTldIContract()
    alpha0 = _summary(0.0, 4)
    alpha002 = _summary(0.02, 10)
    preregistration = preregistration_results(alpha0, alpha002, contract)
    trace_rows: list[dict[str, Any]] = []
    trace_summary = []
    for trial_id, alpha in enumerate((0.02, 0.02, 0.05, 0.05), 1):
        seed = 1000 + trial_id
        trace_summary.append(
            {
                "trial_id": trial_id,
                "alpha_heal": alpha,
                "seed": seed,
                "escaped": True,
                "escape_steps": 1,
                "returned": True,
                "return_steps": 1,
            }
        )
        for phase, step, winner in (("start", 0, 10), ("escape", 1, 9), ("heal", 1, 10)):
            trace_rows.append(
                {
                    "trial_id": trial_id,
                    "alpha_heal": alpha,
                    "seed": seed,
                    "phase": phase,
                    "t": step,
                    "chi": 0.62,
                    "winner_N": winner,
                    "winner_rms": 0.01,
                    "runner_N": 11,
                    "runner_rms": 0.05,
                    "margin": 0.04,
                }
            )
    envelope = []
    envelope_trials = []
    for strength in contract.envelope_p_swap:
        for index in range(2):
            envelope_trials.append(
                {
                    "p_swap_escape": strength,
                    "seed": 12000 + index,
                    "escaped": True,
                    "escape_steps": 1,
                    "returned": True,
                    "return_steps": 2,
                    "flips": 1,
                }
            )
        envelope.append(
            {
                "trials": 2,
                "p_swap_escape": strength,
                "eps_heal": 16.0,
                "alpha_heal": 0.02,
                "escape_rate": 1.0,
                "return_rate_given_escape": 1.0,
                "mean_return_steps": 2.0,
                "mean_flips": 1.0,
                "p90_flips": 1.0,
            }
        )
    source_values_hash = hashlib.sha256(b"fixture-values").hexdigest()
    canonicalization_hash = hashlib.sha256(b"fixture-canonicalization").hexdigest()
    perturbation_hash = hashlib.sha256(b"fixture-perturbation").hexdigest()
    parent = {
        "ladder_id": "ladder-fixture-parent",
        "domain_id": "torus-tld-i-baseline-v1",
        "kind": "observed_parent",
        "parent_ladder_id": None,
        "omega_construction_rule": "natural_log(value), source row order",
        "adjacency_topology": "ordered_path",
        "is_null": False,
        "eligible": True,
        "seed": 42,
        "source_values_hash": source_values_hash,
        "canonicalization_hash": canonicalization_hash,
        "perturbation_contract_hash": perturbation_hash,
        "notes": "Compact deterministic test fixture",
    }
    control = parent | {
        "ladder_id": "control-fixture-alpha-zero",
        "kind": "alpha_zero_mechanistic_control",
        "parent_ladder_id": parent["ladder_id"],
        "is_null": True,
        "eligible": False,
    }
    return {
        "schema_version": "1.0.0",
        "contract": contract.to_dict() | {"sha256": contract.sha256},
        "input_hashes": EXPECTED_INPUT_HASHES,
        "input_rows": rows,
        "registries": {"parents": [parent], "ladders": [parent], "controls": [control]},
        "baseline": {
            "sweep_2_30": _score(values, range(2, 31)),
            "window_7_13": _score(values, range(7, 14)),
        },
        "notebook13": {
            "core": [alpha0, alpha002],
            "alpha_sweep": [
                _summary(alpha, 10 if alpha > 0 else 4) for alpha in contract.alpha_sweep
            ],
            "preregistration": preregistration,
        },
        "notebook14": {
            "traces": trace_rows,
            "trace_summary": trace_summary,
            "transition_counts": [],
            "operating_envelope": envelope,
            "operating_envelope_trials": envelope_trials,
        },
    }


def read_members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}


def resign_bundle(path: Path, members: dict[str, bytes]) -> Path:
    manifest = json.loads(members["manifest.json"])
    specification = json.loads(members["run_spec.json"])
    parent = json.loads(members["registry/parent_registry.json"])
    manifest["specification_sha256"] = content_hash(specification)
    identity = {
        "specification": specification,
        "kernel_id": manifest["kernel_id"],
        "domain_sha256": parent.get("domain_sha256")
        if specification.get("engine") in {"local_brot", "tld"}
        else None,
    }
    manifest["run_id"] = f"run-{content_hash(identity)[:16]}"
    if "provenance/verification_receipts.jsonl" in members:
        receipts = [
            json.loads(line)
            for line in members["provenance/verification_receipts.jsonl"].splitlines()
            if line
        ]
        for receipt in receipts:
            receipt["run_id"] = manifest["run_id"]
        members["provenance/verification_receipts.jsonl"] = b"".join(
            canonical_json(receipt) for receipt in receipts
        )
    sums = "".join(
        f"{hashlib.sha256(payload).hexdigest()}  {name}\n"
        for name, payload in sorted(members.items())
        if name not in {"manifest.json", "audit/SHA256SUMS.txt"}
    )
    members["audit/SHA256SUMS.txt"] = sums.encode()
    manifest["files"] = [
        {
            "path": name,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        }
        for name, payload in sorted(members.items())
        if name != "manifest.json"
    ]
    members["manifest.json"] = canonical_json(manifest, pretty=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in [
            ("manifest.json", members.pop("manifest.json")),
            *sorted(members.items()),
        ]:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload)
    return path
