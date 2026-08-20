/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryEffectiveParentAudit {
  schema_version: "1.0.0";
  audit_id: string;
  nominal_parent_count: number;
  eligible_parent_count: number;
  effective_parent_count: number;
  nested_replicate_count: number;
  dependence_method: string;
  minimum_required: number;
  status: "PASS" | "FAIL" | "INCONCLUSIVE";
}
