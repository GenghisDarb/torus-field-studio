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
  const sourceLabel = table?.source === "tbx_import" ? "TBX CPU ARTIFACT" : "BROWSER PREVIEW";

  const handleImport = async (file?: File) => {
    if (!file) return;
    try {
      setBusy(true);
      const imported = await importBundle(file);
      setTable(imported);
      setSelected(imported.points[Math.floor(imported.points.length / 2)] ?? null);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not read this bundle.");
    } finally {
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
            <div className="brand-subtitle">LOCAL-FIRST SCIENTIFIC WORKBENCH · v0.1</div>
          </div>
        </div>
        <div className="header-actions">
          <button className="quiet-button" type="button" onClick={() => setAuditOpen(true)}><Icon name="shield" /> Audit</button>
          <button className="quiet-button" type="button" onClick={() => importRef.current?.click()}><Icon name="upload" /> Import bundle</button>
          <button className="primary-button" type="button" disabled={!table} onClick={() => table && exportBrowserBundle(table, request, activeEngine)}><Icon name="download" /> Export .tbx</button>
          <input ref={importRef} type="file" accept=".zip,.tbx.zip,.json" hidden onChange={(event) => handleImport(event.target.files?.[0])} />
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
              <span>{activeEngine === "analytic" ? `Complex power · p=${request.power}` : "Synthetic ring · 14 rungs"}</span>
              <span className="chevron">⌄</span>
            </div>
            <div className="source-hash"><span>SHA-256</span><code>{activeEngine === "analytic" ? "5d2b…c14e" : "8f04…a217"}</code></div>
          </section>

          {activeEngine === "analytic" ? (
            <section className="control-section">
              <div className="label-with-value"><label className="section-label" htmlFor="power">Power</label><output>{request.power}</output></div>
              <input id="power" className="range" type="range" min="2" max="32" value={request.power} onChange={(event) => setRequest((current) => ({ ...current, power: Number(event.target.value) }))} />
              <div className="range-ends"><span>2</span><span>32</span></div>
              <div className="notice analytic-notice">Declared visual analog. No TLD evidentiary authority is inferred.</div>
            </section>
          ) : (
            <section className="control-section axes-contract">
              <label className="section-label">Frozen perturbation axes</label>
              <div><span className="axis x">X</span><span>Order mutation</span><code>0.00 → 1.00</code></div>
              <div><span className="axis y">Y</span><span>Anchoring α</span><code>1.00 → 0.00</code></div>
              <div><span className="axis z">Z</span><span>{metric}</span><code>computed</code></div>
            </section>
          )}

          <section className="control-section">
            <label className="section-label" htmlFor="metric">Visual encoding</label>
            <select id="metric" value={metric} onChange={(event) => setMetric(event.target.value as Metric)}>
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
              value={`${request.width}x${request.height}`}
              onChange={(event) => {
                const [width, height] = event.target.value.split("x").map(Number);
                setRequest((current) => ({ ...current, width, height }));
              }}
            >
              {activeEngine === "analytic" ? <>
                <option value="64x44">64 × 44</option><option value="96x64">96 × 64</option><option value="128x88">128 × 88</option>
              </> : <>
                <option value="40x28">40 × 28</option><option value="56x40">56 × 40</option><option value="80x56">80 × 56</option>
              </>}
            </select>
            <Toggle checked={showRaw} onChange={setShowRaw} label="Show raw samples" />
            <div className="frozen-row"><Icon name="check" /><span>Seed {request.seed} · rules frozen</span></div>
          </section>

          <div className="claim-card">
            <div><Icon name="shield" /><span>CLAIM BOUNDARY</span></div>
            <strong>{claimLevel}</strong>
            <p>{activeEngine === "analytic" ? "Useful for intuition and comparison; not a TLD-derived result." : "Reproducible registered computation; external validation not supplied."}</p>
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
            <div className="axis-label axis-y">{activeEngine === "analytic" ? "IMAGINARY" : "ANCHORING α"}</div>
            <div className="axis-label axis-x">{activeEngine === "analytic" ? "REAL" : "ORDER MUTATION"}</div>
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
              <MetricCard label="UI" value={selected.UI.toFixed(3)} />
              <MetricCard label="NSS" value={selected.NSS.toFixed(2)} suffix="σ" />
              <MetricCard label="SEP" value={selected.SEP.toFixed(3)} />
              <MetricCard label="Sₑ" value={selected.S_e.toFixed(3)} />
              <MetricCard label="Tₑ" value={selected.T_e ?? "—"} />
              <MetricCard label="winner N" value={selected.winner_N ?? "—"} />
            </section>
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
              </dl>
            </section>
            <section className="interpretation legal"><h3>Legal interpretation</h3><p>{activeEngine === "analytic" ? "This point is part of a declared complex-power model." : "This point records a reproducible parent/null field computation."}</p></section>
            <section className="interpretation excluded"><h3>Excluded</h3><p>No external validation, causal ownership, or repair authority is implied.</p></section>
          </> : <div className="empty-inspector">Choose a computed point in the field.</div>}
        </aside>

        <section className="timeline-panel">
          <div className="timeline-copy">
            <span>SELECTED TRACE</span>
            <strong>{selected ? `${selected.trace.length} registered steps` : "No point selected"}</strong>
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
        </section>
      </main>

      {error && <div className="toast error" role="alert"><strong>Import failed</strong><span>{error}</span><button type="button" onClick={() => setError(null)}>×</button></div>}
      {auditOpen && (
        <div className="modal-backdrop" onMouseDown={() => setAuditOpen(false)}>
          <section className="audit-modal" onMouseDown={(event) => event.stopPropagation()}>
            <button className="modal-close" type="button" onClick={() => setAuditOpen(false)}>×</button>
            <div className="audit-icon"><Icon name="shield" /></div>
            <span className="eyebrow">ARTIFACT AUDIT</span>
            <h2>{table?.source === "tbx_import" ? "Imported bundle loaded" : "Browser preview is not independently verified"}</h2>
            <p>The studio keeps the scientific classification separate from visual encoding. A CLI-generated bundle additionally carries byte-level SHA-256 verification.</p>
            <div className="audit-checks">
              <div><Icon name="check" /><span>Claim badge always visible</span></div>
              <div><Icon name="check" /><span>Raw samples distinguishable from interpolation</span></div>
              <div><Icon name="check" /><span>Failures and unresolved points preserved</span></div>
              <div><Icon name="check" /><span>Parent/null identity retained per point</span></div>
            </div>
            <button className="primary-button full" type="button" onClick={() => setAuditOpen(false)}>Return to field</button>
          </section>
        </div>
      )}
    </div>
  );
}
