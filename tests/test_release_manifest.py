from __future__ import annotations

import json
from pathlib import Path

from scripts.release_manifest import build_manifest, verify_manifest


def test_v030_release_manifest_preserves_nonbinary_claim_boundary(tmp_path: Path) -> None:
    (tmp_path / "artifact.txt").write_text("evidence\n", encoding="utf-8")
    manifest_path = build_manifest(tmp_path, "v0.3.0", "a" * 40)
    verify_manifest(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["scientific_outcome"] == (
        "GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY"
    )
    assert manifest["method_mode"] == "INSTRUMENTED_EVIDENCE_VECTOR"
    assert manifest["predictive_TLD_discriminator"] is False
    assert manifest["population_generalization"] is False
    assert manifest["TLD_DERIVED_status"] == "BLOCKED"
    assert manifest["EXTERNALLY_VALIDATED"] is False
    assert manifest["geometric_scale"].startswith("ell ")
    assert all(
        str(manifest[name]).startswith("NOT_APPLICABLE") for name in ("T_e", "S_e", "winner_N")
    )


def test_legacy_release_manifest_keeps_v021_outcome(tmp_path: Path) -> None:
    (tmp_path / "artifact.txt").write_text("evidence\n", encoding="utf-8")
    manifest_path = build_manifest(tmp_path, "v0.2.2", "b" * 40)
    verify_manifest(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["scientific_outcome"] == "HELDOUT_TLD_STUDY_NEGATIVE_UNDER_FROZEN_GATES"
