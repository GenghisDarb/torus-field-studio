/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TLDReleaseSourceRegistry {
  schema_version: "1.0.0";
  source_id: string;
  doi: "10.5281/zenodo.18080090";
  record_url: string;
  title: string;
  archive: {
    filename: "TORUS_Zenodo_v1.zip";
    md5: {
      [k: string]: any;
    };
    sha256: {
      [k: string]: any;
    };
  };
  input_sha256: {
    [k: string]: {
      [k: string]: any;
    };
  };
  confirmatory_notebooks: [13, 14];
  exploratory_notebooks_used_as_evidence: false;
  license: string;
  claim_authority_ceiling: "COMPUTED_DYNAMICAL";
}
