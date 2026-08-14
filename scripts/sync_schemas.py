from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path

ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "schemas"
DESTINATION = ROOT / "python" / "torusbrot" / "schemas"


def schema_files(root: Path) -> dict[Path, Path]:
    return {path.relative_to(root): path for path in root.rglob("*.json")}


def check() -> list[str]:
    source_files = schema_files(SOURCE)
    destination_files = schema_files(DESTINATION)
    errors: list[str] = []
    for relative_path, source in sorted(source_files.items()):
        destination = destination_files.get(relative_path)
        if destination is None:
            errors.append(f"missing packaged schema: {relative_path}")
        elif not filecmp.cmp(source, destination, shallow=False):
            errors.append(f"schema differs: {relative_path}")
    for relative_path in sorted(destination_files.keys() - source_files.keys()):
        errors.append(f"orphan packaged schema: {relative_path}")
    return errors


def sync() -> None:
    for relative_path, source in schema_files(SOURCE).items():
        destination = DESTINATION / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize packaged JSON Schemas")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        errors = check()
        if errors:
            print("\n".join(errors))
            return 1
        print("Packaged schemas match the authoritative schemas directory.")
        return 0
    sync()
    print(f"Synchronized schemas into {DESTINATION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
