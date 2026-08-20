import Ajv2020, { type ValidateFunction } from "ajv/dist/2020";
import { unzipSync } from "fflate";
import claimBoundarySchema from "../../../schemas/claim-boundary/v1.schema.json";
import failureSchema from "../../../schemas/evidence/failure-v1.schema.json";
import fieldTableSchema from "../../../schemas/field-table/v1.schema.json";
import fieldPointSchema from "../../../schemas/local-brot/v1.schema.json";
import runSpecSchema from "../../../schemas/run-spec/v1.schema.json";
import manifestSchema from "../../../schemas/tbx/v1.schema.json";
import tldClaimAdjudicationSchema from "../../../schemas/tld-claim-adjudication/v1.schema.json";
import tldEndpointTableSchema from "../../../schemas/tld-endpoint-table/v1.schema.json";
import tldIndependentVerificationSchema from "../../../schemas/independent-verification/v1.schema.json";
import tldLadderRegistrySchema from "../../../schemas/tld-ladder-registry/v1.schema.json";
import tldPreregistrationSchema from "../../../schemas/tld-preregistration-result/v1.schema.json";
import tldProfileSchema from "../../../schemas/tld-tbx-profile/v1.schema.json";
import tldReleaseSourceSchema from "../../../schemas/tld-release-source/v1.schema.json";
import tldTrajectorySchema from "../../../schemas/tld-trajectory-trace/v1.schema.json";
import type { TORUSBundleExchangeManifest } from "./generated/manifest";
import type { FieldTable, GeometryBundleMetadata, HeldoutBundleMetadata, TldBundleMetadata } from "./types";

const REQUIRED_MEMBERS = new Set([
  "run_spec.json",
  "ontology.json",
  "claim_boundary.json",
  "visual_encoding.json",
  "scene_recipe.json",
  "provenance/sources.jsonl",
  "provenance/transformations.jsonl",
  "provenance/verification_receipts.jsonl",
  "registry/parent_registry.json",
  "registry/null_registry.json",
  "tables/field_points.json",
  "tables/metrics_by_N.json",
  "audit/audit.json",
  "audit/failure_ledger.jsonl",
  "audit/SHA256SUMS.txt",
]);

const TLD_REQUIRED_MEMBERS = new Set([
  "source_registry.json",
  "preregistration_contract.json",
  "tld_profile.json",
  "registry/ladder_registry.json",
  "registry/control_or_null_registry.json",
  "tables/tld_endpoint_table.json",
  "tables/baseline_scores.json",
  "tables/alpha_sweep.json",
  "tables/core_alpha_compare.json",
  "tables/preregistration_results.json",
  "tables/trajectories.jsonl",
  "tables/transition_counts.json",
  "tables/operating_envelope.json",
  "audit/independent_verification.json",
  "audit/claim_adjudication.json",
]);

const HELDOUT_REQUIRED_MEMBERS = new Set([
  "heldout_profile.json",
  "source_registry.json",
  "domain_translation.json",
  "preregistration.json",
  "registry/parent_registry.csv",
  "registry/ladder_registry.csv",
  "registry/null_registry.csv",
  "registry/perturbation_registry.csv",
  "tables/byN_surface.csv",
  "tables/emergent_time_by_parent.csv",
  "tables/emergent_scale_by_parent.csv",
  "tables/primary_endpoints.json",
  "tables/closure_mode_results.csv",
  "tables/parent_null_comparison.csv",
  "tables/structured_fragility_results.csv",
  "tables/specificity_audit.csv",
  "tables/domain_baseline_comparison.csv",
  "audit/independent_verification.json",
  "audit/independent_recomputed_endpoints.json",
  "audit/mutation_results.jsonl",
  "audit/claim_adjudication.json",
  "audit/forbidden_claims.json",
  "reports/plain_language_summary.md",
  "reports/technical_report.md",
  "visualization/byN_surface.svg",
  "visualization/byN_surface.png",
]);

const GEOMETRY_REQUIRED_MEMBERS = new Set([
  "geometry_profile.json",
  "source_registry.json",
  "ontology.json",
  "claim_boundary.json",
  "visual_encoding.json",
  "scene_recipe.json",
  "provenance/sources.jsonl",
  "provenance/transformations.jsonl",
  "provenance/verification_receipts.jsonl",
  "provenance/raw_array_custody.json",
  "arrays/registered_binned_fields.npz",
  "registry/parent_registry.jsonl",
  "registry/projection_registry.jsonl",
  "registry/null_registry.jsonl",
  "tables/geometry_channel_results.json",
  "tables/scale_behavior.json",
  "tables/domain_baseline.json",
  "audit/independent_verification.json",
  "audit/claim_adjudication.json",
  "audit/forbidden_claims.json",
  "audit/failure_ledger.jsonl",
  "audit/SHA256SUMS.txt",
]);

const TLD_I_INPUT_HASHES: Record<string, string> = {
  "targets_baseline.csv": "856f102a4f58d53d67fdb1ac5982de12ca18a9c78efe13097f23879e262cb683",
  "targets_metadata_addon.csv": "dfba2dc563706d284313f27e679132d028ea77c49a8816cff944baef13dd135f",
  "targets_metadata_template.csv": "49a536790c6920a6627f903062e0c0d4ce831acd167173ea1a366b7139f980e3",
};

const POLICY = {
  maxFiles: 256,
  maxMemberBytes: 64 * 1024 * 1024,
  maxTotalBytes: 256 * 1024 * 1024,
  maxJsonBytes: 16 * 1024 * 1024,
  maxJsonDepth: 32,
  maxCompressionRatio: 200,
};

type JsonRecord = Record<string, unknown>;

type ManifestEntry = TORUSBundleExchangeManifest["files"][number];
type Manifest = TORUSBundleExchangeManifest & JsonRecord;

export interface TbxAuditResult {
  valid: boolean;
  issueCodes: string[];
  errors: string[];
  checkedFiles: number;
  manifest?: Manifest;
  specification?: JsonRecord;
  table?: FieldTable;
  tld?: TldBundleMetadata;
  heldout?: HeldoutBundleMetadata;
  geometry?: GeometryBundleMetadata;
}

function issue(errors: string[], code: string, detail: string) {
  errors.push(`${code}: ${detail}`);
}

export function compareCodePoints(left: string, right: string): number {
  const leftPoints = [...left];
  const rightPoints = [...right];
  for (let index = 0; index < Math.min(leftPoints.length, rightPoints.length); index += 1) {
    const difference = leftPoints[index].codePointAt(0)! - rightPoints[index].codePointAt(0)!;
    if (difference !== 0) return difference;
  }
  return leftPoints.length - rightPoints.length;
}

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function sortValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortValue);
  if (isRecord(value)) {
    return Object.fromEntries(Object.keys(value).sort(compareCodePoints).map((key) => [key, sortValue(value[key])]));
  }
  return value;
}

export function canonicalJson(value: unknown, pretty = false): string {
  return `${JSON.stringify(sortValue(value), null, pretty ? 2 : undefined)}\n`;
}

