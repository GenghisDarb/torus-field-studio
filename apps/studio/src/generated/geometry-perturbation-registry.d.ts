/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryPerturbationRegistry {
  schema_version: "1.0.0";
  registry_id: string;
  selection_timing: "PRE_OUTCOME_REGISTERED";
  /**
   * @minItems 1
   */
  perturbations: [
    {
      perturbation_id: string;
      target_relation: string;
      nuisances_preserved: string[];
      /**
       * @minItems 2
       */
      strengths: [number, number, ...number[]];
      expected_fragility: "MONOTONE_DECREASE" | "BANDED_DECREASE" | "INVARIANT_CONTROL" | "REGISTERED_OTHER";
      independently_meaningful: true;
      seed_policy: string;
    },
    ...{
      perturbation_id: string;
      target_relation: string;
      nuisances_preserved: string[];
      /**
       * @minItems 2
       */
      strengths: [number, number, ...number[]];
      expected_fragility: "MONOTONE_DECREASE" | "BANDED_DECREASE" | "INVARIANT_CONTROL" | "REGISTERED_OTHER";
      independently_meaningful: true;
      seed_policy: string;
    }[]
  ];
}
