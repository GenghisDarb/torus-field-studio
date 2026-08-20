import Ajv2020 from "ajv/dist/2020";
import geometryClaimAdjudicationSchema from "../../../schemas/geometry-claim-adjudication/v1.schema.json";
import geometryProfileSchema from "../../../schemas/geometry-tbx-profile/v1.schema.json";
import type { FieldTable, GeometryBundleMetadata } from "./types";

type JsonRecord = Record<string, unknown>;

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function issue(errors: string[], code: string, detail: string) {
  errors.push(`${code}: ${detail}`);
}

function finiteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function containsNonfinite(value: unknown): boolean {
  if (typeof value === "number") return !Number.isFinite(value);
  if (Array.isArray(value)) return value.some(containsNonfinite);
  return isRecord(value) && Object.values(value).some(containsNonfinite);
}

function parseJson(members: Record<string, Uint8Array>, name: string, errors: string[]): unknown {
  const payload = members[name];
  if (!payload) return undefined;
  try {
    const value: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(payload));
    if (containsNonfinite(value)) throw new Error("nonfinite numeric value");
    return value;
  } catch (error) {
    issue(errors, "JSON_INVALID", `${name}: ${error instanceof Error ? error.message : "parse error"}`);
    return undefined;
  }
}

function parseJsonl(members: Record<string, Uint8Array>, name: string, errors: string[]): JsonRecord[] {
  const payload = members[name];
  if (!payload) return [];
  const rows: JsonRecord[] = [];
  try {
    for (const [index, line] of new TextDecoder("utf-8", { fatal: true }).decode(payload).split(/\r?\n/).entries()) {
      if (!line) continue;
      const row: unknown = JSON.parse(line);
      if (!isRecord(row) || containsNonfinite(row)) throw new Error(`line ${index + 1} is not a finite object`);
      rows.push(row);
    }
  } catch (error) {
    issue(errors, "JSONL_INVALID", `${name}: ${error instanceof Error ? error.message : "parse error"}`);
  }
  return rows;
}

async function sha256(payload: Uint8Array): Promise<string> {
  const copy = new Uint8Array(payload.byteLength);
  copy.set(payload);
  const digest = await crypto.subtle.digest("SHA-256", copy.buffer);
  return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, "0")).join("");
}

const ajv = new Ajv2020({ allErrors: true, strict: false });
const profileValidator = ajv.compile(geometryProfileSchema);
const adjudicationValidator = ajv.compile(geometryClaimAdjudicationSchema);

function schemaErrors(errors: string[], code: string, validator: typeof profileValidator, value: unknown) {
  if (validator(value)) return;
  for (const error of validator.errors ?? []) {
    issue(errors, code, `${error.instancePath || "$"}: ${error.message ?? "invalid"}`);
  }
}

