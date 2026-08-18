# TLD I reproduction

## Outcome

`FIRST_PUBLISHED_TLD_RESULT_EXACTLY_REPRODUCED`

The authoritative source is Zenodo record `18080090`, DOI `10.5281/zenodo.18080090`, titled
*TORUS Ladder Dynamics I: Structural Escape, Damped Healing, and Ringing Diagnostics*. The archive
`TORUS_Zenodo_v1.zip` is 687,340 bytes, has Zenodo MD5
`25f26f78bf6c73df1e551983af518e9a`, SHA-256
`5bae9af506bd65e74225fc91f869931d70fcd89505cbc672b3538abdfd4b446e`, and 30 members.

The archive's confirmatory notebooks are actually named `TORUS Ladder Validation Notebook
13.ipynb` and `TORUS Ladder Validation Notebook 14.ipynb`; the README's expected underscore names
do not match the archive. Notebooks 1–12 are exploratory and are not used as confirmatory evidence.
The original notebooks ran untouched in isolated Python 3.10.11 workspaces. Every parsed generated
value matched the published output; byte differences were newline and execution-timestamp changes.

## Registered results

- Baseline sweep winner: `winner_N = 10`; margin `0.05108693012191823`.
- Alpha 0: escape rate `1.0`; conditional return rate `0.105`; mean return steps
  `104.64285714285714`; p90 winner flips `13`.
- Alpha 0.02: escape rate `1.0`; conditional return rate `0.9675`; mean return steps
  `134.656330749354`; p90 winner flips `11`.
- Alpha sweep return rates for 0, 0.005, 0.01, 0.02, 0.05, and 0.1 are respectively
  `0.092`, `0.332`, `0.588`, `0.952`, `1.0`, and `1.0`.
- Notebook 14 alpha 0.02: all ten traces return; mean 155.7 steps; 41 transitions; mean 4.1
  flips; p90 7.1.
- Notebook 14 alpha 0.05: all ten traces return; mean 92 steps; 33 transitions; mean 3.3
  flips; p90 3.6.
- Operating-envelope escape strengths 0.005, 0.01, 0.02, and 0.03 have escape rates
  `0.98`, `0.9966666666666667`, `1.0`, and `1.0`; every escaped trial returns.

Notebook 13 passes 4 of 6 preregistered criteria. It fails the alpha 0.02 mean-return-steps maximum
of 120 and p90-flips maximum of 5. The external preregistration document declares 400 maximum
healing steps, while Notebook 13 code executes 300; the historical reproduction preserves and
reports that discrepancy.

## Claim adjudication

The result is `COMPUTED_DYNAMICAL`. `TLD_DERIVED_STATUS = BLOCKED`. Neither lane is
`EXTERNALLY_VALIDATED`, because reproducing a release from the same project is self-reproduction.
The modern lane's controls pass their frozen governance checks, but `T_e` and `S_e` remain
`NOT_APPLICABLE` and the historical failed criteria and declaration mismatch remain visible.

The result does not prove TORUS Theory, establish 14 uniquely, derive a physical law, establish
cross-domain universality, validate ToT-BROT or ToT-BULB, establish observer-state effects, derive
cosmological scales, or establish a causal physical mechanism beyond the computational system.

## Reproduction and mismatch handling

Use the commands in the repository README. A source hash mismatch stops before execution. A schema,
membership, run-identity, transition, preregistration, or failure-preservation mismatch rejects the
TBX with a stable audit code. A numerical mismatch must be reported against the pre-execution
contract; thresholds may not be changed after the run.
