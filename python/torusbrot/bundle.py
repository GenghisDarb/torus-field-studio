from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audit import audit_bundle, read_bundle_members
from .models import (
    AuditReport,
    ClaimLevel,
    DomainPack,
    FailureRecord,
    FieldPoint,
    RunSpec,
    canonical_json,
    content_hash,
)


def _jsonl(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json(row) for row in rows)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass
class FieldResult:
    specification: RunSpec
    points: list[FieldPoint]
    kernel_id: str
    claim_level: ClaimLevel
    run_id: str
    domain: DomainPack | None
    null_registry: list[dict[str, Any]]
    failures: list[FailureRecord]

    @classmethod
    def from_run(
        cls,
        *,
        specification: RunSpec,
        points: list[FieldPoint],
        kernel_id: str,
        claim_level: ClaimLevel,
        domain: DomainPack | None,
        null_registry: list[dict[str, Any]],
        failures: list[FailureRecord] | None = None,
    ) -> FieldResult:
        identity = {
            "specification": specification.to_dict(),
            "kernel_id": kernel_id,
            "domain_sha256": domain.sha256 if domain else None,
        }
        return cls(
            specification=specification,
            points=points,
            kernel_id=kernel_id,
            claim_level=claim_level,
            run_id=f"run-{content_hash(identity)[:16]}",
            domain=domain,
            null_registry=null_registry,
            failures=failures or [],
        )

    @property
    def statistics(self) -> dict[str, Any]:
        classifications = Counter(point.classification for point in self.points)
        count = max(len(self.points), 1)
        return {
            "point_count": len(self.points),
            "classification_counts": dict(sorted(classifications.items())),
            "mean_UI": round(sum(point.UI for point in self.points) / count, 8),
            "mean_NSS": round(sum(point.NSS for point in self.points) / count, 8),
            "mean_S_e": round(sum(point.S_e for point in self.points) / count, 8),
            "failure_count": len(self.failures),
        }

    def _members(self) -> dict[str, bytes]:
        spec = self.specification.to_dict()
        analytic = self.specification.engine == "analytic"
        points = [point.to_dict() for point in self.points]
        winner_counts = Counter(str(point.winner_N) for point in self.points if point.winner_N)
        parent_registry = (
            {
                "parent_id": self.domain.domain_id,
                "title": self.domain.title,
                "ladder": list(self.domain.ladder),
                "domain_sha256": self.domain.sha256,
                "claim_authority": self.domain.claim_authority.name,
            }
            if self.domain
            else {"parent_id": "analytic-origin-z0", "kind": "declared_initial_state"}
        )
        permitted = (
            ["visual analogy", "orbit comparison", "reproducible analytic exploration"]
            if analytic
            else ["registered computation", "parent-versus-matched-null comparison"]
        )
        excluded = [
            "external validation without an independent verification receipt",
            "causal inference from visual appearance",
            "count, repair, release, or terminal authority",
        ]
        members: dict[str, bytes] = {
            "run_spec.json": canonical_json(spec, pretty=True),
            "ontology.json": canonical_json(
                {
                    "schema_version": "1.0.0",
                    "terms": {
                        "omega": "ordered ladder state",
                        "T_e": "first registered depth of observed/null separation",
                        "S_e": "persistence of separation after emergence",
                        "winner_N": "harmonic closure-mode label",
                    },
                    "non_equivalences": [
                        "closure != emergence",
                        "survival != closure",
                        "escape != failure",
                        "interpolation != observation",
                    ],
                },
                pretty=True,
            ),
            "claim_boundary.json": canonical_json(
                {
                    "claim_level": self.claim_level.name,
                    "permitted_interpretations": permitted,
                    "excluded_interpretations": excluded,
                    "experimental_tags": [],
                    "independent_verifier_status": "not_supplied",
                },
                pretty=True,
            ),
            "visual_encoding.json": canonical_json(
                {
                    "position": {
                        "x": "complex_real" if analytic else "order_mutation_strength",
                        "y": "complex_imaginary" if analytic else "anchoring_alpha",
                        "z": "S_e",
                    },
                    "color": "iterations" if analytic else "NSS",
                    "opacity": "UI",
                    "contour": None if analytic else "winner_N",
                    "interpolation": {"method": "bilinear", "used_for_metrics": False},
                    "scale_policy": "frozen_domain_standard",
                },
                pretty=True,
            ),
            "scene_recipe.json": canonical_json(
                {
                    "viewer": "TORUS Field Studio",
                    "default_view": "field",
                    "raw_samples_visible": True,
                    "missing_regions_visible": True,
                    "palette": "spectral-claim-safe-v1",
                },
                pretty=True,
            ),
            "provenance/sources.jsonl": _jsonl(
                [
                    {
                        "source_id": self.domain.domain_id if self.domain else "analytic-equation",
                        "sha256": self.domain.sha256 if self.domain else content_hash(spec),
                        "kind": self.domain.source.get("kind") if self.domain else "declared_model",
                        "details": (
                            self.domain.source
                            if self.domain
                            else {"equation": "z[n+1]=z[n]^p+c"}
                        ),
                    }
                ]
            ),
            "provenance/transformations.jsonl": _jsonl(
                [
                    {
                        "transformation_id": self.kernel_id,
                        "software_version": "0.2.0",
                        "seed": self.specification.seed,
                        "specification_sha256": self.specification.sha256,
                    }
                ]
            ),
            "provenance/verification_receipts.jsonl": b"",
            "registry/parent_registry.json": canonical_json(parent_registry, pretty=True),
            "registry/null_registry.json": canonical_json(self.null_registry, pretty=True),
            "tables/field_points.json": canonical_json(
                {
                    "schema_version": "1.0.0",
                    "width": self.specification.grid.width,
                    "height": self.specification.grid.height,
                    "points": points,
                }
            ),
            "tables/metrics_by_N.json": canonical_json(
                {
                    "winner_N_counts": dict(sorted(winner_counts.items())),
                    "summary": self.statistics,
                },
                pretty=True,
            ),
            "audit/audit.json": canonical_json(
                {
                    "status": "self_checked",
                    "kernel_authority": "deterministic_cpu_reference",
                    "failure_preservation": "complete",
                    "classification_precedes_rendering": True,
                },
                pretty=True,
            ),
            "audit/failure_ledger.jsonl": _jsonl(
                [failure.to_dict() for failure in self.failures]
            ),
        }
        sums = "".join(
            f"{_sha256(payload)}  {path}\n" for path, payload in sorted(members.items())
        )
        members["audit/SHA256SUMS.txt"] = sums.encode()
        return members

    def export_tbx(self, destination: str | Path) -> Path:
        target = Path(destination)
        members = self._members()
        manifest = {
            "tbx_version": "1.0.0",
            "run_id": self.run_id,
            "claim_level": self.claim_level.name,
            "kernel_id": self.kernel_id,
            "specification_sha256": self.specification.sha256,
            "statistics": self.statistics,
            "files": [
                {"path": path, "sha256": _sha256(payload), "bytes": len(payload)}
                for path, payload in sorted(members.items())
            ],
        }
        manifest_payload = canonical_json(manifest, pretty=True)
        if target.name.endswith(".zip"):
            target.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(
                target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
            ) as archive:
                ordered_members = [("manifest.json", manifest_payload), *sorted(members.items())]
                for path, payload in ordered_members:
                    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, payload)
        else:
            target.mkdir(parents=True, exist_ok=True)
            (target / "manifest.json").write_bytes(manifest_payload)
            for path, payload in members.items():
                member = target / path
                member.parent.mkdir(parents=True, exist_ok=True)
                member.write_bytes(payload)
        return target

    def audit(self, source: str | Path | None = None) -> AuditReport:
        if source is None:
            import tempfile

            with tempfile.TemporaryDirectory(prefix="torusbrot-audit-") as temporary:
                target = self.export_tbx(Path(temporary) / "run.tbx")
                return audit_bundle(target)
        return audit_bundle(source)


