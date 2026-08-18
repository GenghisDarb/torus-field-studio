/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TORUSBundleExchangeManifest {
  tbx_version: "1.0.0";
  run_id: string;
  claim_level: string;
  kernel_id: string;
  specification_sha256: string;
  statistics: {
    point_count: number;
    classification_counts: {
      [k: string]: number;
    };
    mean_UI: number;
    mean_NSS: number;
    mean_S_e: number;
    failure_count: number;
  };
  files: {
    path: string;
    sha256: string;
    bytes: number;
  }[];
}
