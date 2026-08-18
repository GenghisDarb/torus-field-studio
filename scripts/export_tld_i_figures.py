from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export an evidence-labelled TLD I SVG summary")
    parser.add_argument("--result", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    rows = result["notebook13"]["alpha_sweep"]
    width, height = 1200, 675
    plot_left, plot_top, plot_width, plot_height = 120, 190, 980, 330
    points = []
    for index, row in enumerate(rows):
        x = plot_left + index * plot_width / (len(rows) - 1)
        y = plot_top + (1 - row["return_rate_given_escape"]) * plot_height
        points.append((x, y, row))
    polyline = " ".join(f"{x:.2f},{y:.2f}" for x, y, _ in points)
    labels = "".join(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="7" fill="#e8b85d"/>'
        f'<text x="{x:.2f}" y="{plot_top + plot_height + 34}" text-anchor="middle" '
        f'fill="#9db2af" font-size="16">{row["alpha_heal"]}</text>'
        f'<text x="{x:.2f}" y="{y - 16:.2f}" text-anchor="middle" fill="#dceceb" '
        f'font-size="15">{row["return_rate_given_escape"]:.3f}</text>'
        for x, y, row in points
    )
    baseline = result["baseline"]["sweep_2_30"]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="1200" height="675" fill="#071014"/>
<text x="70" y="70" fill="#e8b85d" font-family="sans-serif" font-size="28" font-weight="600">TLD I — Structural Escape, Damped Healing, and Ringing</text>
<text x="70" y="108" fill="#8da3a0" font-family="monospace" font-size="16">PUBLISHED-SOURCE EXACT REPRODUCTION · DOI 10.5281/zenodo.18080090</text>
<text x="70" y="145" fill="#dceceb" font-family="monospace" font-size="16">baseline winner_N={baseline["winner_N"]} · margin={baseline["margin"]:.15f} · claim=COMPUTED_DYNAMICAL · TLD_DERIVED=BLOCKED</text>
<line x1="{plot_left}" y1="{plot_top}" x2="{plot_left}" y2="{plot_top + plot_height}" stroke="#315057"/>
<line x1="{plot_left}" y1="{plot_top + plot_height}" x2="{plot_left + plot_width}" y2="{plot_top + plot_height}" stroke="#315057"/>
<line x1="{plot_left}" y1="{plot_top + plot_height * 0.05}" x2="{plot_left + plot_width}" y2="{plot_top + plot_height * 0.05}" stroke="#db674f" stroke-dasharray="8 8"/>
<text x="{plot_left - 18}" y="{plot_top + plot_height * 0.05 + 5}" text-anchor="end" fill="#db8a78" font-family="monospace" font-size="14">0.95</text>
<polyline points="{polyline}" fill="none" stroke="#2ba6a6" stroke-width="4"/>
{labels}
<text x="600" y="585" text-anchor="middle" fill="#9db2af" font-family="monospace" font-size="17">anchoring alpha · conditional return rate</text>
<text x="70" y="635" fill="#8da3a0" font-family="sans-serif" font-size="15">4/6 preregistered criteria pass. alpha=0.02 mean return steps and p90 flips fail. T_e and S_e were not computed.</text>
<title>{html.escape("TLD I exact historical reproduction; not external validation")}</title>
</svg>'''
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(svg, encoding="utf-8", newline="\n")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