def read_field_table(source: str | Path) -> dict[str, Any]:
    report = audit_bundle(source)
    if not report.valid:
        raise ValueError("Bundle audit failed: " + "; ".join(report.errors))
    members = read_bundle_members(source)
    try:
        return json.loads(members["tables/field_points.json"])
    except KeyError as error:
        raise ValueError("Bundle does not contain tables/field_points.json") from error


def export_field_csv(source: str | Path, destination: str | Path) -> Path:
    table = read_field_table(source)
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    points = table["points"]
    excluded = {"trace"}
    headers = [key for key in points[0] if key not in excluded] if points else []
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for point in points:
            writer.writerow({key: point[key] for key in headers})
    return target


def copy_field_json(source: str | Path, destination: str | Path) -> Path:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_json(read_field_table(source), pretty=True))
    return target


def compare_bundles(left: str | Path, right: str | Path) -> dict[str, Any]:
    left_members = read_bundle_members(left)
    right_members = read_bundle_members(right)
    left_manifest = json.loads(left_members["manifest.json"])
    right_manifest = json.loads(right_members["manifest.json"])
    left_points, right_points = read_field_table(left)["points"], read_field_table(right)["points"]
    left_classes = Counter(point["classification"] for point in left_points)
    right_classes = Counter(point["classification"] for point in right_points)
    return {
        "left_run_id": left_manifest["run_id"],
        "right_run_id": right_manifest["run_id"],
        "identical_specification": left_manifest.get("specification_sha256")
        == right_manifest.get("specification_sha256"),
        "point_count_delta": len(right_points) - len(left_points),
        "classification_delta": {
            key: right_classes[key] - left_classes[key]
            for key in sorted(left_classes.keys() | right_classes.keys())
        },
    }
