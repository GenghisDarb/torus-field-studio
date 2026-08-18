# Reproducibility

The historical source archive is identified by DOI, MD5, SHA-256, byte size, member count, notebook
hashes, and input hashes. Contracts were extracted without execution, canonicalized, hashed, made
read-only, and only then used to run Notebooks 13 and 14 in isolated copied workspaces.

Production reproduction uses the raw source inputs and reusable package code. It does not read the
published output CSV files to assign results. A separate verifier recomputes closure ranking and
margin, count-derived rates, mean and percentile summaries, preregistration decisions, raw
winner-state transitions, operating-envelope summaries, hashes, and the claim ceiling.

Discrete identities and classifications compare exactly. Floating-point comparisons use a frozen
absolute and relative tolerance of `1e-12` in the independent verifier; recorded values are not
rounded to force cross-platform agreement. TBX JSON serialization and ZIP metadata are
deterministic. The canonical release is built from an installed wheel and every uploaded asset is
downloaded and reverified.

The mutation suite changes source identity, row order, endpoint meanings, alpha controls, failures,
trajectories, seeds, membership, null scope, claims, observation status, ontology, and analytic
interpretation. Every mutation must fail with its registered code before release.
