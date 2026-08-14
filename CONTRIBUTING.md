# Contributing

Thank you for improving TORUS Field Studio. Changes should preserve the boundary between
computation, evidence, claims, and rendering.

## Set up

On Windows PowerShell, clone the repository, enter it, and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
```

On macOS or Linux, create a Python 3.11+ environment, install `.[dev]`, install Node.js 24, and
run `npx --yes pnpm@11.19.0 install`.

## Before opening a pull request

```text
python scripts/sync_schemas.py --check
python -m ruff check python tests scripts
python -m pytest
pnpm run schemas:check
pnpm run typecheck
pnpm run build
pnpm run budget
python scripts/generate_hostile_fixtures.py --output tests/generated-fixtures
pnpm run e2e
```

Schema changes must include regenerated Python schema resources and TypeScript declarations,
migration notes, hostile or compatibility fixtures where applicable, and tests in both trust
boundaries. Kernel changes must preserve failures instead of dropping points. Visual changes must
not convert interpolation into evidence or hide claim labels.

Keep commits focused, explain the scientific and security impact, and link an issue when one
exists. By contributing, you agree that your contribution is licensed under the repository's MIT
license.
