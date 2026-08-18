/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TLDPreregistrationResult {
  schema_version: "1.0.0";
  contract_sha256: {
    [k: string]: any;
  };
  criteria: {
    [k: string]: boolean;
  };
  passed: number;
  failed: number;
}
