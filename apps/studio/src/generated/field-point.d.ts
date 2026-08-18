/* Generated from the canonical repository schema. Do not edit by hand. */

export interface LocalTORUSBROTFieldPoint {
  index: number;
  grid_x: number;
  grid_y: number;
  x: number;
  y: number;
  classification: "BOUNDED" | "ESCAPED" | "RECOVERED" | "NULL_LIKE" | "UNRESOLVED";
  eligible: boolean;
  emerged: boolean;
  separated_from_null: boolean;
  closed: boolean;
  survived: boolean;
  escaped_from_reference: boolean;
  recovered: boolean | null;
  winner_N: number | null;
  T_e: number | null;
  S_e: number;
  UI: number;
  NSS: number;
  SEP: number;
  rms_to_parent: number;
  iterations: number;
  parent_id: string;
  null_policy_id: string;
  failure_id?: string | null;
  trace: {
    step: number;
    stage: string;
    coherence: number;
    magnitude?: number;
    null_mean?: number;
    similarity?: number;
  }[];
}
