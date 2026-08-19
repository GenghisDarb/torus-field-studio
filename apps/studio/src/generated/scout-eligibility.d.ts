/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryScoutEligibility {
  schema_version: "1.0.0";
  scout_id: string;
  domain_id: string;
  checks: {
    materialized: boolean;
    coordinates_complete: boolean;
    nondegenerate: boolean;
    null_ensemble_complete: boolean;
    independent_parent_support: boolean;
    mask_valid: boolean;
    support_sufficient: boolean;
    units_resolved: boolean;
    sensitivity_adequate: "PASS" | "FAIL" | "NOT_APPLICABLE";
  };
  materialized_fraction: number;
  effective_parent_count: number;
  orbit_length_summary: {
    [k: string]: any;
  } | null;
  closure_authorized: boolean;
  status: "ELIGIBLE" | "INELIGIBLE" | "INCONCLUSIVE";
  failure_codes: string[];
}