export async function auditGeometrySemantics(
  members: Record<string, Uint8Array>,
  manifest: JsonRecord,
  errors: string[],
): Promise<{ table?: FieldTable; geometry?: GeometryBundleMetadata }> {
  const profile = parseJson(members, "geometry_profile.json", errors);
  const source = parseJson(members, "source_registry.json", errors);
  const custody = parseJson(members, "provenance/raw_array_custody.json", errors);
  const results = parseJson(members, "tables/geometry_channel_results.json", errors);
  const scales = parseJson(members, "tables/scale_behavior.json", errors);
  const baseline = parseJson(members, "tables/domain_baseline.json", errors);
  const independent = parseJson(members, "audit/independent_verification.json", errors);
  const adjudication = parseJson(members, "audit/claim_adjudication.json", errors);
  const forbidden = parseJson(members, "audit/forbidden_claims.json", errors);
  const parents = parseJsonl(members, "registry/parent_registry.jsonl", errors);
  const projections = parseJsonl(members, "registry/projection_registry.jsonl", errors);
  const nulls = parseJsonl(members, "registry/null_registry.jsonl", errors);
  const failures = parseJsonl(members, "audit/failure_ledger.jsonl", errors);
  const receipts = parseJsonl(members, "provenance/verification_receipts.jsonl", errors);
  if (
    !isRecord(profile)
    || !isRecord(source)
    || !isRecord(custody)
    || !isRecord(results)
    || !isRecord(scales)
    || !isRecord(baseline)
    || !isRecord(independent)
    || !isRecord(adjudication)
    || !isRecord(forbidden)
  ) return {};
  schemaErrors(errors, "GEOMETRY_PROFILE_SCHEMA_INVALID", profileValidator, profile);
  schemaErrors(errors, "GEOMETRY_CLAIM_SCHEMA_INVALID", adjudicationValidator, adjudication);
  if (profile.profile_id !== "geometry-tbx-v1" || profile.raw_arrays_required !== true) {
    issue(errors, "GEOMETRY_PROFILE_INVALID", "profile or raw-array contract");
  }
  const arrayMember = typeof custody.bundle_member === "string" ? custody.bundle_member : "";
  const arrayPayload = members[arrayMember];
  if (!arrayPayload || custody.sha256 !== await sha256(arrayPayload)) {
    issue(errors, "GEOMETRY_RAW_ARRAY_HASH_MISMATCH", arrayMember || "missing member");
  }
  if (source.pilot_role !== "NONCONFIRMATORY_STRUCTURE_EXPOSED_ENGINEERING_PILOT") {
    issue(errors, "GEOMETRY_PILOT_ROLE_INVALID", "source registry");
  }
  if (source.condition_acquisitions_exchangeable !== false) {
    issue(errors, "GEOMETRY_CONDITION_POOLING_FORBIDDEN", "source registry");
  }
  if (parents.length !== 4 || parents.filter((row) => row.role === "DOMAIN_CONTROL_BASELINE").length !== 1) {
    issue(errors, "GEOMETRY_PARENT_HIERARCHY_INVALID", "expected four conditions and one control");
  }
  if (!projections.length || !nulls.length) issue(errors, "GEOMETRY_REGISTRY_INCOMPLETE", "projection/null registry");
  const conditions = Array.isArray(results.conditions) ? results.conditions : [];
  if (conditions.length !== 4 || conditions.some((row) => !isRecord(row) || row.population_aggregate !== null)) {
    issue(errors, "GEOMETRY_CHANNEL_RESULTS_INVALID", "four separate unpooled condition rows required");
  }
  const scaleRows = Array.isArray(scales.rows) ? scales.rows : [];
  if (!scaleRows.length || scaleRows.some((row) => !isRecord(row) || row.geometric_scale_symbol !== "ell" || "S_e" in row)) {
    issue(errors, "GEOMETRY_SCALE_SE_COLLISION", "scale rows");
  }
  if (baseline.numeric_pooling_with_TLD_channels !== false) {
    issue(errors, "GEOMETRY_BASELINE_POOLING_INVALID", "domain baseline");
  }
  if (independent.status !== "VERIFIED" || independent.disagreements !== 0) {
    issue(errors, "GEOMETRY_INDEPENDENT_VERIFICATION_FAILED", "receipt");
  }
  const verifiedReceipt = receipts.some((row) => row.run_id === manifest.run_id && row.status === "verified" && Boolean(row.verifier));
  if (!verifiedReceipt) issue(errors, "VERIFIER_RECEIPT_MISSING", "geometry pilot");
  if (
    adjudication.run_id !== manifest.run_id
    || adjudication.method_mode !== "INSTRUMENTED_EVIDENCE_VECTOR"
    || adjudication.scientific_outcome !== "NONCONFIRMATORY_STRUCTURE_EXPOSED_ENGINEERING_PILOT"
  ) issue(errors, "GEOMETRY_ADJUDICATION_INVALID", "run, method, or outcome");
  if (adjudication.TLD_DERIVED !== "BLOCKED" || adjudication.EXTERNALLY_VALIDATED !== false) {
    issue(errors, "GEOMETRY_CLAIM_ESCALATION", "TLD or external-validation boundary");
  }
  if (["T_e", "S_e", "winner_N"].some((name) => !String(adjudication[name] ?? "").startsWith("NOT_APPLICABLE"))) {
    issue(errors, "GEOMETRY_SEMANTIC_ENDPOINT_INVALID", "T_e/S_e/winner_N");
  }
  const forbiddenValues = Array.isArray(forbidden.claims) ? forbidden.claims.map(String) : [];
  for (const claim of ["TLD confirmation", "ToT-BROT", "external validation", "population generalization"]) {
    if (!forbiddenValues.includes(claim)) issue(errors, "GEOMETRY_FORBIDDEN_CLAIMS_INCOMPLETE", claim);
  }
  const statistics = isRecord(manifest.statistics) ? manifest.statistics : {};
  const counts = isRecord(statistics.classification_counts) ? statistics.classification_counts : {};
  if (
    statistics.point_count !== 4
    || counts.NONCONFIRMATORY_CONDITION !== 4
    || Object.keys(counts).length !== 1
    || statistics.mean_UI !== null
    || statistics.mean_NSS !== null
    || statistics.mean_S_e !== null
  ) issue(errors, "STATISTICS_MISMATCH", "geometry pilot");
  if (statistics.failure_count !== failures.length) issue(errors, "FAILURE_COUNT_MISMATCH", "geometry failure ledger");
  const expectedSums = (await Promise.all(Object.entries(members)
    .filter(([name]) => name !== "manifest.json" && name !== "audit/SHA256SUMS.txt")
    .sort(([left], [right]) => left < right ? -1 : left > right ? 1 : 0)
    .map(async ([name, payload]) => `${await sha256(payload)}  ${name}\n`))).join("");
  if (new TextDecoder().decode(members["audit/SHA256SUMS.txt"]) !== expectedSums) {
    issue(errors, "SHA256SUMS_MISMATCH", "audit/SHA256SUMS.txt");
  }
  const points = conditions.filter(isRecord).map((row, index) => {
    const yaw = Array.isArray(row.yaw_degrees) ? row.yaw_degrees.map(Number) : [0, 0, 0];
    const channels = isRecord(row.P01_vector_channels) ? row.P01_vector_channels : {};
    const coherence = finiteNumber(channels.curl_coherence) ? channels.curl_coherence : 0;
    return {
      index,
      grid_x: index % 2,
      grid_y: Math.floor(index / 2),
      x: yaw[0] ?? 0,
      y: yaw[1] ?? 0,
      classification: "UNRESOLVED" as const,
      eligible: true,
      emerged: false,
      separated_from_null: false,
      closed: false,
      survived: false,
      escaped_from_reference: false,
      recovered: null,
      winner_N: null,
      T_e: null,
      S_e: null,
      UI: null,
      NSS: null,
      SEP: null,
      rms_to_parent: null,
      iterations: 0,
      parent_id: String(row.parent_id ?? `condition-${index + 1}`),
      null_policy_id: "N03_PARENT_LOCAL_MASK_PRESERVING_JOINT_CELL_PERMUTATION",
      trace: [{ step: 0, stage: "descriptive curl coherence", coherence }],
      observed: true,
      phase: String(row.condition_role ?? "condition"),
    };
  });
  const table: FieldTable = { schema_version: "1.0.0", width: 2, height: 2, points };
  return {
    table,
    geometry: {
      doi: String(source.doi),
      sourceId: String(source.source_id),
      profile: String(manifest.profile),
      pilotRole: String(source.pilot_role),
      methodId: String(adjudication.method_id),
      methodMode: String(adjudication.method_mode),
      scientificOutcome: String(adjudication.scientific_outcome),
      conditionCount: conditions.length,
      campaignCount: Number(source.campaign_count),
      geometricScale: String(adjudication.geometric_scale),
      T_e: String(adjudication.T_e),
      S_e: String(adjudication.S_e),
      winnerN: String(adjudication.winner_N),
      tldDerivedStatus: String(adjudication.TLD_DERIVED),
      externallyValidated: false,
      verificationStatus: String(independent.status),
      failureCount: failures.length,
      forbiddenClaims: forbiddenValues,
    },
  };
}
