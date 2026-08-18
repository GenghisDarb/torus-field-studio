/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TLDEndpointTable {
  schema_version: "1.0.0";
  rows: {
    endpoint_id: string;
    lane: string;
    condition: {
      [k: string]: any;
    };
    winner_N: number | null;
    T_e: number | null;
    S_e: number | null;
    metrics: {
      [k: string]: any;
    };
    eligible: boolean;
    failure_id?: string | null;
  }[];
}
