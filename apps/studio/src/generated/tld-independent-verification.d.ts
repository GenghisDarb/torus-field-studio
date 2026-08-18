/* Generated from the canonical repository schema. Do not edit by hand. */

export interface IndependentVerificationReceipt {
  schema_version: "1.0.0";
  status: "verified" | "rejected";
  verifier: string;
  result_sha256: {
    [k: string]: any;
  };
  checks: {
    [k: string]: any;
  };
}
