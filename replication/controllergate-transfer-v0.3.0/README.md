# ControllerGate read-only transfer package

This package contains shadow evidence and implementation guidance derived from TORUS Field Studio
v0.3.0. It does not modify ControllerGate, start Batch104, authorize a repair, set a terminal
success state, validate AMDS, or establish TLD/ToT/TORUS theory claims.

The transfer is intentionally read-only. A ControllerGate maintainer may evaluate each item in an
isolated ablation branch, but ControllerAudit remains the sole writer of terminal success states.
Timing telemetry and a successful TFS computation have no automatic production authority.

Contents:

- `transfer-contract.json` — parent support, joint nulls, metrology, diagnostics, typed Scout,
  repeat, fragility, and timing firewalls.
- `method-v2-ablation-plan.json` — an ordered shadow-only evaluation plan.
- `SHA256SUMS.txt` — hashes for the two policy documents.

