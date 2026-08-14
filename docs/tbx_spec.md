# TORUS Bundle Exchange (`.tbx`) v0.1

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

