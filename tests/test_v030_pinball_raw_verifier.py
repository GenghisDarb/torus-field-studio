from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.run_v030_pinball_heldout import (
    anti_alias_downsample_2d,
    build_registered_projections,
    derived_seed,
    null_scores,
    typed_projection_scores,
)
from scripts.verify_v030_pinball_raw import (
    compare_numeric,
    downsample,
    null_samples,
    rotation_audit,
    score,
)

ROOT = Path(__file__).resolve().parents[1]
RAW_VERIFICATION = (
    ROOT / "studies" / "v0.3.0-recovery" / "heldout" / "raw_verification"
)


def geometry() -> tuple[np.ndarray, np.ndarray, object]:
    yy, xx = np.mgrid[-1.0:1.0:12j, -1.5:1.5:16j]
    time = np.arange(9, dtype=np.float64)[:, None, None]
    u = xx[None, ...] + 0.2 * yy[None, ...] + 0.01 * time
    v = -0.4 * xx[None, ...] + yy[None, ...] - 0.02 * time
    typed = build_registered_projections(u, v, xx, yy, "raw-verifier").p01
    return np.asarray(typed.values), np.asarray(typed.mask), typed


def test_independent_vector_scores_match_frozen_typed_projection() -> None:
    values, mask, typed = geometry()
    assert score(values, mask) == typed_projection_scores(typed)
    assert rotation_audit(values, mask)["status"] == "PASS"


def test_independent_downsample_matches_frozen_transform() -> None:
    values, mask, typed = geometry()
    independent_values, independent_mask = downsample(values, mask)
    production = anti_alias_downsample_2d(typed, factor=2)
    assert np.array_equal(independent_values, production.values)
    assert np.array_equal(independent_mask, production.mask)
    assert score(independent_values, independent_mask) == typed_projection_scores(production)


def test_independent_null_generator_matches_without_importing_production_in_verifier() -> None:
    values, mask, typed = geometry()
    seed = derived_seed("raw-verifier-null")
    assert null_samples(values, mask, seed) == null_scores(typed, seed=seed)


def test_comparison_ledger_detects_numeric_and_structural_disagreement() -> None:
    ledger: list[dict[str, object]] = []
    compare_numeric("root", {"a": [1.0, 2.0]}, {"a": [1.0, 3.0]}, ledger)
    assert len(ledger) == 1
    assert ledger[0]["issue"] == "NUMERIC_DISAGREEMENT"
    ledger.clear()
    compare_numeric("root", {"a": 1}, {"b": 1}, ledger)
    assert len(ledger) == 1
    assert ledger[0]["issue"] == "KEY_SET_MISMATCH"


def test_public_raw_verification_recomputes_every_frozen_component() -> None:
    verification = json.loads(
        (RAW_VERIFICATION / "independent_raw_recomputation.json").read_text(
            encoding="utf-8"
        )
    )
    scope = json.loads(
        (RAW_VERIFICATION / "independent_verifier_scope.json").read_text(
            encoding="utf-8"
        )
    )
    registry = [
        json.loads(line)
        for line in (
            RAW_VERIFICATION / "raw_recomputation_registry.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        if line
    ]
    disagreements = (
        RAW_VERIFICATION / "independent_disagreement_ledger.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    assert verification["status"] == "PASS"
    assert verification["disagreement_count"] == 0
    assert verification["acquisitions_recomputed"] == 56
    assert verification["paired_blocks_recomputed"] == 28
    assert verification["null_children_recomputed"] == 7_112
    assert verification["joint_null_replicates_recomputed_per_channel"] == 999
    assert verification["P01_channels_recomputed"] is True
    assert verification["P02_channels_recomputed"] is True
    assert verification["production_runner_imported"] is False
    assert verification["production_results_loaded_after_raw_recomputation"] is True
    assert verification["new_scored_execution"] is False
    assert verification["scored_execution_count"] == 1
    assert scope["claim_authority"] == "NONE_VERIFICATION_ONLY"
    assert scope["second_scored_execution"] is False
    assert len(registry) == 56
    assert len({row["member"] for row in registry}) == 56
    assert disagreements == []
