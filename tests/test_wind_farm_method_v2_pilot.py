from __future__ import annotations

import json
import zipfile
from pathlib import Path

from torusbrot.audit import audit_bundle

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "studies" / "v0.3.0-recovery" / "wind_pilot"


def load(name: str) -> dict[str, object]:
    value = json.loads((PILOT / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_wind_pilot_is_descriptive_unpooled_and_nonconfirmatory() -> None:
    contract = load("wind_farm_pilot_contract.json")
    results = load("wind_farm_pilot_results.json")
    claim = load("wind_farm_pilot_claim_boundary.json")
    hierarchy = contract["hierarchy"]
    assert isinstance(hierarchy, dict)
    assert hierarchy["facility_campaigns"] == 1
    assert hierarchy["condition_level_acquisitions"] == 4
    assert hierarchy["condition_acquisitions_exchangeable"] is False
    assert results["population_aggregate"] is None
    assert results["condition_pooling"] == "FORBIDDEN"
    assert claim["scientific_outcome"] == (
        "NONCONFIRMATORY_STRUCTURE_EXPOSED_ENGINEERING_PILOT"
    )
    assert claim["TLD_DERIVED"] == "BLOCKED"
    assert claim["EXTERNALLY_VALIDATED"] is False


def test_wind_pilot_keeps_scale_and_endpoint_semantics_separate() -> None:
    results = load("wind_farm_pilot_results.json")
    claim = load("wind_farm_pilot_claim_boundary.json")
    scale = results["scale_behavior"]
    assert isinstance(scale, dict)
    assert scale["scale_symbol"] == "ell"
    assert scale["S_e"] == "NOT_APPLICABLE"
    assert str(scale["operation_depth"]).startswith("NOT_APPLICABLE")
    assert str(claim["T_e"]).startswith("NOT_APPLICABLE")
    assert str(claim["S_e"]).startswith("NOT_APPLICABLE")
    assert str(claim["winner_N"]).startswith("NOT_APPLICABLE")


def test_wind_pilot_preserves_rotation_failure_and_corrected_equivariance() -> None:
    projection = load("wind_farm_projection_audit.json")
    assert projection["all_rotation_equivariance_passed"] is True
    failures = projection["preserved_engineering_failures"]
    assert isinstance(failures, list) and len(failures) == 1
    assert failures[0]["issue_code"] == "PILOT_EXPOSED_ROTATION_RASTER_DIRECTION_DEFECT"
    assert failures[0]["threshold_or_method_component_changed"] is False


def test_wind_pilot_tbx_passes_strict_geometry_audit() -> None:
    path = PILOT / "wind_farm_pilot.tbx.zip"
    report = audit_bundle(path)
    assert report.valid, report.errors
    assert report.checked_files == 22
    with zipfile.ZipFile(path) as archive:
        adjudication = json.loads(archive.read("audit/claim_adjudication.json"))
        independent = json.loads(archive.read("audit/independent_verification.json"))
        failures = [
            json.loads(line)
            for line in archive.read("audit/failure_ledger.jsonl").decode().splitlines()
        ]
    assert adjudication["TLD_DERIVED"] == "BLOCKED"
    assert adjudication["EXTERNALLY_VALIDATED"] is False
    assert independent["status"] == "VERIFIED"
    assert independent["disagreements"] == 0
    assert any(
        row["issue_code"] == "PILOT_EXPOSED_ROTATION_RASTER_DIRECTION_DEFECT"
        for row in failures
    )
