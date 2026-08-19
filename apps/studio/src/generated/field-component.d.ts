/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryFieldComponent {
  schema_version: "1.0.0";
  component_id: string;
  name: string;
  unit: string;
  role: "SCALAR" | "VECTOR_COMPONENT" | "TENSOR_COMPONENT" | "CATEGORY" | "WEIGHT";
  orientation: string | null;
  value_semantics: string;
}