async function sha256(payload: Uint8Array | string): Promise<string> {
  const bytes = typeof payload === "string" ? new TextEncoder().encode(payload) : payload;
  const copy = new Uint8Array(bytes.byteLength);
  copy.set(bytes);
  const digest = await crypto.subtle.digest("SHA-256", copy.buffer);
  return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, "0")).join("");
}

function canonicalMemberPath(name: string, directory = false): boolean {
  const candidate = directory && name.endsWith("/") ? name.slice(0, -1) : name;
  if (!candidate || candidate.includes("\\") || candidate.includes("\0")) return false;
  if (candidate.startsWith("/") || candidate.endsWith("/") || candidate.includes("//")) return false;
  if (/^[A-Za-z]:/.test(candidate)) return false;
  return candidate.split("/").every((part) => part !== "" && part !== "." && part !== "..");
}

function readUint32(view: DataView, offset: number): number {
  return view.getUint32(offset, true);
}

function preflightArchive(bytes: Uint8Array, errors: string[]): void {
  if (bytes.byteLength < 22) {
    issue(errors, "ARCHIVE_INVALID", "archive is shorter than a ZIP end record");
    return;
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const searchStart = Math.max(0, bytes.byteLength - 65_557);
  let endOffset = -1;
  for (let offset = bytes.byteLength - 22; offset >= searchStart; offset -= 1) {
    if (readUint32(view, offset) === 0x06054b50) {
      endOffset = offset;
      break;
    }
  }
  if (endOffset < 0) {
    issue(errors, "ARCHIVE_INVALID", "ZIP end record is missing");
    return;
  }
  const fileCount = view.getUint16(endOffset + 10, true);
  const centralOffset = readUint32(view, endOffset + 16);
  if (fileCount === 0xffff || centralOffset === 0xffffffff) {
    issue(errors, "ARCHIVE_INVALID", "ZIP64 archives are not accepted by the browser importer");
    return;
  }
  if (fileCount > POLICY.maxFiles) issue(errors, "ARCHIVE_FILE_LIMIT", `${fileCount} files exceeds ${POLICY.maxFiles}`);
  const names = new Set<string>();
  const duplicateNames = new Set<string>();
  let totalBytes = 0;
  let offset = centralOffset;
  try {
    for (let index = 0; index < fileCount; index += 1) {
      if (readUint32(view, offset) !== 0x02014b50) throw new Error("invalid central-directory entry");
      const flags = view.getUint16(offset + 8, true);
      const compressedBytes = readUint32(view, offset + 20);
      const memberBytes = readUint32(view, offset + 24);
      const nameLength = view.getUint16(offset + 28, true);
      const extraLength = view.getUint16(offset + 30, true);
      const commentLength = view.getUint16(offset + 32, true);
      const nameStart = offset + 46;
      const nameEnd = nameStart + nameLength;
      if (nameEnd > bytes.byteLength) throw new Error("truncated member name");
      const name = new TextDecoder("utf-8", { fatal: true }).decode(bytes.subarray(nameStart, nameEnd));
      const directory = name.endsWith("/");
      if (!canonicalMemberPath(name, directory)) issue(errors, "ARCHIVE_PATH_INVALID", name);
      if (!directory) {
        if (names.has(name)) duplicateNames.add(name);
        names.add(name);
        if ((flags & 0x1) !== 0) issue(errors, "ARCHIVE_ENCRYPTED_MEMBER", name);
        totalBytes += memberBytes;
        if (memberBytes > POLICY.maxMemberBytes) issue(errors, "ARCHIVE_MEMBER_LIMIT", `${name} is ${memberBytes} bytes`);
        const ratio = compressedBytes === 0 && memberBytes > 0 ? Infinity : memberBytes / Math.max(compressedBytes, 1);
        if (ratio > POLICY.maxCompressionRatio) issue(errors, "ARCHIVE_COMPRESSION_RATIO", `${name} ratio ${ratio.toFixed(1)} exceeds ${POLICY.maxCompressionRatio}`);
      }
      offset = nameEnd + extraLength + commentLength;
    }
  } catch (error) {
    issue(errors, "ARCHIVE_INVALID", error instanceof Error ? error.message : "invalid central directory");
  }
  if (duplicateNames.size) issue(errors, "ARCHIVE_DUPLICATE_MEMBER", [...duplicateNames].sort().join(", "));
  if (totalBytes > POLICY.maxTotalBytes) issue(errors, "ARCHIVE_TOTAL_LIMIT", `${totalBytes} bytes exceeds limit`);
}

function jsonDepth(value: unknown, depth = 0): number {
  if (Array.isArray(value)) return Math.max(depth, ...value.map((item) => jsonDepth(item, depth + 1)));
  if (isRecord(value)) return Math.max(depth, ...Object.values(value).map((item) => jsonDepth(item, depth + 1)));
  return depth;
}

function containsNonfinite(value: unknown): boolean {
  if (typeof value === "number") return !Number.isFinite(value);
  if (Array.isArray(value)) return value.some(containsNonfinite);
  return isRecord(value) && Object.values(value).some(containsNonfinite);
}

function parseJson(members: Record<string, Uint8Array>, name: string, errors: string[]): unknown {
  const payload = members[name];
  if (!payload) return undefined;
  if (payload.byteLength > POLICY.maxJsonBytes) {
    issue(errors, "JSON_SIZE_LIMIT", name);
    return undefined;
  }
  try {
    const parsed: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(payload));
    if (jsonDepth(parsed) > POLICY.maxJsonDepth) {
      issue(errors, "JSON_DEPTH_LIMIT", name);
      return undefined;
    }
    if (containsNonfinite(parsed)) {
      issue(errors, "JSON_NONFINITE", name);
      return undefined;
    }
    return parsed;
  } catch (error) {
    issue(errors, "JSON_INVALID", `${name}: ${error instanceof Error ? error.message : "parse error"}`);
    return undefined;
  }
}

function parseJsonl(members: Record<string, Uint8Array>, name: string, errors: string[]): JsonRecord[] {
  const payload = members[name] ?? new Uint8Array();
  if (payload.byteLength > POLICY.maxJsonBytes) {
    issue(errors, "JSON_SIZE_LIMIT", name);
    return [];
  }
  const rows: JsonRecord[] = [];
  let text: string;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(payload);
  } catch (error) {
    issue(errors, "JSONL_INVALID", `${name}: ${error instanceof Error ? error.message : "invalid UTF-8"}`);
    return [];
  }
  for (const [index, line] of text.split(/\r?\n/).entries()) {
    if (!line.trim()) continue;
    try {
      const row: unknown = JSON.parse(line);
      if (!isRecord(row) || jsonDepth(row) > POLICY.maxJsonDepth || containsNonfinite(row)) throw new Error("row must be a finite, shallow object");
      rows.push(row);
    } catch (error) {
      issue(errors, "JSONL_INVALID", `${name}:${index + 1}: ${error instanceof Error ? error.message : "parse error"}`);
    }
  }
  return rows;
}

