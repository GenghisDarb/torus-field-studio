# TLD domain pack specification

A TLD domain pack materializes one registered source without outcome-dependent reordering. The TLD I
pack records the Zenodo DOI, `targets_baseline.csv` SHA-256, exact source row order, original family
and labels, positive values, nonnegative uncertainties, and MIT source license.

The historical ladderization is frozen as `omega = natural_log(value)` and
`sigma_omega = sigma/value`. Its adjacency topology is an ordered path. Duplicate rows are
preserved and missing values reject the pack. Values are dimensionless for this release.

Every parent or derived control receives an ID before endpoint computation. Registry identities
include the domain, parent link, construction rule, topology, eligibility, null status, seed,
source-values hash, canonicalization hash, perturbation-contract hash, and notes. Metrics may use
eligible non-null parents only. Modern controls are parent-local and domain-isolated; global pooled
nulls fail audit.

The authoritative schema is `schemas/tld-domain-pack/v1.schema.json`. Raw Zenodo bytes are fetched
by reference and hash rather than vendored into Git.
