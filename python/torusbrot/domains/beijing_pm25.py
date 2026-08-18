"""Registry-first adapter for the frozen Beijing PM2.5 held-out study."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import urllib.request
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from ..models import canonical_json

DOMAIN_ID = "uci-beijing-multisite-air-quality-pm25"
DOI = "10.24432/C5RK5G"
SOURCE_URL = "https://archive.ics.uci.edu/static/public/501/beijing+multi+site+air+quality+data.zip"
OUTER_SHA256 = "b04da438b2f331ac0ffd45aebdfec0d20d2367feb5f6948c4b1f7ce1191e33c4"
SOURCE_SHA256 = "d1b9261c54132f04c374f762f1e5e512af19f95c95fd6bfa1e8ac7e927e3b0b8"
SOURCE_FILENAME = "PRSA2017_Data_20130301-20170228.zip"
EXPECTED_COLUMNS = (
    "No",
    "year",
    "month",
    "day",
    "hour",
    "PM2.5",
    "PM10",
    "SO2",
    "NO2",
    "CO",
    "O3",
    "TEMP",
    "PRES",
    "DEWP",
    "RAIN",
    "wd",
    "WSPM",
    "station",
)
STATIONS = (
    "Aotizhongxin",
    "Changping",
    "Dingling",
    "Dongsi",
    "Guanyuan",
    "Gucheng",
    "Huairou",
    "Nongzhanguan",
    "Shunyi",
    "Tiantan",
    "Wanliu",
    "Wanshouxigong",
)
EXPECTED_HOURS = 35064
EXPECTED_DAYS = 1461
BASE_SEED = 20260818
NULL_COUNT = 127
PRIMARY_CONDITIONS = (
    "baseline",
    "calibration_scale_095",
    "calibration_scale_105",
    "sensor_noise_001",
    "outage_6h_30d",
    "outage_24h_90d",
)
DIAGNOSTIC_CONDITIONS = ("day_order_swap_010", "cyclic_adjacency")


@dataclass(frozen=True)
class ParentSource:
    station: str
    member: str
    member_sha256: str
    member_bytes: int
    raw_values: np.ndarray
    raw_text: tuple[str, ...]
    timestamps_local: tuple[datetime, ...]
    source_order_valid: bool
    duplicate_count: int
    invalid_value_count: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value, pretty=True))


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        for row in rows:
            stream.write(canonical_json(row))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fetch_authoritative_source(output: Path) -> dict[str, Any]:
    """Fetch the registered UCI bytes and extract the authoritative nested archive."""
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    outer = output.with_name("beijing_multi_site_air_quality_data.zip")
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "torusbrot/0.2.1"})
    with urllib.request.urlopen(request, timeout=120) as response, outer.open("wb") as stream:
        while chunk := response.read(1024 * 1024):
            stream.write(chunk)
    outer_hash = sha256_file(outer)
    if outer_hash != OUTER_SHA256:
        raise ValueError(f"outer source SHA-256 mismatch: {outer_hash}")
    with zipfile.ZipFile(outer) as archive:
        names = [name for name in archive.namelist() if name.endswith(SOURCE_FILENAME)]
        if len(names) != 1:
            raise ValueError("registered nested source archive is missing or ambiguous")
        payload = archive.read(names[0])
    if sha256_bytes(payload) != SOURCE_SHA256:
        raise ValueError("authoritative nested source SHA-256 mismatch")
    output.write_bytes(payload)
    return {
        "source_url": SOURCE_URL,
        "doi": DOI,
        "outer_path": str(outer),
        "outer_sha256": outer_hash,
        "authoritative_path": str(output),
        "authoritative_sha256": SOURCE_SHA256,
        "bytes": len(payload),
    }


def verify_preregistration(study_root: Path) -> dict[str, str]:
    manifest = study_root / "preregistration" / "preregistration_sha256.txt"
    repository_root = study_root.parents[1]
    verified: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        candidate = repository_root / Path(relative)
        actual = sha256_file(candidate)
        if actual != expected:
            raise ValueError(f"preregistration hash mismatch: {relative}")
        verified[relative] = actual
    return verified


def _safe_csv_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members: list[zipfile.ZipInfo] = []
    for info in archive.infolist():
        normalized = info.filename.replace("\\", "/")
        path = Path(normalized)
        if path.is_absolute() or ".." in path.parts or ":" in normalized:
            raise ValueError(f"unsafe source member: {info.filename}")
        if not info.is_dir() and normalized.lower().endswith(".csv"):
            members.append(info)
    if len(members) != len(STATIONS):
        raise ValueError(f"expected {len(STATIONS)} station CSV members, got {len(members)}")
    return sorted(members, key=lambda value: value.filename)


def _station_from_member(name: str) -> str:
    matches = [station for station in STATIONS if f"Data_{station}_" in name]
    if len(matches) != 1:
        raise ValueError(f"cannot identify registered station from {name}")
    return matches[0]


def _parse_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> ParentSource:
    payload = archive.read(info)
    station = _station_from_member(info.filename)
    text = io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8-sig", newline="")
    reader = csv.DictReader(text)
    if tuple(reader.fieldnames or ()) != EXPECTED_COLUMNS:
        raise ValueError(f"unexpected schema in {info.filename}")
    values: list[float] = []
    raw_text: list[str] = []
    timestamps: list[datetime] = []
    invalid_value_count = 0
    station_mismatch = 0
    for row in reader:
        timestamp = datetime(int(row["year"]), int(row["month"]), int(row["day"]), int(row["hour"]))
        timestamps.append(timestamp)
        token = row["PM2.5"].strip()
        raw_text.append(token)
        if not token or token.upper() in {"NA", "NAN"}:
            values.append(math.nan)
        else:
            value = float(token)
            if not math.isfinite(value) or value < 0:
                invalid_value_count += 1
            values.append(value)
        station_mismatch += row["station"] != station
    if station_mismatch:
        raise ValueError(f"station label mismatch in {info.filename}: {station_mismatch}")
    duplicate_count = len(timestamps) - len(set(timestamps))
    source_order_valid = all(
        right - left == timedelta(hours=1) for left, right in zip(timestamps, timestamps[1:])
    )
    return ParentSource(
        station=station,
        member=info.filename,
        member_sha256=sha256_bytes(payload),
        member_bytes=len(payload),
        raw_values=np.asarray(values, dtype=np.float64),
        raw_text=tuple(raw_text),
        timestamps_local=tuple(timestamps),
        source_order_valid=source_order_valid,
        duplicate_count=duplicate_count,
        invalid_value_count=invalid_value_count,
    )


def load_sources(source: Path) -> list[ParentSource]:
    if sha256_file(source) != SOURCE_SHA256:
        raise ValueError("authoritative source SHA-256 does not match the selection freeze")
    with zipfile.ZipFile(source) as archive:
        parents = [_parse_member(archive, info) for info in _safe_csv_members(archive)]
    parents.sort(key=lambda value: value.station)
    if tuple(parent.station for parent in parents) != STATIONS:
        raise ValueError("station registry does not match the frozen parent contract")
    return parents


def _month_year_groups(timestamps: tuple[datetime, ...]) -> list[np.ndarray]:
    grouped: dict[tuple[int, int], list[int]] = {}
    for day_index in range(EXPECTED_DAYS):
        timestamp = timestamps[day_index * 24]
        grouped.setdefault((timestamp.year, timestamp.month), []).append(day_index)
    return [np.asarray(indices, dtype=np.int16) for indices in grouped.values()]


def _array_hash(values: np.ndarray) -> str:
    normalized = np.asarray(values, dtype="<f8").copy()
    normalized[np.isnan(normalized)] = np.nan
    return sha256_bytes(normalized.tobytes(order="C"))


def canonicalize(
    hourly: np.ndarray, timestamps: tuple[datetime, ...]
) -> tuple[np.ndarray, dict[str, Any]]:
    if hourly.size != EXPECTED_HOURS:
        raise ValueError(f"expected {EXPECTED_HOURS} hourly values")
    logged = np.where(np.isfinite(hourly), np.log1p(hourly), np.nan)
    daily = np.full(EXPECTED_DAYS, np.nan, dtype=np.float64)
    for day_index in range(EXPECTED_DAYS):
        day = logged[day_index * 24 : (day_index + 1) * 24]
        finite = day[np.isfinite(day)]
        if finite.size >= 18:
            daily[day_index] = float(np.median(finite))
    residual = daily.copy()
    month_medians: dict[str, float | None] = {}
    for month in range(1, 13):
        indices = np.asarray(
            [index for index in range(EXPECTED_DAYS) if timestamps[index * 24].month == month]
        )
        finite = daily[indices][np.isfinite(daily[indices])]
        median = float(np.median(finite)) if finite.size else math.nan
        month_medians[str(month)] = median if math.isfinite(median) else None
        residual[indices] -= median
    finite_residual = residual[np.isfinite(residual)]
    center = float(np.median(finite_residual)) if finite_residual.size else math.nan
    mad = float(np.median(np.abs(finite_residual - center))) if finite_residual.size else math.nan
    scale = 1.4826 * mad
    canonical = residual / scale if math.isfinite(scale) and scale > 1e-12 else residual * math.nan
    return canonical, {
        "eligible_daily_count": int(np.count_nonzero(np.isfinite(daily))),
        "eligible_daily_fraction": float(np.mean(np.isfinite(daily))),
        "month_medians_log1p": month_medians,
        "residual_center": center if math.isfinite(center) else None,
        "residual_mad": mad if math.isfinite(mad) else None,
        "robust_scale": scale if math.isfinite(scale) else None,
        "canonical_sha256": _array_hash(canonical),
    }


def _condition_hourly(parent: ParentSource, condition: str, station_index: int) -> np.ndarray:
    values = parent.raw_values.copy()
    if condition == "baseline" or condition == "cyclic_adjacency":
        return values
    if condition == "calibration_scale_095":
        values[np.isfinite(values)] *= 0.95
    elif condition == "calibration_scale_105":
        values[np.isfinite(values)] *= 1.05
    elif condition == "sensor_noise_001":
        finite = values[np.isfinite(values)]
        median = float(np.median(finite))
        mad = float(np.median(np.abs(finite - median)))
        rng = np.random.default_rng(BASE_SEED + 3000000 + station_index)
        noise = rng.normal(0.0, 0.01 * mad, values.size)
        mask = np.isfinite(values)
        values[mask] = np.maximum(0.0, values[mask] + noise[mask])
    elif condition == "outage_6h_30d":
        for day_index in range(0, EXPECTED_DAYS, 30):
            values[day_index * 24 : day_index * 24 + 6] = np.nan
    elif condition == "outage_24h_90d":
        for day_index in range(0, EXPECTED_DAYS, 90):
            values[day_index * 24 : (day_index + 1) * 24] = np.nan
    elif condition == "day_order_swap_010":
        records = values.reshape(EXPECTED_DAYS, 24).copy()
        groups = _month_year_groups(parent.timestamps_local)
        rng = np.random.default_rng(BASE_SEED + 4000000 + station_index)
        for indices in groups:
            pair_count = math.floor(0.10 * len(indices) / 2)
            selected = rng.permutation(indices)[: pair_count * 2]
            for offset in range(0, len(selected), 2):
                left, right = int(selected[offset]), int(selected[offset + 1])
                records[[left, right]] = records[[right, left]]
        values = records.reshape(EXPECTED_HOURS)
    else:
        raise ValueError(f"unregistered condition: {condition}")
    return values


def _null_permutations(parent: ParentSource, station_index: int) -> np.ndarray:
    groups = _month_year_groups(parent.timestamps_local)
    mappings = np.tile(np.arange(EXPECTED_DAYS, dtype=np.int16), (NULL_COUNT, 1))
    for child_offset in range(NULL_COUNT):
        rng = np.random.default_rng(BASE_SEED + station_index * 10000 + child_offset + 1)
        for indices in groups:
            mappings[child_offset, indices] = rng.permutation(indices)
    return mappings


def _parent_eligible(
    parent: ParentSource, canonical_audit: dict[str, Any]
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if parent.raw_values.size != EXPECTED_HOURS:
        reasons.append("PARENT_RAW_ROW_COUNT_INVALID")
    if not parent.source_order_valid:
        reasons.append("PARENT_HOURLY_COVERAGE_INVALID")
    if parent.duplicate_count:
        reasons.append("PARENT_DUPLICATE_TIMESTAMP")
    if parent.invalid_value_count:
        reasons.append("PARENT_VALUE_INVALID")
    finite_fraction = float(np.mean(np.isfinite(parent.raw_values)))
    if finite_fraction < 0.90:
        reasons.append("PARENT_HOURLY_FINITE_FRACTION_LOW")
    if float(canonical_audit["eligible_daily_fraction"]) < 0.90:
        reasons.append("PARENT_DAILY_FINITE_FRACTION_LOW")
    scale = canonical_audit["robust_scale"]
    if not isinstance(scale, int | float) or not math.isfinite(scale) or scale <= 1e-12:
        reasons.append("PARENT_ROBUST_SCALE_INVALID")
    return not reasons, reasons


def _hash_manifest(root: Path, name: str, *, exclude: set[str] | None = None) -> Path:
    exclude = exclude or set()
    target = root / name
    rows: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path == target or path.name in exclude:
            continue
        rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}\n")
    target.write_text("".join(rows), encoding="utf-8", newline="\n")
    return target


def materialize(source: Path, study_root: Path, output: Path) -> dict[str, Any]:
    """Materialize all parents, perturbations and null identities without metrics."""
    preregistration_hashes = verify_preregistration(study_root)
    source = source.resolve()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    parents = load_sources(source)
    contract_hash = sha256_file(study_root / "preregistration" / "preregistration_sha256.txt")
    canonicalization_hash = sha256_file(study_root / "domain" / "canonicalization_contract.json")

    raw_manifest: list[dict[str, Any]] = []
    parent_rows: list[dict[str, Any]] = []
    daily_rows: list[dict[str, Any]] = []
    value_rows: list[dict[str, Any]] = []
    perturbation_rows: list[dict[str, Any]] = []
    ladder_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    arrays: dict[str, np.ndarray] = {}
    canonical_audits: dict[str, dict[str, Any]] = {}

    for station_index, parent in enumerate(parents):
        raw_manifest.append(
            {
                "source_id": f"uci501:{parent.station}",
                "station": parent.station,
                "archive_sha256": SOURCE_SHA256,
                "member": parent.member,
                "member_sha256": parent.member_sha256,
                "member_bytes": parent.member_bytes,
                "row_count": int(parent.raw_values.size),
            }
        )
        baseline, baseline_audit = canonicalize(parent.raw_values, parent.timestamps_local)
        canonical_audits[parent.station] = baseline_audit
        eligible, reasons = _parent_eligible(parent, baseline_audit)
        finite_fraction = float(np.mean(np.isfinite(parent.raw_values)))
        parent_rows.append(
            {
                "parent_id": f"station:{parent.station}",
                "domain_id": DOMAIN_ID,
                "station": parent.station,
                "station_index": station_index,
                "member": parent.member,
                "member_sha256": parent.member_sha256,
                "raw_rows": int(parent.raw_values.size),
                "finite_hourly_count": int(np.count_nonzero(np.isfinite(parent.raw_values))),
                "finite_hourly_fraction": finite_fraction,
                "eligible_daily_count": baseline_audit["eligible_daily_count"],
                "eligible_daily_fraction": baseline_audit["eligible_daily_fraction"],
                "duplicate_count": parent.duplicate_count,
                "source_order_valid": parent.source_order_valid,
                "eligible": eligible,
                "reason_codes": ";".join(reasons),
            }
        )
        for reason in reasons:
            failure_rows.append(
                {
                    "failure_id": f"materialize:{parent.station}:{reason}",
                    "category": "MATERIALIZATION_FAILURE",
                    "stage": "parent_eligibility",
                    "station": parent.station,
                    "issue_code": reason,
                    "message": reason,
                }
            )
        for row_index, (timestamp, raw_token, value) in enumerate(
            zip(parent.timestamps_local, parent.raw_text, parent.raw_values, strict=True)
        ):
            utc = timestamp - timedelta(hours=8)
            value_rows.append(
                {
                    "station": parent.station,
                    "source_row": row_index + 1,
                    "timestamp_local": timestamp.isoformat(timespec="hours"),
                    "timestamp_utc": utc.isoformat(timespec="hours") + "Z",
                    "pm25_raw_text": raw_token,
                    "pm25_ug_m3": "" if not math.isfinite(value) else format(float(value), ".17g"),
                    "observed": math.isfinite(value),
                }
            )
        permutations = _null_permutations(parent, station_index)
        arrays[f"permutation__{parent.station}"] = permutations
        condition_names = PRIMARY_CONDITIONS + ("day_order_swap_010",)
        condition_values: dict[str, np.ndarray] = {}
        for condition in condition_names:
            hourly = _condition_hourly(parent, condition, station_index)
            canonical, audit = canonicalize(hourly, parent.timestamps_local)
            condition_values[condition] = canonical
            arrays[f"canonical__{condition}__{parent.station}"] = canonical
            perturbation_rows.append(
                {
                    "perturbation_id": f"{parent.station}:{condition}",
                    "parent_id": f"station:{parent.station}",
                    "family": condition,
                    "role": "primary_survival" if condition in PRIMARY_CONDITIONS else "diagnostic",
                    "seed": (
                        BASE_SEED + 3000000 + station_index
                        if condition == "sensor_noise_001"
                        else BASE_SEED + 4000000 + station_index
                        if condition == "day_order_swap_010"
                        else ""
                    ),
                    "canonical_sha256": audit["canonical_sha256"],
                    "eligible_daily_count": audit["eligible_daily_count"],
                    "eligible": eligible and audit["eligible_daily_fraction"] >= 0.90,
                }
            )
        condition_values["cyclic_adjacency"] = condition_values["baseline"]
        arrays[f"canonical__cyclic_adjacency__{parent.station}"] = condition_values["baseline"]
        perturbation_rows.append(
            {
                "perturbation_id": f"{parent.station}:cyclic_adjacency",
                "parent_id": f"station:{parent.station}",
                "family": "cyclic_adjacency",
                "role": "diagnostic",
                "seed": "",
                "canonical_sha256": _array_hash(condition_values["baseline"]),
                "eligible_daily_count": baseline_audit["eligible_daily_count"],
                "eligible": eligible,
            }
        )
        for day_index in range(EXPECTED_DAYS):
            local_day = parent.timestamps_local[day_index * 24].date().isoformat()
            daily_rows.append(
                {
                    "station": parent.station,
                    "local_date": local_day,
                    "canonical_value": (
                        ""
                        if not math.isfinite(baseline[day_index])
                        else format(float(baseline[day_index]), ".17g")
                    ),
                    "observed": math.isfinite(baseline[day_index]),
                }
            )
        for condition in PRIMARY_CONDITIONS + DIAGNOSTIC_CONDITIONS:
            topology = "cyclic" if condition == "cyclic_adjacency" else "linear"
            observed_id = f"ladder:{parent.station}:{condition}:observed"
            observed_values = condition_values[condition]
            observed_eligible = eligible and np.mean(np.isfinite(observed_values)) >= 0.90
            ladder_rows.append(
                {
                    "ladder_id": observed_id,
                    "domain_id": DOMAIN_ID,
                    "kind": "observed",
                    "parent_ladder_id": "",
                    "omega_construction_rule": "frozen_daily_pm25_canonicalization",
                    "adjacency_topology": topology,
                    "is_null": False,
                    "null_family": "",
                    "perturbation_family": condition,
                    "strength": 0.0 if condition == "baseline" else 1.0,
                    "variant": "observed",
                    "eligible": observed_eligible,
                    "seed": "",
                    "source_values_hash": _array_hash(observed_values),
                    "canonicalization_hash": canonicalization_hash,
                    "contract_hash": contract_hash,
                    "notes": "registered before metrics",
                }
            )
            for child_offset, mapping in enumerate(permutations, start=1):
                child_values = observed_values[mapping]
                ladder_rows.append(
                    {
                        "ladder_id": f"ladder:{parent.station}:{condition}:null:{child_offset:03d}",
                        "domain_id": DOMAIN_ID,
                        "kind": "matched_null",
                        "parent_ladder_id": observed_id,
                        "omega_construction_rule": (
                            "frozen_daily_pm25_canonicalization_then_registered_permutation"
                        ),
                        "adjacency_topology": topology,
                        "is_null": True,
                        "null_family": "within_year_month_complete_day_permutation",
                        "perturbation_family": condition,
                        "strength": 0.0 if condition == "baseline" else 1.0,
                        "variant": f"child_{child_offset:03d}",
                        "eligible": observed_eligible,
                        "seed": BASE_SEED + station_index * 10000 + child_offset,
                        "source_values_hash": _array_hash(child_values),
                        "canonicalization_hash": canonicalization_hash,
                        "contract_hash": contract_hash,
                        "notes": "parent-local; registered before metrics",
                    }
                )

    write_jsonl(output / "domain_raw_manifest.jsonl", raw_manifest)
    write_csv(output / "domain_values.csv", list(value_rows[0]), value_rows)
    write_json(
        output / "domain_canonicalization.json",
        {
            "schema_version": "1.0.0",
            "contract_sha256": canonicalization_hash,
            "parents": canonical_audits,
            "metrics_computed": False,
        },
    )
    write_csv(output / "domain_features.csv", list(daily_rows[0]), daily_rows)
    write_csv(output / "parent_registry.csv", list(parent_rows[0]), parent_rows)
    write_csv(output / "ladder_registry.csv", list(ladder_rows[0]), ladder_rows)
    write_csv(output / "perturbation_registry.csv", list(perturbation_rows[0]), perturbation_rows)
    write_jsonl(output / "failure_ledger.jsonl", failure_rows)
    np.savez_compressed(output / "registered_arrays.npz", **arrays)
    expected_ladders = (
        len(STATIONS) * len(PRIMARY_CONDITIONS + DIAGNOSTIC_CONDITIONS) * (NULL_COUNT + 1)
    )
    null_audit = {
        "schema_version": "1.0.0",
        "family": "within_year_month_complete_day_permutation",
        "parent_count": len(parents),
        "children_per_parent_condition": NULL_COUNT,
        "condition_count": len(PRIMARY_CONDITIONS + DIAGNOSTIC_CONDITIONS),
        "registered_ladder_count": len(ladder_rows),
        "expected_ladder_count": expected_ladders,
        "all_children_registered_before_metrics": len(ladder_rows) == expected_ladders,
        "global_pool_used": False,
        "replacement_sampling_used": False,
        "metric_functions_called": False,
    }
    write_json(output / "null_generation_audit.json", null_audit)
    eligibility_audit = {
        "schema_version": "1.0.0",
        "eligible_parent_count": sum(bool(row["eligible"]) for row in parent_rows),
        "ineligible_parent_count": sum(not bool(row["eligible"]) for row in parent_rows),
        "minimum_required": 10,
        "population_endpoint_materializable": sum(bool(row["eligible"]) for row in parent_rows)
        >= 10,
        "parents": parent_rows,
    }
    write_json(output / "eligibility_audit.json", eligibility_audit)
    contamination_audit = {
        "schema_version": "1.0.0",
        "candidate_matches_selection_freeze": True,
        "source_sha256_matches": True,
        "preregistration_files_verified": len(preregistration_hashes),
        "outcome_labels_used": False,
        "cross_parent_pooling": False,
        "nulls_in_observed_registry": False,
        "observed_metrics_computed": False,
        "candidate_substitution": False,
    }
    write_json(output / "contamination_prevention_audit.json", contamination_audit)
    receipt = {
        "schema_version": "1.0.0",
        "stage": "REGISTRY_FIRST_MATERIALIZATION_COMPLETE",
        "source": str(source),
        "source_sha256": SOURCE_SHA256,
        "contract_manifest_sha256": contract_hash,
        "parent_count": len(parent_rows),
        "eligible_parent_count": eligibility_audit["eligible_parent_count"],
        "ladder_count": len(ladder_rows),
        "null_child_count": sum(bool(row["is_null"]) for row in ladder_rows),
        "perturbation_count": len(perturbation_rows),
        "failure_count": len(failure_rows),
        "metrics_computed": False,
        "ready_for_scored_run_authorization": (
            null_audit["all_children_registered_before_metrics"]
            and eligibility_audit["population_endpoint_materializable"]
        ),
    }
    write_json(output / "materialization_receipt.json", receipt)
    _hash_manifest(output, "SHA256SUMS_INPUTS.txt")
    return receipt


def registered_dates() -> np.ndarray:
    start = date(2013, 3, 1)
    return np.asarray(
        [(start + timedelta(days=index)).isoformat() for index in range(EXPECTED_DAYS)]
    )
