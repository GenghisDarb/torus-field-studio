from __future__ import annotations

import hashlib
import json
import math
import re
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
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
            ratio = math.inf if info.compress_size == 0 and info.file_size else (
                info.file_size / max(info.compress_size, 1)
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
    required_missing = sorted(REQUIRED_MEMBERS - set(paths))
    if required_missing:
        errors.append(_issue("REQUIRED_MEMBER_MISSING", ", ".join(required_missing)))
    return checked


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


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
    receipts = _load_jsonl(
        members, "provenance/verification_receipts.jsonl", errors, policy
    )
    transformations = _load_jsonl(
        members, "provenance/transformations.jsonl", errors, policy
    )
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
    if ontology.get("schema_version") != "1.0.0":
        errors.append(_issue("SCHEMA_VERSION_UNSUPPORTED", "ontology"))
    if table.get("schema_version") != "1.0.0":
        errors.append(_issue("SCHEMA_VERSION_UNSUPPORTED", "field table"))
    specification_sha256 = content_hash(run_spec)
    if manifest.get("specification_sha256") != specification_sha256:
        errors.append(_issue("SPECIFICATION_HASH_MISMATCH", "manifest"))
    engine = run_spec.get("engine")
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
        if any(not _is_finite_number(point.get(field)) for field in numeric_fields):
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
    else:
        errors.append(_issue("PROVENANCE_TRANSFORMATION_MISSING", "no transformation"))
    domain_sha256 = parent.get("domain_sha256") if engine == "local_brot" else None
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
        _audit_semantics(members, manifest, errors, policy)
    return AuditReport(
        valid=not errors,
        run_id=str(manifest.get("run_id", "unknown")),
        checked_files=checked,
        errors=tuple(errors),
    )
