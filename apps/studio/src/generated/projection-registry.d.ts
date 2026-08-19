/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryProjectionRegistry {
  schema_version: "1.0.0";
  registry_id: string;
  /**
   * @minItems 2
   */
  projections: [
    {
      projection_id: string;
      rule: string;
      justification: string;
      coordinate_order: string;
      invertibility: "INVERTIBLE" | "NONINVERTIBLE" | "CONDITIONALLY_INVERTIBLE";
      information_loss: string;
      /**
       * @minItems 1
       */
      null_compatibility: [string, ...string[]];
      faithful: boolean;
    },
    {
      projection_id: string;
      rule: string;
      justification: string;
      coordinate_order: string;
      invertibility: "INVERTIBLE" | "NONINVERTIBLE" | "CONDITIONALLY_INVERTIBLE";
      information_loss: string;
      /**
       * @minItems 1
       */
      null_compatibility: [string, ...string[]];
      faithful: boolean;
    },
    ...{
      projection_id: string;
      rule: string;
      justification: string;
      coordinate_order: string;
      invertibility: "INVERTIBLE" | "NONINVERTIBLE" | "CONDITIONALLY_INVERTIBLE";
      information_loss: string;
      /**
       * @minItems 1
       */
      null_compatibility: [string, ...string[]];
      faithful: boolean;
    }[]
  ];
}
