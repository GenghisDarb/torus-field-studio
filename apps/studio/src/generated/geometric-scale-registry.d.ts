/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryScaleRegistry {
  schema_version: "1.0.0";
  registry_id: string;
  symbol: "ell";
  unit: string;
  /**
   * @minItems 3
   */
  scales: [number, number, number, ...number[]];
  selection_rule: string;
}
