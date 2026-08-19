/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryAwareNullRegistry {
  schema_version: "1.0.0";
  registry_id: string;
  selection_timing: "PRE_OUTCOME_REGISTERED";
  /**
   * @minItems 1
   */
  families: [
    {
      null_family_id: string;
      target_destroyed: string;
      nuisances_preserved: string[];
      geometry_preserved: boolean;
      parent_matching: true;
      seed_policy: string;
      child_count: number;
      /**
       * @minItems 1
       */
      bias_diagnostics: [string, ...string[]];
    },
    ...{
      null_family_id: string;
      target_destroyed: string;
      nuisances_preserved: string[];
      geometry_preserved: boolean;
      parent_matching: true;
      seed_policy: string;
      child_count: number;
      /**
       * @minItems 1
       */
      bias_diagnostics: [string, ...string[]];
    }[]
  ];
}
