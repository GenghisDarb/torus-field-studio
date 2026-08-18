/* Generated from the canonical repository schema. Do not edit by hand. */

export interface TLDTBXProfileDeclaration {
  schema_version: "1.0.0";
  profile: "tld-i-historical-v1" | "tld-i-combined-v1" | "tld-i-modern-v21";
  lane: string;
  required_members: string[];
  classification_precedes_rendering: true;
  interpolation_used_for_metrics: false;
}
