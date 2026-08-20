import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { exportBrowserBundle, importBundle } from "./bundle";
import { Field2D } from "./Field2D";
import { Icon } from "./Icon";
import { pointColor } from "./palette";
import { TraceChart } from "./TraceChart";
import type { Engine, FieldPoint, FieldTable, GenerateRequest, Metric, ViewMode } from "./types";

const Surface3D = lazy(() => import("./Surface3D").then((module) => ({ default: module.Surface3D })));

const defaultRequest: GenerateRequest = {
  engine: "local_brot",
  width: 56,
  height: 40,
  power: 14,
  maxIterations: 80,
  seed: 1407,
  recoverySteps: 12,
};

function TorusMark() {
  return (
    <svg className="torus-mark" viewBox="0 0 44 44" aria-hidden="true">
      <ellipse cx="22" cy="22" rx="17" ry="8" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <ellipse cx="22" cy="22" rx="8" ry="17" fill="none" stroke="currentColor" strokeWidth="1.4" transform="rotate(38 22 22)" />
      <ellipse cx="22" cy="22" rx="15" ry="6" fill="none" stroke="currentColor" strokeWidth="1" transform="rotate(-42 22 22)" opacity=".55" />
      <circle cx="22" cy="22" r="2.3" fill="currentColor" />
    </svg>
  );
}

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (value: boolean) => void; label: string }) {
  return (
    <label className="toggle-row">
      <span>{label}</span>
      <button className={`toggle ${checked ? "on" : ""}`} role="switch" aria-checked={checked} onClick={() => onChange(!checked)} type="button">
        <span />
      </button>
    </label>
  );
}

function MetricCard({ label, value, suffix = "" }: { label: string; value: string | number; suffix?: string }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}{suffix}</strong>
    </div>
  );
}

function BooleanRow({ label, value }: { label: string; value: boolean | null }) {
  return (
    <div className="boolean-row">
      <span>{label}</span>
      <span className={value === true ? "state yes" : value === false ? "state no" : "state neutral"}>
        {value === null ? "N/A" : value ? "YES" : "NO"}
      </span>
    </div>
  );
}

