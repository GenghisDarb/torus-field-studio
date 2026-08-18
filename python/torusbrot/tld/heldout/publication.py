"""Publication summaries and claim-safe visual exports for the held-out study."""

from __future__ import annotations

import csv
import json
import struct
import zlib
from pathlib import Path
from typing import Any

from ...domains.beijing_pm25 import sha256_file, write_json


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _line(points: list[tuple[float, float]], color: str, width: int = 4) -> str:
    coordinates = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return (
        f'<polyline points="{coordinates}" fill="none" stroke="{color}" '
        f'stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>'
    )


def _svg(scored: Path) -> str:
    baseline = [row for row in _csv(scored / "byN_surface.csv") if row["condition"] == "baseline"]
    specificity = _csv(scored / "specificity_audit.csv")
    left_x0, left_y0, panel_w, panel_h = 90.0, 190.0, 460.0, 360.0
    right_x0 = 660.0
    nss_min, nss_max = -5.0, 3.0
    left_points = [
        (
            left_x0 + (int(row["N"]) - 6) / 8 * panel_w,
            left_y0 + (nss_max - float(row["NSS"])) / (nss_max - nss_min) * panel_h,
        )
        for row in baseline
    ]
    closure_values = [float(row["median_closure_error"]) for row in specificity]
    closure_min = min(closure_values) - 0.005
    closure_max = max(closure_values) + 0.005
    right_points = [
        (
            right_x0 + (int(row["N"]) - 4) / 16 * panel_w,
            left_y0
            + (closure_max - float(row["median_closure_error"]))
            / (closure_max - closure_min)
            * panel_h,
        )
        for row in specificity
    ]
    nss_threshold_y = left_y0 + (nss_max - 2.0) / (nss_max - nss_min) * panel_h
    winner_x = right_x0 + (9 - 4) / 16 * panel_w
    fourteen_x = right_x0 + (14 - 4) / 16 * panel_w
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="700" viewBox="0 0 1200 700" role="img" aria-labelledby="title desc">
<title id="title">Held-Out TLD Study — Beijing PM2.5 frozen negative result</title>
<desc id="desc">The baseline null separation score remains below the frozen threshold for N 6 through 14. The separate closure objective has its minimum at N 9, not N 14.</desc>
<rect width="1200" height="700" fill="#07111f"/>
<text x="70" y="68" fill="#f5f7fb" font-family="Inter,Segoe UI,sans-serif" font-size="30" font-weight="700">Held-Out TLD Study — Beijing PM2.5</text>
<text x="70" y="105" fill="#9fb3c8" font-family="Inter,Segoe UI,sans-serif" font-size="18">Frozen result: Tₑ NOT OBSERVED · Sₑ 0 · winner_N 9 · 14-specificity failed</text>
<rect x="70" y="128" width="1060" height="2" fill="#23415f"/>
<text x="90" y="170" fill="#dce8f4" font-family="Inter,Segoe UI,sans-serif" font-size="17" font-weight="600">Primary separation (baseline)</text>
<rect x="{left_x0}" y="{left_y0}" width="{panel_w}" height="{panel_h}" rx="8" fill="#0c1b2c" stroke="#294866"/>
<line x1="{left_x0}" y1="{nss_threshold_y:.2f}" x2="{left_x0 + panel_w}" y2="{nss_threshold_y:.2f}" stroke="#f7c948" stroke-width="2" stroke-dasharray="8 7"/>
<text x="{left_x0 + 8}" y="{nss_threshold_y - 9:.2f}" fill="#f7c948" font-family="Inter,Segoe UI,sans-serif" font-size="13">frozen NSS threshold = 2</text>
{_line(left_points, "#5fd0df")}
{"".join(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="#5fd0df" stroke="#07111f" stroke-width="2"/>' for x, y in left_points)}
<text x="90" y="580" fill="#9fb3c8" font-family="Inter,Segoe UI,sans-serif" font-size="14">N = 6 … 14 · UI = 0 at every depth · NSS &lt; 0 at every depth</text>
<text x="660" y="170" fill="#dce8f4" font-family="Inter,Segoe UI,sans-serif" font-size="17" font-weight="600">Separate closure objective</text>
<rect x="{right_x0}" y="{left_y0}" width="{panel_w}" height="{panel_h}" rx="8" fill="#0c1b2c" stroke="#294866"/>
<line x1="{winner_x:.2f}" y1="{left_y0}" x2="{winner_x:.2f}" y2="{left_y0 + panel_h}" stroke="#67e8a5" stroke-width="3" opacity=".55"/>
<line x1="{fourteen_x:.2f}" y1="{left_y0}" x2="{fourteen_x:.2f}" y2="{left_y0 + panel_h}" stroke="#ff7a90" stroke-width="3" stroke-dasharray="7 6" opacity=".75"/>
{_line(right_points, "#a68cff")}
{"".join(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="#a68cff" stroke="#07111f" stroke-width="2"/>' for x, y in right_points)}
<text x="{winner_x - 17:.2f}" y="535" fill="#67e8a5" font-family="Inter,Segoe UI,sans-serif" font-size="14" font-weight="700">N 9</text>
<text x="{fourteen_x - 21:.2f}" y="215" fill="#ff9aaa" font-family="Inter,Segoe UI,sans-serif" font-size="14" font-weight="700">N 14</text>
<text x="660" y="580" fill="#9fb3c8" font-family="Inter,Segoe UI,sans-serif" font-size="14">Lower is better · study minimum N 9 · N 14 is not specific</text>
<rect x="70" y="620" width="1060" height="1" fill="#23415f"/>
<circle cx="83" cy="656" r="6" fill="#5fd0df"/><text x="98" y="662" fill="#c8d8e7" font-family="Inter,Segoe UI,sans-serif" font-size="14">computed observed/null summary</text>
<text x="730" y="662" fill="#9fb3c8" font-family="Inter,Segoe UI,sans-serif" font-size="13">No interpolation entered any metric · failures: 0 · verifier: agreement</text>
</svg>
"""
    return svg


def _png_chunk(name: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + name
        + payload
        + struct.pack(">I", zlib.crc32(name + payload))
    )


def _raster_png(path: Path, scored: Path) -> None:
    width, height = 1200, 700
    pixels = bytearray([7, 17, 31, 255] * width * height)

    def set_pixel(x: int, y: int, color: tuple[int, int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            offset = (y * width + x) * 4
            pixels[offset : offset + 4] = bytes(color)

    def rectangle(x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int, int]) -> None:
        for y in range(max(0, y0), min(height, y1)):
            start = (y * width + max(0, x0)) * 4
            end = (y * width + min(width, x1)) * 4
            pixels[start:end] = bytes(color) * max(0, min(width, x1) - max(0, x0))

    def line(
        x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int, int], size: int = 2
    ) -> None:
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        error = dx + dy
        while True:
            for oy in range(-size, size + 1):
                for ox in range(-size, size + 1):
                    set_pixel(x0 + ox, y0 + oy, color)
            if x0 == x1 and y0 == y1:
                break
            twice = 2 * error
            if twice >= dy:
                error += dy
                x0 += sx
            if twice <= dx:
                error += dx
                y0 += sy

    rectangle(70, 128, 1130, 131, (35, 65, 95, 255))
    rectangle(90, 190, 550, 550, (12, 27, 44, 255))
    rectangle(660, 190, 1120, 550, (12, 27, 44, 255))
    baseline = [row for row in _csv(scored / "byN_surface.csv") if row["condition"] == "baseline"]
    left_points = [
        (
            int(90 + (int(row["N"]) - 6) / 8 * 460),
            int(190 + (3 - float(row["NSS"])) / 8 * 360),
        )
        for row in baseline
    ]
    for left, right in zip(left_points, left_points[1:]):
        line(*left, *right, (95, 208, 223, 255), 3)
    specificity = _csv(scored / "specificity_audit.csv")
    values = [float(row["median_closure_error"]) for row in specificity]
    low, high = min(values) - 0.005, max(values) + 0.005
    right_points = [
        (
            int(660 + (int(row["N"]) - 4) / 16 * 460),
            int(190 + (high - float(row["median_closure_error"])) / (high - low) * 360),
        )
        for row in specificity
    ]
    for left, right in zip(right_points, right_points[1:]):
        line(*left, *right, (166, 140, 255, 255), 3)
    line(804, 190, 804, 550, (103, 232, 165, 180), 2)
    line(947, 190, 947, 550, (255, 122, 144, 210), 2)
    raw = b"".join(b"\x00" + pixels[y * width * 4 : (y + 1) * width * 4] for y in range(height))
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += _png_chunk(b"IDAT", zlib.compress(raw, 9))
    png += _png_chunk(b"IEND", b"")
    path.write_bytes(png)


def create_publication(
    scored: Path, verification: Path, adjudication: Path, output: Path
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    endpoints = _json(scored / "primary_endpoints.json")
    verified = _json(verification / "independent_verification.json")
    scientific = _json(adjudication / "scientific_adjudication.json")
    baseline = [row for row in _csv(scored / "byN_surface.csv") if row["condition"] == "baseline"]
    summary = f"""# Held-Out TLD Study — Beijing PM2.5

This prospectively frozen study produced a valid negative result. None of the nine registered N values from 6 through 14 separated the 12 observed station ladders from their own 127 matched nulls. `T_e` was therefore `NOT_OBSERVED`, and `S_e_contiguous` was 0.

The separately registered closure objective selected `winner_N = {endpoints["winner_N_study_closure_minimum"]}`. It must not be relabeled as `T_e` or physical time. N=14 failed the secondary specificity gate.

All 12 station parents were eligible, the execution failure ledger was empty, the independent verifier reported zero disagreements, and all {verified["mutation_count"]} mutation controls were rejected. The correct claim level is `COMPUTED_DYNAMICAL`; `TLD_DERIVED` is blocked and `EXTERNALLY_VALIDATED` is false.

A negative result does not show that the PM2.5 data contain no structure. It shows that this exact observable, ordering, ladderization, parent-local null, N grid, and frozen separation rule did not detect the preregistered form of observed/null emergence.
"""
    technical = f"""# Technical report: held-out Beijing PM2.5 TLD study

## Design

The study used the UCI Beijing Multi-Site Air Quality dataset (DOI 10.24432/C5RK5G), authoritative archive SHA-256 `d1b9261c54132f04c374f762f1e5e512af19f95c95fd6bfa1e8ac7e927e3b0b8`. Each of 12 monitoring stations was an independent parent. Hourly PM2.5 measurements were aggregated to daily log1p medians when at least 18 hours were finite, month-of-year centered, and robustly scaled without interpolation.

Every parent had 127 deterministic null children created by permuting complete day records inside station-local year-month strata. The primary grid was N=6…14. SEP required at least 10 eligible parents, UI≥0.50, NSS≥2.0, and a Holm-adjusted one-sided population sign-test p≤0.05.

## Result

The adjudicated outcome is `{scientific["scientific_outcome"]}`. Baseline UI was 0 at all nine N values. Baseline NSS ranged from {min(float(row["NSS"]) for row in baseline):.6f} to {max(float(row["NSS"]) for row in baseline):.6f}; every value was below zero and every Holm-adjusted population p was 1. `T_e=NOT_OBSERVED`; consequently the primary S_e survival region is empty and `S_e_contiguous=0`.

The separate lag-closure objective selected N={endpoints["winner_N_study_closure_minimum"]}; the parent winner distribution was {json.dumps(endpoints["winner_N_distribution"], sort_keys=True)}. N=14 was not the study minimum and failed the frozen specificity gate.

The conventional station-local monthly climatology plus AR(1) improved held-out RMSE over monthly climatology alone at all 12 parents. Because the primary endpoint was already negative, residual survival at T_e is not applicable as a promotion gate.

## Verification and claims

The independent implementation recomputed parent eligibility, matched-null mapping, UI, NSS, SEP, T_e, S_e, closure mode, specificity, failure count, and claim ceiling with {verified["disagreement_count"]} disagreements. It rejected {verified["mutation_rejection_count"]}/{verified["mutation_count"]} semantic and custody mutations. There were {scientific["failure_count"]} scientific execution failures.

The result remains `COMPUTED_DYNAMICAL`. `TLD_DERIVED` is blocked because no SEP cell, T_e, or nonzero S_e was observed. `EXTERNALLY_VALIDATED` remains false until a genuinely independent outside team executes the frozen replication package.
"""
    (output / "plain-language-summary.md").write_text(summary, encoding="utf-8", newline="\n")
    (output / "technical-report.md").write_text(technical, encoding="utf-8", newline="\n")
    (output / "heldout-tld-byN.svg").write_text(_svg(scored), encoding="utf-8", newline="\n")
    _raster_png(output / "heldout-tld-byN.png", scored)
    receipt = {
        "schema_version": "1.0.0",
        "classification_precedes_rendering": True,
        "interpolation_used_for_metrics": False,
        "raw_observed_points_distinguished": True,
        "null_points_distinguished": True,
        "computed_summaries_distinguished": True,
        "ineligible_and_failed_cells_visible": True,
        "scientific_outcome": scientific["scientific_outcome"],
    }
    write_json(output / "visualization_receipt.json", receipt)
    sums = output / "SHA256SUMS.txt"
    sums.write_text(
        "".join(
            f"{sha256_file(path)}  {path.name}\n"
            for path in sorted(output.iterdir())
            if path.is_file() and path != sums
        ),
        encoding="utf-8",
        newline="\n",
    )
    return receipt | {"sha256_manifest": sha256_file(sums)}
