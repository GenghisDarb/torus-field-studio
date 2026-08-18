"""Build the historical environment and execute the untouched TLD I notebooks in order."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import time
import venv
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RUNNER_PACKAGES = ["nbclient>=0.10,<0.11", "nbformat>=5.10,<6", "ipykernel>=6.29,<7"]
EXPECTED_OUTPUTS = {
    13: [
        "notebook13_core_alpha_compare.csv",
        "notebook13_alpha_sweep.csv",
        "notebook13_prereg_eval.csv",
        "notebook13_run_summary.json",
    ],
    14: [
        "notebook14_config.json",
        "notebook14_pswap_envelope.csv",
        "notebook14_trace_summary.csv",
        "notebook14_trace_trials.csv",
        "notebook14_transition_counts.csv",
    ],
}
NOTEBOOK_NAMES = {
    13: "TORUS Ladder Validation Notebook 13.ipynb",
    14: "TORUS Ladder Validation Notebook 14.ipynb",
}
INPUT_NAMES = [
    "targets_baseline.csv",
    "targets_metadata_template.csv",
    "targets_metadata_addon.csv",
]


def now() -> str:
    return datetime.now(UTC).isoformat()


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def require_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode:
        raise RuntimeError(
            f"{label} failed ({result.returncode})\n{result.stdout}\n{result.stderr}"
        )


def verify_contract_lock(contract_root: Path) -> dict[str, str]:
    expected: dict[str, str] = {}
    for line in (
        (contract_root / "SHA256SUMS_CONTRACTS.txt").read_text(encoding="utf-8").splitlines()
    ):
        value, name = line.split(maxsplit=1)
        expected[name.strip()] = value
    actual = {name: sha256(contract_root / name) for name in expected}
    if actual != expected:
        raise RuntimeError("Frozen contract hashes changed before execution")
    return actual


def inventory(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return rows


def collect_notebook_logs(
    executed: Path, stdout_path: Path, stderr_path: Path, errors_path: Path
) -> int:
    notebook = json.loads(executed.read_text(encoding="utf-8"))
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    errors: list[dict[str, Any]] = []
    for cell_index, cell in enumerate(notebook.get("cells", [])):
        for output in cell.get("outputs", []):
            if output.get("output_type") == "stream":
                value = "".join(output.get("text", []))
                (stderr_parts if output.get("name") == "stderr" else stdout_parts).append(value)
            elif output.get("output_type") == "error":
                errors.append(
                    {
                        "cell_index": cell_index,
                        "ename": output.get("ename"),
                        "evalue": output.get("evalue"),
                        "traceback": output.get("traceback", []),
                    }
                )
    stdout_path.write_text("".join(stdout_parts), encoding="utf-8")
    stderr_path.write_text("".join(stderr_parts), encoding="utf-8")
    write_json(errors_path, errors)
    return len(errors)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--contracts", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--runtime-package", type=Path, required=True)
    args = parser.parse_args()

    repository = Path.cwd().resolve()
    source_root = args.source_root.resolve(strict=True)
    contracts = args.contracts.resolve(strict=True)
    results = args.results.resolve()
    environment = args.environment.resolve()
    runtime_package = args.runtime_package.resolve(strict=True)
    if results.exists():
        raise RuntimeError(f"Historical results target already exists: {results}")
    if environment.exists():
        raise RuntimeError(f"Historical environment target already exists: {environment}")
    contract_hashes = verify_contract_lock(contracts)

    results.mkdir(parents=True)
    environment_log = results / "environment_install"
    environment_log.mkdir()
    install_started = now()
    venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / "Scripts" / "python.exe"
    requirements = source_root / "env" / "requirements.txt"
    install = run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "-r",
            str(requirements),
            *RUNNER_PACKAGES,
        ]
    )
    (environment_log / "pip_install.stdout.txt").write_text(install.stdout, encoding="utf-8")
    (environment_log / "pip_install.stderr.txt").write_text(install.stderr, encoding="utf-8")
    require_success(install, "historical environment installation")
    freeze = run([str(python), "-m", "pip", "freeze", "--all"])
    require_success(freeze, "pip freeze")
    (results / "historical_environment.lock.txt").write_text(freeze.stdout, encoding="utf-8")
    version = run(
        [
            str(python),
            "-c",
            (
                "import json,platform,sys; print(json.dumps({'python':sys.version,"
                "'implementation':platform.python_implementation()}))"
            ),
        ]
    )
    require_success(version, "environment version probe")

    input_hashes = {name: sha256(source_root / "data_inputs" / name) for name in INPUT_NAMES}
    execution_results: dict[int, dict[str, Any]] = {}
    helper = repository / "scripts" / "execute_tld_i_notebook.py"
    for number in (13, 14):
        notebook_root = results / f"notebook{number}"
        original_root = notebook_root / "original"
        workspace = notebook_root / "workspace"
        logs = notebook_root / "logs"
        for directory in (original_root, workspace, logs):
            directory.mkdir(parents=True)

        source_notebook = source_root / "notebooks" / NOTEBOOK_NAMES[number]
        original_notebook = original_root / source_notebook.name
        workspace_notebook = workspace / source_notebook.name
        shutil.copy2(source_notebook, original_notebook)
        shutil.copy2(source_notebook, workspace_notebook)
        for name in INPUT_NAMES:
            shutil.copy2(source_root / "data_inputs" / name, workspace / name)

        source_before = sha256(source_notebook)
        inputs_before = {name: sha256(workspace / name) for name in INPUT_NAMES}
        executed_notebook = notebook_root / f"notebook{number}_executed.ipynb"
        command = [
            str(python),
            str(helper),
            "--input",
            str(workspace_notebook),
            "--output",
            str(executed_notebook),
            "--cwd",
            str(workspace),
            "--timeout",
            "1200",
        ]
        started_at = now()
        started = time.perf_counter()
        result = run(command, cwd=workspace)
        duration = time.perf_counter() - started
        completed_at = now()
        (logs / "runner.stdout.txt").write_text(result.stdout, encoding="utf-8")
        (logs / "runner.stderr.txt").write_text(result.stderr, encoding="utf-8")

        error_count = None
        if executed_notebook.exists():
            error_count = collect_notebook_logs(
                executed_notebook,
                logs / "cell_stdout.txt",
                logs / "cell_stderr.txt",
                logs / "cell_errors.json",
            )
        inputs_after = {name: sha256(workspace / name) for name in INPUT_NAMES}
        source_after = sha256(source_notebook)
        expected_outputs = {name: (workspace / name).exists() for name in EXPECTED_OUTPUTS[number]}
        run_status = (
            "passed"
            if result.returncode == 0 and error_count == 0 and all(expected_outputs.values())
            else "failed"
        )
        receipt = {
            "schema_version": "1.0.0",
            "notebook": number,
            "status": run_status,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_seconds": duration,
            "return_code": result.returncode,
            "cell_error_count": error_count,
            "memory_usage": {
                "captured": False,
                "reason": (
                    "kernel-process peak memory not available without instrumenting the "
                    "historical code"
                ),
            },
            "command": [
                "<HISTORICAL_ENV>/python.exe",
                "scripts/execute_tld_i_notebook.py",
                "--input",
                "<WORKSPACE>/notebook.ipynb",
                "--output",
                f"notebook{number}_executed.ipynb",
                "--cwd",
                "<WORKSPACE>",
                "--timeout",
                "1200",
            ],
            "source_notebook": {
                "sha256_before": source_before,
                "sha256_after": source_after,
                "unchanged": source_before == source_after,
                "preserved_original_copy_sha256": sha256(original_notebook),
                "executed_notebook_sha256": sha256(executed_notebook)
                if executed_notebook.exists()
                else None,
            },
            "inputs": {
                name: {
                    "sha256_before": inputs_before[name],
                    "sha256_after": inputs_after[name],
                    "unchanged": inputs_before[name] == inputs_after[name],
                }
                for name in INPUT_NAMES
            },
            "expected_outputs": expected_outputs,
            "stdout_sha256": sha256(logs / "runner.stdout.txt"),
            "stderr_sha256": sha256(logs / "runner.stderr.txt"),
            "frozen_contract_hashes": contract_hashes,
        }
        receipt_path = notebook_root / f"notebook{number}_execution_receipt.json"
        write_json(receipt_path, receipt)
        generated_manifest = inventory(workspace)
        write_json(
            notebook_root / f"notebook{number}_generated_member_manifest.json", generated_manifest
        )
        execution_results[number] = receipt

    parsed_version = json.loads(version.stdout)
    historical_environment = {
        "schema_version": "1.0.0",
        "created_at": install_started,
        "operating_system": platform.platform(),
        "machine": platform.machine(),
        "python": parsed_version,
        "historical_environment_description": (
            "Google Colab Linux, Python 3.10.x; descriptive rather than prescriptive"
        ),
        "selected_runtime": (
            "Python 3.10.11 from the official Python NuGet package, isolated under ignored "
            "external_cache"
        ),
        "runtime_package": {
            "source": "https://www.nuget.org/api/v2/package/python/3.10.11",
            "sha256": sha256(runtime_package),
        },
        "source_requirements_sha256": sha256(requirements),
        "runner_packages": RUNNER_PACKAGES,
        "environment_lock": "historical_environment.lock.txt",
        "environment_lock_sha256": sha256(results / "historical_environment.lock.txt"),
        "archive": {
            "md5": "25f26f78bf6c73df1e551983af518e9a",
            "sha256": "5bae9af506bd65e74225fc91f869931d70fcd89505cbc672b3538abdfd4b446e",
        },
        "notebook_hashes": {
            str(number): execution_results[number]["source_notebook"]["sha256_before"]
            for number in (13, 14)
        },
        "input_hashes": input_hashes,
    }
    write_json(results / "historical_environment.json", historical_environment)
    write_json(
        results / "historical_compatibility_assessment.json",
        {
            "schema_version": "1.0.0",
            "original_notebooks_modified": False,
            "compatibility_patch_created": False,
            "compatibility_patch_required": any(
                execution_results[number]["status"] != "passed" for number in (13, 14)
            ),
            "notebook13_status": execution_results[13]["status"],
            "notebook14_status": execution_results[14]["status"],
            "assessment": (
                "Original notebooks executed on the historical Python minor line; exact dependency "
                "pins were unavailable in the source archive."
            ),
        },
    )
    write_json(
        results / "historical_execution_summary.json",
        {
            "schema_version": "1.0.0",
            "execution_order": [13, 14],
            "notebook13_status": execution_results[13]["status"],
            "notebook14_status": execution_results[14]["status"],
            "all_expected_outputs_present": all(
                all(execution_results[number]["expected_outputs"].values()) for number in (13, 14)
            ),
            "contracts_unchanged": verify_contract_lock(contracts) == contract_hashes,
        },
    )
    sums = []
    for path in sorted(
        item
        for item in results.rglob("*")
        if item.is_file() and item.name != "SHA256SUMS_HISTORICAL.txt"
    ):
        sums.append(f"{sha256(path)}  {path.relative_to(results).as_posix()}")
    (results / "SHA256SUMS_HISTORICAL.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "notebook13": execution_results[13]["status"],
                "notebook14": execution_results[14]["status"],
                "results": "<REPOSITORY>/results/tld-i/historical",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
