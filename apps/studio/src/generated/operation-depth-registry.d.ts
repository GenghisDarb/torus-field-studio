/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryOperationDepthRegistry {
  schema_version: "1.0.0";
  registry_id: string;
  symbol: "r";
  /**
   * @minItems 1
   */
  depths: [number, ...number[]];
  recursive_semantics: string;
  te_applicable: boolean;
}
