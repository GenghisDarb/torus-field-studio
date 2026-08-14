/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TORUSFailureRecord {
  failure_id: string;
  category:
    | "INELIGIBLE_COORDINATE"
    | "KERNEL_EXCEPTION"
    | "NONFINITE_METRIC"
    | "INSUFFICIENT_NULL_SUPPORT"
    | "FAILED_CONVERGENCE"
    | "UNAVAILABLE_PROJECTION"
    | "INTERPOLATION_GAP"
    | "PARTIAL_RUN"
    | "CANCELLED_RUN"
    | "INVALID_SOURCE_ROW"
    | "AUDIT_FAILURE";
  stage: string;
  message: string;
  grid_x: number | null;
  grid_y: number | null;
  coordinate: {
    [k: string]: number;
  } | null;
  recoverable: boolean;
}
