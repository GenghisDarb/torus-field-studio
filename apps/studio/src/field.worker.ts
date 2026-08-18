/// <reference lib="webworker" />

import type { FieldPoint, FieldTable, GenerateRequest, TracePoint } from "./types";

const worker = self as DedicatedWorkerGlobalScope;

function clamp(value: number, lower = 0, upper = 1): number {
  return Math.max(lower, Math.min(upper, value));
}

function lerp(lower: number, upper: number, index: number, count: number): number {
  return count <= 1 ? lower : lower + ((upper - lower) * index) / (count - 1);
}

function mul(ar: number, ai: number, br: number, bi: number): [number, number] {
  return [ar * br - ai * bi, ar * bi + ai * br];
}

function integerPower(real: number, imaginary: number, power: number): [number, number] {
  let outReal = 1;
  let outImaginary = 0;
  let baseReal = real;
  let baseImaginary = imaginary;
  let exponent = power;
  while (exponent > 0) {
    if (exponent % 2 === 1) [outReal, outImaginary] = mul(outReal, outImaginary, baseReal, baseImaginary);
    [baseReal, baseImaginary] = mul(baseReal, baseImaginary, baseReal, baseImaginary);
    exponent = Math.floor(exponent / 2);
  }
  return [outReal, outImaginary];
}

function analyticPoint(index: number, gridX: number, gridY: number, request: GenerateRequest): FieldPoint {
  const x = lerp(-1.35, 1.35, gridX, request.width);
  const y = lerp(1.05, -1.05, gridY, request.height);
  let zr = 0;
  let zi = 0;
  let escapedAt: number | null = null;
  const trace: TracePoint[] = [];
  for (let iteration = 0; iteration < request.maxIterations; iteration += 1) {
    const [pr, pi] = integerPower(zr, zi, request.power);
    zr = pr + x;
    zi = pi + y;
    const magnitude = Math.hypot(zr, zi);
    if (iteration < 12) {
      trace.push({ step: iteration, stage: "orbit", magnitude: Number.isFinite(magnitude) ? magnitude : 2, coherence: clamp(1 - magnitude / 2) });
    }
    if (!Number.isFinite(magnitude) || magnitude > 2) {
      escapedAt = iteration + 1;
      break;
    }
  }
  const bounded = escapedAt === null;
  const iterations = escapedAt ?? request.maxIterations;
  const survival = iterations / request.maxIterations;
  return {
    index,
    grid_x: gridX,
    grid_y: gridY,
    x,
    y,
    classification: bounded ? "BOUNDED" : "ESCAPED",
    eligible: true,
    emerged: false,
    separated_from_null: false,
    closed: bounded,
    survived: bounded,
    escaped_from_reference: !bounded,
    recovered: null,
    winner_N: null,
    T_e: null,
    S_e: survival,
    UI: survival,
    NSS: 0,
    SEP: 0,
    rms_to_parent: 0,
    iterations,
    parent_id: "analytic-origin-z0",
    null_policy_id: "none",
    trace,
  };
}

function noise(x: number, y: number, seed: number): number {
  const value = Math.sin(x * 127.1 + y * 311.7 + seed * 0.013) * 43758.5453123;
  return value - Math.floor(value);
}

function localPoint(index: number, gridX: number, gridY: number, request: GenerateRequest): FieldPoint {
  const mutation = lerp(0, 1, gridX, request.width);
  const anchoring = lerp(1, 0, gridY, request.height);
  const variance = (noise(gridX, gridY, request.seed) - 0.5) * 0.07 * mutation;
  const initialSimilarity = clamp(1 - mutation * (0.78 + variance));
  const escaped = initialSimilarity < 0.46;
  const nullMean = 0.34 + 0.025 * Math.sin(gridX * 0.22);
  const nullStd = 0.075;
  const trace: TracePoint[] = [];
  let emergence: number | null = null;
  let recoveryStep: number | null = null;
  let separatedSteps = 0;
  let consideredSteps = 0;
  let finalCoherence = 0;
  let finalSimilarity = initialSimilarity;
  for (let step = 0; step <= request.recoverySteps; step += 1) {
    const healing = 1 - Math.exp(-anchoring * step * 0.42);
    finalSimilarity = clamp(initialSimilarity + (1 - initialSimilarity) * healing);
    const ring = Math.sin(step * 1.7 + mutation * 5) * 0.055 * (1 - anchoring) * Math.exp(-step * 0.2);
    finalCoherence = clamp(0.18 + 0.7 * finalSimilarity + ring);
    const sep = finalCoherence - nullMean;
    const nss = sep / nullStd;
    const separated = sep >= 0.08 && nss >= 1;
    if (separated && emergence === null) emergence = step;
    if (emergence !== null) {
      consideredSteps += 1;
      if (separated) separatedSteps += 1;
    }
    if (escaped && recoveryStep === null && finalSimilarity >= 0.78) recoveryStep = step;
    trace.push({
      step,
      stage: recoveryStep === step ? "healing" : step === 0 ? "perturbation" : "recovery",
      coherence: finalCoherence,
      null_mean: nullMean,
      similarity: finalSimilarity,
    });
  }
  const sep = finalCoherence - nullMean;
  const nss = sep / nullStd;
  const survival = consideredSteps ? separatedSteps / consideredSteps : 0;
  const separated = sep >= 0.08 && nss >= 1;
  const recovered = escaped ? recoveryStep !== null : null;
  const classification = recovered
    ? "RECOVERED"
    : escaped && finalSimilarity < 0.78
      ? "ESCAPED"
      : separated && survival >= 0.6
        ? "BOUNDED"
        : !separated
          ? "NULL_LIKE"
          : "UNRESOLVED";
  return {
    index,
    grid_x: gridX,
    grid_y: gridY,
    x: mutation,
    y: anchoring,
    classification,
    eligible: true,
    emerged: emergence !== null,
    separated_from_null: separated,
    closed: finalCoherence >= 0.7,
    survived: survival >= 0.6,
    escaped_from_reference: escaped,
    recovered,
    winner_N: 1 + Math.floor(2 + 8 * (1 - mutation) + 2 * anchoring) % 12,
    T_e: emergence,
    S_e: survival,
    UI: finalCoherence,
    NSS: nss,
    SEP: sep,
    rms_to_parent: 1 - finalSimilarity,
    iterations: request.recoverySteps,
    parent_id: "synthetic-ring-14",
    null_policy_id: `preserve_multiset_shuffle:12:${request.seed}`,
    trace,
  };
}

worker.onmessage = (event: MessageEvent<GenerateRequest>) => {
  const request = event.data;
  const points: FieldPoint[] = [];
  for (let gridY = 0; gridY < request.height; gridY += 1) {
    for (let gridX = 0; gridX < request.width; gridX += 1) {
      const index = gridY * request.width + gridX;
      points.push(
        request.engine === "analytic"
          ? analyticPoint(index, gridX, gridY, request)
          : localPoint(index, gridX, gridY, request),
      );
    }
  }
  const table: FieldTable = {
    schema_version: "1.0.0",
    width: request.width,
    height: request.height,
    points,
    source: "browser_preview",
    engine: request.engine,
  };
  worker.postMessage(table);
};

export {};
