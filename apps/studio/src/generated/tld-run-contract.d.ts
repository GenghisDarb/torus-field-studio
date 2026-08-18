/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TLDRunContract {
  schema_version: "1.0.0";
  lane: "HISTORICAL_PUBLISHED_RELEASE_REPRODUCTION" | "MODERN_V21_COMPLIANCE_EXTENSION";
  doi: "10.5281/zenodo.18080090";
  contract_sha256: {
    [k: string]: any;
  };
  seed: number;
  /**
   * @minItems 2
   */
  n_window: [number, number, ...number[]];
  n_center: number;
  operators: {
    [k: string]: any;
  };
  trials: {
    [k: string]: any;
  };
  claim_ceiling: "COMPUTED_DYNAMICAL" | "TLD_DERIVED";
}
