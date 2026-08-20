from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.run_v030_pinball_heldout import (
    AUTHORIZATION,
    JOINT_REPLICATES,
    NULL_CHILDREN,
    ROOT_SEED,
    RUN_ID,
    VELOCITY_CONVERSION,
    build_registered_projections,
    channel_summary,
    derived_seed,
    joint_null_summary,
    null_scores,
    perturbation_audit,
    scalar_channel_delta,
    scale_views,
    typed_projection_scores,
    write_json_exclusive,
)


def synthetic_arrays() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    yy, xx = np.mgrid[-1.0:1.0:12j, -1.5:1.5:16j]
    time = np.arange(7, dtype=np.float64)[:, None, None]
    u = xx[None, ...] + 0.1 * yy[None, ...] + 0.02 * time
    v = -0.3 * xx[None, ...] + yy[None, ...] - 0.01 * time
    return u, v, xx, yy


def test_registered_projections_disclose_temporal_mean_and_retain_fluctuations() -> None:
    u, v, x, y = synthetic_arrays()
    projections = build_registered_projections(u, v, x, y, "synthetic")
    assert projections.p01.values.shape == (12, 16, 2)
    assert projections.p02.values.shape == (7, 12, 16, 2)
    assert projections.audit["snapshot_axis"] == 0
    assert projections.audit["p02_uses_same_spatial_mask_as_p01"] is True
    assert np.all(projections.p01.mask)
    assert np.allclose(projections.p01.values[..., 0], np.mean(u, axis=0) * VELOCITY_CONVERSION)
    assert np.allclose(np.mean(projections.p02.values, axis=0), 0.0, atol=1e-15)
    assert all(np.isfinite(value) for value in typed_projection_scores(projections.p01).values())
    assert all(np.isfinite(value) for value in typed_projection_scores(projections.p02).values())


def test_missing_cell_is_masked_without_fill_or_interpolation() -> None:
    u, v, x, y = synthetic_arrays()
    u[2, 1, 3] = np.nan
    projections = build_registered_projections(u, v, x, y, "missing")
    assert projections.p01.mask[1, 3] == np.bool_(False)
    assert np.array_equal(projections.p01.values[1, 3], np.zeros(2))
    assert np.all(projections.p02.values[:, 1, 3] == 0.0)
    assert projections.audit["excluded_grid_cells"] == 1
    assert projections.audit["fill_performed"] is False
    assert projections.audit["interpolation_performed"] is False


def test_null_and_sensitivity_helpers_are_deterministic_and_nonbinary() -> None:
    u, v, x, y = synthetic_arrays()
    geometry = build_registered_projections(u, v, x, y, "null").p01
    first = null_scores(geometry, seed=derived_seed("unit-null"), children=7)
    second = null_scores(geometry, seed=derived_seed("unit-null"), children=7)
    assert first == second
    assert all(len(values) == 7 for values in first.values())
    summary = channel_summary(typed_projection_scores(geometry), first)
    assert set(summary) == set(typed_projection_scores(geometry))
    perturbations = perturbation_audit(geometry, seed=derived_seed("unit-perturbation"))
    assert perturbations[
        "PERT01_ROTATE_90_WITH_COORDINATES_COMPONENTS_AND_MASK"
    ]["status"] == "PASS"
    assert all(row["S_e"] == "NOT_APPLICABLE" for row in scale_views(geometry))


def test_joint_null_reports_all_replicates_without_p_value_or_threshold() -> None:
    observed = np.linspace(-0.2, 0.3, 28)
    children = np.vstack(
        [
            np.linspace(-0.5 + index / 100.0, 0.5 + index / 100.0, NULL_CHILDREN)
            for index in range(28)
        ]
    )
    result = joint_null_summary(observed, children, seed=derived_seed("joint-test"))
    assert result["joint_null_replicates"] == JOINT_REPLICATES
    assert len(result["joint_null_values"]) == JOINT_REPLICATES
    assert result["binary_threshold_applied"] is False
    assert result["p_value_computed"] is False
    assert not any("tail_p" in name for name in result)
    assert result["population_generalization"] is False


def test_pair_delta_never_aligns_cells_and_requires_named_channel_identity() -> None:
    assert scalar_channel_delta({"curl": 0.5}, {"curl": 0.2}) == {"curl": 0.3}
    with pytest.raises(ValueError, match="CHANNEL_SET_MISMATCH"):
        scalar_channel_delta({"curl": 0.5}, {"divergence": 0.2})


def test_authorization_and_one_shot_sentinel_are_exact(tmp_path: Path) -> None:
    authorization = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    assert authorization["run_id"] == RUN_ID
    assert authorization["root_seed"] == ROOT_SEED
    assert authorization["authorization_scope"]["permitted_scored_executions"] == 1
    assert authorization["authorization_scope"]["tld_derived"] == "BLOCKED"
    sentinel = tmp_path / "execution_attempt.json"
    write_json_exclusive(sentinel, {"attempt": 1})
    with pytest.raises(FileExistsError):
        write_json_exclusive(sentinel, {"attempt": 2})
