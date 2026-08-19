/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryCoordinateSystem {
  schema_version: "1.0.0";
  coordinate_system_id: string;
  /**
   * @minItems 1
   */
  axes: [
    {
      name: string;
      unit: string;
      sampling_interval: number | null;
      orientation: string;
      is_time: boolean;
    },
    ...{
      name: string;
      unit: string;
      sampling_interval: number | null;
      orientation: string;
      is_time: boolean;
    }[]
  ];
  reference_frame: string;
  grid_regularity: "REGULAR" | "IRREGULAR" | "GRAPH" | "MANIFOLD" | "NOT_APPLICABLE";
  orientation: string;
  periodicity: boolean[];
}
