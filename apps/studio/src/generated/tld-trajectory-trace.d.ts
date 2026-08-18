/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TLDTrajectoryTrace {
  schema_version: "1.0.0";
  rows: {
    trial_id: number;
    alpha_heal: number;
    seed: number;
    phase: "start" | "escape" | "heal";
    t: number;
    chi: number;
    winner_N: number;
    winner_rms: number;
    runner_N: number;
    runner_rms: number;
    margin: number;
  }[];
}
