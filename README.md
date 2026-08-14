# TORUS Field Studio

> Every beautiful structure should trace back to a frozen computation.

TORUS Field Studio is a local-first scientific workbench for generating, inspecting, and
auditing geometric field artifacts. The v0.1 release deliberately separates two engines:

- **Analytic Sandbox** — reproducible `z -> z^p + c` fields with an explicit
  `ILLUSTRATIVE_ANALYTIC` claim badge.
- **TORUS-BROT** — a deterministic registered-ladder reference kernel with matched nulls,
  structural escape, recovery, ringing, `T_e`, `S_e`, `winner_N`, UI, NSS, and SEP retained
  as separate values.

The image is downstream of the artifact: classification is computed before rendering,
interpolation never creates observations, and every exported bundle includes a SHA-256
manifest, run specification, visual encoding, provenance, claim boundary, and failure ledger.

![TORUS Field Studio interface](docs/assets/studio-overview.svg)

## Quick start

```bash
python -m venv .venv
.venv/Scripts/pip install -e .[dev]  # Windows
torusbrot generate local --spec examples/tld-parent-null/run-spec.json \
  --domain examples/tld-parent-null/domain.json --output results/parent-null.tbx
torusbrot audit results/parent-null.tbx

pnpm install
pnpm run dev
```

Open the Vite URL to explore the built-in analytic and ladder examples. Click any computed
point to inspect its classification, parent/null metrics, provenance, legal interpretation,
and recovery timeline. Use **Import bundle** to open a `.tbx.zip` created by the CLI.

## CLI

```text
torusbrot init my-study
torusbrot validate domain-pack examples/tld-parent-null/domain.json
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

ToT-BROT, ToT-BULB, and Dual-Space contracts are included as forward-compatible schemas only.
They are not represented as validated engines in v0.1.

Read [the scientific contract](docs/scientific_contract.md),
[the TBX format](docs/tbx_spec.md), and [the roadmap](docs/roadmap.md) before interpreting a
result.

## Development

```bash
python -m pytest
python -m ruff check python tests
pnpm run build
```

The Python reference engine is the classification authority. Browser kernels are small-run
exploration tools and identify themselves as browser previews. No computed field, large bundle,
or `node_modules` directory is committed to Git.

## License

MIT. Scientific results remain subject to the claim boundary stored with each artifact.
