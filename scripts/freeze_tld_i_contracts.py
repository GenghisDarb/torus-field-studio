"""Freeze the source-only TLD I historical reproduction contract before execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def notebook_source(path: Path) -> tuple[list[dict[str, Any]], str]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    cells = [
        {
            "cell_index": index,
            "cell_type": cell["cell_type"],
            "source": "".join(cell.get("source", [])),
        }
        for index, cell in enumerate(notebook["cells"])
    ]
    canonical = json.dumps(cells, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return cells, sha256_bytes(canonical.encode("utf-8"))


def source_at(cells: list[dict[str, Any]], index: int) -> str:
    return str(cells[index]["source"])


def require(source: str, *snippets: str) -> None:
    missing = [snippet for snippet in snippets if snippet not in source]
    if missing:
        raise RuntimeError(f"Historical notebook source changed; missing snippets: {missing}")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def lock_read_only(path: Path) -> None:
    os.chmod(path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--archive-identity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.source_root.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise RuntimeError(f"Contract output already exists: {output}")

    notebook13 = root / "notebooks" / "TORUS Ladder Validation Notebook 13.ipynb"
    notebook14 = root / "notebooks" / "TORUS Ladder Validation Notebook 14.ipynb"
    prereg_document = root / "docs" / "PREREG_CRITERIA.md"
    requirements = root / "env" / "requirements.txt"
    environment_report = root / "env" / "environment_report.txt"
    archive_identity = json.loads(args.archive_identity.read_text(encoding="utf-8"))
    cells13, source_hash13 = notebook_source(notebook13)
    cells14, source_hash14 = notebook_source(notebook14)

    # Source assertions make the manually reviewed extraction fail closed if the archive changes.
    require(
        source_at(cells13, 1), "SEED = 42", "np.random.default_rng(SEED)", "np.random.seed(SEED)"
    )
    require(
        source_at(cells13, 3),
        'BASELINE_CSV = "targets_baseline.csv"',
        'META_TEMPLATE_CSV = "targets_metadata_template.csv"',
        'META_ADDON_CSV = "targets_metadata_addon.csv"',
    )
    require(source_at(cells13, 5), "omega0 = np.log(values)", "sigma_omega = sigmas_value / values")
    require(source_at(cells13, 7), "1.0 / np.arange(1, K + 1", "abs(chi_val - (2.0 * math.pi / N))")
    require(source_at(cells13, 9), "N_SWEEP = list(range(2, 31))")
    require(
        source_at(cells13, 11),
        '"p_swap_escape": 0.02',
        '"max_escape_steps": 60',
        '"required_escape_rate_min": 0.90',
        '"required_return_rate_max": 0.40',
        '"alpha_heal": 0.02',
        '"required_return_rate_min": 0.95',
        '"required_mean_return_steps_max": 120',
        '"required_p90_flips_max": 5',
    )
    require(
        source_at(cells13, 13), "for i in range(K - 1)", "out[i], out[i+1]", "eps * sigma_omega * z"
    )
    require(source_at(cells13, 16), "N_WINDOW = list(range(7, 14))", "N_center=10")
    require(
        source_at(cells13, 18),
        "TRIALS = 400",
        "MAX_HEAL = 300",
        "EPS_HEAL = 16.0",
        "alpha_heal=0.0",
        "alpha_heal=0.02",
    )
    require(
        source_at(cells13, 22), "ALPHA_LIST = [0.0, 0.005, 0.01, 0.02, 0.05, 0.1]", "trials=250"
    )
    require(
        source_at(cells13, 26),
        'out_core_csv = "notebook13_core_alpha_compare.csv"',
        'out_alpha_csv = "notebook13_alpha_sweep.csv"',
        'out_eval_csv = "notebook13_prereg_eval.csv"',
        'out_summary_json = "notebook13_run_summary.json"',
    )

    require(source_at(cells14, 1), "GLOBAL_SEED = 42", "np.random.default_rng(GLOBAL_SEED)")
    require(source_at(cells14, 2), "omega0 = np.log(values)", "sigmas / values")
    require(source_at(cells14, 5), "np.sum(omega / k)", "abs(chi - target)")
    require(source_at(cells14, 6), "N_CENTER = 10", "N_WINDOW = list(range(7, 14))")
    require(
        source_at(cells14, 8), "for i in range(K)", "rng.integers(0, K)", "eps * sigma_omega * z"
    )
    require(
        source_at(cells14, 11),
        "TRACE_TRIALS = 10",
        "P_SWAP_ESCAPE = 0.02",
        "MAX_ESCAPE_STEPS = 60",
        "EPS_HEAL = 16.0",
        "MAX_HEAL_STEPS = 500",
        "ALPHAS = [0.02, 0.05]",
        "seed = 1000 + 100*int(alpha*100) + j",
    )
    require(
        source_at(cells14, 12),
        'to_csv("notebook14_trace_trials.csv"',
        'to_csv("notebook14_trace_summary.csv"',
    )
    require(source_at(cells14, 15), 'to_csv("notebook14_transition_counts.csv"')
    require(
        source_at(cells14, 17),
        "PSWAP_LIST = [0.005, 0.01, 0.02, 0.03]",
        "ALPHA_FIXED = 0.02",
        "trials=300",
        "seed0=12000 + int(ps*100000)",
        'to_csv("notebook14_pswap_envelope.csv"',
    )
    require(source_at(cells14, 19), 'with open("notebook14_config.json"')

    frozen_at = datetime.now(UTC).isoformat()
    source_identity = {
        "doi": "10.5281/zenodo.18080090",
        "archive_md5": archive_identity["md5"],
        "archive_sha256": archive_identity["sha256"],
        "notebook13_sha256": sha256_file(notebook13),
        "notebook13_source_only_sha256": source_hash13,
        "notebook14_sha256": sha256_file(notebook14),
        "notebook14_source_only_sha256": source_hash14,
        "preregistration_document_sha256": sha256_file(prereg_document),
        "requirements_sha256": sha256_file(requirements),
        "environment_report_sha256": sha256_file(environment_report),
    }
    tolerances = {
        "discrete_values": "exact equality",
        "booleans_and_labels": "exact equality",
        "row_order_and_membership": "exact equality",
        "serialized_source_and_input_identity": "exact SHA-256 equality",
        "floating_point": {"absolute": 1e-12, "relative": 1e-12},
        "timestamps": "excluded from semantic comparison but preserved verbatim",
        "missing_or_nonfinite": "never coerced; exact blocker",
    }
    historical = {
        "schema_version": "1.0.0",
        "frozen_at": frozen_at,
        "frozen_before_execution": True,
        "lane": "HISTORICAL_PUBLISHED_RELEASE_REPRODUCTION",
        "question": [
            "Does the exact public release reproduce its own preregistered Notebook 13 result?",
            (
                "Does Notebook 14 reproduce its diagnostic tracing, transition, ringing, and "
                "operating-envelope results?"
            ),
        ],
        "not_a_new_held_out_test": True,
        "execution_order": [13, 14],
        "source_identity": source_identity,
        "tolerances": tolerances,
        "environment": {
            "historical_python": "3.10.x (Google Colab, descriptive)",
            "requirements": requirements.read_text(encoding="utf-8").splitlines(),
            "float": "IEEE-754 float64",
            "processor": "CPU",
            "parallelism": "none declared",
        },
        "known_pre_execution_discrepancies": [
            {
                "code": "HISTORICAL_MAX_HEAL_STEPS_DECLARATION_MISMATCH",
                "document": "docs/PREREG_CRITERIA.md declares max_heal_steps = 400",
                "notebook13_effective_core_and_sweep": 300,
                "handling": (
                    "execute the untouched notebook at 300; preserve the discrepancy for "
                    "adjudication"
                ),
            },
            {
                "code": "README_NOTEBOOK_FILENAMES_DIFFER_FROM_ARCHIVE",
                "documented_names": [
                    "Notebook_13_Public_Structural_Escape_Healing.ipynb",
                    "Notebook_14_Diagnostics_Ringing_Envelope.ipynb",
                ],
                "archive_names": [notebook13.name, notebook14.name],
                "handling": (
                    "use the hashed notebooks actually present in the authoritative archive"
                ),
            },
        ],
    }
    notebook13_contract = {
        "schema_version": "1.0.0",
        "frozen_at": frozen_at,
        "notebook": notebook13.name,
        "identity": {
            "sha256": source_identity["notebook13_sha256"],
            "source_only_sha256": source_hash13,
        },
        "inputs": [
            "targets_baseline.csv",
            "targets_metadata_template.csv",
            "targets_metadata_addon.csv",
        ],
        "seed": 42,
        "randomness": (
            "one shared numpy Generator, plus numpy legacy global seed; no reset between conditions"
        ),
        "transform": {"omega": "natural_log(value)", "sigma_omega": "sigma_value / value"},
        "row_order": "input CSV order, reset_index(drop=True); no outcome-dependent reordering",
        "scoring": {
            "chi": "sum((1/k) * omega_k) for k=1..K",
            "rms": "abs(chi - 2*pi/N)",
            "winner_N": "N with minimum RMS",
            "margin": "runner_RMS - winner_RMS",
        },
        "baseline_sweep": {"N_inclusive": [2, 30]},
        "closure": {
            "N_window_inclusive": [7, 13],
            "winner_N": 10,
            "min_margin": "computed deterministic baseline margin on the same window",
            "max_rms": None,
        },
        "escape": {
            "operator": "single left-to-right pass of adjacent swaps i<->i+1, each with p_swap",
            "p_swap": 0.02,
            "max_steps": 60,
        },
        "healing": {
            "noise": "omega += eps * sigma_omega * standard_normal for every rung",
            "eps": 16.0,
            "anchoring": "omega <- (1-alpha)*omega + alpha*omega0",
            "effective_max_steps": 300,
            "external_prereg_document_max_steps": 400,
        },
        "core": {"trials": 400, "alphas_in_order": [0.0, 0.02]},
        "alpha_sweep": {
            "trials_per_alpha": 250,
            "alphas_in_order": [0.0, 0.005, 0.01, 0.02, 0.05, 0.1],
        },
        "preregistered_criteria": {
            "escape_rate_min": 0.90,
            "alpha0_return_rate_given_escape_max": 0.40,
            "alpha002_return_rate_given_escape_min": 0.95,
            "alpha002_mean_return_steps_max": 120,
            "alpha002_p90_flips_max": 5,
        },
        "ringing_metric": (
            "winner_N changes between consecutive healing steps, p90 over escaped trials"
        ),
        "outputs": [
            "notebook13_core_alpha_compare.csv",
            "notebook13_alpha_sweep.csv",
            "notebook13_prereg_eval.csv",
            "notebook13_run_summary.json",
        ],
    }
    notebook14_contract = {
        "schema_version": "1.0.0",
        "frozen_at": frozen_at,
        "notebook": notebook14.name,
        "identity": {
            "sha256": source_identity["notebook14_sha256"],
            "source_only_sha256": source_hash14,
        },
        "diagnostic_not_preregistered_pass_fail": True,
        "inputs": {
            "required": ["targets_baseline.csv"],
            "optional": ["targets_metadata_template.csv", "targets_metadata_addon.csv"],
            "notebook13_outputs_required": False,
        },
        "global_seed": 42,
        "transform": {"omega": "natural_log(value)", "sigma_omega": "sigma_value / value"},
        "scoring_and_closure": (
            "same formulas and N=7..13, center=10, baseline-margin lock as Notebook 13"
        ),
        "escape": {
            "operator": (
                "for every rung i, with p_swap choose uniform random j in [0,K) and swap i<->j"
            ),
            "operator_differs_from_notebook13": True,
            "p_swap": 0.02,
            "max_steps": 60,
        },
        "healing": {
            "eps": 16.0,
            "max_steps": 500,
            "anchoring": "omega <- omega + alpha*(omega0-omega)",
        },
        "trajectory_traces": {
            "trials_per_alpha": 10,
            "alphas_in_order": [0.02, 0.05],
            "seeds": {"alpha_0.02": list(range(1200, 1210)), "alpha_0.05": list(range(1500, 1510))},
            "fields": [
                "phase",
                "t",
                "chi",
                "winner_N",
                "winner_rms",
                "runner_N",
                "runner_rms",
                "margin",
            ],
        },
        "transition_metric": (
            "counts of consecutive winner_N pairs during healing, grouped by alpha"
        ),
        "operating_envelope": {
            "p_swap_in_order": [0.005, 0.01, 0.02, 0.03],
            "alpha": 0.02,
            "trials_per_p_swap": 300,
            "seed0_by_p_swap": {"0.005": 12500, "0.01": 13000, "0.02": 14000, "0.03": 15000},
            "metrics": [
                "escape_rate",
                "return_rate_given_escape",
                "mean_return_steps",
                "mean_flips",
                "p90_flips",
            ],
        },
        "outputs": [
            "notebook14_config.json",
            "notebook14_pswap_envelope.csv",
            "notebook14_trace_summary.csv",
            "notebook14_trace_trials.csv",
            "notebook14_transition_counts.csv",
        ],
    }

    inputs = {}
    for name in (
        "targets_baseline.csv",
        "targets_metadata_template.csv",
        "targets_metadata_addon.csv",
    ):
        path = root / "data_inputs" / name
        inputs[name] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    input_output_contract = {
        "schema_version": "1.0.0",
        "frozen_at": frozen_at,
        "inputs": inputs,
        "working_directory_contract": (
            "fresh copied workspace containing notebook and exact input bytes"
        ),
        "outputs": {
            "notebook13": notebook13_contract["outputs"],
            "notebook14": notebook14_contract["outputs"],
        },
        "published_reference_paths": {
            "notebook13": "data_outputs_notebook13",
            "notebook14": "data_outputs_notebook14",
        },
        "no_result_values_copied_into_contract": True,
    }
    claim_boundary = {
        "schema_version": "1.0.0",
        "frozen_at": frozen_at,
        "before_execution": True,
        "historical_lane_maximum": "COMPUTED_DYNAMICAL",
        "modern_lane_maximum_if_all_governance_gates_pass": "TLD_DERIVED",
        "externally_validated_permitted": False,
        "analytic_z14_claim": "ILLUSTRATIVE_ANALYTIC",
        "winner_N_is_not": ["T_e", "S_e", "time", "scale"],
        "T_e_and_S_e_policy": (
            "NOT_APPLICABLE unless separately computed under registered definitions"
        ),
        "forbidden_claims": [
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
        ],
    }

    output.mkdir(parents=True)
    documents = {
        "tld_i_historical_reproduction_contract.json": historical,
        "notebook13_prereg_contract.json": notebook13_contract,
        "notebook14_diagnostic_contract.json": notebook14_contract,
        "input_output_contract.json": input_output_contract,
        "claim_boundary_before_execution.json": claim_boundary,
    }
    for name, value in documents.items():
        write_json(output / name, value)
    hashes = {name: sha256_file(output / name) for name in documents}
    checksum = output / "SHA256SUMS_CONTRACTS.txt"
    checksum.write_text(
        "".join(f"{value}  {name}\n" for name, value in sorted(hashes.items())), encoding="utf-8"
    )
    for name in documents:
        lock_read_only(output / name)
    lock_read_only(checksum)
    print(
        json.dumps(
            {"status": "frozen_read_only", "contracts": hashes, "source_identity": source_identity},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
