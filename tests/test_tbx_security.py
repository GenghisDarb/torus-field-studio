import json
from dataclasses import replace
from pathlib import Path

from torusbrot import DomainPack, LocalBrotRun
from torusbrot.audit import BundlePolicy, audit_bundle
from torusbrot.kernels import LadderKernel
from torusbrot.models import GridSpec

from scripts.generate_hostile_fixtures import generate_corpus

ROOT = Path(__file__).parents[1]


def test_hostile_bundle_corpus_has_stable_decisions(tmp_path: Path) -> None:
    expectations = generate_corpus(tmp_path)
    for name, expected in expectations.items():
        report = audit_bundle(tmp_path / name)
        if expected == "VALID":
            assert report.valid, report.errors
        else:
            assert not report.valid
            assert expected in report.issue_codes, (name, report.errors)


def test_policy_rejects_members_before_reading(tmp_path: Path) -> None:
    generate_corpus(tmp_path)
    report = audit_bundle(
        tmp_path / "valid-reference.tbx.zip",
        BundlePolicy(max_member_bytes=100, max_total_bytes=10_000_000),
    )
    assert not report.valid
    assert "ARCHIVE_MEMBER_LIMIT" in report.issue_codes


def test_kernel_exception_is_preserved_as_visible_failure(tmp_path: Path, monkeypatch) -> None:
    domain = DomainPack.load(ROOT / "examples/tld-parent-null/domain.json")
    run = LocalBrotRun.from_file(ROOT / "examples/tld-parent-null/run-spec.json")
    run.specification = replace(run.specification, grid=GridSpec(width=8, height=6))
    original = LadderKernel._point

    def fail_one_point(self, grid_x, grid_y, *args, **kwargs):
        if grid_x == 3 and grid_y == 2:
            raise RuntimeError("synthetic kernel fault")
        return original(self, grid_x, grid_y, *args, **kwargs)

    monkeypatch.setattr(LadderKernel, "_point", fail_one_point)
    result = run.execute(domain)
    failed = [point for point in result.points if point.failure_id]
    assert len(failed) == 1
    assert failed[0].classification == "UNRESOLVED"
    assert failed[0].eligible is False
    assert result.statistics["failure_count"] == 1
    bundle = result.export_tbx(tmp_path / "failure-preserved.tbx.zip")
    report = audit_bundle(bundle)
    assert report.valid, report.errors
    with __import__("zipfile").ZipFile(bundle) as archive:
        ledger = archive.read("audit/failure_ledger.jsonl").decode()
    record = json.loads(ledger)
    assert record["failure_id"] == failed[0].failure_id
    assert record["category"] == "KERNEL_EXCEPTION"
