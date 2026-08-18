/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TORUSRunSpecification {
  schema_version: "1.0.0";
  engine: "analytic" | "local_brot";
  seed: number;
  domain_id?: string;
  claim_level?: "ILLUSTRATIVE_ANALYTIC" | "COMPUTED_DYNAMICAL" | "TLD_DERIVED" | "EXTERNALLY_VALIDATED";
  grid: {
    width: number;
    height: number;
  };
  parameters?: {
    [k: string]: any;
  };
  classification_rules?: {
    separation_threshold?: number;
    nss_threshold?: number;
    survival_threshold?: number;
    recovery_threshold?: number;
    escape_threshold?: number;
    bounded_iteration?: number;
  };
  null_policy?: {
    kind: "none" | "preserve_multiset_shuffle";
    count: number;
    seed?: number;
  };
}
