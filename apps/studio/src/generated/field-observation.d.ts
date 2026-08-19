/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryFieldObservation {
  schema_version: "1.0.0";
  observation_id: string;
  domain_id: string;
  parent_id: string;
  replicate_id: string | null;
  run_id: string | null;
  condition_id: string | null;
  /**
   * @minItems 1
   */
  component_ids: [string, ...string[]];
  array_sha256: string;
  /**
   * @minItems 1
   */
  shape: [number, ...number[]];
  dtype: string;
  mask_id: string | null;
  acquisition_identity: string;
}
