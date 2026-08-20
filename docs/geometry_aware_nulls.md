# Geometry-Aware Nulls

A geometry-aware null destroys a named target relation while preserving registered nuisance properties and parent identity. It does not merely randomize values.

Every family declares:

- the target relation destroyed;
- marginals, spectrum, mask, sampling, boundaries, components, or geometry preserved;
- parent matching and child count;
- deterministic seed policy;
- projection compatibility; and
- bias diagnostics.

Candidate families include coordinate permutation within valid support, phase randomization with spectrum preservation, block or patch shuffles, graph degree-preserving rewires, rotations/reflections used as invariance controls, component decoupling for coupled fields, and matched parametric baselines. Only families appropriate to the domain and estimand may be frozen.

Null adequacy requires sufficient children per parent, no child assigned to the wrong parent, stable direction under seed groups, acceptable boundary/tie rates, and diagnostics for positive or negative bias. A null can be syntactically valid yet scientifically inadequate. Selection or replacement after outcomes invalidates the assay.

Closure minima are compared with the parent-matched null winner distribution. Absolute curvature prominence is not a null calibration. Relative curvature uses interior points only and is standardized by a registered robust null scale with an explicit numerical zero-variance policy.

Nulls and perturbations are distinct. A null supports a reference distribution; a perturbation traces a preregistered fragility response. Reusing one family in both roles requires an explicit nonredundancy argument.