export default function App() {
  const [request, setRequest] = useState(defaultRequest);
  const [table, setTable] = useState<FieldTable | null>(null);
  const [selected, setSelected] = useState<FieldPoint | null>(null);
  const [metric, setMetric] = useState<Metric>("NSS");
  const [viewMode, setViewMode] = useState<ViewMode>("field");
  const [showRaw, setShowRaw] = useState(true);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [auditOpen, setAuditOpen] = useState(false);
  const workerRef = useRef<Worker | null>(null);
  const importRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const worker = new Worker(new URL("./field.worker.ts", import.meta.url), { type: "module" });
    workerRef.current = worker;
    worker.onmessage = (event: MessageEvent<FieldTable>) => {
      setTable(event.data);
      setSelected(event.data.points[Math.floor(event.data.points.length * 0.47)] ?? null);
      setBusy(false);
    };
    return () => worker.terminate();
  }, []);

  useEffect(() => {
    if (!workerRef.current) return;
    setBusy(true);
    const timer = window.setTimeout(() => workerRef.current?.postMessage(request), 100);
    return () => window.clearTimeout(timer);
  }, [request]);

  const setEngine = useCallback((engine: Engine) => {
    setError(null);
    setRequest((current) => ({
      ...current,
      engine,
      width: engine === "analytic" ? 96 : 56,
      height: engine === "analytic" ? 64 : 40,
    }));
    setMetric(engine === "analytic" ? "S_e" : "NSS");
  }, []);

  const activeEngine = table?.source === "tbx_import" && table.engine ? table.engine : request.engine;
  const isHistoricalTld = activeEngine === "tld" && table?.tld != null;
  const isHeldout = activeEngine === "tld" && table?.heldout != null;
  const isForensic = isHeldout && table?.heldout?.profile.includes("forensic");
  const isTld = isHistoricalTld || isHeldout;
  const isGeometry = table?.geometry != null;
  const isGeometryHeldout = isGeometry && (
    table?.geometry?.profile.includes("heldout") || table?.geometry?.profile.includes("combined")
  );
  const claimLevel = table?.source === "tbx_import"
    ? table.claimLevel ?? "BUNDLE CLAIM UNKNOWN"
    : activeEngine === "analytic"
      ? "ILLUSTRATIVE_ANALYTIC"
      : "COMPUTED_DYNAMICAL";
  const classificationCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    table?.points.forEach((point) => { counts[point.classification] = (counts[point.classification] ?? 0) + 1; });
    return counts;
  }, [table]);
  const sourceLabel = isGeometry
    ? isGeometryHeldout ? "GEOMETRY HELD-OUT · AUDIT PASSED" : "GEOMETRY PILOT · AUDIT PASSED"
    : isHeldout ? "HELD-OUT SOURCE · AUDIT PASSED" : isHistoricalTld ? "PUBLISHED SOURCE · AUDIT PASSED" : table?.source === "tbx_import" ? "TBX AUDIT PASSED" : "BROWSER PREVIEW";

  const handleImport = async (file?: File) => {
    if (!file) return;
    try {
      setBusy(true);
      const imported = await importBundle(file);
      setTable(imported);
      setSelected(imported.points[Math.floor(imported.points.length / 2)] ?? null);
      if (imported.engine === "tld" || imported.geometry) setMetric("classification");
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not read this bundle.");
    } finally {
      setBusy(false);
    }
  };

  const loadPublishedTld = async () => {
    try {
      setBusy(true);
      const response = await fetch(`${import.meta.env.BASE_URL}examples/tld-i-combined-historical-reproduction.tbx.zip`);
      if (!response.ok) throw new Error(`Published example request failed (${response.status})`);
      const file = new File([await response.blob()], "tld-i-combined-historical-reproduction.tbx.zip", { type: "application/zip" });
      await handleImport(file);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load the published TLD I example.");
      setBusy(false);
    }
  };

  const loadHeldoutStudy = async () => {
    try {
      setBusy(true);
      const response = await fetch(`${import.meta.env.BASE_URL}examples/v021-forensic-combined.tbx.zip`);
      if (!response.ok) throw new Error(`Held-out study request failed (${response.status})`);
      const file = new File([await response.blob()], "v021-forensic-combined.tbx.zip", { type: "application/zip" });
      await handleImport(file);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load the held-out study.");
      setBusy(false);
    }
  };

  const loadGeometryHeldout = async () => {
    try {
      setBusy(true);
      const response = await fetch(`${import.meta.env.BASE_URL}examples/v030-geometry-combined.tbx.zip`);
      if (!response.ok) throw new Error(`v0.3.0 geometry result request failed (${response.status})`);
      const file = new File([await response.blob()], "v030-geometry-combined.tbx.zip", { type: "application/zip" });
      await handleImport(file);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load the v0.3.0 geometry result.");
      setBusy(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <TorusMark />
          <div>
            <div className="brand-name"><span>TORUS</span> FIELD STUDIO</div>
            <div className="brand-subtitle">LOCAL-FIRST SCIENTIFIC WORKBENCH · v0.3.0</div>
          </div>
        </div>
        <div className="header-actions">
          <button className="quiet-button" type="button" onClick={loadGeometryHeldout}><Icon name="spark" /> Load v0.3.0 field assay</button>
          <button className="quiet-button" type="button" onClick={loadHeldoutStudy}><Icon name="shield" /> Load v0.2.2 forensic audit</button>
          <button className="quiet-button" type="button" onClick={loadPublishedTld}><Icon name="spark" /> Load TLD I result</button>
          <button className="quiet-button" type="button" onClick={() => setAuditOpen(true)}><Icon name="shield" /> Audit</button>
          <button className="quiet-button" type="button" onClick={() => importRef.current?.click()}><Icon name="upload" /> Import bundle</button>
          <button className="primary-button" type="button" disabled={!table || isTld || isGeometry} title={isTld || isGeometry ? "Audited source TBX bytes are preserved outside the browser exporter." : undefined} onClick={() => table && exportBrowserBundle(table, request, activeEngine)}><Icon name="download" /> Export .tbx</button>
          <input ref={importRef} type="file" accept=".zip,.tbx.zip" hidden onChange={(event) => handleImport(event.target.files?.[0])} />
        </div>
      </header>

      <main className="workspace">
        <aside className="left-panel panel">
          <div className="panel-heading">
            <span>RUN CONFIGURATION</span>
            <span className="status-dot">FROZEN</span>
          </div>

          <section className="control-section">
            <label className="section-label">Engine</label>
            <div className="engine-switch">
              <button type="button" className={activeEngine === "local_brot" ? "active" : ""} onClick={() => setEngine("local_brot")}>
                <Icon name="link" />
                <span>TORUS-BROT<small>Registered ladder</small></span>
              </button>
              <button type="button" className={activeEngine === "analytic" ? "active" : ""} onClick={() => setEngine("analytic")}>
                <Icon name="spark" />
                <span>ANALYTIC<small>Complex power</small></span>
              </button>
            </div>
          </section>

          <section className="control-section compact">
            <label className="section-label">Dataset</label>
            <div className="select-like">
              <span>{isGeometry ? isGeometryHeldout ? "Fluidic pinball · prospective paired assay" : "Wind farm · nonconfirmatory pilot" : isForensic ? "v0.2.2 forensic · Beijing PM2.5" : isHeldout ? "Held-Out TLD · Beijing PM2.5" : isHistoricalTld ? "TLD I · published-source reproduction" : activeEngine === "analytic" ? `Complex power · p=${request.power}` : "Synthetic ring · 14 rungs"}</span>
              <span className="chevron">⌄</span>
            </div>
            <div className="source-hash"><span>{isTld || isGeometry ? "DOI" : "SHA-256"}</span><code>{isGeometry ? table?.geometry?.doi : isHeldout ? table?.heldout?.doi : isHistoricalTld ? table?.tld?.doi : activeEngine === "analytic" ? "5d2b…c14e" : "8f04…a217"}</code></div>
          </section>

          {isHistoricalTld && table?.tld && (
            <section className="control-section tld-source-card" data-testid="tld-source-panel">
              <span className="eyebrow">REAL DATA · HISTORICAL LANE</span>
              <strong>TLD I — Structural Escape, Damped Healing, and Ringing</strong>
              <p>{table.tld.title}</p>
              <dl>
                <div><dt>Source DOI</dt><dd>{table.tld.doi}</dd></div>
                <div><dt>Baseline</dt><dd>winner N {table.tld.baselineWinnerN} · margin {table.tld.baselineMargin.toFixed(6)}</dd></div>
                <div><dt>Preregistration</dt><dd>{table.tld.preregistrationPassed} pass · {table.tld.preregistrationFailed} fail</dd></div>
                <div><dt>Verifier</dt><dd>{table.tld.verificationStatus.toUpperCase()}</dd></div>
                <div><dt>TLD-derived</dt><dd>{table.tld.tldDerivedStatus}</dd></div>
              </dl>
            </section>
          )}

          {isHeldout && table?.heldout && (
            <section className="control-section tld-source-card" data-testid="heldout-source-panel">
              <span className="eyebrow">{isForensic ? "POST-HOC FORENSIC AUDIT · IMMUTABLE ORIGINAL" : "REAL DATA · PROSPECTIVE HELD-OUT LANE"}</span>
              <strong>{isForensic ? "v0.2.2 Negative-Result Reconciliation" : "Held-Out TLD Study — Beijing PM2.5"}</strong>
              <p>{table.heldout.scientificOutcome.replaceAll("_", " ")}</p>
              <dl>
                <div><dt>Source DOI</dt><dd>{table.heldout.doi}</dd></div>
                <div><dt>Parents / nulls</dt><dd>{table.heldout.eligibleParentCount} · {table.heldout.nullsPerParent} each</dd></div>
                <div><dt>Tₑ / Sₑ</dt><dd>{table.heldout.T_e} · {table.heldout.S_e.toFixed(3)}</dd></div>
                <div><dt>winner_N</dt><dd>{table.heldout.winnerN} · separate closure mode</dd></div>
                <div><dt>14 specificity</dt><dd>{table.heldout.specificity14 ? "PASSED" : "FAILED"}</dd></div>
                <div><dt>Verifier</dt><dd>{table.heldout.verificationStatus.toUpperCase()} · {table.heldout.mutationRejectionCount}/{table.heldout.mutationCount} mutations</dd></div>
                <div><dt>TLD-derived</dt><dd>{table.heldout.tldDerivedStatus}</dd></div>
              </dl>
              <div className="notice analytic-notice">Negative under frozen gates. {isForensic ? "Forensic diagnostics are post-hoc and do not reverse v0.2.1." : "Valid and publishable;"} external validation remains false.</div>
            </section>
          )}

          {isGeometry && table?.geometry && (
            <section className="control-section tld-source-card" data-testid="geometry-source-panel">
              <span className="eyebrow">{isGeometryHeldout ? "REAL DATA · PROSPECTIVE HELD-OUT GEOMETRY" : "REAL DATA · NONCONFIRMATORY ENGINEERING PILOT"}</span>
              <strong>{isGeometryHeldout ? "Fluidic-Pinball Geometry Method V2 Assay" : "Wind-Farm Geometry Method V2 Pilot"}</strong>
              <p>{table.geometry.scientificOutcome.replaceAll("_", " ")}</p>
              <dl>
                <div><dt>Source DOI</dt><dd>{table.geometry.doi}</dd></div>
                <div><dt>Hierarchy</dt><dd>{table.geometry.campaignCount} system/campaign · {table.geometry.conditionCount} {isGeometryHeldout ? "paired blocks" : "nonexchangeable conditions"}</dd></div>
                <div><dt>Statistical unit</dt><dd>{table.geometry.statisticalUnit}</dd></div>
                <div><dt>Raw observations</dt><dd>{table.geometry.registeredObservationCount} · {table.geometry.rawObservationRole}</dd></div>
                <div><dt>Coordinates / units</dt><dd>{table.geometry.coordinateContract} · {table.geometry.unitContract}</dd></div>
                <div><dt>Mask / nesting</dt><dd>{table.geometry.maskPolicy} · {table.geometry.nestedReplicates}</dd></div>
                <div><dt>Modalities</dt><dd>{table.geometry.modalities}</dd></div>
                <div><dt>Projections</dt><dd>{table.geometry.projectionCount} · {table.geometry.projectionContract}</dd></div>
                <div><dt>Nulls</dt><dd>{table.geometry.nullCount} · {table.geometry.nullContract}</dd></div>
                <div><dt>Closure-null calibration</dt><dd>{table.geometry.closureNullCalibration}</dd></div>
                <div><dt>Method</dt><dd>{table.geometry.methodMode}</dd></div>
                <div><dt>Scale</dt><dd>{table.geometry.geometricScale}</dd></div>
                <div><dt>Operation depth</dt><dd>{table.geometry.operationDepth}</dd></div>
                <div><dt>Tₑ / Sₑ / winner_N</dt><dd>NOT APPLICABLE</dd></div>
                <div><dt>Baseline</dt><dd>{table.geometry.domainBaseline}</dd></div>
                <div><dt>Fragility / representation</dt><dd>{table.geometry.structuredFragility} · {table.geometry.representationAgreement}</dd></div>
                <div><dt>Claim tier</dt><dd>{table.geometry.claimTier}</dd></div>
                <div><dt>Verifier</dt><dd>{table.geometry.verificationStatus} · {table.geometry.failureCount} preserved ledger entries</dd></div>
                <div><dt>TLD-derived</dt><dd>{table.geometry.tldDerivedStatus}</dd></div>
              </dl>
              <div className="notice analytic-notice">{isGeometryHeldout ? "Nonbinary evidence vector only. One scored execution; no positive/negative TLD classification, population generalization, ToT-BROT, TORUS proof, or external validation." : "Descriptive condition panels only. No threshold tuning, population aggregation, confirmatory TLD result, or external validation."}</div>
            </section>
          )}

          {activeEngine === "analytic" ? (
            <section className="control-section">
              <div className="label-with-value"><label className="section-label" htmlFor="power">Power</label><output>{request.power}</output></div>
              <input id="power" className="range" type="range" min="2" max="32" value={request.power} onChange={(event) => setRequest((current) => ({ ...current, power: Number(event.target.value) }))} />
              <div className="range-ends"><span>2</span><span>32</span></div>
              <div className="notice analytic-notice">Declared visual analog. No TLD evidentiary authority is inferred.</div>
            </section>
          ) : !isTld && !isGeometry ? (
            <section className="control-section axes-contract">
              <label className="section-label">Frozen perturbation axes</label>
              <div><span className="axis x">X</span><span>Order mutation</span><code>0.00 → 1.00</code></div>
              <div><span className="axis y">Y</span><span>Anchoring α</span><code>1.00 → 0.00</code></div>
              <div><span className="axis z">Z</span><span>{metric}</span><code>computed</code></div>
            </section>
          ) : null}

          <section className="control-section">
            <label className="section-label" htmlFor="metric">Visual encoding</label>
            <select id="metric" value={metric} disabled={isTld || isGeometry} onChange={(event) => setMetric(event.target.value as Metric)}>
              <option value="classification">Classification</option>
              <option value="NSS">Null separation (NSS)</option>
              <option value="UI">Unification index (UI)</option>
              <option value="S_e">Survival (S_e)</option>
            </select>
            <div className="gradient-bar" />
            <div className="range-ends"><span>low</span><span>registered scale</span><span>high</span></div>
          </section>

          <section className="control-section compact">
            <label className="section-label" htmlFor="resolution">Sample grid</label>
            <select
              id="resolution"
              value={isTld || isGeometry ? `${table?.width}x${table?.height}` : `${request.width}x${request.height}`}
              disabled={isTld || isGeometry}
              onChange={(event) => {
                const [width, height] = event.target.value.split("x").map(Number);
                setRequest((current) => ({ ...current, width, height }));
              }}
            >
              {isTld || isGeometry ? <option value={`${table?.width}x${table?.height}`}>{table?.width} × {table?.height} registered condition panels</option> : activeEngine === "analytic" ? <>
                <option value="64x44">64 × 44</option><option value="96x64">96 × 64</option><option value="128x88">128 × 88</option>
              </> : <>
                <option value="40x28">40 × 28</option><option value="56x40">56 × 40</option><option value="80x56">80 × 56</option>
              </>}
            </select>
            <Toggle checked={showRaw} onChange={setShowRaw} label="Show raw samples" />
            <div className="frozen-row"><Icon name="check" /><span>Seed {isHeldout ? 20260818 : isHistoricalTld ? 42 : request.seed} · rules frozen</span></div>
          </section>

          <div className="claim-card">
            <div><Icon name="shield" /><span>CLAIM BOUNDARY</span></div>
            <strong>{claimLevel}</strong>
            <p>{isGeometry ? isGeometryHeldout ? "Prospective paired geometry assay; the result is a nonbinary evidence vector, TLD_DERIVED is blocked, and external validation is false." : "Nonconfirmatory, source-specific engineering pilot; TLD_DERIVED is blocked, the four conditions are not pooled, and external validation is false." : isHeldout ? "Prospective held-out negative result; TLD_DERIVED is blocked and external validation is not supplied." : isHistoricalTld ? "Exact self-reproduction of a published computational release; TLD_DERIVED is blocked and external validation is not supplied." : activeEngine === "analytic" ? "Useful for intuition and comparison; not a TLD-derived result." : "Reproducible registered computation; external validation not supplied."}</p>
          </div>
        </aside>

        <section className="center-stage">
          <div className="stage-toolbar">
            <div className="view-tabs">
              <button className={viewMode === "field" ? "active" : ""} type="button" onClick={() => setViewMode("field")}><Icon name="grid" /> Field</button>
              <button className={viewMode === "surface" ? "active" : ""} type="button" onClick={() => setViewMode("surface")}><Icon name="cube" /> Surface</button>
            </div>
            <div className="stage-status">
              <span className={`source-pill ${table?.source === "tbx_import" ? "verified" : ""}`}>{sourceLabel}</span>
              <span>{table?.width ?? request.width} × {table?.height ?? request.height}</span>
              <span>{table?.points.length.toLocaleString() ?? "—"} points</span>
            </div>
          </div>
          <div className="visual-stage">
            {table && viewMode === "field" && <Field2D table={table} metric={metric} selected={selected} showRaw={showRaw} onSelect={setSelected} />}
            {table && viewMode === "surface" && <Suspense fallback={<div className="busy-overlay"><span className="loader-ring" /><strong>Loading surface renderer</strong></div>}><Surface3D table={table} metric={metric} selected={selected} showRaw={showRaw} /></Suspense>}
            {busy && <div className="busy-overlay"><span className="loader-ring" /><strong>Computing frozen field</strong><small>Classification precedes rendering</small></div>}
            <div className="axis-label axis-y">{isGeometry ? isGeometryHeldout ? "EVIDENCE CHANNEL" : "CONDITION PANEL" : isHeldout ? "REGISTERED CONDITION" : isHistoricalTld ? "TRIAL / ENDPOINT" : activeEngine === "analytic" ? "IMAGINARY" : "ANCHORING α"}</div>
            <div className="axis-label axis-x">{isGeometry ? isGeometryHeldout ? "ACTUATION p" : "YAW INTERVENTION" : isHeldout ? "OPERATION DEPTH N" : isHistoricalTld ? "REGISTERED STEP / α" : activeEngine === "analytic" ? "REAL" : "ORDER MUTATION"}</div>
            <div className="corner-readout"><span>COLOR</span><strong>{metric}</strong><span>INTERPOLATION</span><strong>VISUAL ONLY</strong></div>
          </div>
          <div className="stage-caption">
            <span><i className="raw-dot" /> Raw computed sample</span>
            <span><i className="surface-swatch" /> Interpolated display</span>
            <span className="caption-warning">Interpolated pixels are never counted as observations.</span>
          </div>
        </section>

        <aside className="right-panel panel">
          <div className="panel-heading"><span>POINT INSPECTOR</span><code>#{selected?.index.toString().padStart(4, "0") ?? "—"}</code></div>
          {selected ? <>
            <section className="point-identity">
              <div className="classification-mark" style={{ borderColor: pointColor(selected, "classification") }}>
                <span style={{ backgroundColor: pointColor(selected, "classification") }} />
              </div>
              <div><span>CLASSIFICATION</span><strong>{selected.classification.replace("_", " ")}</strong><small>x {selected.x.toFixed(4)} · y {selected.y.toFixed(4)}</small></div>
            </section>
            <section className="inspector-section metric-grid">
              <MetricCard label="UI" value={selected.UI?.toFixed(3) ?? "N/A"} />
              <MetricCard label="NSS" value={selected.NSS?.toFixed(2) ?? "N/A"} suffix={selected.NSS == null ? "" : "σ"} />
              <MetricCard label="SEP" value={selected.SEP?.toFixed(3) ?? "N/A"} />
              <MetricCard label="Sₑ" value={selected.S_e?.toFixed(3) ?? "N/A"} />
              <MetricCard label="Tₑ" value={selected.T_e ?? "—"} />
              <MetricCard label="winner N" value={selected.winner_N ?? "—"} />
            </section>
            {isTld && <section className="inspector-section evidence-block" data-testid="tld-raw-point">
              <h3>{isHeldout ? "Registered summary identity" : "Raw trajectory identity"}</h3>
              <dl>
                <div><dt>Observed</dt><dd>{selected.observed ? "YES" : "NO — MISSING PRESERVED"}</dd></div>
                <div><dt>Phase</dt><dd>{selected.phase ?? selected.trace[0]?.stage ?? "after terminal event"}</dd></div>
                <div><dt>Trial</dt><dd>{selected.trial_id ?? "endpoint"}</dd></div>
                <div><dt>α</dt><dd>{selected.alpha ?? "—"}</dd></div>
                <div><dt>Registered t</dt><dd>{selected.t ?? "—"}</dd></div>
              </dl>
            </section>}
            <section className="inspector-section">
              <h3>Endpoint state</h3>
              <BooleanRow label="Eligible" value={selected.eligible} />
              <BooleanRow label="Emerged" value={selected.emerged} />
              <BooleanRow label="Separated from null" value={selected.separated_from_null} />
              <BooleanRow label="Closed" value={selected.closed} />
              <BooleanRow label="Survived" value={selected.survived} />
              <BooleanRow label="Escaped reference" value={selected.escaped_from_reference} />
              <BooleanRow label="Recovered" value={selected.recovered} />
            </section>
            <section className="inspector-section evidence-block">
              <h3>Provenance</h3>
              <dl>
                <div><dt>Parent</dt><dd>{selected.parent_id}</dd></div>
                <div><dt>Null policy</dt><dd>{selected.null_policy_id}</dd></div>
                <div><dt>Run</dt><dd>{table?.runId ?? `browser:${request.seed}`}</dd></div>
                <div><dt>Authority</dt><dd>{sourceLabel}</dd></div>
                {(isTld || isGeometry) && <div><dt>Source DOI</dt><dd>{isGeometry ? table?.geometry?.doi : isHeldout ? table?.heldout?.doi : table?.tld?.doi}</dd></div>}
              </dl>
            </section>
            <section className="interpretation legal"><h3>Legal interpretation</h3><p>{isGeometry ? "This panel is one source-specific, nonexchangeable condition from a descriptive engineering pilot." : isHeldout ? "This cell is a computed population summary from the prospectively frozen held-out study." : isHistoricalTld ? "This point belongs to the independently audited historical published-source reproduction." : activeEngine === "analytic" ? "This point is part of a declared complex-power model." : "This point records a reproducible parent/null field computation."}</p></section>
            <section className="interpretation excluded"><h3>Excluded</h3><p>No external validation, causal ownership, or repair authority is implied.</p></section>
          </> : <div className="empty-inspector">Choose a computed point in the field.</div>}
        </aside>

        <section className="timeline-panel">
          <div className="timeline-copy">
            <span>SELECTED TRACE</span>
            <strong>{selected ? isHeldout ? `${selected.trace[0]?.stage ?? "condition"} · N ${selected.x}` : isHistoricalTld ? `${selected.phase ?? "missing"} · trial ${selected.trial_id ?? "endpoint"}` : `${selected.trace.length} registered steps` : "No point selected"}</strong>
            <small>{selected?.trace.some((item) => item.stage === "healing") ? "Recovery threshold crossed" : activeEngine === "analytic" ? "Complex orbit" : "No healing event recorded"}</small>
          </div>
          <TraceChart point={selected} />
          <div className="timeline-legend">
            <span><i className="line observed" />Observed</span>
            <span><i className="line null" />Null mean</span>
            <span><i className="point healing" />Healing</span>
          </div>
          <div className="run-summary">
            <span>FIELD STATUS</span>
            <strong>{busy ? "COMPUTING" : "COMPLETE"}</strong>
            <small>{Object.entries(classificationCounts).map(([key, value]) => `${key.toLowerCase()} ${value}`).join(" · ")}</small>
          </div>
          {isHistoricalTld && table?.tld && <div className="tld-run-evidence" data-testid="tld-evidence-summary">
            <span>REGISTERED RESULTS</span>
            <strong>Escape · recovery · ringing</strong>
            <small>{table.tld.alphaSweep.map((row) => `α ${row.alpha}: return ${(row.returnRate * 100).toFixed(1)}%, steps ${row.meanReturnSteps.toFixed(1)}, p90 flips ${row.p90Flips}`).join(" · ")}</small>
            <small>Operating envelope: {table.tld.operatingEnvelope.map((row) => `p ${row.escapeStrength}: return ${(row.returnRate * 100).toFixed(1)}%`).join(" · ")} · {table.tld.transitionCount} winner-state transitions</small>
          </div>}
          {isHeldout && table?.heldout && <div className="tld-run-evidence" data-testid="heldout-evidence-summary">
            <span>FROZEN HELD-OUT RESULT</span>
            <strong>Tₑ {table.heldout.T_e} · Sₑ {table.heldout.S_e.toFixed(3)} · winner_N {table.heldout.winnerN}</strong>
            <small>SEP observed: {table.heldout.sepAny ? "YES" : "NO"} · 14 specificity: {table.heldout.specificity14 ? "PASS" : "FAIL"} · failures: {table.heldout.failureCount}</small>
            <small>{table.heldout.baselineStatus} · external validation: NO</small>
          </div>}
          {isGeometry && table?.geometry && <div className="tld-run-evidence" data-testid="geometry-evidence-summary">
            <span>{isGeometryHeldout ? "FROZEN HELD-OUT NONBINARY RESULT" : "NONCONFIRMATORY PILOT"}</span>
            <strong>{table.geometry.geometricScale} · Tₑ N/A · Sₑ N/A · winner_N N/A</strong>
            <small>{table.geometry.conditionCount} {isGeometryHeldout ? "paired block deltas" : "condition outputs"} retained · one deposited system/campaign · no population aggregate</small>
            <small>TLD_DERIVED: {table.geometry.tldDerivedStatus} · external validation: NO · failures preserved: {table.geometry.failureCount}</small>
            <small>Forbidden: {table.geometry.forbiddenClaims.join(" · ")}</small>
          </div>}
        </section>
      </main>

      {error && <div className="toast error" role="alert"><strong>Import failed</strong><span>{error}</span><button type="button" onClick={() => setError(null)}>×</button></div>}
      {auditOpen && (
        <div className="modal-backdrop" onMouseDown={() => setAuditOpen(false)}>
          <section className="audit-modal" onMouseDown={(event) => event.stopPropagation()}>
            <button className="modal-close" type="button" onClick={() => setAuditOpen(false)}>×</button>
            <div className="audit-icon"><Icon name="shield" /></div>
            <span className="eyebrow">ARTIFACT AUDIT</span>
            <h2>{table?.source === "tbx_import" ? "Imported bundle passed strict audit" : "Browser preview is not independently verified"}</h2>
            <p>The studio keeps scientific classification separate from visual encoding. Imported TBX archives are preflighted before decompression and checked for exact membership, hashes, schema validity, claim consistency, run identity, and semantic invariants.</p>
            <div className="audit-checks">
              <div><Icon name="check" /><span>Claim badge always visible</span></div>
              <div><Icon name="check" /><span>Raw samples distinguishable from interpolation</span></div>
              <div><Icon name="check" /><span>Failures and unresolved points preserved</span></div>
              <div><Icon name="check" /><span>Parent/null identity retained per point</span></div>
              {table?.auditCheckedFiles != null && <div><Icon name="check" /><span>{table.auditCheckedFiles} manifested files verified</span></div>}
              {table?.tld && <div><Icon name="check" /><span>Source DOI and published input hashes verified</span></div>}
              {table?.heldout && <div><Icon name="check" /><span>Source DOI and registered input hashes verified</span></div>}
              {table?.geometry && <div><Icon name="check" /><span>Geometry raw-array custody, masks, hierarchy, and claim boundary verified</span></div>}
              {(table?.tld || table?.heldout || table?.geometry) && <div><Icon name="check" /><span>Preregistration or frozen contract and independent verification panels linked</span></div>}
            </div>
            <button className="primary-button full" type="button" onClick={() => setAuditOpen(false)}>Return to field</button>
          </section>
        </div>
      )}
    </div>
  );
}
