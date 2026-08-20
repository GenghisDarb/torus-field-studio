# What TORUS Field Studio v0.3.0 found

The project repaired and stress-tested its geometry tools, then used the repaired method once on
a new public fluid-flow dataset. The execution worked as preregistered, the independent checker
recomputed the result from the raw files, and the two implementations agreed.

The scientific conclusion is deliberately narrow: the software produced a useful set of named
geometry measurements for 28 paired experimental acquisitions. The method was not calibrated to
turn those measurements into a universal “TLD positive” or “TLD negative” verdict. It also cannot
generalize from one deposited experimental system to a broader population.

The geometric resolutions tested were 1, 2, and 4 source grid cells, written as `ell`. They are
not `S_e`. The study had no registered operation-depth axis, so `T_e` is not applicable. It also
had no canonical path-closure axis, so `winner_N` is not applicable.

The important quality-control result is strong: the raw verifier independently reopened all 56
acquisitions, reconstructed both registered projections, generated 7,112 null children, repeated
the paired comparisons and perturbation checks, and found zero disagreements. That verifies the
computation—not the larger theory. `TLD_DERIVED` remains blocked and external validation remains
false.

