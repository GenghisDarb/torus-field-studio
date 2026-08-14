export type Engine = "analytic" | "local_brot";
export type Metric = "classification" | "S_e" | "UI" | "NSS";
export type ViewMode = "field" | "surface";

export interface TracePoint {
  step: number;
  stage: string;
  magnitude?: number;
  coherence: number;
  null_mean?: number;
  similarity?: number;
}

export interface FieldPoint {
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
  trace: TracePoint[];
}

export interface FieldTable {
  schema_version: string;
  width: number;
  height: number;
  points: FieldPoint[];
  source?: "browser_preview" | "tbx_import";
  runId?: string;
  claimLevel?: string;
  engine?: Engine;
}

export interface GenerateRequest {
  engine: Engine;
  width: number;
  height: number;
  power: number;
  maxIterations: number;
  seed: number;
  recoverySteps: number;
}
