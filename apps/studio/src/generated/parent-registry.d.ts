/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryParentRegistry {
  schema_version: "1.0.0";
  registry_id: string;
  independent_parent_key: string;
  /**
   * @minItems 1
   */
  parents: [
    {
      parent_id: string;
      source_acquisition_identity: string;
      eligible: boolean;
      exclusion_reason?: string | null;
    },
    ...{
      parent_id: string;
      source_acquisition_identity: string;
      eligible: boolean;
      exclusion_reason?: string | null;
    }[]
  ];
}
