import Ajv2020, { type ValidateFunction } from "ajv/dist/2020";
import { unzipSync } from "fflate";
import claimBoundarySchema from "../../../schemas/claim-boundary/v1.schema.json";
import failureSchema from "../../../schemas/evidence/failure-v1.schema.json";
import fieldTableSchema from "../../../schemas/field-table/v1.schema.json";
import fieldPointSchema from "../../../schemas/local-brot/v1.schema.json";
import runSpecSchema from "../../../schemas/run-spec/v1.schema.json";
import manifestSchema from "../../../schemas/tbx/v1.schema.json";
import type { TORUSBundleExchangeManifest } from "./generated/manifest";
import type { FieldTable } from "./types";

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

const ajv = new Ajv2020({ allErrors: true, strict: false });
for (const schema of [manifestSchema, runSpecSchema, claimBoundarySchema, fieldPointSchema, fieldTableSchema, failureSchema]) {
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

async function auditSemantics(
  members: Record<string, Uint8Array>,
  manifest: Manifest,
  errors: string[],
): Promise<{ specification?: JsonRecord; table?: FieldTable }> {
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
    const authority = claimLevels[String(parent.claim_authority)];
    if (authority !== undefined && outputLevel > authority) issue(errors, "CLAIM_LEVEL_DOMAIN_CONFLICT", manifest.claim_level);
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
    if (numericFields.some((field) => !finiteNumber(point[field]))) issue(errors, "FIELD_METRIC_NONFINITE", String(position));
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
  if (statistics.failure_count !== failures.length) issue(errors, "FAILURE_COUNT_MISMATCH", "failure ledger");
  const nullPolicy = isRecord(specification.null_policy) ? specification.null_policy : {};
  if (nulls.length !== nullPolicy.count) issue(errors, "NULL_REGISTRY_COUNT_MISMATCH", String(nulls.length));
  if (transformations.length === 0) issue(errors, "PROVENANCE_TRANSFORMATION_MISSING", "no transformation");
  else {
    if (transformations[0].specification_sha256 !== manifest.specification_sha256) issue(errors, "PROVENANCE_HASH_MISMATCH", "transformation");
    if (transformations[0].transformation_id !== manifest.kernel_id) issue(errors, "PROVENANCE_KERNEL_MISMATCH", "transformation");
  }
  if (canonicalSpecification) {
    const domainSha = specification.engine === "local_brot" && typeof parent.domain_sha256 === "string" ? parent.domain_sha256 : null;
    const identity = `{"domain_sha256":${JSON.stringify(domainSha)},"kernel_id":${JSON.stringify(manifest.kernel_id)},"specification":${canonicalSpecification.trimEnd()}}\n`;
    const expectedRunId = `run-${(await sha256(identity)).slice(0, 16)}`;
    if (manifest.run_id !== expectedRunId) issue(errors, "RUN_ID_MISMATCH", expectedRunId);
  }
  const expectedSums = (await Promise.all(Object.entries(members)
    .filter(([name]) => name !== "manifest.json" && name !== "audit/SHA256SUMS.txt")
    .sort(([left], [right]) => compareCodePoints(left, right))
    .map(async ([name, payload]) => `${await sha256(payload)}  ${name}\n`))).join("");
  if (new TextDecoder().decode(members["audit/SHA256SUMS.txt"]) !== expectedSums) issue(errors, "SHA256SUMS_MISMATCH", "audit/SHA256SUMS.txt");
  return { specification, table: table as unknown as FieldTable };
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
  const requiredMissing = [...REQUIRED_MEMBERS].filter((name) => !listed.has(name)).sort();
  if (requiredMissing.length) issue(errors, "REQUIRED_MEMBER_MISSING", requiredMissing.join(", "));
  let semantics: { specification?: JsonRecord; table?: FieldTable } = {};
  if (!errors.length) semantics = await auditSemantics(members, manifest, errors);
  const issueCodes = [...new Set(errors.map((error) => error.split(":", 1)[0]))];
  return { valid: errors.length === 0, issueCodes, errors, checkedFiles, manifest, ...semantics };
}
