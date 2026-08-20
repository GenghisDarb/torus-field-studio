# Geometry Projection Contract

A projection is a registered scientific transformation, not an array convenience.

Each projection records its identifier, exact transformation rule, physical or mathematical justification, coordinate traversal/order, invertibility class, information loss, compatible null families, and whether it is claimed to be faithful for a specified estimand.

At least two faithful projections are required for binary Methods A and B. Faithfulness is estimand-specific: a radial spectrum may be faithful for isotropic scale content while discarding orientation, and a spatial multiscale statistic may retain orientation while discarding phase. Neither becomes canonical merely because it is easy to compute.

Projection choice and all hyperparameters are frozen before candidate outcomes. A projection chosen after observing separation is contamination. A coordinate rotation, reflection, reindexing, or equivalent encoding must satisfy its registered invariance or equivariance expectation. Agreement includes effect direction and registered rank/mode tolerances; it does not require numerically identical values across incomparable estimands.

Flattening is permitted only when the projection registry explicitly states the coordinate order, information loss, and null compatibility and when an independent representation check is present. Silent row-major, column-major, or file-order flattening is prohibited.

Different modalities are reported as separate evidence channels unless a common estimand and cross-modal calibration or validated hierarchical model has been registered. Logical intersection is the safe v0.3.0 default, not a universal law. Uncalibrated numeric averaging is forbidden.
