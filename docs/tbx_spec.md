# TORUS Bundle Exchange (`.tbx`) v1 profiles

A TBX artifact is either an ordinary directory ending in `.tbx` or a deterministic ZIP ending in
`.tbx.zip`. Analysis tools should support the directory directly.

```text
run.tbx/
├── manifest.json
├── run_spec.json
├── ontology.json
├── claim_boundary.json
├── visual_encoding.json
├── scene_recipe.json
├── provenance/
│   ├── sources.jsonl
│   ├── transformations.jsonl
│   └── verification_receipts.jsonl
├── registry/
│   ├── parent_registry.json
│   └── null_registry.json
├── tables/
│   ├── field_points.json
│   └── metrics_by_N.json
└── audit/
    ├── audit.json
    ├── failure_ledger.jsonl
    └── SHA256SUMS.txt
```

`manifest.json` contains the bundle version, run identity, claim level, and the hash and byte size
of every other member. It does not hash itself. Tabular JSON is the dependency-free v0.1
reference encoding; future minor versions may add Parquet, Arrow, Zarr, GLB, PNG, or SVG members
without removing the canonical small-run JSON data.

## v1 audit policy

Readers must not expose bundle data until audit succeeds. ZIP readers preflight the central
directory before decompression and reject unsafe or non-canonical paths, duplicate names,
encrypted members, more than 256 files, any expanded member over 64 MiB, total expansion over
256 MiB, JSON documents over 16 MiB, JSON nesting beyond 32 levels, or compression ratios above
200:1.

The manifest file list is sorted by Unicode code point and must contain every member other than
the manifest itself, exactly once, with no unlisted extras. The current required members are the
15 files shown above. Each byte count and SHA-256 digest is checked before semantic validation.

Semantic validation then checks the canonical schemas and cross-file invariants: specification
hash, engine and claim compatibility, independent-verifier receipts, grid dimensions and complete
cell coverage, point indices and finite metrics, classification and mean statistics, failure-ledger
references, matched-null count, provenance transformation identity, deterministic run ID, and the
audit checksum list. Mean comparisons allow an absolute `1.1e-8` tolerance solely for
cross-language floating-point accumulation; recorded values remain rounded to eight decimals.

`audit/failure_ledger.jsonl` is never a log sink for ignored exceptions. Each failure has a stable
ID and, when it affects a grid cell, that cell remains in the field table as an ineligible
`UNRESOLVED` point linked by `failure_id`.

Unknown versions fail closed. See [schema migrations](schema_migrations.md) for compatibility and
versioning rules.

## TLD I profiles

Profiles `tld-i-historical-v1` and `tld-i-combined-v1` add source and preregistration registries,
ladder and control registries, endpoint, baseline, alpha, core-control, raw trajectory, transition,
and operating-envelope tables, an independent-verification receipt, and claim adjudication. The
profile declaration lists this exact required set. Both Python and browser auditors recompute its
semantic cross-file invariants.

TLD fields may be null only where the profile declares them uncomputed. For TLD I, `T_e`, `S_e`,
UI, NSS, SEP, and their manifest means remain null. Raw missing cells require `observed=false`,
classification `UNRESOLVED`, and an exact failure-ledger link. A modern profile additionally rejects
global pooled nulls.
