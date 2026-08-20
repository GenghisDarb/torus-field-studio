from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from statistics import median
from typing import Any

from .models import AuditReport, ClaimLevel, canonical_json, content_hash, validate_run_spec
from .schema_validation import validate_with_schema

REQUIRED_MEMBERS = frozenset(
    {
        "run_spec.json",
        "ontology.json",
        "claim_boundary.json",
        "visual_encoding.json",
        "scene_recipe.json",
        "provenance/sources.jsonl",
        "provenance/transformations.jsonl",
        "provenance/verification_receipts.jsonl",
        "registry/parent_registry.json",
        "registry/null_registry.json",
        "tables/field_points.json",
        "tables/metrics_by_N.json",
        "audit/audit.json",
        "audit/failure_ledger.jsonl",
        "audit/SHA256SUMS.txt",
    }
)
TLD_REQUIRED_MEMBERS = frozenset(
    {
        "source_registry.json",
        "preregistration_contract.json",
        "tld_profile.json",
        "registry/ladder_registry.json",
        "registry/control_or_null_registry.json",
        "tables/tld_endpoint_table.json",
        "tables/baseline_scores.json",
        "tables/alpha_sweep.json",
        "tables/core_alpha_compare.json",
        "tables/preregistration_results.json",
        "tables/trajectories.jsonl",
        "tables/transition_counts.json",
        "tables/operating_envelope.json",
        "audit/independent_verification.json",
        "audit/claim_adjudication.json",
    }
)
HELDOUT_REQUIRED_MEMBERS = frozenset(
    {
        "heldout_profile.json",
        "source_registry.json",
        "domain_translation.json",
        "preregistration.json",
        "registry/parent_registry.csv",
        "registry/ladder_registry.csv",
        "registry/null_registry.csv",
        "registry/perturbation_registry.csv",
        "tables/byN_surface.csv",
        "tables/emergent_time_by_parent.csv",
        "tables/emergent_scale_by_parent.csv",
        "tables/primary_endpoints.json",
        "tables/closure_mode_results.csv",
        "tables/parent_null_comparison.csv",
        "tables/structured_fragility_results.csv",
        "tables/specificity_audit.csv",
        "tables/domain_baseline_comparison.csv",
        "audit/independent_verification.json",
        "audit/independent_recomputed_endpoints.json",
        "audit/mutation_results.jsonl",
        "audit/claim_adjudication.json",
        "audit/forbidden_claims.json",
        "reports/plain_language_summary.md",
        "reports/technical_report.md",
        "visualization/byN_surface.svg",
        "visualization/byN_surface.png",
    }
)
GEOMETRY_REQUIRED_MEMBERS = frozenset(
    {
        "geometry_profile.json",
        "source_registry.json",
        "ontology.json",
        "claim_boundary.json",
        "visual_encoding.json",
        "scene_recipe.json",
        "provenance/sources.jsonl",
        "provenance/transformations.jsonl",
        "provenance/verification_receipts.jsonl",
        "provenance/raw_array_custody.json",
        "arrays/registered_binned_fields.npz",
        "registry/parent_registry.jsonl",
        "registry/projection_registry.jsonl",
        "registry/null_registry.jsonl",
        "tables/geometry_channel_results.json",
        "tables/scale_behavior.json",
        "tables/domain_baseline.json",
        "audit/independent_verification.json",
        "audit/claim_adjudication.json",
        "audit/forbidden_claims.json",
        "audit/failure_ledger.jsonl",
        "audit/SHA256SUMS.txt",
    }
)
TLD_I_INPUT_HASHES = {
    "targets_baseline.csv": "856f102a4f58d53d67fdb1ac5982de12ca18a9c78efe13097f23879e262cb683",
    "targets_metadata_addon.csv": (
        "dfba2dc563706d284313f27e679132d028ea77c49a8816cff944baef13dd135f"
    ),
    "targets_metadata_template.csv": (
        "49a536790c6920a6627f903062e0c0d4ce831acd167173ea1a366b7139f980e3"
    ),
}


@dataclass(frozen=True)
class BundlePolicy:
    max_files: int = 256
    max_member_bytes: int = 64 * 1024 * 1024
    max_total_bytes: int = 256 * 1024 * 1024
    max_json_bytes: int = 16 * 1024 * 1024
    max_json_depth: int = 32
    max_compression_ratio: float = 200.0


DEFAULT_POLICY = BundlePolicy()


