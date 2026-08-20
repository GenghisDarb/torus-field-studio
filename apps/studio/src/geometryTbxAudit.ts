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
  const profileName = String(manifest.profile ?? "");
  const studyRole = String(source.study_role ?? source.pilot_role ?? "");
  const expectedRoles: Record<string, string> = {
    "geometry-pilot-v0.3.0": "NONCONFIRMATORY_STRUCTURE_EXPOSED_ENGINEERING_PILOT",
    "geometry-method-v2-v0.3.0": "METHOD_V2_SYNTHETIC_AND_HISTORICAL_CALIBRATION",
    "geometry-representation-v0.3.0": "METHOD_V2_REPRESENTATION_EQUIVARIANCE_AUDIT",
    "geometry-heldout-v0.3.0": "PROSPECTIVE_HELDOUT_FIELD_ASSAY",
    "geometry-combined-v0.3.0": "METHOD_V2_WITH_FIRST_HELDOUT_FIELD",
  };
  if (studyRole !== expectedRoles[profileName]) {
    issue(errors, "GEOMETRY_STUDY_ROLE_INVALID", "source registry");
  }
  if (source.condition_acquisitions_exchangeable !== false) {
    issue(errors, "GEOMETRY_CONDITION_POOLING_FORBIDDEN", "source registry");
  }
  const expectedParentCount = finiteNumber(source.registered_parent_count)
    ? source.registered_parent_count
    : profileName === "geometry-pilot-v0.3.0" ? 4 : -1;
  if (parents.length !== expectedParentCount || expectedParentCount < 1) {
    issue(errors, "GEOMETRY_PARENT_HIERARCHY_INVALID", "parent registry does not match source hierarchy");
  }
  if (
    profileName === "geometry-pilot-v0.3.0"
    && (parents.length !== 4 || parents.filter((row) => row.role === "DOMAIN_CONTROL_BASELINE").length !== 1)
  ) issue(errors, "GEOMETRY_PARENT_HIERARCHY_INVALID", "expected four conditions and one control");
  if (
    ["geometry-heldout-v0.3.0", "geometry-combined-v0.3.0"].includes(profileName)
    && (parents.length !== 28
      || parents.some((row) => row.statistical_unit !== "PAIRED_ACQUISITION_BLOCK")
      || source.population_generalization !== false
      || source.registered_observation_count !== 56
      || !String(source.projection_contract ?? "").includes("P01 temporal mean vector")
      || !String(source.projection_contract ?? "").includes("P02 full spatiotemporal fluctuations")
      || !String(source.null_contract ?? "").includes("127 local joint spatial cell permutations")
      || !String(source.null_contract ?? "").includes("999 frozen joint within-campaign replicates")
      || !String(source.closure_null_calibration ?? "").includes("parent-matched aggregate nulls"))
  ) issue(errors, "GEOMETRY_HELDOUT_HIERARCHY_INVALID", "expected 28 paired blocks, 56 observations, and frozen P01/P02 null contracts on one nonpopulation system");
  if (!projections.length || !nulls.length) issue(errors, "GEOMETRY_REGISTRY_INCOMPLETE", "projection/null registry");
  const conditions = Array.isArray(results.conditions) ? results.conditions : [];
  const expectedConditionCount = finiteNumber(source.display_condition_count)
    ? source.display_condition_count
    : profileName === "geometry-pilot-v0.3.0" ? 4 : -1;
  if (conditions.length !== expectedConditionCount || conditions.some((row) => !isRecord(row) || row.population_aggregate !== null)) {
    issue(errors, "GEOMETRY_CHANNEL_RESULTS_INVALID", "registered unpooled condition rows required");
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
  const expectedOutcome = profileName === "geometry-pilot-v0.3.0"
    ? "NONCONFIRMATORY_STRUCTURE_EXPOSED_ENGINEERING_PILOT"
    : "GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY";
  if (
    adjudication.run_id !== manifest.run_id
    || adjudication.method_mode !== "INSTRUMENTED_EVIDENCE_VECTOR"
    || adjudication.scientific_outcome !== expectedOutcome
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
  const recomputedCounts: Record<string, number> = {};
  for (const row of conditions.filter(isRecord)) {
    const classification = String(row.classification ?? "UNSPECIFIED");
    recomputedCounts[classification] = (recomputedCounts[classification] ?? 0) + 1;
  }
  if (
    statistics.point_count !== expectedConditionCount
    || JSON.stringify(counts) !== JSON.stringify(recomputedCounts)
    || statistics.mean_UI !== null
    || statistics.mean_NSS !== null
    || statistics.mean_S_e !== null
  ) issue(errors, "STATISTICS_MISMATCH", "geometry condition rows");
  if (statistics.failure_count !== failures.length) issue(errors, "FAILURE_COUNT_MISMATCH", "geometry failure ledger");
  const expectedSums = (await Promise.all(Object.entries(members)
    .filter(([name]) => name !== "manifest.json" && name !== "audit/SHA256SUMS.txt")
    .sort(([left], [right]) => left < right ? -1 : left > right ? 1 : 0)
    .map(async ([name, payload]) => `${await sha256(payload)}  ${name}\n`))).join("");
  if (new TextDecoder().decode(members["audit/SHA256SUMS.txt"]) !== expectedSums) {
    issue(errors, "SHA256SUMS_MISMATCH", "audit/SHA256SUMS.txt");
  }
  const gridWidth = Math.max(1, Math.ceil(Math.sqrt(conditions.length)));
  const points = conditions.filter(isRecord).map((row, index) => {
    const yaw = Array.isArray(row.yaw_degrees) ? row.yaw_degrees.map(Number) : [0, 0, 0];
    const channels = isRecord(row.P01_vector_channels)
      ? row.P01_vector_channels
      : isRecord(row.P01_pair_delta) ? row.P01_pair_delta : {};
    const coherence = finiteNumber(channels.curl_coherence) ? channels.curl_coherence : 0;
    return {
      index,
      grid_x: index % gridWidth,
      grid_y: Math.floor(index / gridWidth),
      x: finiteNumber(row.p) ? row.p : yaw[0] ?? index,
      y: finiteNumber(row.p) ? coherence : yaw[1] ?? 0,
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
      parent_id: String(row.pair_id ?? row.parent_id ?? `condition-${index + 1}`),
      null_policy_id: "N03_PARENT_LOCAL_MASK_PRESERVING_JOINT_CELL_PERMUTATION",
      trace: [{ step: 0, stage: "descriptive curl coherence", coherence }],
      observed: true,
      phase: String(row.classification ?? row.condition_role ?? "condition"),
    };
  });
  const table: FieldTable = {
    schema_version: "1.0.0",
    width: gridWidth,
    height: Math.max(1, Math.ceil(points.length / gridWidth)),
    points,
  };
  return {
    table,
    geometry: {
      doi: String(source.doi),
      sourceId: String(source.source_id),
      profile: String(manifest.profile),
      pilotRole: studyRole,
      studyRole,
      statisticalUnit: String(source.statistical_unit ?? "condition acquisition"),
      rawObservationRole: String(custody.content_role ?? "registered arrays"),
      coordinateContract: String(source.coordinate_contract ?? "registered source coordinates"),
      unitContract: String(source.unit_contract ?? "source units with provenance"),
      maskPolicy: String(source.mask_policy ?? "explicit mask; no fill or interpolation"),
      nestedReplicates: String(source.nested_replicates ?? "not promoted to parents"),
      modalities: String(source.modalities ?? "registered typed geometry"),
      registeredObservationCount: Number(source.registered_observation_count ?? conditions.length),
      projectionContract: String(source.projection_contract ?? "registered projections"),
      nullContract: String(source.null_contract ?? "registered structure-preserving nulls"),
      closureNullCalibration: String(source.closure_null_calibration ?? "registered separately"),
      projectionCount: projections.length,
      nullCount: nulls.length,
      operationDepth: String(source.operation_depth ?? "NOT_APPLICABLE"),
      claimTier: String(source.claim_tier ?? adjudication.claim_ceiling),
      domainBaseline: String(baseline.baseline_id ?? "registered separately"),
      structuredFragility: String(source.structured_fragility ?? "registered perturbation panel"),
      representationAgreement: String(source.representation_agreement ?? independent.status),
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
