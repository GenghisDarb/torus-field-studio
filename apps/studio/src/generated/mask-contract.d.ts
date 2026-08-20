/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryMaskContract {
  schema_version: "1.0.0";
  mask_id: string;
  semantics: "VALID_SUPPORT" | "INVALID_SUPPORT" | "REGION_OF_INTEREST" | "NOT_APPLICABLE";
  true_means: "INCLUDE" | "EXCLUDE" | "NOT_APPLICABLE";
  mask_sha256: string | null;
  selection_timing: "SOURCE_DEFINED" | "PRE_OUTCOME_REGISTERED" | "NOT_APPLICABLE";
  mutable_after_freeze: false;
}
