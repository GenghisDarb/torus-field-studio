from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare cross-platform determinism digests")
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    files = sorted(args.directory.rglob("*.sha256"))
    if len(files) < 3:
        raise ValueError(f"Expected three platform digests, found {len(files)}")
    values = {path.read_text(encoding="ascii").strip() for path in files}
    for path in files:
        print(f"{path.name}: {path.read_text(encoding='ascii').strip()}")
    if len(values) != 1:
        raise ValueError("Bundle output differs across operating systems")
    print("Cross-platform bundle determinism verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