function parseCsv(members: Record<string, Uint8Array>, name: string, errors: string[]): Record<string, string>[] {
  const payload = members[name];
  if (!payload) {
    issue(errors, "MEMBER_MISSING", name);
    return [];
  }
  let text = "";
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(payload);
  } catch (error) {
    issue(errors, "CSV_INVALID", `${name}: ${error instanceof Error ? error.message : "decode failed"}`);
    return [];
  }
  const lines = text.trimEnd().split(/\r?\n/);
  if (!lines.length || !lines[0]) return [];
  const headers = lines[0].split(",");
  return lines.slice(1).filter(Boolean).map((line) => {
    const values = line.split(",");
    return Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]));
  });
}

const ajv = new Ajv2020({ allErrors: true, strict: false });
for (const schema of [
  manifestSchema,
  runSpecSchema,
  claimBoundarySchema,
  fieldPointSchema,
  fieldTableSchema,
  failureSchema,
  tldClaimAdjudicationSchema,
  tldEndpointTableSchema,
  tldIndependentVerificationSchema,
  tldLadderRegistrySchema,
  tldPreregistrationSchema,
  tldProfileSchema,
  tldReleaseSourceSchema,
  tldTrajectorySchema,
]) {
  ajv.addSchema(schema);
}

function schemaValidator(id: string): ValidateFunction {
  const validator = ajv.getSchema(id);
  if (!validator) throw new Error(`Missing bundled schema: ${id}`);
  return validator;
}

const validators = {
  manifest: schemaValidator(manifestSchema.$id),
  runSpec: schemaValidator(runSpecSchema.$id),
  claim: schemaValidator(claimBoundarySchema.$id),
  table: schemaValidator(fieldTableSchema.$id),
  failure: schemaValidator(failureSchema.$id),
  tldClaimAdjudication: schemaValidator(tldClaimAdjudicationSchema.$id),
  tldEndpointTable: schemaValidator(tldEndpointTableSchema.$id),
  tldIndependentVerification: schemaValidator(tldIndependentVerificationSchema.$id),
  tldLadderRegistry: schemaValidator(tldLadderRegistrySchema.$id),
  tldPreregistration: schemaValidator(tldPreregistrationSchema.$id),
  tldProfile: schemaValidator(tldProfileSchema.$id),
  tldReleaseSource: schemaValidator(tldReleaseSourceSchema.$id),
  tldTrajectory: schemaValidator(tldTrajectorySchema.$id),
};

function schemaErrors(errors: string[], code: string, validator: ValidateFunction, value: unknown) {
  if (validator(value)) return;
  for (const error of validator.errors ?? []) {
    const detail = `${error.instancePath || "$"}: ${error.message ?? "invalid"}`;
    issue(errors, code, detail);
  }
}

interface LosslessNumber { numberToken: string }
type LosslessJson = null | boolean | string | LosslessNumber | LosslessJson[] | { [key: string]: LosslessJson };

function parseLosslessJson(source: string): LosslessJson {
  let offset = 0;
  const whitespace = () => { while (/\s/.test(source[offset] ?? "")) offset += 1; };
  const parseString = (): string => {
    const start = offset;
    offset += 1;
    while (offset < source.length) {
      if (source[offset] === "\\") offset += 2;
      else if (source[offset++] === "\"") break;
    }
    return JSON.parse(source.slice(start, offset)) as string;
  };
  const parseValue = (): LosslessJson => {
    whitespace();
    const current = source[offset];
    if (current === "\"") return parseString();
    if (current === "[") {
      offset += 1;
      const values: LosslessJson[] = [];
      whitespace();
      while (source[offset] !== "]") {
        values.push(parseValue());
        whitespace();
        if (source[offset] === ",") offset += 1;
        else if (source[offset] !== "]") throw new Error("invalid array");
      }
      offset += 1;
      return values;
    }
    if (current === "{") {
      offset += 1;
      const value: { [key: string]: LosslessJson } = {};
      whitespace();
      while (source[offset] !== "}") {
        if (source[offset] !== "\"") throw new Error("invalid object key");
        const key = parseString();
        whitespace();
        if (source[offset++] !== ":") throw new Error("invalid object separator");
        value[key] = parseValue();
        whitespace();
        if (source[offset] === ",") offset += 1;
        else if (source[offset] !== "}") throw new Error("invalid object");
        whitespace();
      }
      offset += 1;
      return value;
    }
    for (const literal of ["true", "false", "null"] as const) {
      if (source.startsWith(literal, offset)) {
        offset += literal.length;
        return literal === "true" ? true : literal === "false" ? false : null;
      }
    }
    const token = source.slice(offset).match(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/)?.[0];
    if (!token) throw new Error("invalid JSON value");
    offset += token.length;
    return { numberToken: token };
  };
  const value = parseValue();
  whitespace();
  if (offset !== source.length) throw new Error("trailing JSON content");
  return value;
}

function stringifyLossless(value: LosslessJson, pretty = false, depth = 0): string {
  if (value === null || typeof value === "boolean") return String(value);
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) {
    if (!pretty) return `[${value.map((item) => stringifyLossless(item)).join(",")}]`;
    if (value.length === 0) return "[]";
    const indentation = "  ".repeat(depth + 1);
    const closing = "  ".repeat(depth);
    return `[\n${value.map((item) => `${indentation}${stringifyLossless(item, true, depth + 1)}`).join(",\n")}\n${closing}]`;
  }
  if ("numberToken" in value && typeof value.numberToken === "string") return value.numberToken;
  const record = value as { [key: string]: LosslessJson };
  const keys = Object.keys(record).sort(compareCodePoints);
  if (!pretty) return `{${keys.map((key) => `${JSON.stringify(key)}:${stringifyLossless(record[key])}`).join(",")}}`;
  if (keys.length === 0) return "{}";
  const indentation = "  ".repeat(depth + 1);
  const closing = "  ".repeat(depth);
  return `{\n${keys.map((key) => `${indentation}${JSON.stringify(key)}: ${stringifyLossless(record[key], true, depth + 1)}`).join(",\n")}\n${closing}}`;
}

function canonicalizeRawJson(source: string, pretty = false): string {
  return `${stringifyLossless(parseLosslessJson(source), pretty)}\n`;
}

function equalCounts(left: unknown, right: Record<string, number>): boolean {
  if (!isRecord(left)) return false;
  const leftKeys = Object.keys(left).sort();
  const rightKeys = Object.keys(right).sort();
  return leftKeys.length === rightKeys.length && leftKeys.every((key, index) => key === rightKeys[index] && left[key] === right[key]);
}

function finiteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function equalStringSet(left: unknown, right: Set<string>): boolean {
  return Array.isArray(left)
    && left.every((value) => typeof value === "string")
    && left.length === right.size
    && left.every((value) => right.has(value));
}

