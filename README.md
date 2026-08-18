# TORUS Field Studio

> Every beautiful structure should trace back to a frozen computation.

TORUS Field Studio is a local-first scientific workbench for generating, inspecting, and
auditing geometric field artifacts. The v0.2.1 release deliberately separates four lanes:

- **Analytic Sandbox** — reproducible `z -> z^p + c` fields with an explicit
  `ILLUSTRATIVE_ANALYTIC` claim badge.
- **TORUS-BROT** — a deterministic registered-ladder reference kernel with matched nulls,
  structural escape, recovery, ringing, `T_e`, `S_e`, `winner_N`, UI, NSS, and SEP retained
  as separate values.
- **TLD I published-source reproduction** — an exact, independently checked reproduction of
  the confirmatory Zenodo release at DOI `10.5281/zenodo.18080090`, capped at
  `COMPUTED_DYNAMICAL`.
- **Held-out Beijing PM2.5 study** — a prospectively frozen, parent-matched test on 12 UCI
  monitoring stations. Its valid negative result is capped at `COMPUTED_DYNAMICAL`.

The image is downstream of the artifact: classification is computed before rendering,
interpolation never creates observations, and every exported bundle includes a SHA-256
manifest, run specification, visual encoding, provenance, claim boundary, and failure ledger.

