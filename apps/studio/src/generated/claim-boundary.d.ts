/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TORUSClaimBoundary {
  claim_level: "ILLUSTRATIVE_ANALYTIC" | "COMPUTED_DYNAMICAL" | "TLD_DERIVED" | "EXTERNALLY_VALIDATED";
  permitted_interpretations: string[];
  excluded_interpretations: string[];
  experimental_tags: string[];
  independent_verifier_status: "not_supplied" | "independently_verified";
}
