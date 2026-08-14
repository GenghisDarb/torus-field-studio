import json
import zipfile
from pathlib import Path

from torusbrot import DomainPack, LocalBrotRun
from torusbrot.bundle import audit_bundle, export_field_csv

ROOT = Path(__file__).parents[1]


def result_fixture():
    domain = DomainPack.load(ROOT / "examples/tld-parent-null/domain.json")
    return LocalBrotRun.from_file(ROOT / "examples/tld-parent-null/run-spec.json").execute(domain)


def test_directory_and_zip_bundles_verify(tmp_path: Path) -> None:
    result = result_fixture()
    directory = result.export_tbx(tmp_path / "result.tbx")
    archive = result.export_tbx(tmp_path / "result.tbx.zip")
    assert audit_bundle(directory).valid
    assert audit_bundle(archive).valid


def test_zip_output_is_byte_deterministic(tmp_path: Path) -> None:
    result = result_fixture()
    first = result.export_tbx(tmp_path / "first.tbx.zip")
    second = result.export_tbx(tmp_path / "second.tbx.zip")
    assert first.read_bytes() == second.read_bytes()


def test_manifest_detects_tampering(tmp_path: Path) -> None:
    bundle = result_fixture().export_tbx(tmp_path / "result.tbx")
    table = bundle / "tables/field_points.json"
    data = json.loads(table.read_text(encoding="utf-8"))
    data["points"][0]["classification"] = "UNRESOLVED"
    table.write_text(json.dumps(data), encoding="utf-8")
    report = audit_bundle(bundle)
    assert not report.valid
    assert any("field_points.json" in error for error in report.errors)


def test_bundle_contains_claim_and_failure_contracts(tmp_path: Path) -> None:
    archive = result_fixture().export_tbx(tmp_path / "result.tbx.zip")
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
    assert "claim_boundary.json" in names
    assert "visual_encoding.json" in names
    assert "audit/failure_ledger.jsonl" in names
    assert "provenance/verification_receipts.jsonl" in names


def test_csv_compatibility_export(tmp_path: Path) -> None:
    bundle = result_fixture().export_tbx(tmp_path / "result.tbx")
    csv_path = export_field_csv(bundle, tmp_path / "field.csv")
    text = csv_path.read_text(encoding="utf-8")
    assert "classification" in text.splitlines()[0]
    assert len(text.splitlines()) > 10
