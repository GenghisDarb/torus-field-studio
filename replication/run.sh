#!/usr/bin/env sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
study="$repo/studies/heldout-v0.2.1"
source_path=${REPLICATION_SOURCE:-"$repo/external_cache/heldout-v0.2.1/PRSA2017_Data_20130301-20170228.zip"}
output=${REPLICATION_OUTPUT:-"$repo/results/external-replication"}
exe="$repo/.replication-venv/bin/torusbrot"
test -x "$exe" || { echo 'Run replication/setup.sh first.' >&2; exit 1; }
test -f "$source_path" || { echo 'Run replication/fetch.sh first.' >&2; exit 1; }
test ! -e "$output/scored/.scored_execution_started" || {
  echo "This attempt has already started. Preserve it and choose a new REPLICATION_OUTPUT: $output" >&2
  exit 1
}
implementation=$(git -C "$repo" rev-parse HEAD 2>/dev/null || printf 'v0.2.1-source-archive')
"$exe" materialize heldout-study --source "$source_path" --study "$study" --output "$output/materialized"
"$exe" authorize heldout-study --materialized "$output/materialized" --study "$study" --output "$output/scored" \
  --preregistration-commit f15422bc64b1b101150240e612621683b15b3606 --implementation-commit "$implementation"
"$exe" execute heldout-study --materialized "$output/materialized" --study "$study" --output "$output/scored"
"$exe" verify heldout-study --materialized "$output/materialized" --study "$study" --scored "$output/scored" --output "$output/verification"
"$exe" adjudicate heldout-study --scored "$output/scored" --verification "$output/verification" --output "$output/adjudication"
"$exe" publish heldout-study --scored "$output/scored" --verification "$output/verification" --adjudication "$output/adjudication" --output "$output/publication"
"$exe" package heldout-study --study "$study" --materialized "$output/materialized" --scored "$output/scored" \
  --verification "$output/verification" --adjudication "$output/adjudication" --publication "$output/publication" --output "$output/bundles"
"$repo/.replication-venv/bin/python" "$repo/replication/verify.py" --source "$source_path" --output "$output"
