import { strToU8, zipSync } from "fflate";
import { auditTbx, canonicalJson, compareCodePoints } from "./tbxAudit";
import type { Engine, FieldPoint, FieldTable, GenerateRequest } from "./types";

function jsonBytes(value: unknown): Uint8Array {
  return strToU8(canonicalJson(value, true));
}

function jsonlBytes(rows: unknown[]): Uint8Array {
  return strToU8(rows.map((row) => canonicalJson(row)).join(""));
}

async function sha256(payload: Uint8Array | string): Promise<string> {
  const bytes = typeof payload === "string" ? strToU8(payload) : payload;
  const copy = new Uint8Array(bytes.byteLength);
  copy.set(bytes);
  const digest = await crypto.subtle.digest("SHA-256", copy.buffer);
  return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, "0")).join("");
}

async function contentHash(value: unknown): Promise<string> {
  return sha256(canonicalJson(value));
}

function statistics(points: FieldPoint[]) {
  const counts: Record<string, number> = {};
  for (const point of points) counts[point.classification] = (counts[point.classification] ?? 0) + 1;
  const mean = (field: "UI" | "NSS" | "S_e") => {
    const values = points.map((point) => point[field]).filter((value): value is number => value != null);
    return values.length ? Number((values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(8)) : null;
  };
  return {
    point_count: points.length,
    classification_counts: Object.fromEntries(Object.entries(counts).sort(([left], [right]) => compareCodePoints(left, right))),
    mean_UI: mean("UI"),
    mean_NSS: mean("NSS"),
    mean_S_e: mean("S_e"),
    failure_count: 0,
  };
}

export async function exportBrowserBundle(table: FieldTable, request: GenerateRequest, engine: Engine) {
  const claimLevel = engine === "analytic" ? "ILLUSTRATIVE_ANALYTIC" : "COMPUTED_DYNAMICAL";
  const kernelId = `browser.${engine}.v1`;
  const nullCount = engine === "analytic" ? 0 : 12;
  const specification = {
    schema_version: "1.0.0",
    engine,
    seed: request.seed,
    domain_id: engine === "analytic" ? "analytic-browser-preview" : "synthetic-ring-14",
    claim_level: claimLevel,
    grid: { width: table.width, height: table.height },
    parameters: {
      power: request.power,
      max_iterations: request.maxIterations,
      recovery_steps: request.recoverySteps,
    },
    classification_rules: {
      separation_threshold: 0.08,
      nss_threshold: 1,
      survival_threshold: 0.6,
      recovery_threshold: 0.78,
      escape_threshold: 0.46,
    },
    null_policy: engine === "analytic"
      ? { kind: "none", count: 0, seed: request.seed }
      : { kind: "preserve_multiset_shuffle", count: nullCount, seed: request.seed },
  };
  const specificationSha256 = await contentHash(specification);
  const runId = `run-${(await contentHash({ specification, kernel_id: kernelId, domain_sha256: null })).slice(0, 16)}`;
  const tableForBundle = {
    schema_version: "1.0.0",
    width: table.width,
    height: table.height,
    points: table.points,
  };
  const summary = statistics(table.points);
  const winnerCounts: Record<string, number> = {};
  for (const point of table.points) {
    if (point.winner_N != null) winnerCounts[String(point.winner_N)] = (winnerCounts[String(point.winner_N)] ?? 0) + 1;
  }
  const nullRegistry = Array.from({ length: nullCount }, (_, index) => ({
    null_id: `browser-null-${String(index).padStart(2, "0")}`,
    policy: "preserve_multiset_shuffle",
    seed: request.seed + index,
  }));
  const files: Record<string, Uint8Array> = {
    "run_spec.json": jsonBytes(specification),
    "ontology.json": jsonBytes({
      schema_version: "1.0.0",
      terms: { omega: "ordered ladder state", T_e: "first observed/null separation", S_e: "persistence after emergence", winner_N: "closure-mode label" },
      non_equivalences: ["closure != emergence", "survival != closure", "interpolation != observation"],
    }),
    "claim_boundary.json": jsonBytes({
      claim_level: claimLevel,
      permitted_interpretations: ["browser-side reproducible preview"],
      excluded_interpretations: ["external validation", "causal authority", "scientific use without CPU regeneration"],
      experimental_tags: ["browser_preview"],
      independent_verifier_status: "not_supplied",
    }),
    "visual_encoding.json": jsonBytes({
      position: { x: engine === "analytic" ? "complex_real" : "order_mutation_strength", y: engine === "analytic" ? "complex_imaginary" : "anchoring_alpha", z: "S_e" },
      color: "selected_by_user",
      interpolation: { method: "bilinear", used_for_metrics: false },
    }),
    "scene_recipe.json": jsonBytes({ viewer: "TORUS Field Studio", raw_samples_visible: true }),
    "provenance/sources.jsonl": jsonlBytes([{ source_id: specification.domain_id, kind: "browser_preview", engine }]),
    "provenance/transformations.jsonl": jsonlBytes([{
      transformation_id: kernelId,
      software_version: "0.2.1",
      seed: request.seed,
      specification_sha256: specificationSha256,
    }]),
    "provenance/verification_receipts.jsonl": new Uint8Array(),
    "registry/parent_registry.json": jsonBytes({
      parent_id: table.points[0]?.parent_id ?? "none",
      kind: engine === "analytic" ? "declared_initial_state" : "browser_synthetic_fixture",
      claim_authority: claimLevel,
    }),
    "registry/null_registry.json": jsonBytes(nullRegistry),
    "tables/field_points.json": strToU8(canonicalJson(tableForBundle)),
    "tables/metrics_by_N.json": jsonBytes({ winner_N_counts: winnerCounts, summary }),
    "audit/audit.json": jsonBytes({
      status: "browser_preview_unverified",
      kernel_authority: "deterministic_browser_preview",
      failure_preservation: "complete",
      classification_precedes_rendering: true,
    }),
    "audit/failure_ledger.jsonl": new Uint8Array(),
  };
  const entries = await Promise.all(Object.entries(files).map(async ([path, payload]) => ({ path, sha256: await sha256(payload), bytes: payload.byteLength })));
  files["audit/SHA256SUMS.txt"] = strToU8(entries
    .sort((left, right) => compareCodePoints(left.path, right.path))
    .map((entry) => `${entry.sha256}  ${entry.path}\n`).join(""));
  entries.push({
    path: "audit/SHA256SUMS.txt",
    sha256: await sha256(files["audit/SHA256SUMS.txt"]),
    bytes: files["audit/SHA256SUMS.txt"].byteLength,
  });
  files["manifest.json"] = jsonBytes({
    tbx_version: "1.0.0",
    run_id: runId,
    claim_level: claimLevel,
    kernel_id: kernelId,
    specification_sha256: specificationSha256,
    statistics: summary,
    files: entries.sort((left, right) => compareCodePoints(left.path, right.path)),
  });
  const blob = new Blob([zipSync(files, { level: 9 }) as BlobPart], { type: "application/zip" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${runId}.tbx.zip`;
  link.click();
  URL.revokeObjectURL(link.href);
}

export async function importBundle(file: File): Promise<FieldTable> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  const audit = await auditTbx(bytes);
  if (!audit.valid || !audit.table || !audit.manifest || !audit.specification) {
    const summary = audit.errors.slice(0, 3).join("; ");
    throw new Error(`TBX audit rejected [${audit.issueCodes.join(", ")}]: ${summary}`);
  }
  const engine = audit.specification.engine;
  return {
    ...audit.table,
    source: "tbx_import",
    runId: audit.manifest.run_id,
    claimLevel: audit.manifest.claim_level,
    engine: engine === "analytic" || engine === "local_brot" || engine === "tld" ? engine : undefined,
    auditCheckedFiles: audit.checkedFiles,
    tld: audit.tld,
    heldout: audit.heldout,
  };
}
