# Outside replication package

This package lets a team with no access to Brad's local files fetch the registered UCI source,
build and install the TORUS Field Studio wheel, run the frozen v0.2.1 Beijing PM2.5 study into a
fresh directory, independently recompute its endpoints, and audit all three TBX bundles.

Running these scripts is a **replication attempt**. It is not `EXTERNALLY_VALIDATED` until an
independent outside party executes the package and reports agreement. The scripts do not embed an
expected positive result or substitute a candidate, endpoint, threshold, seed, or N grid.

## Requirements

- Python 3.11, 3.12, or 3.13
- Git checkout of the v0.2.1 tag (or its source archive)
- Network access to UCI and PyPI during setup/fetch
- Roughly 1 GB of free disk space

## Windows PowerShell

Run from the repository root:

```powershell
.\replication\setup.ps1
.\replication\fetch.ps1
.\replication\run.ps1
.\replication\verify.ps1
```

Each stage is one command. `run.ps1` refuses to reuse an output directory whose scored execution
has started. To make another attempt, choose a new `-Output` path; never delete or overwrite a
completed attempt.

## macOS or Linux

Run from the repository root:

```bash
./replication/setup.sh
./replication/fetch.sh
./replication/run.sh
./replication/verify.sh
```

The default output is `results/external-replication`, and the downloaded source is kept under
`external_cache/heldout-v0.2.1`. Override those paths with the documented script arguments or the
`REPLICATION_OUTPUT` and `REPLICATION_SOURCE` environment variables on Unix.

## What the run does

The run uses the console script from `.replication-venv`, which is installed from the locally
built wheel rather than an editable source tree. It performs registry-first materialization,
authorizes one fresh execution identity, executes it once, invokes the separately implemented
endpoint verifier and mutation suite, adjudicates the result, creates publication files, packages
the primary/specificity/combined TBX archives, and audits each archive.

Floating-point byte identity is not treated as scientific truth across platforms. Verification
freezes source and contract hashes, exact registries and discrete classifications, and compares
numeric endpoint values at the verifier's declared narrow tolerance. Raw platform output remains
in the attempt directory; values are not rounded to manufacture equality.

## Reporting agreement or disagreement

Copy `report_template.json`, fill every field, retain the complete output directory, and attach
the completed report plus `replication-verification-report.json` to a GitHub issue. Report any
disagreement exactly as observed; do not tune a threshold, rerun into the same directory, or
replace the selected dataset. A disagreement does not invalidate or overwrite the canonical
v0.2.1 record—it opens an audit of custody, environment, and implementation differences.

The expected paths, not expected scientific outcomes, are listed in
`expected_artifact_inventory.json`. `SHA256SUMS.txt` authenticates the replication-package files.
