#!/usr/bin/env sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
source_path=${REPLICATION_SOURCE:-"$repo/external_cache/heldout-v0.2.1/PRSA2017_Data_20130301-20170228.zip"}
output=${REPLICATION_OUTPUT:-"$repo/results/external-replication"}
test -x "$repo/.replication-venv/bin/python" || { echo 'Run replication/setup.sh first.' >&2; exit 1; }
"$repo/.replication-venv/bin/python" "$repo/replication/verify.py" --source "$source_path" --output "$output"
