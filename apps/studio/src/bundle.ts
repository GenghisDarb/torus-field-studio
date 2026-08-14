import { strToU8, unzipSync, zipSync } from "fflate";
import type { Engine, FieldTable, GenerateRequest } from "./types";

function jsonBytes(value: unknown): Uint8Array {
  return strToU8(`${JSON.stringify(value, null, 2)}\n`);
}

async function sha256(payload: Uint8Array): Promise<string> {
  const copy = new Uint8Array(payload.byteLength);
  copy.set(payload);
  const digest = await crypto.subtle.digest("SHA-256", copy.buffer);
  return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, "0")).join("");
}

export async function exportBrowserBundle(table: FieldTable, request: GenerateRequest, engine: Engine) {
  const claimLevel = engine === "analytic" ? "ILLUSTRATIVE_ANALYTIC" : "COMPUTED_DYNAMICAL";
  const files: Record<string, Uint8Array> = {
    "run_spec.json": jsonBytes({
      schema_version: "1.0.0",
      engine,
      seed: request.seed,
      domain_id: engine === "analytic" ? "analytic-browser-preview" : "synthetic-ring-14",
      claim_level: claimLevel,
      grid: { width: table.width, height: table.height },
      parameters: { power: request.power, max_iterations: request.maxIterations, recovery_steps: request.recoverySteps },
      classification_rules: {},
      null_policy: engine === "analytic" ? { kind: "none", count: 0 } : { kind: "browser_preview", count: 12, seed: request.seed },
    }),
    "ontology.json": jsonBytes({
      terms: { omega: "ordered ladder state", T_e: "first observed/null separation", S_e: "persistence after emergence", winner_N: "closure-mode label" },
      non_equivalences: ["closure != emergence", "survival != closure", "interpolation != observation"],
    }),
    "claim_boundary.json": jsonBytes({
      claim_level: claimLevel,
      permitted_interpretations: ["browser-side reproducible preview"],
      excluded_interpretations: ["external validation", "causal authority", "scientific use without CPU regeneration"],
      independent_verifier_status: "not_supplied",
    }),
    "visual_encoding.json": jsonBytes({
      position: { x: engine === "analytic" ? "complex_real" : "order_mutation_strength", y: engine === "analytic" ? "complex_imaginary" : "anchoring_alpha", z: "S_e" },
      color: "selected_by_user",
      interpolation: { method: "bilinear", used_for_metrics: false },
    }),
    "scene_recipe.json": jsonBytes({ viewer: "TORUS Field Studio", raw_samples_visible: true }),
    "provenance/sources.jsonl": strToU8(`${JSON.stringify({ kind: "browser_preview", engine })}\n`),
    "provenance/transformations.jsonl": strToU8(`${JSON.stringify({ transformation_id: `browser.${engine}.v1`, seed: request.seed })}\n`),
    "provenance/verification_receipts.jsonl": new Uint8Array(),
    "registry/parent_registry.json": jsonBytes({ parent_id: table.points[0]?.parent_id ?? "none" }),
    "registry/null_registry.json": jsonBytes([]),
    "tables/field_points.json": jsonBytes(table),
    "tables/metrics_by_N.json": jsonBytes({ source: "browser_preview" }),
    "audit/audit.json": jsonBytes({ status: "browser_preview_unverified", classification_precedes_rendering: true }),
    "audit/failure_ledger.jsonl": new Uint8Array(),
  };
  const entries = await Promise.all(Object.entries(files).map(async ([path, payload]) => ({ path, sha256: await sha256(payload), bytes: payload.byteLength })));
  const sums = entries.map((entry) => `${entry.sha256}  ${entry.path}\n`).join("");
  files["audit/SHA256SUMS.txt"] = strToU8(sums);
  entries.push({ path: "audit/SHA256SUMS.txt", sha256: await sha256(files["audit/SHA256SUMS.txt"]), bytes: files["audit/SHA256SUMS.txt"].byteLength });
  const runId = `browser-${(await sha256(files["tables/field_points.json"])).slice(0, 16)}`;
  files["manifest.json"] = jsonBytes({ tbx_version: "1.0.0", run_id: runId, claim_level: claimLevel, kernel_id: `browser.${engine}.v1`, files: entries.sort((a, b) => a.path.localeCompare(b.path)) });
  const blob = new Blob([zipSync(files, { level: 9 }) as BlobPart], { type: "application/zip" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${runId}.tbx.zip`;
  link.click();
  URL.revokeObjectURL(link.href);
}

export async function importBundle(file: File): Promise<FieldTable> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  if (file.name.endsWith(".json")) {
    return { ...(JSON.parse(new TextDecoder().decode(bytes)) as FieldTable), source: "tbx_import" };
  }
  const members = unzipSync(bytes);
  const tableBytes = members["tables/field_points.json"];
  if (!tableBytes) throw new Error("This archive has no tables/field_points.json member.");
  const table = JSON.parse(new TextDecoder().decode(tableBytes)) as FieldTable;
  const manifestBytes = members["manifest.json"];
  const manifest = manifestBytes ? JSON.parse(new TextDecoder().decode(manifestBytes)) : {};
  const specBytes = members["run_spec.json"];
  const specification = specBytes ? JSON.parse(new TextDecoder().decode(specBytes)) : {};
  return { ...table, source: "tbx_import", runId: manifest.run_id, claimLevel: manifest.claim_level, engine: specification.engine };
}
