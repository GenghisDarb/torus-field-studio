/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryRepresentationAgreement {
  schema_version: "1.0.0";
  agreement_id: string;
  /**
   * @minItems 2
   */
  projection_ids: [string, string, ...string[]];
  faithful_projection_count: number;
  effect_direction_agreement: boolean;
  rank_agreement: number | null;
  mode_agreement: boolean | null;
  tolerance_rule: string;
  status: "PASS" | "FAIL" | "INCONCLUSIVE";
}
