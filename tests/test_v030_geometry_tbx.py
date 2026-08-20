from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import numpy as np
from torusbrot.audit import audit_bundle

ROOT = Path(__file__).resolve().parents[1]
TBX = ROOT / "studies" / "v0.3.0-recovery" / "tbx"
COMBINED = TBX / "geometry-method-v2-combined-v0.3.0.tbx.zip"


def resign_geometry_bundle(path: Path, members: dict[str, bytes]) -> Path:
    manifest = json.loads(members["manifest.json"])
    sums = "".join(
        f"{hashlib.sha256(payload).hexdigest()}  {name}\n"
        for name, payload in sorted(members.items())
        if name not in {"manifest.json", "audit/SHA256SUMS.txt"}
    )
    members["audit/SHA256SUMS.txt"] = sums.encode()
    manifest["files"] = [
        {
            "path": name,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        }
        for name, payload in sorted(members.items())
        if name != "manifest.json"
    ]
    members["manifest.json"] = (
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        ).encode()
        + b"\n"
    )
    with zipfile.ZipFile(
        path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name, payload in [
            ("manifest.json", members.pop("manifest.json")),
            *sorted(members.items()),
        ]:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload)
    return path


def test_all_v030_geometry_bundles_pass_strict_audit() -> None:
    receipt = json.loads((TBX / "tbx_build_receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS"
    assert len(receipt["bundles"]) == 5
    for row in receipt["bundles"]:
        if row["profile"] == "geometry-pilot-v0.3.0":
            path = ROOT / "studies/v0.3.0-recovery/wind_pilot" / row["filename"]
        else:
            path = TBX / row["filename"]
        report = audit_bundle(path)
        assert report.valid, (path, report.errors)
        assert report.checked_files == row["checked_files"]


def test_combined_bundle_carries_registered_observations_coordinates_and_masks() -> None:
    with zipfile.ZipFile(COMBINED) as archive:
        source = json.loads(archive.read("source_registry.json"))
        custody = json.loads(archive.read("provenance/raw_array_custody.json"))
        arrays = np.load(
            io.BytesIO(archive.read(custody["bundle_member"])),
            allow_pickle=False,
        )
    assert source["registered_observation_count"] == 56
    assert source["registered_parent_count"] == 28
    assert source["campaign_count"] == 1
    assert source["population_generalization"] is False
    assert custody["source_archive_sha256"] == (
        "5819f9071c3b3b0b856934602b5e7b487852abe0e0a3a5b1b62eae17720d822f"
    )
    assert len(arrays.files) == 56 * 3
    assert sum(name.endswith("_coordinates") for name in arrays.files) == 56
    assert sum(name.endswith("_mask") for name in arrays.files) == 56
    assert sum(name.endswith("_p01_values") for name in arrays.files) == 56
    assert all(arrays[name].dtype != object for name in arrays.files)


def test_combined_bundle_keeps_scale_endpoints_and_claims_separate() -> None:
    with zipfile.ZipFile(COMBINED) as archive:
        adjudication = json.loads(archive.read("audit/claim_adjudication.json"))
        scale = json.loads(archive.read("tables/scale_behavior.json"))
        channels = json.loads(archive.read("tables/geometry_channel_results.json"))
        forbidden = json.loads(archive.read("audit/forbidden_claims.json"))
    assert adjudication["scientific_outcome"] == (
        "GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY"
    )
    assert adjudication["TLD_DERIVED"] == "BLOCKED"
    assert adjudication["EXTERNALLY_VALIDATED"] is False
    assert all(
        str(adjudication[key]).startswith("NOT_APPLICABLE") for key in ("T_e", "S_e", "winner_N")
    )
    assert all(row["geometric_scale_symbol"] == "ell" and "S_e" not in row for row in scale["rows"])
    assert channels["population_aggregate"] is None
    assert {
        "TLD confirmation",
        "ToT-BROT",
        "external validation",
        "population generalization",
    } <= set(forbidden["claims"])


def test_heldout_observation_and_null_contract_mutation_fails_closed(tmp_path: Path) -> None:
    target = tmp_path / "mutated.tbx.zip"
    with zipfile.ZipFile(COMBINED) as source:
        members = {
            info.filename: source.read(info.filename)
            for info in source.infolist()
            if not info.is_dir()
        }
    registry = json.loads(members["source_registry.json"])
    registry["registered_observation_count"] = 55
    registry["null_contract"] = "unregistered null"
    members["source_registry.json"] = json.dumps(registry).encode()
    report = audit_bundle(resign_geometry_bundle(target, members))
    assert not report.valid
    assert "GEOMETRY_HELDOUT_HIERARCHY_INVALID" in report.issue_codes
