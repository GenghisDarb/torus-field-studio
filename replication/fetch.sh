#!/usr/bin/env sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
source_path=${REPLICATION_SOURCE:-"$repo/external_cache/heldout-v0.2.1/PRSA2017_Data_20130301-20170228.zip"}
test -x "$repo/.replication-venv/bin/torusbrot" || { echo 'Run replication/setup.sh first.' >&2; exit 1; }
"$repo/.replication-venv/bin/torusbrot" fetch heldout-source --output "$source_path"
