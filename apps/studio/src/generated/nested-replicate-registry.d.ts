/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryNestedReplicateRegistry {
  schema_version: "1.0.0";
  registry_id: string;
  nested_replicate_key: string | null;
  replicates: {
    replicate_id: string;
    parent_id: string;
    acquisition_identity: string;
  }[];
}