function auditTldSemantics(
  members: Record<string, Uint8Array>,
  manifest: Manifest,
  claim: JsonRecord,
  ontology: JsonRecord,
  points: unknown[],
  failures: JsonRecord[],
  errors: string[],
): TldBundleMetadata | undefined {
  const source = parseJson(members, "source_registry.json", errors);
  const preregistration = parseJson(members, "preregistration_contract.json", errors);
  const profile = parseJson(members, "tld_profile.json", errors);
  const ladderRegistry = parseJson(members, "registry/ladder_registry.json", errors);
  const endpoints = parseJson(members, "tables/tld_endpoint_table.json", errors);
  const independent = parseJson(members, "audit/independent_verification.json", errors);
  const adjudication = parseJson(members, "audit/claim_adjudication.json", errors);
  const transitions = parseJson(members, "tables/transition_counts.json", errors);
  const baseline = parseJson(members, "tables/baseline_scores.json", errors);
  const alphaSweep = parseJson(members, "tables/alpha_sweep.json", errors);
  const operatingEnvelope = parseJson(members, "tables/operating_envelope.json", errors);
  const core = parseJson(members, "tables/core_alpha_compare.json", errors);
  const controls = parseJson(members, "registry/control_or_null_registry.json", errors);
  const trajectories = parseJsonl(members, "tables/trajectories.jsonl", errors);
  const documents: Array<[string, ValidateFunction, unknown]> = [
    ["source registry", validators.tldReleaseSource, source],
    ["preregistration", validators.tldPreregistration, preregistration],
    ["profile", validators.tldProfile, profile],
    ["ladder registry", validators.tldLadderRegistry, ladderRegistry],
    ["endpoint table", validators.tldEndpointTable, endpoints],
    ["independent verification", validators.tldIndependentVerification, independent],
    ["claim adjudication", validators.tldClaimAdjudication, adjudication],
    ["trajectory trace", validators.tldTrajectory, { schema_version: "1.0.0", rows: trajectories }],
  ];
  for (const [name, validator, value] of documents) schemaErrors(errors, "TLD_SCHEMA_INVALID", validator, value);
  if (
    !isRecord(source)
    || !isRecord(preregistration)
    || !isRecord(profile)
    || !isRecord(ladderRegistry)
    || !isRecord(endpoints)
    || !isRecord(independent)
    || !isRecord(adjudication)
  ) return undefined;
  if (source.doi !== "10.5281/zenodo.18080090") issue(errors, "TLD_SOURCE_DOI_MISMATCH", String(source.doi));
  if (source.claim_authority_ceiling !== "COMPUTED_DYNAMICAL") issue(errors, "TLD_SOURCE_CLAIM_CEILING_INVALID", "source registry");
  if (canonicalJson(source.input_sha256) !== canonicalJson(TLD_I_INPUT_HASHES)) issue(errors, "TLD_SOURCE_INPUT_HASH_MISMATCH", "source registry");
  if (profile.profile !== manifest.profile) issue(errors, "TLD_PROFILE_MISMATCH", "manifest and profile declaration");
  if (!equalStringSet(profile.required_members, TLD_REQUIRED_MEMBERS)) issue(errors, "TLD_PROFILE_MEMBERS_INVALID", "required member declaration");
  if (profile.interpolation_used_for_metrics !== false) issue(errors, "TLD_INTERPOLATION_AS_OBSERVATION", "profile declaration");
  if (independent.status !== "verified" || !isRecord(independent.checks) || Object.values(independent.checks).some((value) => typeof value === "boolean" && value !== true)) {
    issue(errors, "TLD_INDEPENDENT_VERIFICATION_FAILED", "receipt status or checks");
  }
  if (adjudication.externally_validated !== false) issue(errors, "TLD_EXTERNAL_VALIDATION_FORBIDDEN", "claim adjudication");
  if (adjudication.claim_level !== claim.claim_level) issue(errors, "TLD_CLAIM_ADJUDICATION_MISMATCH", "claim boundary");
  if (manifest.claim_level === "TLD_DERIVED" && adjudication.tld_derived_status !== "PERMITTED") issue(errors, "TLD_DERIVED_GATE_BLOCKED", "claim adjudication");

  const nonEquivalences = Array.isArray(ontology.non_equivalences) ? ontology.non_equivalences : [];
  if (!["winner_N != T_e", "winner_N != S_e", "TORUS-BROT != ToT-BROT"].every((term) => nonEquivalences.includes(term))) {
    issue(errors, "TLD_ONTOLOGY_CONFLATION", "required non-equivalences");
  }
  if (isRecord(preregistration.criteria)) {
    const passed = Object.values(preregistration.criteria).filter((value) => value === true).length;
    const failed = Object.values(preregistration.criteria).filter((value) => value === false).length;
    if (preregistration.passed !== passed || preregistration.failed !== failed) issue(errors, "TLD_PREREGISTRATION_COUNT_MISMATCH", "criteria counts");
    if (Array.isArray(core) && core.length === 2 && core.every(isRecord)) {
      const [alpha0, alpha002] = core;
      const expected = {
        "alpha0_escape_rate_at_least_0.90": Number(alpha0.escape_rate) >= 0.9,
        "alpha0_return_rate_at_most_0.40": Number(alpha0.return_rate_given_escape) <= 0.4,
        "alpha002_escape_rate_at_least_0.90": Number(alpha002.escape_rate) >= 0.9,
        "alpha002_return_rate_at_least_0.95": Number(alpha002.return_rate_given_escape) >= 0.95,
        "alpha002_mean_return_steps_at_most_120": Number(alpha002.mean_return_steps) <= 120,
        "alpha002_p90_flips_at_most_5": Number(alpha002.p90_flips) <= 5,
      };
      if (canonicalJson(preregistration.criteria) !== canonicalJson(expected)) issue(errors, "TLD_PREREGISTRATION_OUTCOME_MISMATCH", "core results");
      if (alpha0.alpha_heal !== 0 || alpha002.alpha_heal !== 0.02) issue(errors, "TLD_PREREGISTRATION_CONTROL_MISMATCH", "alpha order");
    } else issue(errors, "TLD_PREREGISTRATION_SOURCE_INVALID", "core results");
  }
  if (Array.isArray(endpoints.rows)) {
    endpoints.rows.forEach((row, index) => {
      if (isRecord(row) && (row.T_e != null || row.S_e != null)) issue(errors, "TLD_UNCOMPUTED_ENDPOINT_POPULATED", String(index));
    });
  }

  const seenTraceRows = new Set<string>();
  const grouped = new Map<number, JsonRecord[]>();
  trajectories.forEach((row, index) => {
    const identity = `${row.trial_id}:${row.phase}:${row.t}`;
    if (seenTraceRows.has(identity)) issue(errors, "TLD_TRAJECTORY_DUPLICATE", String(index));
    seenTraceRows.add(identity);
    if (row.phase === "heal" && Number.isInteger(row.trial_id)) {
      const trial = Number(row.trial_id);
      grouped.set(trial, [...(grouped.get(trial) ?? []), row]);
    }
  });
  const recomputed = new Map<string, number>();
  grouped.forEach((rows) => {
    rows.sort((left, right) => Number(left.t) - Number(right.t));
    for (let index = 1; index < rows.length; index += 1) {
      const key = `${rows[index - 1].alpha_heal}:${rows[index - 1].winner_N}:${rows[index].winner_N}`;
      recomputed.set(key, (recomputed.get(key) ?? 0) + 1);
    }
  });
  const reported = new Map<string, number>();
  if (Array.isArray(transitions)) transitions.forEach((row) => {
    if (isRecord(row)) reported.set(`${row.alpha_heal}:${row.from_N}:${row.to_N}`, Number(row.count));
  });
  if (canonicalJson(Object.fromEntries([...reported].sort())) !== canonicalJson(Object.fromEntries([...recomputed].sort()))) {
    issue(errors, "TLD_TRANSITION_COUNT_MISMATCH", "raw trajectories");
  }
  const missingFailureIds = new Set(points.filter(isRecord).filter((point) => point.observed === false).map((point) => point.failure_id));
  const ledgerIds = new Set(failures.map((failure) => failure.failure_id));
  if (canonicalJson([...missingFailureIds].sort()) !== canonicalJson([...ledgerIds].sort())) issue(errors, "TLD_FAILURE_PRESERVATION_MISMATCH", "missing cells and ledger");
  if (profile.profile === "tld-i-modern-v21" && Array.isArray(controls) && controls.some((control) => isRecord(control) && ["scope", "pool", "null_pool"].some((key) => ["global", "global_pool", "pooled_global"].includes(String(control[key] ?? "").toLowerCase())))) {
    issue(errors, "TLD_GLOBAL_NULL_POOL_FORBIDDEN", "modern controls");
  }
  return {
    doi: String(source.doi),
    title: String(source.title),
    profile: String(profile.profile),
    lane: String(profile.lane),
    preregistrationPassed: Number(preregistration.passed),
    preregistrationFailed: Number(preregistration.failed),
    verificationStatus: String(independent.status),
    tldDerivedStatus: String(adjudication.tld_derived_status),
    blockers: Array.isArray(adjudication.blockers) ? adjudication.blockers.map(String) : [],
    forbiddenClaims: Array.isArray(adjudication.forbidden_claims) ? adjudication.forbidden_claims.map(String) : [],
    failureCount: failures.length,
    baselineWinnerN: isRecord(baseline) && isRecord(baseline.sweep_2_30) ? Number(baseline.sweep_2_30.winner_N) : Number.NaN,
    baselineMargin: isRecord(baseline) && isRecord(baseline.sweep_2_30) ? Number(baseline.sweep_2_30.margin) : Number.NaN,
    alphaSweep: Array.isArray(alphaSweep) ? alphaSweep.filter(isRecord).map((row) => ({
      alpha: Number(row.alpha_heal),
      escapeRate: Number(row.escape_rate),
      returnRate: Number(row.return_rate_given_escape),
      meanReturnSteps: Number(row.mean_return_steps),
      p90Flips: Number(row.p90_flips),
    })) : [],
    operatingEnvelope: Array.isArray(operatingEnvelope) ? operatingEnvelope.filter(isRecord).map((row) => ({
      escapeStrength: Number(row.p_swap_escape),
      returnRate: Number(row.return_rate_given_escape),
      meanReturnSteps: Number(row.mean_return_steps),
      p90Flips: Number(row.p90_flips),
    })) : [],
    transitionCount: Array.isArray(transitions) ? transitions.filter(isRecord).reduce((sum, row) => sum + Number(row.count), 0) : 0,
  };
}

