from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from torusbrot.adapters.zenodo_tld_i import _member_path, validate_release_source
from torusbrot.audit import audit_bundle
from torusbrot.models import content_hash
from torusbrot.schema_validation import validate_with_schema
from torusbrot.tld.bundle import _domain_pack, export_tld_bundle
from torusbrot.tld.contracts import HistoricalTldIContract
from torusbrot.tld.modern import ModernTldIContract, execute_modern_extension
from torusbrot.tld.registry import build_registries
from torusbrot.tld.verification import verify_historical_result

from tests.tld_fixtures import compact_tld_result, read_members, resign_bundle


def test_independent_verifier_recomputes_registered_endpoints() -> None:
    receipt = verify_historical_result(compact_tld_result())
    assert receipt["status"] == "verified"
    assert all(value is True for value in receipt["checks"].values() if isinstance(value, bool))


def test_tld_bundle_is_deterministic_and_auditable(tmp_path: Path) -> None:
    result = compact_tld_result()
    first = export_tld_bundle(result, "notebook14", tmp_path / "first.tbx.zip")
    second = export_tld_bundle(result, "notebook14", tmp_path / "second.tbx.zip")
    assert first.read_bytes() == second.read_bytes()
    report = audit_bundle(first)
    assert report.valid, report.errors


def test_domain_materialization_and_frozen_modern_contract(tmp_path: Path) -> None:
    result = compact_tld_result()
    assert validate_with_schema("tld-domain-pack", _domain_pack(result)) == []
    root = Path(__file__).parents[1]
    declared = json.loads(
        (root / "examples/tld-i/modern-v21-preregistration.json").read_text(encoding="utf-8")
    )
    assert declared == ModernTldIContract().to_dict()
    source = tmp_path / "release" / "data_inputs"
    source.mkdir(parents=True)
    source.joinpath("targets_baseline.csv").write_text(
        "family,codata_name,value,sigma\n"
        "fixture,row-0,1.1,0.01\nfixture,row-1,1.2,0.01\n"
        "fixture,row-2,1.3,0.01\nfixture,row-3,1.4,0.01\n",
        encoding="utf-8",
    )
    modern = execute_modern_extension(tmp_path / "release", result)
    assert modern["registry_frozen_before_metrics"] is True
    assert len(modern["registry"]) == 33
    assert all(row["scope"] == "parent_local" for row in modern["registry"])
    assert modern["endpoint_applicability"]["T_e"] == "NOT_APPLICABLE"
    assert modern["TLD_DERIVED_STATUS"] == "BLOCKED"


def test_zenodo_adapter_validates_layout_and_rejects_unsafe_names(tmp_path: Path) -> None:
    release = tmp_path / "TORUS_Zenodo_v1"
    inputs = release / "data_inputs"
    notebooks = release / "notebooks"
    inputs.mkdir(parents=True)
    notebooks.mkdir()
    for name in (
        "targets_baseline.csv",
        "targets_metadata_template.csv",
        "targets_metadata_addon.csv",
    ):
        inputs.joinpath(name).write_text("value,sigma\n1,0\n", encoding="utf-8")
    for number in (13, 14):
        notebooks.joinpath(f"TORUS Ladder Validation Notebook {number}.ipynb").write_text(
            '{"cells": []}', encoding="utf-8"
        )
    receipt = validate_release_source(tmp_path)
    assert receipt["valid"] is True
    import zipfile

    with pytest.raises(ValueError, match="ARCHIVE_PATH_INVALID"):
        _member_path(zipfile.ZipInfo("../escape.txt"))


def test_input_and_order_changes_change_registered_identities() -> None:
    result = compact_tld_result()
    changed = compact_tld_result()
    changed["input_rows"][0]["value"] = 1.1001
    changed["input_hashes"] = changed["input_hashes"] | {"targets_baseline.csv": "b" * 64}
    assert content_hash(_domain_pack(result)) != content_hash(_domain_pack(changed))
    specification = {"engine": "tld", "seed": 42}

    def identity(value):
        return content_hash(
            {
                "specification": specification,
                "kernel_id": "torusbrot.tld_i.historical.v1",
                "domain_sha256": content_hash(_domain_pack(value)),
            }
        )

    assert identity(result) != identity(changed)
    values = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    forward = build_registries(
        baseline_sha256="a" * 64,
        values_sha256=__import__("hashlib").sha256(values.tobytes()).hexdigest(),
        contract=HistoricalTldIContract(),
    )
    reversed_values = values[::-1].copy()
    reverse = build_registries(
        baseline_sha256="a" * 64,
        values_sha256=__import__("hashlib").sha256(reversed_values.tobytes()).hexdigest(),
        contract=HistoricalTldIContract(),
    )
    assert forward["parents"][0]["ladder_id"] != reverse["parents"][0]["ladder_id"]


