/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TLDDomainPack {
  schema_version: "1.0.0";
  domain_id: string;
  doi: "10.5281/zenodo.18080090";
  source_input: "targets_baseline.csv";
  source_sha256: {
    [k: string]: any;
  };
  row_order: "source_csv_order";
  /**
   * @minItems 4
   */
  rows: [
    {
      index: number;
      family: string;
      label: string;
      value: number;
      sigma: number;
    },
    {
      index: number;
      family: string;
      label: string;
      value: number;
      sigma: number;
    },
    {
      index: number;
      family: string;
      label: string;
      value: number;
      sigma: number;
    },
    {
      index: number;
      family: string;
      label: string;
      value: number;
      sigma: number;
    },
    ...{
      index: number;
      family: string;
      label: string;
      value: number;
      sigma: number;
    }[]
  ];
  canonicalization: "none; preserve source scalar bytes and row order";
  ladderization: "omega=natural_log(value); sigma_omega=sigma/value";
  adjacency_topology: "ordered_path";
  units: "dimensionless";
  duplicate_policy: "preserve source rows";
  missing_value_policy: "reject";
  claim_authority: "COMPUTED_DYNAMICAL";
  license: string;
}
