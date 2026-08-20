# TORUS Field Studio v0.3.0 technical report

## Result in one sentence

Geometry Method V2 passed only as the nonpredictive `INSTRUMENTED_EVIDENCE_VECTOR`; its first
prospectively preregistered held-out field assay completed exactly once on 28 paired fluidic-
pinball acquisitions and produced a valid nonbinary evidence vector, with `TLD_DERIVED` blocked
and `EXTERNALLY_VALIDATED = false`.

## Preservation and recovery

The v0.2.1 held-out result, v0.2.2 forensic reconciliation, historical TLD I reproduction, first
v0.3.0 method freeze, first wind-farm selection, and blocked four-acquisition result remain
append-only. The 34-item expected-red audit identified the fixed parent gate, parent/null
pseudoreplication, midpoint penalty, semantic collisions, incomplete vector transformations,
silent projection risks, weak fragility controls, and summary-level verification as defects or
scope errors. Method V2 repairs were calibrated without Beijing or wind-farm outcome tuning.

## Method V2 calibration

- Method freeze: `dcaeb72b29fc0d32b002d9b5de0809b13f2ed272`.
- 31 structure families and 620 deterministic raw realizations.
- 12 positive channel controls, 12 true negatives, and 7 adversarial near-nulls.
- 999 parent-matched joint-null replicates per calibration family.
- Three lossless sequence representations reproduced the historical TLD construct with zero
  bridge disagreements.
- Independent raw recomputation reported zero unexplained disagreements.
- 50/50 registered scientific mutations were rejected.

Cross-platform CI subsequently exposed exact floating-point tail comparisons in two
mathematically tied synthetic diagnostics. The post-freeze numerical erratum counts values within
`max(1e-10, abs(observed) * 1e-10)` as ties and normalizes verifier-only hashes to ten decimal
places. This repair changed no held-out endpoint, threshold, winner, scored execution, or claim.

The binary and hierarchical candidates failed their frozen acceptance gates. In particular, the
family type-I upper confidence bounds did not establish a universal 0.05 family bound, no general
multichannel adjudication rule was calibrated, and general-geometry `T_e`/`S_e` endpoints were not
established. The accepted method therefore carries named evidence channels without a binary
positive/negative label or universal population interpretation.

## Wind-farm engineering pilot

After the method freeze, the already outcome-exposed wind source (DOI
`10.5281/zenodo.18731994`) was used only as a nonconfirmatory engineering pilot. It retained one
campaign, one baseline acquisition, three nonexchangeable yaw conditions, nested samples, two
lidar modalities, and three turbines. Coordinate-aware binning, masks, scale `ell`, projection
integrity, and component-aware rotation were exercised. A rotation raster-direction defect was
found, preserved, repaired, and regression-tested. No condition pooling, threshold tuning,
confirmatory classification, or population aggregate was performed.

## Held-out field assay

Structural preflight selected the actuated fluidic-pinball PIV archive at DOI
`10.5281/zenodo.20794709` for a Tier 2 within-campaign assay. The source archive contains
1,333,197,134 bytes and has SHA-256
`5819f9071c3b3b0b856934602b5e7b487852abe0e0a3a5b1b62eae17720d822f`.

The preregistration was frozen at
`a8e3cba766bd8b160fc9b8074086a48fb7aceceb`. The single scored execution used 56 acquisitions
forming 28 actuated/reference paired blocks. P01 was the temporal mean vector; P02 retained full
spatiotemporal fluctuations. Each acquisition used 127 local joint spatial cell permutations,
and each of six P01 channels used 999 frozen joint within-campaign replicates. Scale views were
`ell = 1, 2, 4` native PIV grid cells. Three pair shape mismatches were handled by scoring each
acquisition on its own registered grid and comparing scalar channel scores, without cross-file
cell alignment.

The result is
`GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY`. No p-value, winner selection,
positive/negative threshold, or causal actuation claim was added. `T_e`, `S_e`, and `winner_N`
are not applicable. `TLD_DERIVED` is blocked, and external validation remains false.

The saved-evidence verifier reported zero disagreements and detected 12/12 mutations. A separately
frozen raw verifier then reopened all 56 raw HDF5 acquisitions, recomputed P01, P02, 7,112 null
children, all 28 pair deltas, perturbations, scale behavior, the domain baseline, and 999 joint
summaries per channel before loading production outputs. It reported zero disagreements and did
not create a second scored execution or a new scientific claim. Its public per-acquisition
receipts hash values rounded to ten decimal places after the strict numerical comparison, so
those receipt identities remain reproducible across supported operating systems.

## Interpretation boundary

This is a valid source-specific, within-campaign, nonbinary geometry evidence artifact from one
deposited system. It is not a predictive TLD result, population validation, external replication,
ToT-BROT validation, ControllerGate repair authorization, or proof of TORUS Theory.
