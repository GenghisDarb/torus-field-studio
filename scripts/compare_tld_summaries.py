from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def compare(left: Any, right: Any, path: str = "$") -> list[str]:
    if isinstance(left, bool) or isinstance(right, bool):
        return [] if left is right else [path]
    if isinstance(left, int) and isinstance(right, int):
        return [] if left == right else [path]
    if isinstance(left, int | float) and isinstance(right, int | float):
        return [] if math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12) else [path]
    if isinstance(left, dict) and isinstance(right, dict):
        if left.keys() != right.keys():
            return [path + ".keys"]
        return [
            mismatch for key in left for mismatch in compare(left[key], right[key], f"{path}.{key}")
        ]
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return [path + ".length"]
        return [
            mismatch
            for index, (left_item, right_item) in enumerate(zip(left, right))
            for mismatch in compare(left_item, right_item, f"{path}[{index}]")
        ]
    return [] if left == right else [path]


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare cross-platform TLD summaries")
    parser.add_argument("directory")
    args = parser.parse_args()
    paths = sorted(Path(args.directory).glob("*.json"))
    if len(paths) < 3:
        raise ValueError(f"Expected at least three platform summaries, found {len(paths)}")
    reference = json.loads(paths[0].read_text(encoding="utf-8"))
    failures = {
        path.name: compare(reference, json.loads(path.read_text(encoding="utf-8")))
        for path in paths[1:]
    }
    failures = {name: values for name, values in failures.items() if values}
    if failures:
        print(json.dumps(failures, indent=2))
        return 1
    print(f"{len(paths)} TLD summaries agree within frozen 1e-12 tolerance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
