# Geometry Method V2 specification

Status: frozen at commit `dcaeb72b29fc0d32b002d9b5de0809b13f2ed272`.

The accepted method is `METHOD_V2_C_EVIDENCE_VECTOR`, and its required public name is
`INSTRUMENTED_EVIDENCE_VECTOR`. It is a container for named, nonpooled geometry evidence
channels. Calibration did not establish a universal binary TLD discriminator or a universal
hierarchical multichannel rule.

## Inferential design

The inferential unit is declared per study. Campaigns, independent acquisitions, conditions,
modalities, nested observations, grid cells, and null children remain distinct. There is no
universal minimum-parent rule. Support is assessed against the frozen claim tier, estimand,
dependence assumptions, effect size, sensitivity, and power surface. Nested observations and
null children never become independent parents.

For parent-level inference, each joint null replicate takes one registered null child from each
parent and applies the same aggregate statistic as the observed data. Individual null children
are not flattened into a pseudo-population. Within-campaign evidence remains within-campaign and
does not imply population generalization.

## Geometry and representation

Each source uses a typed handler. Projection contracts preserve coordinates, components, units,
orientation, masks, modalities, and nesting. Vector rotations transform both coordinates and
components. Missingness remains a mask; downsampling is anti-aliased. Scalarization and leading-
dimension averaging require an explicit registered projection.

Representation claims require a frozen invariant or equivariant relationship. The calibration
suite found zero representation disagreements across its registered checks. The only bridge to
canonical one-dimensional TLD authority is lossless sequence extraction from a coordinate field,
one-by-M scalar field, or path graph; all three reproduced the historical construct exactly.

## Statistics and diagnostics

Geometric scale is `ell`. It is never `S_e`. An interior curvature elbow is a diagnostic and is
never `T_e` or `winner_N`. Boundary-adjacent minima, ties, flat traces, and multiple elbows remain
visible. The closure implementation has no midpoint penalty and uses parent-matched aggregate
null traces.

Structured fragility records graded responses to component-aware rotation, mask dropout,
relative robust noise, and anti-aliased scale changes. Domain baselines remain named and separate;
their values are not pooled numerically with TLD channels. Timing measurements have no claim,
endpoint, theory, or ControllerGate repair authority.

## Calibration boundary

Synthetic Geometry Suite V2 contains 31 families: 12 positive channel controls, 12 true-negative
families, and 7 adversarial near-null families, with 20 realizations per family (620 raw
realizations). It uses 999 joint null replicates per family. Wilson upper bounds did not establish
the frozen 0.05 family error target, so binary and hierarchical predictive methods failed their
acceptance gates. The independent raw verifier recomputed all 620 realizations, reported zero
unexplained disagreements, and rejected 50/50 scientific mutations.

Accordingly:

- `TLD_DERIVED` is blocked by default.
- `EXTERNALLY_VALIDATED` is false.
- `T_e` and `S_e` are not applicable unless separately calibrated and preregistered.
- `winner_N` is available only for a justified canonical path-closure axis.
- One system or field is never labeled ToT-BROT.
- TORUS-BROT imagery is never evidence or proof by itself.

