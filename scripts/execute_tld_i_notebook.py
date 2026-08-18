"""Execute one copied historical notebook while preserving a partial notebook on failure."""

from __future__ import annotations

import argparse
import traceback
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=1200)
    args = parser.parse_args()

    notebook = nbformat.read(args.input, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=args.timeout,
        kernel_name="python3",
        resources={"metadata": {"path": str(args.cwd.resolve())}},
        allow_errors=False,
        record_timing=True,
    )
    exit_code = 0
    try:
        client.execute(cwd=str(args.cwd.resolve()))
    except Exception:  # noqa: BLE001 - preserving arbitrary historical cell failures is the point
        traceback.print_exc()
        exit_code = 1
    finally:
        nbformat.write(notebook, args.output)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
