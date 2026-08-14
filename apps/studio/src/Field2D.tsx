import { useEffect, useRef } from "react";
import { pointColor } from "./palette";
import type { FieldPoint, FieldTable, Metric } from "./types";

interface Props {
  table: FieldTable;
  metric: Metric;
  selected: FieldPoint | null;
  showRaw: boolean;
  onSelect: (point: FieldPoint) => void;
}

export function Field2D({ table, metric, selected, showRaw, onSelect }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const render = () => {
      const rect = canvas.getBoundingClientRect();
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.round(rect.width * ratio));
      canvas.height = Math.max(1, Math.round(rect.height * ratio));
      const context = canvas.getContext("2d");
      if (!context) return;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      context.clearRect(0, 0, rect.width, rect.height);
      const cellWidth = rect.width / table.width;
      const cellHeight = rect.height / table.height;
      for (const point of table.points) {
        context.fillStyle = pointColor(point, metric);
        context.fillRect(point.grid_x * cellWidth, point.grid_y * cellHeight, cellWidth + 0.7, cellHeight + 0.7);
      }
      const vignette = context.createRadialGradient(rect.width / 2, rect.height / 2, rect.width * 0.15, rect.width / 2, rect.height / 2, rect.width * 0.68);
      vignette.addColorStop(0, "rgba(7,16,20,0)");
      vignette.addColorStop(1, "rgba(7,16,20,.22)");
      context.fillStyle = vignette;
      context.fillRect(0, 0, rect.width, rect.height);
      if (showRaw && cellWidth > 3) {
        context.fillStyle = "rgba(240,246,242,.5)";
        for (const point of table.points) {
          context.fillRect((point.grid_x + 0.5) * cellWidth, (point.grid_y + 0.5) * cellHeight, 1, 1);
        }
      }
      if (selected) {
        const cx = (selected.grid_x + 0.5) * cellWidth;
        const cy = (selected.grid_y + 0.5) * cellHeight;
        context.strokeStyle = "#f8f0dc";
        context.lineWidth = 1.4;
        context.beginPath();
        context.arc(cx, cy, Math.max(6, Math.min(cellWidth, cellHeight) * 1.3), 0, Math.PI * 2);
        context.stroke();
        context.strokeStyle = "rgba(248,240,220,.35)";
        context.beginPath();
        context.arc(cx, cy, Math.max(11, Math.min(cellWidth, cellHeight) * 2.2), 0, Math.PI * 2);
        context.stroke();
      }
      context.strokeStyle = "rgba(194,222,217,.18)";
      context.lineWidth = 1;
      context.strokeRect(0.5, 0.5, rect.width - 1, rect.height - 1);
    };
    render();
    const observer = new ResizeObserver(render);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [metric, selected, showRaw, table]);

  return (
    <canvas
      className="field-canvas"
      ref={canvasRef}
      onClick={(event) => {
        const rect = event.currentTarget.getBoundingClientRect();
        const gridX = Math.min(table.width - 1, Math.floor(((event.clientX - rect.left) / rect.width) * table.width));
        const gridY = Math.min(table.height - 1, Math.floor(((event.clientY - rect.top) / rect.height) * table.height));
        onSelect(table.points[gridY * table.width + gridX]);
      }}
      aria-label="Computed field map. Click a point to inspect its evidence."
    />
  );
}

