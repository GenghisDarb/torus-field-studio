/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryScoutEligibility {
  schema_version: "1.0.0";
  scout_id: string;
  domain_id: string;
  checks: {
    source_bytes_verified: boolean;
    materialized: boolean;
    coordinates_complete: boolean;
    units_resolved: boolean;
    orientation_known: boolean;
    components_registered: boolean;
    mask_valid: boolean;
    missingness_within_bounds: boolean;
    nondegenerate: boolean;
    variance_finite: boolean;
    support_sufficient: boolean;
    resolution_sufficient: boolean;
    independent_parent_support: boolean;
    effective_parent_support: boolean;
    nested_replicates_identified: boolean;
    null_ensemble_complete: boolean;
    nulls_finite: boolean;
    projection_deterministic: boolean;
    projection_not_outcome_selected: boolean;
    projection_justified: boolean;
    boundary_conditions_known: boolean;
    operation_depth_applicable: boolean;
    geometric_scale_applicable: boolean;
    domain_baseline_materializable: boolean;
    failure_ledger_active: boolean;
    sensitivity_adequate: boolean | "NOT_APPLICABLE";
  };
  materialized_fraction: number;
  effective_parent_count: number;
  orbit_length_summary: {
    [k: string]: any;
  } | null;
  closure_authorized: boolean;
  status:
    | "ELIGIBLE"
    | "INELIGIBLE_DEGENERATE"
    | "INELIGIBLE_COORDINATE_AMBIGUITY"
    | "INELIGIBLE_UNIT_AMBIGUITY"
    | "INELIGIBLE_PARENT_SUPPORT"
    | "INELIGIBLE_NULL_INCOMPLETE"
    | "INELIGIBLE_PROJECTION_UNJUSTIFIED"
    | "INELIGIBLE_OPERATION_DEPTH_NOT_APPLICABLE"
    | "INELIGIBLE_BASELINE_UNAVAILABLE"
    | "MATERIALIZATION_BLOCKED";
  failure_codes: string[];
}