function auditHeldoutSemantics(
  members: Record<string, Uint8Array>,
  manifest: Manifest,
  claim: JsonRecord,
  failures: JsonRecord[],
  errors: string[],
): HeldoutBundleMetadata | undefined {
  const profile = parseJson(members, "heldout_profile.json", errors);
  const source = parseJson(members, "source_registry.json", errors);
  const preregistration = parseJson(members, "preregistration.json", errors);
  const endpoints = parseJson(members, "tables/primary_endpoints.json", errors);
  const independent = parseJson(members, "audit/independent_verification.json", errors);
  const adjudication = parseJson(members, "audit/claim_adjudication.json", errors);
  const forbidden = parseJson(members, "audit/forbidden_claims.json", errors);
  const mutations = parseJsonl(members, "audit/mutation_results.jsonl", errors);
  const surface = parseCsv(members, "tables/byN_surface.csv", errors);
  const parents = parseCsv(members, "registry/parent_registry.csv", errors);
  const nulls = parseCsv(members, "registry/null_registry.csv", errors);
  const perturbations = parseCsv(members, "registry/perturbation_registry.csv", errors);
  if (
    !isRecord(profile)
    || !isRecord(source)
    || !isRecord(preregistration)
    || !isRecord(endpoints)
    || !isRecord(independent)
    || !isRecord(adjudication)
    || !isRecord(forbidden)
  ) return undefined;
  if (profile.profile !== manifest.profile) issue(errors, "HELDOUT_PROFILE_MISMATCH", "manifest and profile");
  if (!equalStringSet(profile.required_members, HELDOUT_REQUIRED_MEMBERS)) issue(errors, "HELDOUT_PROFILE_MEMBERS_INVALID", "required members");
  if (profile.interpolation_used_for_metrics !== false) issue(errors, "HELDOUT_INTERPOLATION_AS_OBSERVATION", "profile");
  if (source.doi !== "10.24432/C5RK5G") issue(errors, "HELDOUT_SOURCE_DOI_MISMATCH", String(source.doi));
  const sourceSha = "d1b9261c54132f04c374f762f1e5e512af19f95c95fd6bfa1e8ac7e927e3b0b8";
  if (source.authoritative_archive_sha256 !== sourceSha) issue(errors, "HELDOUT_SOURCE_HASH_MISMATCH", "authoritative archive");
  const preregSha = "eb3a886aa3bc344ccf715d0036d5054cfba107aa3eae017ba00c68852bb73bfc";
  if (profile.preregistration_manifest_sha256 !== preregSha) issue(errors, "HELDOUT_PREREGISTRATION_HASH_MISMATCH", "profile");
  if (preregistration.selection_commit !== "2ff2ddb1a4f656d3c672079a6e8821bf9c3858eb") issue(errors, "HELDOUT_SELECTION_COMMIT_MISMATCH", "preregistration");
  if (parents.length !== 12 || parents.some((row) => row.eligible.toLowerCase() !== "true")) issue(errors, "HELDOUT_PARENT_REGISTRY_INVALID", String(parents.length));
  if (nulls.length !== 12192) issue(errors, "HELDOUT_NULL_REGISTRY_COUNT_MISMATCH", String(nulls.length));
  if (nulls.some((row) => row.null_family !== "within_year_month_complete_day_permutation")) issue(errors, "HELDOUT_GLOBAL_NULL_POOL_FORBIDDEN", "null registry");
  if (perturbations.length !== 96) issue(errors, "HELDOUT_PERTURBATION_REGISTRY_INVALID", String(perturbations.length));
  const baseline = surface.filter((row) => row.condition === "baseline");
  const separated = baseline.filter((row) => row.SEP.toLowerCase() === "true").map((row) => Number(row.N));
  const recomputedTe: number | "NOT_OBSERVED" = separated.length ? Math.min(...separated) : "NOT_OBSERVED";
  if (endpoints.T_e !== recomputedTe) issue(errors, "HELDOUT_TE_MISMATCH", String(recomputedTe));
  if (recomputedTe === "NOT_OBSERVED" && Number(endpoints.S_e_contiguous) !== 0) issue(errors, "HELDOUT_SE_MISMATCH", String(endpoints.S_e_contiguous));
  if (Number(endpoints.winner_N_study_closure_minimum) !== 9) issue(errors, "HELDOUT_WINNER_MISMATCH", String(endpoints.winner_N_study_closure_minimum));
  if (independent.status !== "verified" || independent.disagreement_count !== 0) issue(errors, "HELDOUT_INDEPENDENT_VERIFICATION_FAILED", "receipt");
  if (mutations.length !== 25 || mutations.some((row) => row.rejected !== true)) issue(errors, "HELDOUT_MUTATION_SUITE_FAILED", String(mutations.length));
  if (adjudication.EXTERNALLY_VALIDATED !== false) issue(errors, "HELDOUT_EXTERNAL_VALIDATION_FORBIDDEN", "adjudication");
  const outcome = recomputedTe === "NOT_OBSERVED"
    ? "HELDOUT_TLD_STUDY_NEGATIVE_UNDER_FROZEN_GATES"
    : "HELDOUT_TLD_STUDY_POSITIVE_UNDER_FROZEN_GATES";
  if (adjudication.scientific_outcome !== outcome) issue(errors, "HELDOUT_ADJUDICATION_MISMATCH", outcome);
  if (outcome.includes("NEGATIVE") && claim.claim_level !== "COMPUTED_DYNAMICAL") issue(errors, "HELDOUT_NEGATIVE_CLAIM_ESCALATION", String(claim.claim_level));
  if (failures.length !== Number(endpoints.failure_count ?? 0)) issue(errors, "HELDOUT_FAILURE_COUNT_MISMATCH", String(failures.length));
  const atTe = typeof recomputedTe === "number" ? baseline.find((row) => Number(row.N) === recomputedTe) : undefined;
  return {
    doi: String(source.doi),
    title: String(source.title),
    profile: String(profile.profile),
    scientificOutcome: String(adjudication.scientific_outcome),
    preregistrationSha256: preregSha,
    sourceSha256: sourceSha,
    eligibleParentCount: Number(endpoints.eligible_parent_count),
    nullsPerParent: 127,
    T_e: recomputedTe,
    S_e: Number(endpoints.S_e_contiguous),
    winnerN: Number(endpoints.winner_N_study_closure_minimum),
    UI: atTe ? Number(atTe.UI) : null,
    NSS: atTe ? Number(atTe.NSS) : null,
    sepAny: separated.length > 0,
    specificity14: Boolean(endpoints.fourteen_specificity_passed),
    baselineStatus: "Monthly climatology + AR(1) completed; model beat climatology at 12/12 parents",
    verificationStatus: String(independent.status),
    mutationCount: Number(independent.mutation_count),
    mutationRejectionCount: Number(independent.mutation_rejection_count),
    failureCount: failures.length,
    tldDerivedStatus: String(adjudication.TLD_DERIVED_status),
    externallyValidated: false,
    forbiddenClaims: Array.isArray(forbidden.forbidden_claims) ? forbidden.forbidden_claims.map(String) : [],
  };
}

