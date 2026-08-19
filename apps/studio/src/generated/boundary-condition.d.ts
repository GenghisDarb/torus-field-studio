/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryBoundaryCondition {
  schema_version: "1.0.0";
  boundary_condition_id: string;
  /**
   * @minItems 1
   */
  axis_conditions: [
    {
      axis: string;
      kind: "PERIODIC" | "OPEN" | "REFLECTING" | "DIRICHLET" | "NEUMANN" | "SOURCE_DEFINED" | "NOT_APPLICABLE";
    },
    ...{
      axis: string;
      kind: "PERIODIC" | "OPEN" | "REFLECTING" | "DIRICHLET" | "NEUMANN" | "SOURCE_DEFINED" | "NOT_APPLICABLE";
    }[]
  ];
  source_basis: string;
  padding_allowed: boolean;
}
