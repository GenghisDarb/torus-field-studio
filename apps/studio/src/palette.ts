import type { FieldPoint, Metric } from "./types";

export const palette = {
  ink: "#071014",
  teal: "#2ba6a6",
  sea: "#1f6972",
  amber: "#e8b85d",
  coral: "#db674f",
  ice: "#dceceb",
  muted: "#5f7578",
};

const stops = [
  [7, 16, 20],
  [16, 57, 65],
  [31, 112, 117],
  [232, 184, 93],
  [219, 103, 79],
  [243, 238, 228],
];

function interpolate(t: number): string {
  const safe = Math.max(0, Math.min(0.9999, t));
  const scaled = safe * (stops.length - 1);
  const index = Math.floor(scaled);
  const local = scaled - index;
  const left = stops[index];
  const right = stops[index + 1];
  const channels = left.map((value, channel) => Math.round(value + (right[channel] - value) * local));
  return `rgb(${channels.join(",")})`;
}

export function metricValue(point: FieldPoint, metric: Metric): number {
  if (metric === "S_e") return point.S_e ?? 0.46;
  if (metric === "UI") return point.UI ?? 0.46;
  if (metric === "NSS") return point.NSS == null ? 0.46 : Math.max(0, Math.min(1, (point.NSS + 1) / 8));
  return {
    ESCAPED: 0.08,
    NULL_LIKE: 0.25,
    UNRESOLVED: 0.46,
    RECOVERED: 0.74,
    BOUNDED: 0.94,
  }[point.classification];
}

export function pointColor(point: FieldPoint, metric: Metric): string {
  return interpolate(metricValue(point, metric));
}

export function colorAsRgb(point: FieldPoint, metric: Metric): [number, number, number] {
  const match = pointColor(point, metric).match(/\d+/g)?.map(Number) ?? [220, 236, 235];
  return [match[0] / 255, match[1] / 255, match[2] / 255];
}