async function auditGeometrySemantics(
  members: Record<string, Uint8Array>,
  manifest: Manifest,
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
  if (
    manifest.statistics.point_count !== 4
    || !equalCounts(manifest.statistics.classification_counts, { NONCONFIRMATORY_CONDITION: 4 })
    || manifest.statistics.mean_UI !== null
    || manifest.statistics.mean_NSS !== null
    || manifest.statistics.mean_S_e !== null
  ) issue(errors, "STATISTICS_MISMATCH", "geometry pilot");
  if (manifest.statistics.failure_count !== failures.length) issue(errors, "FAILURE_COUNT_MISMATCH", "geometry failure ledger");
  const expectedSums = (await Promise.all(Object.entries(members)
    .filter(([name]) => name !== "manifest.json" && name !== "audit/SHA256SUMS.txt")
    .sort(([left], [right]) => compareCodePoints(left, right))
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
      studyRole: String(source.study_role ?? source.pilot_role),
      statisticalUnit: String(source.statistical_unit ?? "condition acquisition"),
      rawObservationRole: String(custody.content_role ?? "registered arrays"),
      coordinateContract: String(source.coordinate_contract ?? "registered source coordinates"),
      unitContract: String(source.unit_contract ?? "source units with provenance"),
      maskPolicy: String(source.mask_policy ?? "explicit mask"),
      nestedReplicates: String(source.nested_replicates ?? "not promoted"),
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

async function auditSemantics(
  members: Record<string, Uint8Array>,
  manifest: Manifest,
  errors: string[],
): Promise<{ specification?: JsonRecord; table?: FieldTable; tld?: TldBundleMetadata; heldout?: HeldoutBundleMetadata; geometry?: GeometryBundleMetadata }> {
  const specification = parseJson(members, "run_spec.json", errors);
  const ontology = parseJson(members, "ontology.json", errors);
  const claim = parseJson(members, "claim_boundary.json", errors);
  const table = parseJson(members, "tables/field_points.json", errors);
  const parent = parseJson(members, "registry/parent_registry.json", errors);
  const nulls = parseJson(members, "registry/null_registry.json", errors);
  const failures = parseJsonl(members, "audit/failure_ledger.jsonl", errors);
  const receipts = parseJsonl(members, "provenance/verification_receipts.jsonl", errors);
  const transformations = parseJsonl(members, "provenance/transformations.jsonl", errors);
  if (!isRecord(specification) || !isRecord(ontology) || !isRecord(claim) || !isRecord(table) || !isRecord(parent) || !Array.isArray(nulls)) return {};
  schemaErrors(errors, "RUN_SPEC_INVALID", validators.runSpec, specification);
  schemaErrors(errors, "CLAIM_SCHEMA_INVALID", validators.claim, claim);
  schemaErrors(errors, "FIELD_TABLE_SCHEMA_INVALID", validators.table, table);
  for (const failure of failures) schemaErrors(errors, "FAILURE_SCHEMA_INVALID", validators.failure, failure);
  if (ontology.schema_version !== "1.0.0") issue(errors, "SCHEMA_VERSION_UNSUPPORTED", "ontology");
  const historicalTldProfile = typeof manifest.profile === "string" && manifest.profile.startsWith("tld-i-");
  const heldoutTldProfile = typeof manifest.profile === "string" && manifest.profile.startsWith("tld-heldout-");
  const tldProfile = historicalTldProfile || heldoutTldProfile;

  const specText = new TextDecoder().decode(members["run_spec.json"]);
  let canonicalSpecification = "";
  try {
    canonicalSpecification = canonicalizeRawJson(specText);
    if (await sha256(canonicalSpecification) !== manifest.specification_sha256) issue(errors, "SPECIFICATION_HASH_MISMATCH", "manifest");
  } catch (error) {
    issue(errors, "RUN_SPEC_INVALID", error instanceof Error ? error.message : "cannot canonicalize specification");
  }
  if (claim.claim_level !== manifest.claim_level) issue(errors, "CLAIM_LEVEL_MISMATCH", "claim boundary and manifest");
  const claimLevels: Record<string, number> = { ILLUSTRATIVE_ANALYTIC: 0, COMPUTED_DYNAMICAL: 1, TLD_DERIVED: 2, EXTERNALLY_VALIDATED: 3 };
  const outputLevel = claimLevels[manifest.claim_level];
  const requestedLevel = claimLevels[String(specification.claim_level)];
  if (outputLevel === undefined) issue(errors, "CLAIM_LEVEL_INVALID", String(manifest.claim_level));
  else {
    if (requestedLevel === undefined || outputLevel > requestedLevel) issue(errors, "CLAIM_LEVEL_EXCEEDS_REQUEST", manifest.claim_level);
    if (specification.engine === "analytic" && outputLevel !== 0) issue(errors, "CLAIM_LEVEL_ENGINE_CONFLICT", "analytic engine");
    if (specification.engine === "local_brot" && outputLevel > 2) issue(errors, "CLAIM_LEVEL_ENGINE_CONFLICT", "local engine");
    if (specification.engine === "tld" && !tldProfile) issue(errors, "TLD_PROFILE_MISSING", "tld engine requires a TLD profile");
    if (specification.engine === "tld" && tldProfile && manifest.profile !== "tld-i-modern-v21" && outputLevel > 1) issue(errors, "CLAIM_LEVEL_ENGINE_CONFLICT", "historical TLD lane");
    const authority = claimLevels[String(parent.claim_authority)];
    if (authority !== undefined && outputLevel > authority) issue(errors, "CLAIM_LEVEL_DOMAIN_CONFLICT", manifest.claim_level);
  }
  if (specification.engine === "analytic" && JSON.stringify(claim).toLowerCase().includes("tld evidence")) {
    issue(errors, "ANALYTIC_TLD_EVIDENCE_FORBIDDEN", "claim boundary");
  }
  const verifiedReceipt = receipts.some((row) => row.run_id === manifest.run_id && row.status === "verified" && Boolean(row.verifier));
  if ((claim.independent_verifier_status === "independently_verified" || manifest.claim_level === "EXTERNALLY_VALIDATED") && !verifiedReceipt) {
    issue(errors, "VERIFIER_RECEIPT_MISSING", "independent status requires a matching receipt");
  }

  const grid = isRecord(specification.grid) ? specification.grid : {};
  const width = grid.width;
  const height = grid.height;
  const points = table.points;
  if (!Number.isInteger(width) || !Number.isInteger(height)) {
    issue(errors, "GRID_DIMENSION_INVALID", "width and height must be integers");
    return { specification };
  }
  if (table.width !== width || table.height !== height) issue(errors, "GRID_DIMENSION_MISMATCH", "run specification and table");
  if (!Array.isArray(points)) {
    issue(errors, "FIELD_POINTS_INVALID", "points must be an array");
    return { specification };
  }
  const numericFields = ["x", "y", "S_e", "UI", "NSS", "SEP", "rms_to_parent"];
  const classifications: Record<string, number> = {};
  const seen = new Set<string>();
  const failureIds = new Set(failures.map((failure) => failure.failure_id));
  if (points.length !== Number(width) * Number(height)) issue(errors, "GRID_POINT_COUNT_MISMATCH", `expected ${Number(width) * Number(height)}, got ${points.length}`);
  points.forEach((point, position) => {
    if (!isRecord(point)) {
      issue(errors, "FIELD_POINT_INVALID", String(position));
      return;
    }
    if (historicalTldProfile) {
      if (!["x", "y"].every((field) => finiteNumber(point[field]))) issue(errors, "FIELD_METRIC_NONFINITE", String(position));
      if (["T_e", "S_e", "UI", "NSS", "SEP"].some((field) => point[field] != null)) issue(errors, "TLD_UNCOMPUTED_ENDPOINT_POPULATED", String(position));
      if (point.observed === true && point.failure_id != null) issue(errors, "TLD_OBSERVED_FAILURE_CONFLICT", String(position));
      if (point.observed === false && (point.classification !== "UNRESOLVED" || point.failure_id == null)) issue(errors, "TLD_MISSING_CELL_NOT_PRESERVED", String(position));
    } else if (numericFields.some((field) => !finiteNumber(point[field]))) issue(errors, "FIELD_METRIC_NONFINITE", String(position));
    if (!Number.isInteger(point.grid_x) || !Number.isInteger(point.grid_y) || Number(point.grid_x) < 0 || Number(point.grid_y) < 0 || Number(point.grid_x) >= Number(width) || Number(point.grid_y) >= Number(height)) {
      issue(errors, "FIELD_COORDINATE_INVALID", String(position));
    } else {
      const cell = `${point.grid_x}:${point.grid_y}`;
      if (seen.has(cell)) issue(errors, "FIELD_COORDINATE_DUPLICATE", String(position));
      seen.add(cell);
    }
    if (point.index !== position) issue(errors, "FIELD_INDEX_MISMATCH", String(position));
    if (typeof point.classification === "string") classifications[point.classification] = (classifications[point.classification] ?? 0) + 1;
    if (point.failure_id != null && !failureIds.has(point.failure_id)) issue(errors, "FAILURE_REFERENCE_MISSING", String(point.failure_id));
  });
  const statistics = manifest.statistics;
  if (statistics.point_count !== points.length) issue(errors, "STATISTICS_MISMATCH", "point_count");
  if (!equalCounts(statistics.classification_counts, classifications)) issue(errors, "STATISTICS_MISMATCH", "classification_counts");
  for (const [field, statisticsKey] of [["UI", "mean_UI"], ["NSS", "mean_NSS"], ["S_e", "mean_S_e"]] as const) {
    const values = points.map((point) => isRecord(point) ? point[field] : undefined);
    if (values.every(finiteNumber)) {
      const expectedMean = Number((values.reduce((sum, value) => sum + value, 0) / Math.max(values.length, 1)).toFixed(8));
      const reportedMean = statistics[statisticsKey];
      if (!finiteNumber(reportedMean) || Math.abs(reportedMean - expectedMean) > 1.1e-8) issue(errors, "STATISTICS_MISMATCH", statisticsKey);
    }
  }
  if (historicalTldProfile && (statistics.mean_UI != null || statistics.mean_NSS != null || statistics.mean_S_e != null)) issue(errors, "TLD_UNCOMPUTED_STATISTIC_POPULATED", "manifest statistics");
  if (statistics.failure_count !== failures.length) issue(errors, "FAILURE_COUNT_MISMATCH", "failure ledger");
  const nullPolicy = isRecord(specification.null_policy) ? specification.null_policy : {};
  if (nulls.length !== nullPolicy.count) issue(errors, "NULL_REGISTRY_COUNT_MISMATCH", String(nulls.length));
  if (transformations.length === 0) issue(errors, "PROVENANCE_TRANSFORMATION_MISSING", "no transformation");
  else {
    if (transformations[0].specification_sha256 !== manifest.specification_sha256) issue(errors, "PROVENANCE_HASH_MISMATCH", "transformation");
    if (transformations[0].transformation_id !== manifest.kernel_id) issue(errors, "PROVENANCE_KERNEL_MISMATCH", "transformation");
    if (transformations[0].seed !== specification.seed) issue(errors, "PROVENANCE_SEED_MISMATCH", "transformation");
  }
  const tld = historicalTldProfile
    ? auditTldSemantics(members, manifest, claim, ontology, points, failures, errors)
    : undefined;
  const heldout = heldoutTldProfile
    ? auditHeldoutSemantics(members, manifest, claim, failures, errors)
    : undefined;
  if (canonicalSpecification) {
    const domainSha = (specification.engine === "local_brot" || specification.engine === "tld") && typeof parent.domain_sha256 === "string" ? parent.domain_sha256 : null;
    const identity = `{"domain_sha256":${JSON.stringify(domainSha)},"kernel_id":${JSON.stringify(manifest.kernel_id)},"specification":${canonicalSpecification.trimEnd()}}\n`;
    const expectedRunId = `run-${(await sha256(identity)).slice(0, 16)}`;
    if (manifest.run_id !== expectedRunId) issue(errors, "RUN_ID_MISMATCH", expectedRunId);
  }
  const expectedSums = (await Promise.all(Object.entries(members)
    .filter(([name]) => name !== "manifest.json" && name !== "audit/SHA256SUMS.txt")
    .sort(([left], [right]) => compareCodePoints(left, right))
    .map(async ([name, payload]) => `${await sha256(payload)}  ${name}\n`))).join("");
  if (new TextDecoder().decode(members["audit/SHA256SUMS.txt"]) !== expectedSums) issue(errors, "SHA256SUMS_MISMATCH", "audit/SHA256SUMS.txt");
  return { specification, table: table as unknown as FieldTable, tld, heldout };
}

export async function auditTbx(bytes: Uint8Array): Promise<TbxAuditResult> {
  const errors: string[] = [];
  preflightArchive(bytes, errors);
  if (errors.length) return { valid: false, issueCodes: errors.map((error) => error.split(":", 1)[0]), errors, checkedFiles: 0 };
  let allMembers: Record<string, Uint8Array>;
  try {
    allMembers = unzipSync(bytes);
  } catch (error) {
    issue(errors, "ARCHIVE_INVALID", error instanceof Error ? error.message : "could not decompress archive");
    return { valid: false, issueCodes: ["ARCHIVE_INVALID"], errors, checkedFiles: 0 };
  }
  const members = Object.fromEntries(Object.entries(allMembers).filter(([name]) => !name.endsWith("/")));
  if (!members["manifest.json"]) {
    issue(errors, "MANIFEST_MISSING", "manifest.json");
    return { valid: false, issueCodes: ["MANIFEST_MISSING"], errors, checkedFiles: 0 };
  }
  const parsedManifest = parseJson(members, "manifest.json", errors);
  if (!isRecord(parsedManifest)) return { valid: false, issueCodes: errors.map((error) => error.split(":", 1)[0]), errors, checkedFiles: 0 };
  const manifestText = new TextDecoder().decode(members["manifest.json"]);
  try {
    if (manifestText !== canonicalizeRawJson(manifestText, true)) issue(errors, "MANIFEST_NONCANONICAL", "manifest bytes are not canonical JSON");
  } catch (error) {
    issue(errors, "MANIFEST_NONCANONICAL", error instanceof Error ? error.message : "manifest cannot be canonicalized");
  }
  schemaErrors(errors, "MANIFEST_SCHEMA_INVALID", validators.manifest, parsedManifest);
  const manifest = parsedManifest as Manifest;
  const entries = Array.isArray(manifest.files) ? manifest.files : [];
  let checkedFiles = 0;
  const listed = new Set<string>();
  for (const entry of entries) {
    if (!isRecord(entry) || typeof entry.path !== "string" || typeof entry.sha256 !== "string" || typeof entry.bytes !== "number") continue;
    const name = entry.path;
    if (listed.has(name)) issue(errors, "MANIFEST_DUPLICATE_ENTRY", name);
    listed.add(name);
    if (!canonicalMemberPath(name)) issue(errors, "MANIFEST_PATH_INVALID", name);
    const payload = members[name];
    if (!payload) {
      issue(errors, "MANIFEST_MEMBER_MISSING", name);
      continue;
    }
    checkedFiles += 1;
    if (payload.byteLength !== entry.bytes) issue(errors, "MANIFEST_SIZE_MISMATCH", name);
    if (await sha256(payload) !== entry.sha256) issue(errors, "MANIFEST_HASH_MISMATCH", name);
  }
  const paths = entries.filter((entry): entry is ManifestEntry => isRecord(entry) && typeof entry.path === "string").map((entry) => entry.path);
  if (paths.some((path, index) => index > 0 && compareCodePoints(paths[index - 1], path) > 0)) issue(errors, "MANIFEST_ORDER_INVALID", "file entries must be sorted");
  const extras = Object.keys(members).filter((name) => name !== "manifest.json" && !listed.has(name)).sort();
  if (extras.length) issue(errors, "MANIFEST_UNLISTED_MEMBER", extras.join(", "));
  const geometryProfile = typeof manifest.profile === "string" && manifest.profile.startsWith("geometry-");
  const required = new Set(geometryProfile ? GEOMETRY_REQUIRED_MEMBERS : REQUIRED_MEMBERS);
  if (!geometryProfile && typeof manifest.profile === "string" && manifest.profile.startsWith("tld-i-")) {
    TLD_REQUIRED_MEMBERS.forEach((name) => required.add(name));
  }
  if (!geometryProfile && typeof manifest.profile === "string" && manifest.profile.startsWith("tld-heldout-")) {
    HELDOUT_REQUIRED_MEMBERS.forEach((name) => required.add(name));
  }
  const requiredMissing = [...required].filter((name) => !listed.has(name)).sort();
  if (requiredMissing.length) issue(errors, "REQUIRED_MEMBER_MISSING", requiredMissing.join(", "));
  let semantics: { specification?: JsonRecord; table?: FieldTable; tld?: TldBundleMetadata; heldout?: HeldoutBundleMetadata; geometry?: GeometryBundleMetadata } = {};
  if (!errors.length) {
    if (geometryProfile) {
      const geometryAudit = await import("./geometryTbxAudit");
      semantics = await geometryAudit.auditGeometrySemantics(members, manifest, errors);
    } else {
      semantics = await auditSemantics(members, manifest, errors);
    }
  }
  const issueCodes = [...new Set(errors.map((error) => error.split(":", 1)[0]))];
  return { valid: errors.length === 0, issueCodes, errors, checkedFiles, manifest, ...semantics };
}
