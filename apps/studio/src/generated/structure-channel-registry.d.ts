/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryStructureChannelRegistry {
  schema_version: "1.0.0";
  registry_id: string;
  /**
   * @minItems 4
   */
  channels: [
    {
      channel_id:
        | "SIGNED_BIDIRECTIONAL_SEPARATION"
        | "CLOSURE_NULL_CALIBRATION"
        | "CANONICAL_TLD_CONSTRUCT_RECOVERY"
        | "STRUCTURED_FRAGILITY"
        | "REPRESENTATION_AGREEMENT"
        | "DOMAIN_BASELINE_EXCLUSION"
        | "GEOMETRY_TOPOLOGY_INVARIANT";
      estimand: string;
      direction_policy: "BIDIRECTIONAL" | "UPPER" | "LOWER" | "NON_DIRECTIONAL";
      claim_role: "PRIMARY" | "SUPPORTING" | "DESCRIPTIVE_ONLY";
    },
    {
      channel_id:
        | "SIGNED_BIDIRECTIONAL_SEPARATION"
        | "CLOSURE_NULL_CALIBRATION"
        | "CANONICAL_TLD_CONSTRUCT_RECOVERY"
        | "STRUCTURED_FRAGILITY"
        | "REPRESENTATION_AGREEMENT"
        | "DOMAIN_BASELINE_EXCLUSION"
        | "GEOMETRY_TOPOLOGY_INVARIANT";
      estimand: string;
      direction_policy: "BIDIRECTIONAL" | "UPPER" | "LOWER" | "NON_DIRECTIONAL";
      claim_role: "PRIMARY" | "SUPPORTING" | "DESCRIPTIVE_ONLY";
    },
    {
      channel_id:
        | "SIGNED_BIDIRECTIONAL_SEPARATION"
        | "CLOSURE_NULL_CALIBRATION"
        | "CANONICAL_TLD_CONSTRUCT_RECOVERY"
        | "STRUCTURED_FRAGILITY"
        | "REPRESENTATION_AGREEMENT"
        | "DOMAIN_BASELINE_EXCLUSION"
        | "GEOMETRY_TOPOLOGY_INVARIANT";
      estimand: string;
      direction_policy: "BIDIRECTIONAL" | "UPPER" | "LOWER" | "NON_DIRECTIONAL";
      claim_role: "PRIMARY" | "SUPPORTING" | "DESCRIPTIVE_ONLY";
    },
    {
      channel_id:
        | "SIGNED_BIDIRECTIONAL_SEPARATION"
        | "CLOSURE_NULL_CALIBRATION"
        | "CANONICAL_TLD_CONSTRUCT_RECOVERY"
        | "STRUCTURED_FRAGILITY"
        | "REPRESENTATION_AGREEMENT"
        | "DOMAIN_BASELINE_EXCLUSION"
        | "GEOMETRY_TOPOLOGY_INVARIANT";
      estimand: string;
      direction_policy: "BIDIRECTIONAL" | "UPPER" | "LOWER" | "NON_DIRECTIONAL";
      claim_role: "PRIMARY" | "SUPPORTING" | "DESCRIPTIVE_ONLY";
    },
    ...{
      channel_id:
        | "SIGNED_BIDIRECTIONAL_SEPARATION"
        | "CLOSURE_NULL_CALIBRATION"
        | "CANONICAL_TLD_CONSTRUCT_RECOVERY"
        | "STRUCTURED_FRAGILITY"
        | "REPRESENTATION_AGREEMENT"
        | "DOMAIN_BASELINE_EXCLUSION"
        | "GEOMETRY_TOPOLOGY_INVARIANT";
      estimand: string;
      direction_policy: "BIDIRECTIONAL" | "UPPER" | "LOWER" | "NON_DIRECTIONAL";
      claim_role: "PRIMARY" | "SUPPORTING" | "DESCRIPTIVE_ONLY";
    }[]
  ];
  fusion_policy: "STRICT_CONJUNCTION" | "HIERARCHICAL_GATE" | "EVIDENCE_VECTOR_NO_NUMERIC_POOLING";
}
