/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TORUSDomainPack {
  schema_version: "1.0.0";
  domain_id: string;
  title: string;
  description?: string;
  /**
   * @minItems 4
   */
  ladder: [number, number, number, number, ...number[]];
  claim_authority: "COMPUTED_DYNAMICAL" | "TLD_DERIVED" | "EXTERNALLY_VALIDATED";
  source?: {
    [k: string]: any;
  };
}
