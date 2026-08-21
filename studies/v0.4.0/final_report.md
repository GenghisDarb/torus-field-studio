# TORUS Field Studio v0.4.0 audit — final report

High-level outcome: `V040_PHASE_ORIENTATION_METHOD_NOT_ESTABLISHED`

`TLD_DERIVED`: `BLOCKED`

The authoritative repository is
`C:\Users\thisb\Documents\Codex\2026-08-13\pok\work\torus-field-studio`.
The public repository remains `GenghisDarb/torus-field-studio`; `main` and tag
`v0.3.0` remain at `abe12e1da964c8902978ac7460028975f1f0324d`.

## Custody and lineage

v0.3.0 reproduced exactly within its frozen numerical tolerances: all release
assets and manifests, package installation, five TBX bundles, installed-wheel
replication, public Pages TBX, raw HDF5 recomputation, 118 historical Python tests,
and eight browser E2E tests reconciled.

All fourteen immutable public TLD releases were located. Exact public notebook
source covers Notebooks 13–44; Notebook 12 is executable only through an authority-D
ledger; Notebooks 1–11 remain summary-only. The lineage outcome is
`FULL_TLD_I_XIV_LINEAGE_PARTIALLY_RECOVERED_WITH_BLOCKERS`. Notebook 44 also fails
EEG baseline parity against Notebook 43 on all nine N rows, so its EEG compound
interpretation is blocked.

The semantic firewall is retained: `winner_N` is a harmonic/closure label; `T_e`
is minimum registered onset at first separation and is not physical time or the
historical `T_hat_maxN`; `S_e` is persistence/survival and is not `winner_N` or
geometric scale `ell`.

## Critic and operator audit

The 18 critic statements classify as: 1 supported, 2 supported with scope
correction, 5 contradicted by v0.3.0 code, 1 historical defect already repaired,
3 mathematically incomplete, 2 mathematically inconsistent, 2 source not found,
and 2 requiring prospective testing.

v0.3.0 did not flatten PIV and is not completely sign-blind. P01 is a typed
`(y,x,2)` field and P02 is a typed `(time,y,x,2)` field. Signed mean curl,
component coherence, curl energy/coherence, divergence energy, coordinates, masks,
time, and orientation metadata are preserved. The real gaps are local chirality
cancellation, local complex winding, temporal phase/cross-spectrum, parity events,
and orientation-bundle monodromy. The 28 pairs remain paired acquisition blocks in
one physical system; frames and cells are nested.

## Mathematics and calibration

Pure vertex-derived U(1) links telescope to a unit closed-loop product. Wrapped
winding is invariant to a global phase offset, but not to arbitrary local vertex
rephasing; a nontrivial locally gauge-invariant holonomy requires independent
connection links. U(1) alone is orientation preserving.

For explicitly declared O(2) transitions, determinant parity is invariant under
frame conjugation: one reflection reverses orientation and two preserve it. That
transition bundle cannot be inferred from an ordinary unannotated scalar/vector
field. `w1` is the applicable orientation obstruction for a declared real bundle;
`c1` is not a nonorientability or anomaly proof. A 4π return has no authority without
an explicitly justified spinorial representation.

The frozen arithmetic is π/7 × 7 = π, × 14 = 2π, and × 28 = 4π. The blind search
gave no privileged scoring term to 14 or 28.

Forty synthetic families with 96 parents each were generated and hash-custodied.
The blind period lane was 1,728/1,728 over the frozen 18-period family; explicit O(2)
parity was 576/576 with zero false parity calls (upper Wilson 95% bound about 0.00663).
These are bounded operator-recognition results, not field validation or classifier
power. The U(1) lane abstained 480 times and the temporal lane 288 times.

The complete method gate failed because there is no frozen matched-null selective
decision with type-I/false-sign control, scalar-derived winding fails arbitrary
local-gauge invariance, O(2) requires supplied transition data, and instrument,
boundary, irregular-sampling, independent-verifier, mutation, and combined-rule
gates remain incomplete. The freeze commit is
`2a9ab03a3fb4edb6e702d0695d27fd87f4b642f9`.

## Stop boundary

No real candidate was selected. No candidate-freeze, domain preregistration,
authorization, scored held-out execution, Phase K diagnostic replay, independent
field verifier, v0.4 TBX/Studio change, PR, merge, tag, or release was created.
`T_e`, `S_e`, `ell`, `winner_N`, N=14, and N=28 therefore have no held-out result.
`EXTERNALLY_VALIDATED` remains false.

All 122 Python tests and repository lint pass. The exact next legal action is to stop
this assay. A future research cycle would need a narrower representation/gauge
contract plus frozen matched-null, instrument, boundary, independent-verifier, and
mutation gates before any real candidate search.
