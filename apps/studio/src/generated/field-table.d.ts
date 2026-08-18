/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TORUSFieldTable {
  schema_version: "1.0.0";
  width: number;
  height: number;
  points: LocalTORUSBROTFieldPoint[];
}
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
  S_e: number | null;
  UI: number | null;
  NSS: number | null;
  SEP: number | null;
  rms_to_parent: number | null;
  iterations: number;
  parent_id: string;
  null_policy_id: string;
  failure_id?: string | null;
  observed?: boolean;
  phase?: string | null;
  trial_id?: number | null;
  alpha?: number | null;
  t?: number | null;
  trace: {
    step: number;
    stage: string;
    coherence: number;
    magnitude?: number;
    null_mean?: number;
    similarity?: number;
  }[];
}
