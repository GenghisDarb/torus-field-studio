/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryOperatorRegistry {
  schema_version: "1.0.0";
  registry_id: string;
  /**
   * @minItems 1
   */
  operators: [
    {
      operator_id: string;
      input_kind: string;
      output_kind: string;
      depth_semantics: string;
      /**
       * @minItems 1
       */
      boundary_compatibility: [string, ...string[]];
      mask_compatibility: string;
      historical_status: "CANONICAL_SEQUENCE_ADAPTER" | "NEW_CALIBRATED_GEOMETRY_OPERATOR" | "EXPLORATORY_EXCLUDED";
    },
    ...{
      operator_id: string;
      input_kind: string;
      output_kind: string;
      depth_semantics: string;
      /**
       * @minItems 1
       */
      boundary_compatibility: [string, ...string[]];
      mask_compatibility: string;
      historical_status: "CANONICAL_SEQUENCE_ADAPTER" | "NEW_CALIBRATED_GEOMETRY_OPERATOR" | "EXPLORATORY_EXCLUDED";
    }[]
  ];
}
