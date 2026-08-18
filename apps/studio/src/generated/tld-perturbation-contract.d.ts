/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TLDPerturbationContract {
  schema_version: "1.0.0";
  contract_id: string;
  escape_operator: string;
  healing_operator: string;
  p_swap: number;
  epsilon: number;
  alphas: number[];
  max_escape_steps: number;
  max_heal_steps: number;
  seed_policy: string;
}
