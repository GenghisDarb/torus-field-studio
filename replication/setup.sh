#!/usr/bin/env sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo"
python3 -m venv .replication-venv
py="$repo/.replication-venv/bin/python"
"$py" -m pip install --disable-pip-version-check --requirement replication/environment_lock
"$py" -m build
wheel=$(find "$repo/dist" -maxdepth 1 -type f -name 'torusbrot-*.whl' | sort | tail -n 1)
test -n "$wheel" || { echo 'No TORUS wheel was built.' >&2; exit 1; }
"$py" -m pip install --disable-pip-version-check --no-deps --force-reinstall "$wheel"
"$repo/.replication-venv/bin/torusbrot" --help >/dev/null
printf 'Installed replication wheel: %s\n' "$(basename "$wheel")"
