# TLD workbench

Version 0.2 adds a reusable TORUS Ladder Dynamics spine under `torusbrot.tld`. It is production
code, not an import of the Zenodo notebooks or their output labels.

The package separates source custody, domain materialization, registry identity, closure scoring,
perturbation, escape/recovery execution, ringing and transition analysis, endpoints, provenance,
independent verification, claim adjudication, and TBX materialization. Authoritative JSON Schemas
generate both Python and TypeScript bindings.

## Scientific lanes

`HISTORICAL_PUBLISHED_RELEASE_REPRODUCTION` preserves the published inputs, row order, random
seeds, operators, thresholds, and executed step limits. It answers whether the public release
reproduces itself. It is not a new held-out experiment.

`MODERN_V21_COMPLIANCE_EXTENSION` is separately preregistered in
`examples/tld-i/modern-v21-preregistration.json`. It registers the observed parent and 32
parent-local, domain-isolated, exact-multiset permutation controls before scoring. It does not
replace the historical alpha=0 mechanistic control, pool nulls across domains, or retune after
seeing Lane 1.

The modern lane records `T_e` and `S_e` as `NOT_APPLICABLE`: the historical experiment does not
define an observed/null depth axis on which either endpoint can be computed. `winner_N` remains a
closure-mode label and is never substituted for either endpoint.

## Trust boundaries

The Zenodo adapter verifies the immutable expected MD5 and SHA-256 before extraction, then applies
path, type, encryption, member-count, member-size, total-expansion, and compression-ratio limits.
The independent verifier does not call production scoring or summary functions. Python and browser
TBX auditors independently enforce source hashes, profile membership, preregistration outcomes,
raw transition counts, missing-cell preservation, ontology non-equivalence, and the claim ceiling.

See [TLD I reproduction](tld_i_reproduction.md), [domain packs](domain_pack_spec.md), and
[reproducibility](reproducibility.md).