[Open the browser studio](https://genghisdarb.github.io/torus-field-studio/) or download the
[v0.2.1 release](https://github.com/GenghisDarb/torus-field-studio/releases/tag/v0.2.1).
Choose **Load held-out study** to audit the v0.2.1 result or **Load TLD I result** to inspect the
preserved historical reproduction.

![TORUS Field Studio interface](docs/assets/studio-overview.svg)

## Quick start

Clone the repository and enter it before installing. The commands below are for Windows
PowerShell and do not require a globally installed `pnpm`:

```powershell
git clone https://github.com/GenghisDarb/torus-field-studio.git
Set-Location torus-field-studio
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1

& .\.venv\Scripts\python.exe -m torusbrot.cli generate local `
  --spec examples/tld-parent-null/run-spec.json `
  --domain examples/tld-parent-null/domain.json `
  --output results/parent-null.tbx.zip
& .\.venv\Scripts\python.exe -m torusbrot.cli audit results/parent-null.tbx.zip

.\scripts\studio.ps1
```

If the repository is already cloned, start with `Set-Location` using its actual folder. The
bootstrap script creates `.venv`, installs the Python package and development tools, and uses
the repository-pinned pnpm version through npm, an existing pnpm, or Codex's bundled runtime.
Outside Codex, install Node.js 24 before running the browser studio. Python-only users can run
`.\scripts\setup.ps1 -SkipWeb`.

For macOS or Linux:

```bash
git clone https://github.com/GenghisDarb/torus-field-studio.git
cd torus-field-studio
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m torusbrot.cli generate local --spec examples/tld-parent-null/run-spec.json \
  --domain examples/tld-parent-null/domain.json --output results/parent-null.tbx.zip
.venv/bin/python -m torusbrot.cli audit results/parent-null.tbx.zip
npx --yes pnpm@11.19.0 install
npx --yes pnpm@11.19.0 run dev
```

Open the Vite URL to explore the built-in analytic and ladder examples. Click any computed
point to inspect its classification, parent/null metrics, provenance, legal interpretation,
and recovery timeline. Use **Import bundle** to open a `.tbx.zip` created by the CLI.

The errors shown when setup was run from the user-profile directory occurred because that directory was
not the repository and therefore had no `pyproject.toml`. PowerShell also uses a backtick—not a
backslash—for line continuation. The commands above fix both issues. Calling the venv Python
directly also avoids relying on an unactivated shell, while `setup.ps1` supplies the pinned pnpm
runtime when `pnpm` is not globally installed.

## Reproduce the held-out v0.2.1 study

The complete outside-replication package is in [replication/README.md](replication/README.md).
It builds and installs the wheel, fetches and hashes the registered UCI source, executes into a
fresh directory, invokes the independent endpoint verifier and 25-mutation suite, and audits all
three TBX profiles. The package does not require Brad's local files and does not embed an expected
positive result.

The canonical execution was scientifically negative under the frozen gates: no primary N from 6
through 14 satisfied SEP, `T_e` was `NOT_OBSERVED`, contiguous `S_e` was 0, the separate closure
minimum was N=9, and the secondary N=14 specificity gate failed. The independent verifier agreed
with every endpoint and rejected 25 of 25 registered mutations. Therefore `TLD_DERIVED` remains
blocked and `EXTERNALLY_VALIDATED` remains false. See the
[plain-language summary](studies/heldout-v0.2.1/publication/plain-language-summary.md) and
[technical report](studies/heldout-v0.2.1/publication/technical-report.md).

## Reproduce the published TLD I result

The source archive is fetched from Zenodo and kept in the ignored `external_cache` directory.
These PowerShell commands perform custody validation, execute the production implementation,
independently verify it, and create all three TBX profiles:

```powershell
& .\.venv\Scripts\python.exe -m torusbrot fetch tld-release `
  --doi 10.5281/zenodo.18080090 `
  --output external_cache\zenodo\18080090\TORUS_Zenodo_v1.zip
& .\.venv\Scripts\python.exe -m torusbrot validate tld-release `
  external_cache\zenodo\18080090\TORUS_Zenodo_v1.zip
& .\.venv\Scripts\python.exe -m torusbrot reproduce tld-i `
  --source external_cache\zenodo\18080090\TORUS_Zenodo_v1.zip `
  --output results\tld-i
& .\.venv\Scripts\python.exe -m torusbrot verify tld-result `
  results\tld-i\bundles\tld-i-combined-historical-reproduction.tbx.zip
```

Expected runtime is roughly 1–2 minutes on a current laptop. The exact result is honest but
mixed: Notebook 13 passes 4 of 6 preregistered criteria. The alpha=0.02 mean-return-steps and
p90-flips limits fail. The archive's preregistration document says 400 healing steps while the
executed Notebook 13 code uses 300. Neither historical lane computes `T_e` or `S_e`; those fields
remain null. See [the full reproduction report](docs/tld_i_reproduction.md).

## Strict TBX audit

Both the CLI and browser treat archives as hostile. Before a bundle is trusted, the auditor
checks safe canonical paths, duplicate and encrypted members, expansion limits, exact manifest
membership, byte counts and SHA-256 hashes, JSON schemas, grid and point identity, finite metrics,
statistics, parent/null counts, provenance, claim authority, verification receipts, failure
references, specification hashes, run identity, and `SHA256SUMS.txt`.

```powershell
& .\.venv\Scripts\python.exe -m torusbrot.cli audit path\to\artifact.tbx.zip
```

A failed audit returns stable issue codes such as `ARCHIVE_PATH_INVALID`,
`MANIFEST_HASH_MISMATCH`, or `VERIFIER_RECEIPT_MISSING`. No field table is exposed after failure.

## CLI

```text
torusbrot init my-study
torusbrot validate domain-pack examples/tld-parent-null/domain.json
torusbrot validate tld-release external_cache/zenodo/18080090/TORUS_Zenodo_v1.zip
torusbrot fetch tld-release --doi 10.5281/zenodo.18080090 -o external_cache/zenodo/18080090/TORUS_Zenodo_v1.zip
torusbrot reproduce tld-i --source external_cache/zenodo/18080090/TORUS_Zenodo_v1.zip -o results/tld-i
torusbrot generate tld --spec examples/tld-i/historical-combined-run-spec.json --domain external_cache/zenodo/18080090/TORUS_Zenodo_v1.zip -o results/tld-i.tbx.zip
torusbrot verify tld-result results/tld-i.tbx.zip
torusbrot freeze examples/tld-parent-null/run-spec.json
torusbrot generate analytic --spec examples/analytic-z14/run-spec.json -o results/z14.tbx
torusbrot generate local --spec examples/tld-parent-null/run-spec.json \
  --domain examples/tld-parent-null/domain.json -o results/parent-null.tbx
torusbrot nulls generate --domain examples/tld-parent-null/domain.json --seed 1407
torusbrot audit results/parent-null.tbx
torusbrot compare results/run-a.tbx results/run-b.tbx
torusbrot export results/parent-null.tbx --format csv --output results/field.csv
torusbrot studio
```

## Python API

```python
from torusbrot import DomainPack, LocalBrotRun, MatchedNullPolicy

domain = DomainPack.load("examples/tld-parent-null/domain.json")
run = LocalBrotRun.from_file("examples/tld-parent-null/run-spec.json")
result = run.execute(domain, MatchedNullPolicy(count=12, seed=1407))
result.audit()
result.export_tbx("results/example.tbx")
```

## Scientific contract

This repository makes a strict claim distinction:

| Level | Badge | Meaning |
| --- | --- | --- |
| 0 | `ILLUSTRATIVE_ANALYTIC` | Declared visual or analytic model only |
| 1 | `COMPUTED_DYNAMICAL` | Reproducible registered computation |
| 2 | `TLD_DERIVED` | Registered ladder plus matched-null endpoints |
| 3 | `EXTERNALLY_VALIDATED` | Independently reproduced, held-out result |

The bundled ladder example is a **synthetic reference fixture** and is marked
`COMPUTED_DYNAMICAL`. Supplying a domain pack does not automatically grant Level 2 or Level 3;
that authority must be registered in the pack and independently audited.

The TLD I artifact is also `COMPUTED_DYNAMICAL`. It exactly reproduces Brad's published
computational release, which is self-reproduction rather than external validation. The modern
v2.1 compliance lane uses frozen parent-matched, domain-isolated controls, but `TLD_DERIVED`
remains blocked; the contract is not weakened to promote the result.

The v0.2.1 held-out PM2.5 artifact is likewise `COMPUTED_DYNAMICAL`. It is a valid, publishable
negative result under the prospectively frozen gates. A successful internal independent verifier
does not constitute an outside replication, so the external-validation badge remains forbidden.

ToT-BROT, ToT-BULB, and Dual-Space contracts are included as forward-compatible schemas only.
They are not represented as validated engines in v0.2.

Read [the scientific contract](docs/scientific_contract.md),
[the TLD workbench](docs/tld_workbench.md), [the TBX format](docs/tbx_spec.md),
[schema migration policy](docs/schema_migrations.md),
[browser performance budget](docs/performance_budget.md), and [the roadmap](docs/roadmap.md)
before interpreting a result.

## Development

```bash
python -m pytest
python -m ruff check python tests scripts
python scripts/sync_schemas.py --check
pnpm run schemas:check
pnpm run typecheck
pnpm run build
pnpm run budget
python scripts/generate_hostile_fixtures.py --output tests/generated-fixtures
pnpm run e2e
```

The Python reference engine is the classification authority. Browser kernels are small-run
exploration tools and identify themselves as browser previews. The committed computed bundles are
the checksum-addressed, browser-importable TLD I and held-out-study examples; transient results,
source archives, notebook executions, build products, and `node_modules` remain ignored.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and
[CHANGELOG.md](CHANGELOG.md) for project policy and release history.

## License

MIT. Scientific results remain subject to the claim boundary stored with each artifact.
