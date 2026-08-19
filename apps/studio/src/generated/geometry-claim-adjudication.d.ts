/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryClaimAdjudication {
  schema_version: "1.0.0";
  run_id: string;
  method_id: string;
  method_mode: "BINARY_STRICT" | "BINARY_HIERARCHICAL" | "NONBINARY_EVIDENCE_VECTOR";
  scout_status: "ELIGIBLE" | "INELIGIBLE" | "INCONCLUSIVE";
  channel_results: {
    [k: string]: any;
  };
  scientific_outcome:
    | "V030_GEOMETRY_INDEXED_METHOD_NOT_ESTABLISHED"
    | "GEOMETRY_INDEXED_TLD_HELDOUT_POSITIVE_UNDER_FROZEN_GATES"
    | "GEOMETRY_INDEXED_TLD_HELDOUT_NEGATIVE_UNDER_FROZEN_GATES"
    | "GEOMETRY_INDEXED_TLD_HELDOUT_MIXED_WITH_EXACT_COMPONENTS"
    | "GEOMETRY_INDEXED_TLD_HELDOUT_EXECUTION_BLOCKED"
    | "GEOMETRY_INDEXED_TLD_HELDOUT_INVALIDATED_BY_PROTOCOL"
    | "GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY";
  T_e: number | string | null;
  S_e: number | string | null;
  winner_N: number | string | null;
  geometric_scale: number | string | null;
  TLD_DERIVED: "SUPPORTED" | "BLOCKED" | "NOT_APPLICABLE";
  EXTERNALLY_VALIDATED: false;
  claim_ceiling: "DESCRIPTIVE" | "COMPUTED_DYNAMICAL" | "CALIBRATED_ASSAY";
  blockers: string[];
}
