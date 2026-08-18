# Technical report: held-out Beijing PM2.5 TLD study

## Design

The study used the UCI Beijing Multi-Site Air Quality dataset (DOI 10.24432/C5RK5G), authoritative archive SHA-256 `d1b9261c54132f04c374f762f1e5e512af19f95c95fd6bfa1e8ac7e927e3b0b8`. Each of 12 monitoring stations was an independent parent. Hourly PM2.5 measurements were aggregated to daily log1p medians when at least 18 hours were finite, month-of-year centered, and robustly scaled without interpolation.

Every parent had 127 deterministic null children created by permuting complete day records inside station-local year-month strata. The primary grid was N=6…14. SEP required at least 10 eligible parents, UI≥0.50, NSS≥2.0, and a Holm-adjusted one-sided population sign-test p≤0.05.

## Result

The adjudicated outcome is `HELDOUT_TLD_STUDY_NEGATIVE_UNDER_FROZEN_GATES`. Baseline UI was 0 at all nine N values. Baseline NSS ranged from -3.719858 to -2.287134; every value was below zero and every Holm-adjusted population p was 1. `T_e=NOT_OBSERVED`; consequently the primary S_e survival region is empty and `S_e_contiguous=0`.

The separate lag-closure objective selected N=9; the parent winner distribution was {"14": 1, "15": 1, "8": 1, "9": 9}. N=14 was not the study minimum and failed the frozen specificity gate.

The conventional station-local monthly climatology plus AR(1) improved held-out RMSE over monthly climatology alone at all 12 parents. Because the primary endpoint was already negative, residual survival at T_e is not applicable as a promotion gate.

## Verification and claims

The independent implementation recomputed parent eligibility, matched-null mapping, UI, NSS, SEP, T_e, S_e, closure mode, specificity, failure count, and claim ceiling with 0 disagreements. It rejected 25/25 semantic and custody mutations. There were 0 scientific execution failures.

The result remains `COMPUTED_DYNAMICAL`. `TLD_DERIVED` is blocked because no SEP cell, T_e, or nonzero S_e was observed. `EXTERNALLY_VALIDATED` remains false until a genuinely independent outside team executes the frozen replication package.
