/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TLDClaimAdjudication {
  schema_version: "1.0.0";
  lane: string;
  claim_level: "COMPUTED_DYNAMICAL" | "TLD_DERIVED";
  tld_derived_status: "PERMITTED" | "BLOCKED" | "NOT_APPLICABLE";
  externally_validated: false;
  blockers: string[];
  forbidden_claims: string[];
}
