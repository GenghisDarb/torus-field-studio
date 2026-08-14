import type { FieldPoint } from "./types";

export function TraceChart({ point }: { point: FieldPoint | null }) {
  if (!point || point.trace.length < 2) {
    return <div className="trace-empty">Select a field point to inspect its orbit or recovery trace.</div>;
  }
  const width = 680;
  const height = 92;
  const pad = 8;
  const values = point.trace.map((item) => item.similarity ?? item.coherence ?? 0);
  const nullValues = point.trace.map((item) => item.null_mean).filter((value): value is number => value !== undefined);
  const line = values.map((value, index) => {
    const x = pad + (index / Math.max(1, values.length - 1)) * (width - pad * 2);
    const y = height - pad - Math.max(0, Math.min(1, value)) * (height - pad * 2);
    return `${x},${y}`;
  }).join(" ");
  const nullLine = nullValues.length
    ? nullValues.map((value, index) => {
      const x = pad + (index / Math.max(1, nullValues.length - 1)) * (width - pad * 2);
      const y = height - pad - value * (height - pad * 2);
      return `${x},${y}`;
    }).join(" ")
    : null;
  return (
    <svg className="trace-chart" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img" aria-label="Selected point trace">
      <defs>
        <linearGradient id="trace-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#e8b85d" stopOpacity=".28" />
          <stop offset="1" stopColor="#e8b85d" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map((value) => <line key={value} x1="0" x2={width} y1={height - value * height} y2={height - value * height} className="trace-grid" />)}
      {nullLine && <polyline points={nullLine} className="trace-null" />}
      <polygon points={`${pad},${height - pad} ${line} ${width - pad},${height - pad}`} fill="url(#trace-fill)" />
      <polyline points={line} className="trace-line" />
      {point.trace.map((item, index) => {
        if (item.stage !== "healing") return null;
        const x = pad + (index / Math.max(1, values.length - 1)) * (width - pad * 2);
        return <circle key={index} cx={x} cy={height - pad - values[index] * (height - pad * 2)} r="3.5" className="trace-healing" />;
      })}
    </svg>
  );
}