class BundleRejected(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = tuple(errors)


def _issue(code: str, detail: str) -> str:
    return f"{code}: {detail}"


def _canonical_member_path(name: str, *, directory: bool = False) -> bool:
    candidate = name[:-1] if directory and name.endswith("/") else name
    if not candidate or "\\" in candidate or "\x00" in candidate:
        return False
    if candidate.startswith("/") or candidate.endswith("/") or "//" in candidate:
        return False
    if re.match(r"^[A-Za-z]:", candidate):
        return False
    path = PurePosixPath(candidate)
    return not path.is_absolute() and all(part not in {"", ".", ".."} for part in path.parts)


def _preflight_zip(path: Path, policy: BundlePolicy) -> list[zipfile.ZipInfo]:
    errors: list[str] = []
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise BundleRejected([_issue("ARCHIVE_INVALID", str(error))]) from error
    with archive:
        infos = archive.infolist()
        file_infos = [info for info in infos if not info.is_dir()]
        names = [info.filename for info in file_infos]
        duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
        if duplicates:
            errors.append(_issue("ARCHIVE_DUPLICATE_MEMBER", ", ".join(duplicates)))
        if len(file_infos) > policy.max_files:
            errors.append(
                _issue("ARCHIVE_FILE_LIMIT", f"{len(file_infos)} files exceeds {policy.max_files}")
            )
        total = 0
        for info in infos:
            if not _canonical_member_path(info.filename, directory=info.is_dir()):
                errors.append(_issue("ARCHIVE_PATH_INVALID", info.filename))
            if info.is_dir():
                continue
            if info.flag_bits & 0x1:
                errors.append(_issue("ARCHIVE_ENCRYPTED_MEMBER", info.filename))
            total += info.file_size
            if info.file_size > policy.max_member_bytes:
                errors.append(
                    _issue(
                        "ARCHIVE_MEMBER_LIMIT",
                        f"{info.filename} is {info.file_size} bytes",
                    )
                )
            ratio = (
                math.inf
                if info.compress_size == 0 and info.file_size
                else (info.file_size / max(info.compress_size, 1))
            )
            if ratio > policy.max_compression_ratio:
                errors.append(
                    _issue(
                        "ARCHIVE_COMPRESSION_RATIO",
                        f"{info.filename} ratio {ratio:.1f} exceeds {policy.max_compression_ratio}",
                    )
                )
        if total > policy.max_total_bytes:
            errors.append(_issue("ARCHIVE_TOTAL_LIMIT", f"{total} bytes exceeds limit"))
        if errors:
            raise BundleRejected(errors)
        return file_infos


def _read_zip(path: Path, policy: BundlePolicy) -> dict[str, bytes]:
    infos = _preflight_zip(path, policy)
    with zipfile.ZipFile(path) as archive:
        return {info.filename: archive.read(info) for info in infos}


def _read_directory(path: Path, policy: BundlePolicy) -> dict[str, bytes]:
    errors: list[str] = []
    members: dict[str, bytes] = {}
    total = 0
    files = [member for member in path.rglob("*") if member.is_file() or member.is_symlink()]
    if len(files) > policy.max_files:
        errors.append(_issue("ARCHIVE_FILE_LIMIT", f"{len(files)} files exceeds limit"))
    for member in files:
        name = str(member.relative_to(path)).replace("\\", "/")
        if member.is_symlink():
            errors.append(_issue("ARCHIVE_SYMLINK", name))
            continue
        if not _canonical_member_path(name):
            errors.append(_issue("ARCHIVE_PATH_INVALID", name))
            continue
        size = member.stat().st_size
        total += size
        if size > policy.max_member_bytes:
            errors.append(_issue("ARCHIVE_MEMBER_LIMIT", f"{name} is {size} bytes"))
            continue
        members[name] = member.read_bytes()
    if total > policy.max_total_bytes:
        errors.append(_issue("ARCHIVE_TOTAL_LIMIT", f"{total} bytes exceeds limit"))
    if errors:
        raise BundleRejected(errors)
    return members


def read_bundle_members(
    source: str | Path,
    policy: BundlePolicy = DEFAULT_POLICY,
) -> dict[str, bytes]:
    path = Path(source)
    if path.is_dir():
        return _read_directory(path, policy)
    return _read_zip(path, policy)


def _json_depth(value: Any, depth: int = 0) -> int:
    if isinstance(value, dict):
        return max([depth, *(_json_depth(item, depth + 1) for item in value.values())])
    if isinstance(value, list):
        return max([depth, *(_json_depth(item, depth + 1) for item in value)])
    return depth


def _contains_nonfinite(value: Any) -> bool:
    if isinstance(value, bool | str) or value is None:
        return False
    if isinstance(value, int):
        return False
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, dict):
        return any(_contains_nonfinite(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_nonfinite(item) for item in value)
    return False


def _load_json(
    members: dict[str, bytes],
    name: str,
    errors: list[str],
    policy: BundlePolicy,
) -> Any | None:
    payload = members.get(name)
    if payload is None:
        return None
    if len(payload) > policy.max_json_bytes:
        errors.append(_issue("JSON_SIZE_LIMIT", name))
        return None
    try:
        value = json.loads(
            payload.decode("utf-8"),
            parse_constant=lambda constant: (_ for _ in ()).throw(
                ValueError(f"nonfinite constant {constant}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        errors.append(_issue("JSON_INVALID", f"{name}: {error}"))
        return None
    if _json_depth(value) > policy.max_json_depth:
        errors.append(_issue("JSON_DEPTH_LIMIT", name))
        return None
    if _contains_nonfinite(value):
        errors.append(_issue("JSON_NONFINITE", name))
        return None
    return value


def _load_jsonl(
    members: dict[str, bytes],
    name: str,
    errors: list[str],
    policy: BundlePolicy,
) -> list[dict[str, Any]]:
    payload = members.get(name, b"")
    if len(payload) > policy.max_json_bytes:
        errors.append(_issue("JSON_SIZE_LIMIT", name))
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(payload.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            errors.append(_issue("JSONL_INVALID", f"{name}:{line_number}: {error}"))
            continue
        if (
            not isinstance(row, dict)
            or _json_depth(row) > policy.max_json_depth
            or _contains_nonfinite(row)
        ):
            errors.append(_issue("JSONL_INVALID", f"{name}:{line_number}"))
            continue
        rows.append(row)
    return rows


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _audit_manifest(
    members: dict[str, bytes],
    manifest: Any,
    errors: list[str],
) -> int:
    if not isinstance(manifest, dict):
        errors.append(_issue("MANIFEST_INVALID", "manifest must be an object"))
        return 0
    for validation_error in validate_with_schema("tbx", manifest):
        errors.append(_issue("MANIFEST_SCHEMA_INVALID", validation_error))
    if members["manifest.json"] != canonical_json(manifest, pretty=True):
        errors.append(_issue("MANIFEST_NONCANONICAL", "manifest bytes are not canonical JSON"))
    if manifest.get("tbx_version") != "1.0.0":
        errors.append(_issue("SCHEMA_VERSION_UNSUPPORTED", "tbx_version"))
    entries = manifest.get("files")
    if not isinstance(entries, list):
        errors.append(_issue("MANIFEST_INVALID", "files must be an array"))
        return 0
    paths: list[str] = []
    checked = 0
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "bytes"}:
            errors.append(_issue("MANIFEST_ENTRY_INVALID", repr(entry)))
            continue
        name = entry.get("path")
        if not isinstance(name, str) or not _canonical_member_path(name):
            errors.append(_issue("MANIFEST_PATH_INVALID", repr(name)))
            continue
        paths.append(name)
        payload = members.get(name)
        if payload is None:
            errors.append(_issue("MANIFEST_MEMBER_MISSING", name))
            continue
        checked += 1
        if entry.get("bytes") != len(payload):
            errors.append(_issue("MANIFEST_SIZE_MISMATCH", name))
        if entry.get("sha256") != _sha256(payload):
            errors.append(_issue("MANIFEST_HASH_MISMATCH", name))
    duplicates = sorted(name for name, count in Counter(paths).items() if count > 1)
    if duplicates:
        errors.append(_issue("MANIFEST_DUPLICATE_ENTRY", ", ".join(duplicates)))
    if paths != sorted(paths):
        errors.append(_issue("MANIFEST_ORDER_INVALID", "file entries must be sorted"))
    expected = set(paths) | {"manifest.json"}
    extras = sorted(set(members) - expected)
    if extras:
        errors.append(_issue("MANIFEST_UNLISTED_MEMBER", ", ".join(extras)))
    profile = str(manifest.get("profile", ""))
    if profile == "geometry-pilot-v0.3.0":
        required = set(GEOMETRY_REQUIRED_MEMBERS)
    else:
        required = set(REQUIRED_MEMBERS)
        if profile.startswith("tld-i-"):
            required.update(TLD_REQUIRED_MEMBERS)
        if profile.startswith("tld-heldout-"):
            required.update(HELDOUT_REQUIRED_MEMBERS)
    required_missing = sorted(required - set(paths))
    if required_missing:
        errors.append(_issue("REQUIRED_MEMBER_MISSING", ", ".join(required_missing)))
    return checked


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def _load_csv(
    members: dict[str, bytes], name: str, errors: list[str], policy: BundlePolicy
) -> list[dict[str, str]]:
    payload = members.get(name)
    if payload is None:
        errors.append(_issue("MEMBER_MISSING", name))
        return []
    if len(payload) > policy.max_json_bytes:
        errors.append(_issue("MEMBER_SIZE_LIMIT", name))
        return []
    try:
        text = payload.decode("utf-8")
        return list(csv.DictReader(io.StringIO(text, newline="")))
    except (UnicodeDecodeError, csv.Error) as error:
        errors.append(_issue("CSV_INVALID", f"{name}: {error}"))
        return []


def _sign_p(positive: int, total: int) -> float:
    return sum(math.comb(total, count) for count in range(positive, total + 1)) / (2**total)


def _holm(raw: dict[int, float]) -> dict[int, float]:
    ordered = sorted(raw.items(), key=lambda item: (item[1], item[0]))
    adjusted: dict[int, float] = {}
    running = 0.0
    for rank, (key, value) in enumerate(ordered):
        running = max(running, min(1.0, (len(ordered) - rank) * value))
        adjusted[key] = running
    return adjusted


def _audit_heldout_semantics(
    members: dict[str, bytes],
    manifest: dict[str, Any],
    claim: dict[str, Any],
    failures: list[dict[str, Any]],
    errors: list[str],
    policy: BundlePolicy,
) -> None:
    profile = _load_json(members, "heldout_profile.json", errors, policy)
    source = _load_json(members, "source_registry.json", errors, policy)
    preregistration = _load_json(members, "preregistration.json", errors, policy)
    endpoints = _load_json(members, "tables/primary_endpoints.json", errors, policy)
    independent = _load_json(members, "audit/independent_verification.json", errors, policy)
    recomputed = _load_json(members, "audit/independent_recomputed_endpoints.json", errors, policy)
    adjudication = _load_json(members, "audit/claim_adjudication.json", errors, policy)
    mutation_results = _load_jsonl(members, "audit/mutation_results.jsonl", errors, policy)
    parent_cells = _load_csv(members, "tables/parent_null_comparison.csv", errors, policy)
    surface = _load_csv(members, "tables/byN_surface.csv", errors, policy)
    closure = _load_csv(members, "tables/closure_mode_results.csv", errors, policy)
    parents = _load_csv(members, "registry/parent_registry.csv", errors, policy)
    nulls = _load_csv(members, "registry/null_registry.csv", errors, policy)
    perturbations = _load_csv(members, "registry/perturbation_registry.csv", errors, policy)
    if not all(
        isinstance(value, dict)
        for value in (
            profile,
            source,
            preregistration,
            endpoints,
            independent,
            recomputed,
            adjudication,
        )
    ):
        return
    if profile.get("profile") != manifest.get("profile"):
        errors.append(_issue("HELDOUT_PROFILE_MISMATCH", "manifest and profile"))
    if set(profile.get("required_members", [])) != set(HELDOUT_REQUIRED_MEMBERS):
        errors.append(_issue("HELDOUT_PROFILE_MEMBERS_INVALID", "required member declaration"))
    if profile.get("interpolation_used_for_metrics") is not False:
        errors.append(_issue("HELDOUT_INTERPOLATION_AS_OBSERVATION", "profile declaration"))
    if source.get("doi") != "10.24432/C5RK5G":
        errors.append(_issue("HELDOUT_SOURCE_DOI_MISMATCH", repr(source.get("doi"))))
    expected_source = "d1b9261c54132f04c374f762f1e5e512af19f95c95fd6bfa1e8ac7e927e3b0b8"
    if source.get("authoritative_archive_sha256") != expected_source:
        errors.append(_issue("HELDOUT_SOURCE_HASH_MISMATCH", "authoritative archive"))
    expected_prereg = "eb3a886aa3bc344ccf715d0036d5054cfba107aa3eae017ba00c68852bb73bfc"
    if profile.get("preregistration_manifest_sha256") != expected_prereg:
        errors.append(_issue("HELDOUT_PREREGISTRATION_HASH_MISMATCH", "profile"))
    if preregistration.get("selection_commit") != "2ff2ddb1a4f656d3c672079a6e8821bf9c3858eb":
        errors.append(_issue("HELDOUT_SELECTION_COMMIT_MISMATCH", "preregistration"))
    if (
        len(parents) != 12
        or sum(row.get("eligible", "").casefold() == "true" for row in parents) != 12
    ):
        errors.append(_issue("HELDOUT_PARENT_REGISTRY_INVALID", str(len(parents))))
    if len(nulls) != 12192:
        errors.append(_issue("HELDOUT_NULL_REGISTRY_COUNT_MISMATCH", str(len(nulls))))
    if any(row.get("null_family") != "within_year_month_complete_day_permutation" for row in nulls):
        errors.append(_issue("HELDOUT_GLOBAL_NULL_POOL_FORBIDDEN", "null registry"))
    if len(perturbations) != 96:
        errors.append(_issue("HELDOUT_PERTURBATION_REGISTRY_INVALID", str(len(perturbations))))

    grouped: dict[str, dict[int, list[dict[str, str]]]] = {}
    for row in parent_cells:
        if row.get("eligible", "").casefold() == "true":
            grouped.setdefault(row["condition"], {}).setdefault(int(row["N"]), []).append(row)
    recomputed_surface: dict[tuple[str, int], dict[str, Any]] = {}
    for condition, by_n in grouped.items():
        raw_p: dict[int, float] = {}
        staged: dict[int, tuple[float, float, int, int]] = {}
        for n_value, rows in by_n.items():
            ui = sum(float(row["local_p"]) <= 0.05 for row in rows) / len(rows)
            nss = median(float(row["robust_z"]) for row in rows)
            positive = sum(float(row["observed_score"]) > float(row["null_median"]) for row in rows)
            raw_p[n_value] = _sign_p(positive, len(rows))
            staged[n_value] = (ui, nss, positive, len(rows))
        adjusted = _holm(raw_p)
        for n_value, (ui, nss, positive, count) in staged.items():
            recomputed_surface[(condition, n_value)] = {
                "UI": ui,
                "NSS": nss,
                "positive_parent_count": positive,
                "eligible_parent_count": count,
                "holm_p": adjusted[n_value],
                "SEP": count >= 10 and ui >= 0.5 and nss >= 2 and adjusted[n_value] <= 0.05,
            }
    for row in surface:
        key = (row["condition"], int(row["N"]))
        expected = recomputed_surface.get(key)
        if expected is None:
            errors.append(_issue("HELDOUT_SURFACE_CELL_MISSING", repr(key)))
            continue
        for field in ("UI", "NSS", "holm_p"):
            if not math.isclose(float(row[field]), expected[field], rel_tol=0.0, abs_tol=1e-12):
                errors.append(_issue("HELDOUT_SURFACE_MISMATCH", f"{key}:{field}"))
        if (row["SEP"].casefold() == "true") != expected["SEP"]:
            errors.append(_issue("HELDOUT_SEP_MISMATCH", repr(key)))
    baseline_depths = [
        n_value
        for (condition, n_value), value in recomputed_surface.items()
        if condition == "baseline" and value["SEP"]
    ]
    t_e: int | str = min(baseline_depths) if baseline_depths else "NOT_OBSERVED"
    if endpoints.get("T_e") != t_e or recomputed.get("T_e") != t_e:
        errors.append(_issue("HELDOUT_TE_MISMATCH", repr(t_e)))
    primary_conditions = (
        "baseline",
        "calibration_scale_095",
        "calibration_scale_105",
        "sensor_noise_001",
        "outage_6h_30d",
        "outage_24h_90d",
    )
    region: list[int] = []
    if isinstance(t_e, int):
        for n_value in range(t_e, 15):
            survives = (
                recomputed_surface[("baseline", n_value)]["SEP"]
                and sum(
                    recomputed_surface[(condition, n_value)]["SEP"]
                    for condition in primary_conditions[1:]
                )
                >= 4
            )
            if not survives:
                break
            region.append(n_value)
    region_cells = [
        recomputed_surface[(condition, n_value)]
        for n_value in region
        for condition in primary_conditions
    ]
    s_e = sum(cell["SEP"] for cell in region_cells) / len(region_cells) if region_cells else 0.0
    if not math.isclose(float(endpoints.get("S_e_contiguous", -1)), s_e, abs_tol=1e-12):
        errors.append(_issue("HELDOUT_SE_MISMATCH", repr(s_e)))
    closure_by_station: dict[str, dict[int, float]] = {}
    for row in closure:
        closure_by_station.setdefault(row["station"], {})[int(row["N"])] = float(
            row["closure_error"]
        )
    medians = {
        n_value: median(values[n_value] for values in closure_by_station.values())
        for n_value in range(4, 21)
    }
    winner = min(medians, key=lambda key: (medians[key], key))
    if endpoints.get("winner_N_study_closure_minimum") != winner:
        errors.append(_issue("HELDOUT_WINNER_MISMATCH", repr(winner)))
    if independent.get("status") != "verified" or independent.get("disagreement_count") != 0:
        errors.append(_issue("HELDOUT_INDEPENDENT_VERIFICATION_FAILED", "receipt"))
    if len(mutation_results) != 25 or any(
        row.get("rejected") is not True for row in mutation_results
    ):
        errors.append(_issue("HELDOUT_MUTATION_SUITE_FAILED", str(len(mutation_results))))
    if adjudication.get("EXTERNALLY_VALIDATED") is not False:
        errors.append(_issue("HELDOUT_EXTERNAL_VALIDATION_FORBIDDEN", "adjudication"))
    expected_outcome = (
        "HELDOUT_TLD_STUDY_POSITIVE_UNDER_FROZEN_GATES"
        if isinstance(t_e, int) and s_e > 0
        else "HELDOUT_TLD_STUDY_NEGATIVE_UNDER_FROZEN_GATES"
    )
    if adjudication.get("scientific_outcome") != expected_outcome:
        errors.append(_issue("HELDOUT_ADJUDICATION_MISMATCH", expected_outcome))
    if claim.get("claim_level") != "COMPUTED_DYNAMICAL" and expected_outcome.endswith(
        "NEGATIVE_UNDER_FROZEN_GATES"
    ):
        errors.append(_issue("HELDOUT_NEGATIVE_CLAIM_ESCALATION", str(claim.get("claim_level"))))
    if len(failures) != int(endpoints.get("failure_count", 0)):
        errors.append(_issue("HELDOUT_FAILURE_COUNT_MISMATCH", str(len(failures))))


def _audit_tld_semantics(
    members: dict[str, bytes],
    manifest: dict[str, Any],
    claim: dict[str, Any],
    points: list[Any],
    failures: list[dict[str, Any]],
    errors: list[str],
    policy: BundlePolicy,
) -> None:
    source = _load_json(members, "source_registry.json", errors, policy)
    preregistration = _load_json(members, "preregistration_contract.json", errors, policy)
    profile = _load_json(members, "tld_profile.json", errors, policy)
    ladder_registry = _load_json(members, "registry/ladder_registry.json", errors, policy)
    endpoints = _load_json(members, "tables/tld_endpoint_table.json", errors, policy)
    independent = _load_json(members, "audit/independent_verification.json", errors, policy)
    adjudication = _load_json(members, "audit/claim_adjudication.json", errors, policy)
    trajectories = _load_jsonl(members, "tables/trajectories.jsonl", errors, policy)
    transitions = _load_json(members, "tables/transition_counts.json", errors, policy)
    core = _load_json(members, "tables/core_alpha_compare.json", errors, policy)
    controls = _load_json(members, "registry/control_or_null_registry.json", errors, policy)
    documents = {
        "tld-release-source": source,
        "tld-preregistration-result": preregistration,
        "tld-tbx-profile": profile,
        "tld-ladder-registry": ladder_registry,
        "tld-endpoint-table": endpoints,
        "tld-independent-verification": independent,
        "tld-claim-adjudication": adjudication,
        "tld-trajectory-trace": {"schema_version": "1.0.0", "rows": trajectories},
    }
    for schema, value in documents.items():
        if not isinstance(value, dict):
            errors.append(_issue("TLD_MEMBER_INVALID", schema))
            continue
        for validation_error in validate_with_schema(schema, value):
            errors.append(_issue("TLD_SCHEMA_INVALID", f"{schema}: {validation_error}"))
    if not all(isinstance(value, dict) for value in documents.values()):
        return
    if source.get("doi") != "10.5281/zenodo.18080090":
        errors.append(_issue("TLD_SOURCE_DOI_MISMATCH", repr(source.get("doi"))))
    if source.get("claim_authority_ceiling") != "COMPUTED_DYNAMICAL":
        errors.append(_issue("TLD_SOURCE_CLAIM_CEILING_INVALID", "source registry"))
    if source.get("input_sha256") != TLD_I_INPUT_HASHES:
        errors.append(_issue("TLD_SOURCE_INPUT_HASH_MISMATCH", "source registry"))
    if profile.get("profile") != manifest.get("profile"):
        errors.append(_issue("TLD_PROFILE_MISMATCH", "manifest and profile declaration"))
    declared_members = set(profile.get("required_members", []))
    if declared_members != set(TLD_REQUIRED_MEMBERS):
        errors.append(_issue("TLD_PROFILE_MEMBERS_INVALID", "required member declaration"))
    if profile.get("interpolation_used_for_metrics") is not False:
        errors.append(_issue("TLD_INTERPOLATION_AS_OBSERVATION", "profile declaration"))
    if independent.get("status") != "verified":
        errors.append(_issue("TLD_INDEPENDENT_VERIFICATION_FAILED", "receipt status"))
    independent_checks = independent.get("checks")
    if not isinstance(independent_checks, dict) or any(
        value is not True for value in independent_checks.values() if isinstance(value, bool)
    ):
        errors.append(_issue("TLD_INDEPENDENT_VERIFICATION_FAILED", "receipt checks"))
    if adjudication.get("externally_validated") is not False:
        errors.append(_issue("TLD_EXTERNAL_VALIDATION_FORBIDDEN", "claim adjudication"))
    if adjudication.get("claim_level") != claim.get("claim_level"):
        errors.append(_issue("TLD_CLAIM_ADJUDICATION_MISMATCH", "claim boundary"))
    if (
        manifest.get("claim_level") == "TLD_DERIVED"
        and adjudication.get("tld_derived_status") != "PERMITTED"
    ):
        errors.append(_issue("TLD_DERIVED_GATE_BLOCKED", "claim adjudication"))
    criteria = preregistration.get("criteria", {})
    if isinstance(criteria, dict):
        passed = sum(value is True for value in criteria.values())
        failed = sum(value is False for value in criteria.values())
        if preregistration.get("passed") != passed or preregistration.get("failed") != failed:
            errors.append(_issue("TLD_PREREGISTRATION_COUNT_MISMATCH", "criteria counts"))
        if isinstance(core, list) and len(core) == 2 and all(isinstance(row, dict) for row in core):
            alpha0, alpha002 = core
            expected_criteria = {
                "alpha0_escape_rate_at_least_0.90": alpha0.get("escape_rate", -1) >= 0.90,
                "alpha0_return_rate_at_most_0.40": alpha0.get("return_rate_given_escape", math.inf)
                <= 0.40,
                "alpha002_escape_rate_at_least_0.90": alpha002.get("escape_rate", -1) >= 0.90,
                "alpha002_return_rate_at_least_0.95": alpha002.get("return_rate_given_escape", -1)
                >= 0.95,
                "alpha002_mean_return_steps_at_most_120": alpha002.get(
                    "mean_return_steps", math.inf
                )
                <= 120,
                "alpha002_p90_flips_at_most_5": alpha002.get("p90_flips", math.inf) <= 5,
            }
            if criteria != expected_criteria:
                errors.append(_issue("TLD_PREREGISTRATION_OUTCOME_MISMATCH", "core results"))
            if [row.get("alpha_heal") for row in core] != [0.0, 0.02]:
                errors.append(_issue("TLD_PREREGISTRATION_CONTROL_MISMATCH", "alpha order"))
        else:
            errors.append(_issue("TLD_PREREGISTRATION_SOURCE_INVALID", "core results"))
    endpoint_rows = endpoints.get("rows", [])
    if isinstance(endpoint_rows, list):
        for index, row in enumerate(endpoint_rows):
            if isinstance(row, dict) and (row.get("T_e") is not None or row.get("S_e") is not None):
                errors.append(_issue("TLD_UNCOMPUTED_ENDPOINT_POPULATED", f"endpoint {index}"))
    seen_trace_rows: set[tuple[Any, Any, Any]] = set()
    grouped: dict[int, list[dict[str, Any]]] = {}
    for index, row in enumerate(trajectories):
        identity = (row.get("trial_id"), row.get("phase"), row.get("t"))
        if identity in seen_trace_rows:
            errors.append(_issue("TLD_TRAJECTORY_DUPLICATE", str(index)))
        seen_trace_rows.add(identity)
        if row.get("phase") == "heal" and isinstance(row.get("trial_id"), int):
            grouped.setdefault(row["trial_id"], []).append(row)
    recomputed: Counter[tuple[float, int, int]] = Counter()
    for rows in grouped.values():
        rows.sort(key=lambda row: int(row["t"]))
        for left, right in zip(rows[:-1], rows[1:]):
            recomputed[
                (float(left["alpha_heal"]), int(left["winner_N"]), int(right["winner_N"]))
            ] += 1
    if isinstance(transitions, list):
        reported = Counter(
            {
                (float(row["alpha_heal"]), int(row["from_N"]), int(row["to_N"])): int(row["count"])
                for row in transitions
                if isinstance(row, dict)
            }
        )
        if reported != recomputed:
            errors.append(_issue("TLD_TRANSITION_COUNT_MISMATCH", "raw trajectories"))
    missing_failure_ids = {
        point.get("failure_id")
        for point in points
        if isinstance(point, dict) and point.get("observed") is False
    }
    ledger_ids = {failure.get("failure_id") for failure in failures}
    if missing_failure_ids != ledger_ids:
        errors.append(_issue("TLD_FAILURE_PRESERVATION_MISMATCH", "missing cells and ledger"))
    if profile.get("profile") == "tld-i-modern-v21" and isinstance(controls, list):
        if any(
            isinstance(control, dict)
            and any(
                str(control.get(key, "")).casefold() in {"global", "global_pool", "pooled_global"}
                for key in ("scope", "pool", "null_pool")
            )
            for control in controls
        ):
            errors.append(_issue("TLD_GLOBAL_NULL_POOL_FORBIDDEN", "modern controls"))


def _audit_semantics(
    members: dict[str, bytes],
    manifest: dict[str, Any],
    errors: list[str],
    policy: BundlePolicy,
) -> None:
    run_spec = _load_json(members, "run_spec.json", errors, policy)
    ontology = _load_json(members, "ontology.json", errors, policy)
    claim = _load_json(members, "claim_boundary.json", errors, policy)
    table = _load_json(members, "tables/field_points.json", errors, policy)
    parent = _load_json(members, "registry/parent_registry.json", errors, policy)
    nulls = _load_json(members, "registry/null_registry.json", errors, policy)
    failures = _load_jsonl(members, "audit/failure_ledger.jsonl", errors, policy)
    receipts = _load_jsonl(members, "provenance/verification_receipts.jsonl", errors, policy)
    transformations = _load_jsonl(members, "provenance/transformations.jsonl", errors, policy)
    if not all(
        isinstance(value, dict) for value in (run_spec, ontology, claim, table, parent)
    ) or not isinstance(nulls, list):
        return
    for validation_error in validate_run_spec(run_spec):
        errors.append(_issue("RUN_SPEC_INVALID", validation_error))
    for validation_error in validate_with_schema("claim-boundary", claim):
        errors.append(_issue("CLAIM_SCHEMA_INVALID", validation_error))
    for validation_error in validate_with_schema("field-table", table):
        errors.append(_issue("FIELD_TABLE_SCHEMA_INVALID", validation_error))
    for failure in failures:
        for validation_error in validate_with_schema("failure", failure):
            errors.append(_issue("FAILURE_SCHEMA_INVALID", validation_error))
    engine = run_spec.get("engine")
    profile_name = str(manifest.get("profile", ""))
    historical_tld_profile = profile_name.startswith("tld-i-")
    heldout_tld_profile = profile_name.startswith("tld-heldout-")
    tld_profile = historical_tld_profile or heldout_tld_profile
    if ontology.get("schema_version") != "1.0.0":
        errors.append(_issue("SCHEMA_VERSION_UNSUPPORTED", "ontology"))
    non_equivalences = ontology.get("non_equivalences", [])
    if tld_profile and (
        "winner_N != T_e" not in non_equivalences
        or "winner_N != S_e" not in non_equivalences
        or "TORUS-BROT != ToT-BROT" not in non_equivalences
    ):
        errors.append(_issue("TLD_ONTOLOGY_CONFLATION", "required non-equivalences"))
    if engine == "analytic" and "tld evidence" in json.dumps(claim).casefold():
        errors.append(_issue("ANALYTIC_TLD_EVIDENCE_FORBIDDEN", "claim boundary"))
    if table.get("schema_version") != "1.0.0":
        errors.append(_issue("SCHEMA_VERSION_UNSUPPORTED", "field table"))
    specification_sha256 = content_hash(run_spec)
    if manifest.get("specification_sha256") != specification_sha256:
        errors.append(_issue("SPECIFICATION_HASH_MISMATCH", "manifest"))
    manifest_claim = manifest.get("claim_level")
    claim_name = claim.get("claim_level")
    if claim_name != manifest_claim:
        errors.append(_issue("CLAIM_LEVEL_MISMATCH", "claim boundary and manifest"))
    claim_values = {level.name: level.value for level in ClaimLevel}
    if manifest_claim not in claim_values:
        errors.append(_issue("CLAIM_LEVEL_INVALID", repr(manifest_claim)))
    else:
        output_level = claim_values[manifest_claim]
        requested_level = claim_values.get(run_spec.get("claim_level"), -1)
        if output_level > requested_level:
            errors.append(_issue("CLAIM_LEVEL_EXCEEDS_REQUEST", manifest_claim))
        if engine == "analytic" and output_level != ClaimLevel.ILLUSTRATIVE_ANALYTIC:
            errors.append(_issue("CLAIM_LEVEL_ENGINE_CONFLICT", "analytic engine"))
        if engine == "local_brot" and output_level > ClaimLevel.TLD_DERIVED:
            errors.append(_issue("CLAIM_LEVEL_ENGINE_CONFLICT", "local engine"))
        if engine == "tld" and not tld_profile:
            errors.append(_issue("TLD_PROFILE_MISSING", "tld engine requires a TLD profile"))
        if engine == "tld" and "historical" in str(manifest.get("profile")):
            if output_level > ClaimLevel.COMPUTED_DYNAMICAL:
                errors.append(_issue("CLAIM_LEVEL_ENGINE_CONFLICT", "historical TLD lane"))
        authority = claim_values.get(parent.get("claim_authority"))
        if authority is not None and output_level > authority:
            errors.append(_issue("CLAIM_LEVEL_DOMAIN_CONFLICT", manifest_claim))
    independent_status = claim.get("independent_verifier_status")
    if independent_status not in {"not_supplied", "independently_verified"}:
        errors.append(_issue("VERIFIER_STATUS_INVALID", repr(independent_status)))
    verified_receipt = any(
        receipt.get("run_id") == manifest.get("run_id")
        and receipt.get("status") == "verified"
        and bool(receipt.get("verifier"))
        for receipt in receipts
    )
    if independent_status == "independently_verified" and not verified_receipt:
        errors.append(_issue("VERIFIER_RECEIPT_MISSING", "independent status is forged"))
    if manifest_claim == "EXTERNALLY_VALIDATED" and not verified_receipt:
        errors.append(_issue("VERIFIER_RECEIPT_MISSING", "Level 3 requires a receipt"))

    grid = run_spec.get("grid", {})
    width, height = grid.get("width"), grid.get("height")
    points = table.get("points")
    if not isinstance(width, int) or not isinstance(height, int):
        errors.append(_issue("GRID_DIMENSION_INVALID", "width and height must be integers"))
        return
    if table.get("width") != width or table.get("height") != height:
        errors.append(_issue("GRID_DIMENSION_MISMATCH", "run specification and table"))
    if not isinstance(points, list):
        errors.append(_issue("FIELD_POINTS_INVALID", "points must be an array"))
        return
    expected_count = width * height
    if len(points) != expected_count:
        errors.append(
            _issue("GRID_POINT_COUNT_MISMATCH", f"expected {expected_count}, got {len(points)}")
        )
    classifications: Counter[str] = Counter()
    seen_cells: set[tuple[int, int]] = set()
    failure_ids = {failure.get("failure_id") for failure in failures}
    numeric_fields = ("x", "y", "S_e", "UI", "NSS", "SEP", "rms_to_parent")
    for position, point in enumerate(points):
        if not isinstance(point, dict):
            errors.append(_issue("FIELD_POINT_INVALID", str(position)))
            continue
        if historical_tld_profile:
            if any(not _is_finite_number(point.get(field)) for field in ("x", "y")):
                errors.append(_issue("FIELD_METRIC_NONFINITE", str(position)))
            if any(point.get(field) is not None for field in ("T_e", "S_e", "UI", "NSS", "SEP")):
                errors.append(_issue("TLD_UNCOMPUTED_ENDPOINT_POPULATED", str(position)))
            observed = point.get("observed")
            if observed is True and point.get("failure_id") is not None:
                errors.append(_issue("TLD_OBSERVED_FAILURE_CONFLICT", str(position)))
            if observed is False and (
                point.get("classification") != "UNRESOLVED" or point.get("failure_id") is None
            ):
                errors.append(_issue("TLD_MISSING_CELL_NOT_PRESERVED", str(position)))
        elif any(not _is_finite_number(point.get(field)) for field in numeric_fields):
            errors.append(_issue("FIELD_METRIC_NONFINITE", str(position)))
        grid_x, grid_y = point.get("grid_x"), point.get("grid_y")
        if not isinstance(grid_x, int) or not isinstance(grid_y, int):
            errors.append(_issue("FIELD_COORDINATE_INVALID", str(position)))
        elif not (0 <= grid_x < width and 0 <= grid_y < height):
            errors.append(_issue("FIELD_COORDINATE_INVALID", str(position)))
        elif (grid_x, grid_y) in seen_cells:
            errors.append(_issue("FIELD_COORDINATE_DUPLICATE", str(position)))
        else:
            seen_cells.add((grid_x, grid_y))
        if point.get("index") != position:
            errors.append(_issue("FIELD_INDEX_MISMATCH", str(position)))
        classification = point.get("classification")
        if classification not in {"BOUNDED", "ESCAPED", "RECOVERED", "NULL_LIKE", "UNRESOLVED"}:
            errors.append(_issue("FIELD_CLASSIFICATION_INVALID", str(position)))
        else:
            classifications[classification] += 1
        point_failure = point.get("failure_id")
        if point_failure is not None and point_failure not in failure_ids:
            errors.append(_issue("FAILURE_REFERENCE_MISSING", str(point_failure)))
    statistics = manifest.get("statistics", {})
    if statistics.get("point_count") != len(points):
        errors.append(_issue("STATISTICS_MISMATCH", "point_count"))
    if statistics.get("classification_counts") != dict(sorted(classifications.items())):
        errors.append(_issue("STATISTICS_MISMATCH", "classification_counts"))
    point_count = max(len(points), 1)
    for field, statistics_key in (
        ("UI", "mean_UI"),
        ("NSS", "mean_NSS"),
        ("S_e", "mean_S_e"),
    ):
        values = [point.get(field) for point in points if isinstance(point, dict)]
        if len(values) == len(points) and all(_is_finite_number(value) for value in values):
            expected_mean = round(sum(values) / point_count, 8)
            reported_mean = statistics.get(statistics_key)
            if not _is_finite_number(reported_mean) or not math.isclose(
                reported_mean, expected_mean, rel_tol=0.0, abs_tol=1.1e-8
            ):
                errors.append(_issue("STATISTICS_MISMATCH", statistics_key))
    if historical_tld_profile and any(
        statistics.get(key) is not None for key in ("mean_UI", "mean_NSS", "mean_S_e")
    ):
        errors.append(_issue("TLD_UNCOMPUTED_STATISTIC_POPULATED", "manifest statistics"))
    if statistics.get("failure_count") != len(failures):
        errors.append(_issue("FAILURE_COUNT_MISMATCH", "failure ledger"))
    null_policy = run_spec.get("null_policy", {})
    if len(nulls) != null_policy.get("count", 0):
        errors.append(_issue("NULL_REGISTRY_COUNT_MISMATCH", str(len(nulls))))
    if transformations:
        transformation = transformations[0]
        if transformation.get("specification_sha256") != specification_sha256:
            errors.append(_issue("PROVENANCE_HASH_MISMATCH", "transformation"))
        if transformation.get("transformation_id") != manifest.get("kernel_id"):
            errors.append(_issue("PROVENANCE_KERNEL_MISMATCH", "transformation"))
        if transformation.get("seed") != run_spec.get("seed"):
            errors.append(_issue("PROVENANCE_SEED_MISMATCH", "transformation"))
    else:
        errors.append(_issue("PROVENANCE_TRANSFORMATION_MISSING", "no transformation"))
    if historical_tld_profile:
        _audit_tld_semantics(members, manifest, claim, points, failures, errors, policy)
    if heldout_tld_profile:
        _audit_heldout_semantics(members, manifest, claim, failures, errors, policy)
    domain_sha256 = parent.get("domain_sha256") if engine in {"local_brot", "tld"} else None
    identity = {
        "specification": run_spec,
        "kernel_id": manifest.get("kernel_id"),
        "domain_sha256": domain_sha256,
    }
    expected_run_id = f"run-{content_hash(identity)[:16]}"
    if manifest.get("run_id") != expected_run_id:
        errors.append(_issue("RUN_ID_MISMATCH", expected_run_id))
    expected_sums = "".join(
        f"{_sha256(payload)}  {name}\n"
        for name, payload in sorted(members.items())
        if name not in {"manifest.json", "audit/SHA256SUMS.txt"}
    ).encode()
    if members.get("audit/SHA256SUMS.txt") != expected_sums:
        errors.append(_issue("SHA256SUMS_MISMATCH", "audit/SHA256SUMS.txt"))


def _audit_geometry_semantics(
    members: dict[str, bytes],
    manifest: dict[str, Any],
    errors: list[str],
    policy: BundlePolicy,
) -> None:
    profile = _load_json(members, "geometry_profile.json", errors, policy)
    source = _load_json(members, "source_registry.json", errors, policy)
    claim = _load_json(members, "claim_boundary.json", errors, policy)
    custody = _load_json(members, "provenance/raw_array_custody.json", errors, policy)
    channels = _load_json(members, "tables/geometry_channel_results.json", errors, policy)
    scales = _load_json(members, "tables/scale_behavior.json", errors, policy)
    baseline = _load_json(members, "tables/domain_baseline.json", errors, policy)
    independent = _load_json(members, "audit/independent_verification.json", errors, policy)
    adjudication = _load_json(members, "audit/claim_adjudication.json", errors, policy)
    forbidden = _load_json(members, "audit/forbidden_claims.json", errors, policy)
    parents = _load_jsonl(members, "registry/parent_registry.jsonl", errors, policy)
    projections = _load_jsonl(members, "registry/projection_registry.jsonl", errors, policy)
    nulls = _load_jsonl(members, "registry/null_registry.jsonl", errors, policy)
    failures = _load_jsonl(members, "audit/failure_ledger.jsonl", errors, policy)
    receipts = _load_jsonl(members, "provenance/verification_receipts.jsonl", errors, policy)
    objects = [
        profile,
        source,
        claim,
        custody,
        channels,
        scales,
        baseline,
        independent,
        adjudication,
        forbidden,
    ]
    if not all(isinstance(value, dict) for value in objects):
        return
    for validation_error in validate_with_schema("geometry-tbx-profile", profile):
        errors.append(_issue("GEOMETRY_PROFILE_SCHEMA_INVALID", validation_error))
    for validation_error in validate_with_schema("geometry-claim-adjudication", adjudication):
        errors.append(_issue("GEOMETRY_CLAIM_SCHEMA_INVALID", validation_error))
    if profile.get("profile_id") != "geometry-tbx-v1":
        errors.append(_issue("GEOMETRY_PROFILE_INVALID", "profile_id"))
    if profile.get("raw_arrays_required") is not True:
        errors.append(_issue("GEOMETRY_RAW_ARRAY_REQUIREMENT_INVALID", "profile"))
    array_member = custody.get("bundle_member")
    array_payload = members.get(array_member) if isinstance(array_member, str) else None
    if array_payload is None or custody.get("sha256") != _sha256(array_payload):
        errors.append(_issue("GEOMETRY_RAW_ARRAY_HASH_MISMATCH", repr(array_member)))
    if source.get("pilot_role") != "NONCONFIRMATORY_STRUCTURE_EXPOSED_ENGINEERING_PILOT":
        errors.append(_issue("GEOMETRY_PILOT_ROLE_INVALID", "source registry"))
    if source.get("condition_acquisitions_exchangeable") is not False:
        errors.append(_issue("GEOMETRY_CONDITION_POOLING_FORBIDDEN", "source registry"))
    control_count = sum(row.get("role") == "DOMAIN_CONTROL_BASELINE" for row in parents)
    if len(parents) != 4 or control_count != 1:
        errors.append(
            _issue(
                "GEOMETRY_PARENT_HIERARCHY_INVALID",
                "expected four conditions and one control",
            )
        )
    if not projections or not nulls:
        errors.append(_issue("GEOMETRY_REGISTRY_INCOMPLETE", "projection/null registry"))
    condition_rows = channels.get("conditions")
    if not isinstance(condition_rows, list) or len(condition_rows) != 4:
        errors.append(_issue("GEOMETRY_CHANNEL_RESULTS_INVALID", "condition rows"))
    elif any(row.get("population_aggregate") is not None for row in condition_rows):
        errors.append(_issue("GEOMETRY_CONDITION_POOLING_FORBIDDEN", "channel results"))
    scale_rows = scales.get("rows")
    if not isinstance(scale_rows, list) or not scale_rows:
        errors.append(_issue("GEOMETRY_SCALE_ROWS_INVALID", "scale behavior"))
    elif any(
        row.get("geometric_scale_symbol") != "ell" or "S_e" in row for row in scale_rows
    ):
        errors.append(_issue("GEOMETRY_SCALE_SE_COLLISION", "scale rows"))
    if baseline.get("numeric_pooling_with_TLD_channels") is not False:
        errors.append(_issue("GEOMETRY_BASELINE_POOLING_INVALID", "domain baseline"))
    if independent.get("status") != "VERIFIED" or independent.get("disagreements") != 0:
        errors.append(_issue("GEOMETRY_INDEPENDENT_VERIFICATION_FAILED", "audit receipt"))
    if not any(
        row.get("run_id") == manifest.get("run_id")
        and row.get("status") == "verified"
        and bool(row.get("verifier"))
        for row in receipts
    ):
        errors.append(_issue("VERIFIER_RECEIPT_MISSING", "geometry pilot"))
    if adjudication.get("run_id") != manifest.get("run_id"):
        errors.append(_issue("GEOMETRY_RUN_ID_MISMATCH", "claim adjudication"))
    if adjudication.get("method_mode") != "INSTRUMENTED_EVIDENCE_VECTOR":
        errors.append(_issue("GEOMETRY_METHOD_MODE_INVALID", "claim adjudication"))
    pilot_outcome = "NONCONFIRMATORY_STRUCTURE_EXPOSED_ENGINEERING_PILOT"
    if adjudication.get("scientific_outcome") != pilot_outcome:
        errors.append(_issue("GEOMETRY_PILOT_OUTCOME_INVALID", "claim adjudication"))
    if adjudication.get("TLD_DERIVED") != "BLOCKED" or adjudication.get(
        "EXTERNALLY_VALIDATED"
    ) is not False:
        errors.append(_issue("GEOMETRY_CLAIM_ESCALATION", "claim adjudication"))
    if any(
        not str(adjudication.get(name, "")).startswith("NOT_APPLICABLE")
        for name in ("T_e", "S_e", "winner_N")
    ):
        errors.append(_issue("GEOMETRY_SEMANTIC_ENDPOINT_INVALID", "T_e/S_e/winner_N"))
    forbidden_values = forbidden.get("claims")
    required_forbidden = {
        "TLD confirmation",
        "ToT-BROT",
        "external validation",
        "population generalization",
    }
    if not isinstance(forbidden_values, list) or not required_forbidden.issubset(
        set(forbidden_values)
    ):
        errors.append(_issue("GEOMETRY_FORBIDDEN_CLAIMS_INCOMPLETE", "audit list"))
    statistics = manifest.get("statistics", {})
    if statistics.get("point_count") != 4 or statistics.get("classification_counts") != {
        "NONCONFIRMATORY_CONDITION": 4
    }:
        errors.append(_issue("STATISTICS_MISMATCH", "geometry pilot conditions"))
    if any(statistics.get(key) is not None for key in ("mean_UI", "mean_NSS", "mean_S_e")):
        errors.append(_issue("GEOMETRY_UNCOMPUTED_STATISTIC_POPULATED", "manifest"))
    if statistics.get("failure_count") != len(failures):
        errors.append(_issue("FAILURE_COUNT_MISMATCH", "geometry failure ledger"))
    expected_sums = "".join(
        f"{_sha256(payload)}  {name}\n"
        for name, payload in sorted(members.items())
        if name not in {"manifest.json", "audit/SHA256SUMS.txt"}
    ).encode()
    if members.get("audit/SHA256SUMS.txt") != expected_sums:
        errors.append(_issue("SHA256SUMS_MISMATCH", "audit/SHA256SUMS.txt"))


def audit_bundle(
    source: str | Path,
    policy: BundlePolicy = DEFAULT_POLICY,
) -> AuditReport:
    try:
        members = read_bundle_members(source, policy)
    except BundleRejected as error:
        return AuditReport(False, "unknown", 0, error.errors)
    except OSError as error:
        return AuditReport(False, "unknown", 0, (_issue("ARCHIVE_READ_ERROR", str(error)),))
    if "manifest.json" not in members:
        return AuditReport(
            False,
            "unknown",
            0,
            (_issue("MANIFEST_MISSING", "manifest.json"),),
        )
    errors: list[str] = []
    manifest = _load_json(members, "manifest.json", errors, policy)
    if not isinstance(manifest, dict):
        return AuditReport(False, "unknown", 0, tuple(errors))
    checked = _audit_manifest(members, manifest, errors)
    if not errors:
        if manifest.get("profile") == "geometry-pilot-v0.3.0":
            _audit_geometry_semantics(members, manifest, errors, policy)
        else:
            _audit_semantics(members, manifest, errors, policy)
    return AuditReport(
        valid=not errors,
        run_id=str(manifest.get("run_id", "unknown")),
        checked_files=checked,
        errors=tuple(errors),
    )
