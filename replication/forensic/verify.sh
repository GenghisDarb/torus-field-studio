#!/usr/bin/env sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
"$repo/.venv/bin/python" "$repo/replication/forensic/verify.py" --assets "$1"
