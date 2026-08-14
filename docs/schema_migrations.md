# Schema migrations

Canonical schemas live under `schemas/`. Packaged Python copies and generated browser declarations
are derived artifacts:

```text
python scripts/sync_schemas.py
pnpm run schemas:generate
```

Never edit `python/torusbrot/schemas/` or `apps/studio/src/generated/` directly.

## Compatibility policy

- Patch releases may tighten auditing of malformed data without changing valid v1 documents.
- Additive optional properties require an explicit schema revision because current contracts use
  `additionalProperties: false` where evidence identity matters.
- Breaking property, meaning, or canonicalization changes require a new schema directory and TBX
  version, migration notes, old/new fixtures, and readers that fail clearly on unsupported data.
- A migration must not silently raise a claim level or invent missing evidence.

CI runs both derivation checks and audits canonical plus hostile fixtures. A schema change is not
complete until Python validation, browser validation, generated types, docs, and both valid and
invalid fixtures agree.