def test_tld_semantic_mutations_fail_closed(tmp_path: Path) -> None:
    source = export_tld_bundle(compact_tld_result(), "notebook14", tmp_path / "base.tbx.zip")

    def mutate(name: str, member: str, update, code: str) -> None:
        members = read_members(source)
        document = json.loads(members[member])
        update(document)
        members[member] = (
            json.dumps(document, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        )
        target = resign_bundle(tmp_path / name, members)
        report = audit_bundle(target)
        assert not report.valid
        assert code in report.issue_codes, report.errors

    mutate(
        "winner-as-te.tbx.zip",
        "tables/tld_endpoint_table.json",
        lambda value: value["rows"][0].update({"T_e": value["rows"][0]["winner_N"]}),
        "TLD_UNCOMPUTED_ENDPOINT_POPULATED",
    )
    mutate(
        "uncomputed-se.tbx.zip",
        "tables/tld_endpoint_table.json",
        lambda value: value["rows"][0].update({"S_e": 1.0}),
        "TLD_UNCOMPUTED_ENDPOINT_POPULATED",
    )
    mutate(
        "wrong-control.tbx.zip",
        "tables/core_alpha_compare.json",
        lambda value: value.__setitem__(0, value[1] | {"alpha_heal": 0.0}),
        "TLD_PREREGISTRATION_OUTCOME_MISMATCH",
    )
    mutate(
        "seed-mismatch.tbx.zip",
        "provenance/transformations.jsonl",
        lambda value: value.update({"seed": 43}),
        "PROVENANCE_SEED_MISMATCH",
    )
    mutate(
        "interpolated-observation.tbx.zip",
        "tld_profile.json",
        lambda value: value.update({"interpolation_used_for_metrics": True}),
        "TLD_INTERPOLATION_AS_OBSERVATION",
    )
    mutate(
        "ontology-conflation.tbx.zip",
        "ontology.json",
        lambda value: value["non_equivalences"].remove("TORUS-BROT != ToT-BROT"),
        "TLD_ONTOLOGY_CONFLATION",
    )
    mutate(
        "external-validation.tbx.zip",
        "audit/claim_adjudication.json",
        lambda value: value.update({"externally_validated": True}),
        "TLD_EXTERNAL_VALIDATION_FORBIDDEN",
    )
    mutate(
        "source-input-hash.tbx.zip",
        "source_registry.json",
        lambda value: value["input_sha256"].update({"targets_baseline.csv": "b" * 64}),
        "TLD_SOURCE_INPUT_HASH_MISMATCH",
    )


def test_global_null_and_analytic_evidence_claims_are_rejected(tmp_path: Path) -> None:
    source = export_tld_bundle(compact_tld_result(), "notebook14", tmp_path / "base.tbx.zip")
    members = read_members(source)
    manifest = json.loads(members["manifest.json"])
    manifest["profile"] = "tld-i-modern-v21"
    members["manifest.json"] = json.dumps(manifest).encode()
    profile = json.loads(members["tld_profile.json"])
    profile["profile"] = "tld-i-modern-v21"
    members["tld_profile.json"] = json.dumps(profile).encode()
    controls = json.loads(members["registry/control_or_null_registry.json"])
    controls[0]["scope"] = "global_pool"
    members["registry/control_or_null_registry.json"] = json.dumps(controls).encode()
    report = audit_bundle(resign_bundle(tmp_path / "global-null.tbx.zip", members))
    assert "TLD_GLOBAL_NULL_POOL_FORBIDDEN" in report.issue_codes

    from torusbrot.runs import AnalyticRun

    root = Path(__file__).parents[1]
    analytic = AnalyticRun.from_file(root / "examples/analytic-z14/run-spec.json").execute()
    analytic_bundle = analytic.export_tbx(tmp_path / "analytic.tbx.zip")
    members = read_members(analytic_bundle)
    claim = json.loads(members["claim_boundary.json"])
    claim["permitted_interpretations"].append("TLD evidence")
    members["claim_boundary.json"] = json.dumps(claim).encode()
    report = audit_bundle(resign_bundle(tmp_path / "analytic-tld-evidence.tbx.zip", members))
    assert "ANALYTIC_TLD_EVIDENCE_FORBIDDEN" in report.issue_codes


def test_tld_membership_and_failure_mutations_fail_closed(tmp_path: Path) -> None:
    source = export_tld_bundle(compact_tld_result(), "notebook14", tmp_path / "base.tbx.zip")
    members = read_members(source)
    members.pop("tables/operating_envelope.json")
    report = audit_bundle(resign_bundle(tmp_path / "dropped-output.tbx.zip", members))
    assert "REQUIRED_MEMBER_MISSING" in report.issue_codes

    members = read_members(source)
    members["undeclared.txt"] = b"not manifested"
    target = tmp_path / "unmanifested.tbx.zip"
    target.write_bytes(source.read_bytes())
    import zipfile

    with zipfile.ZipFile(target, "a") as archive:
        archive.writestr("undeclared.txt", b"not manifested")
    assert "MANIFEST_UNLISTED_MEMBER" in audit_bundle(target).issue_codes

    members = read_members(source)
    rows = members["audit/failure_ledger.jsonl"].splitlines()
    members["audit/failure_ledger.jsonl"] = b"\n".join(rows[1:]) + b"\n"
    report = audit_bundle(resign_bundle(tmp_path / "missing-failure.tbx.zip", members))
    assert "TLD_FAILURE_PRESERVATION_MISMATCH" in report.issue_codes

    members = read_members(source)
    trajectories = members["tables/trajectories.jsonl"].splitlines()
    row = json.loads(trajectories[0])
    row["chi"] += 0.1
    trajectories[0] = json.dumps(row).encode()
    members["tables/trajectories.jsonl"] = b"\n".join(trajectories) + b"\n"
    target = tmp_path / "trajectory-tamper.tbx.zip"
    import shutil

    shutil.copyfile(source, target)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    assert "MANIFEST_HASH_MISMATCH" in audit_bundle(target).issue_codes
