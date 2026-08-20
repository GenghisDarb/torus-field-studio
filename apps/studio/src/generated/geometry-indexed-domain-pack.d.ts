/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryIndexedDomainPack {
  schema_version: "1.0.0";
  standard_version: "Geometry-Indexed Domain Pack Standard v1.0";
  domain_id: string;
  source_id: string;
  stable_source_identifier: string;
  source_url: string;
  license: string;
  /**
   * @minItems 1
   */
  raw_source_hashes: [string, ...string[]];
  field_kind:
    | "SEQUENCE_1D"
    | "SCALAR_FIELD_2D"
    | "VECTOR_FIELD_2D"
    | "SCALAR_VOLUME_3D"
    | "VECTOR_VOLUME_3D"
    | "SPATIOTEMPORAL_SCALAR_FIELD"
    | "SPATIOTEMPORAL_VECTOR_FIELD"
    | "POINT_CLOUD"
    | "MANIFOLD_SAMPLES"
    | "GRAPH_GEOMETRY"
    | "CORRELATION_GEOMETRY"
    | "MULTIMODAL_COUPLED_FIELD";
  coordinate_system_id: string;
  boundary_condition_id: string;
  mask_contract_id: string;
  missing_data_semantics: "REJECT" | "MASK" | "REGISTERED_IMPUTATION" | "NOT_APPLICABLE";
  /**
   * @minItems 1
   */
  field_component_ids: [string, ...string[]];
  independent_parent_key: string;
  nested_replicate_key: string | null;
  experimental_run_key: string | null;
  condition_key: string | null;
  source_acquisition_identity: string;
  canonicalization_identity: string;
  projection_registry_identity: string;
  null_registry_identity: string;
  perturbation_registry_identity: string;
  domain_baseline_identity: string;
  claim_ceiling: "DESCRIPTIVE" | "COMPUTED_DYNAMICAL" | "CALIBRATED_ASSAY" | "EXTERNAL_VALIDATION";
  known_limitations: string[];
}
