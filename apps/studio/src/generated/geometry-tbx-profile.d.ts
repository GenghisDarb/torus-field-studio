/* Generated from the canonical repository schema. Do not edit by hand. */

export interface GeometryTBXProfile {
  schema_version: "1.0.0";
  profile_id: "geometry-tbx-v1";
  /**
   * @minItems 8
   */
  required_member_roles: [string, string, string, string, string, string, string, string, ...string[]];
  forbidden_claims: string[];
  independent_verifier_required: true;
  raw_arrays_required: true;
  registry_hashes_required: true;
}
