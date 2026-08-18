/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TLDLadderRegistry {
  schema_version: "1.0.0";
  /**
   * @minItems 1
   */
  ladders: [
    {
      ladder_id: string;
      domain_id: string;
      kind: string;
      parent_ladder_id: string | null;
      omega_construction_rule: string;
      adjacency_topology: string;
      is_null: boolean;
      eligible: boolean;
      seed: number;
      source_values_hash: {
        [k: string]: any;
      };
      canonicalization_hash: {
        [k: string]: any;
      };
      perturbation_contract_hash: {
        [k: string]: any;
      };
      notes: string;
    },
    ...{
      ladder_id: string;
      domain_id: string;
      kind: string;
      parent_ladder_id: string | null;
      omega_construction_rule: string;
      adjacency_topology: string;
      is_null: boolean;
      eligible: boolean;
      seed: number;
      source_values_hash: {
        [k: string]: any;
      };
      canonicalization_hash: {
        [k: string]: any;
      };
      perturbation_contract_hash: {
        [k: string]: any;
      };
      notes: string;
    }[]
  ];
}
