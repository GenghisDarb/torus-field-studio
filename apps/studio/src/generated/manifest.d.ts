/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TORUSBundleExchangeManifest {
  tbx_version: "1.0.0";
  profile?:
    | "field-v1"
    | "tld-i-historical-v1"
    | "tld-i-combined-v1"
    | "tld-i-modern-v21"
    | "tld-heldout-primary-v0.2.1"
    | "tld-heldout-specificity-v0.2.1"
    | "tld-heldout-combined-v0.2.1"
    | "tld-heldout-v021-forensic-v0.2.2"
    | "geometry-pilot-v0.3.0";
  run_id: string;
  claim_level: string;
  kernel_id: string;
  specification_sha256: string;
  statistics: {
    point_count: number;
    classification_counts: {
      [k: string]: number;
    };
    mean_UI: number | null;
    mean_NSS: number | null;
    mean_S_e: number | null;
    failure_count: number;
  };
  files: {
    path: string;
    sha256: string;
    bytes: number;
  }[];
}
