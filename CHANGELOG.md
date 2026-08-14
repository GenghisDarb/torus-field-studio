# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project uses semantic versioning.

## [0.1.1] - Unreleased

### Added

- Strict, fail-closed TBX auditing in Python and the browser, including ZIP preflight limits,
  exact membership, schema validation, semantic invariants, claim checks, and run identity.
- Executable failure preservation with visible `UNRESOLVED` points and a linked failure ledger.
- Hostile archive fixtures, browser end-to-end tests, screenshot regression, mobile and
  accessibility checks, WebGL context-loss handling, and bundle-size budgets.
- Python 3.11-3.13 CI on Linux, Windows, and macOS, built-wheel smoke tests, and cross-platform
  deterministic bundle comparison.
- Generated browser types and packaged Python schemas from canonical repository contracts.
- GitHub Pages deployment, security and contribution policies, issue forms, and Windows setup.

### Changed

- Browser-created TBX archives now pass the Python reference auditor.
- Citation metadata names Bradley Charles Peter and points to the canonical repository.
- The Windows quick start enters the repository, uses PowerShell continuation syntax, invokes
  the venv executable directly, and works without globally installed pnpm.

### Security

- Archive members are rejected before decompression when paths, duplication, encryption,
  compression ratio, member count, member size, or total expanded size violates policy.

## [0.1.0] - 2026-08-13

- Initial local-first field workbench, Python reference kernels, browser explorer, TBX export,
  provenance, claim boundaries, synthetic parent/null fixture, and analytic sandbox.

[0.1.1]: https://github.com/GenghisDarb/torus-field-studio/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/GenghisDarb/torus-field-studio/releases/tag/v0.1.0
