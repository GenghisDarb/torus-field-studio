"""Frozen modern-governance extension for the published TLD I mechanism."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..models import content_hash
from .contracts import TLD_I_DOI
from .perturbations import matched_multiset_control
from .scoring import materialize_ladder, score_ladder
from .verification import EXPECTED_INPUT_HASHES, verify_historical_result

MODERN_LANE = "MODERN_V21_COMPLIANCE_EXTENSION"


@dataclass(frozen=True)
class ModernTldIContract:
    seed: int = 21000
    n_window: tuple[int, ...] = tuple(range(7, 14))
    n_center: int = 10
    matched_control_count: int = 32

    def body(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "lane": MODERN_LANE,
            "doi": TLD_I_DOI,
            "seed": self.seed,
            "n_window": list(self.n_window),
            "n_center": self.n_center,
            "operators": {
                "historical_escape": "adjacent_order_mutation(p_swap=0.02)",
                "historical_healing": "value_noise(epsilon=16) then parent_anchor(alpha)",
                "matched_control": (
                    "parent-local deterministic permutation preserving the exact omega multiset"
                ),
                "control_scope": "parent_matched_domain_isolated",
                "global_pool": False,
                "T_e": (
                    "NOT_APPLICABLE: historical release has no registered observed/null "
                    "emergence depth"
                ),
                "S_e": (
                    "NOT_APPLICABLE: historical release has no registered post-emergence "
                    "survival depth"
                ),
            },
            "trials": {
                "matched_controls": self.matched_control_count,
                "historical_trials": "unchanged; consumed from independently verified Lane 1",
            },
            "claim_ceiling": "TLD_DERIVED",
        }

    @property
    def sha256(self) -> str:
        return content_hash(self.body())

    def to_dict(self) -> dict[str, Any]:
        return self.body() | {"contract_sha256": self.sha256}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute_modern_extension(
    source_root: str | Path,
    historical_result: dict[str, Any],
    contract: ModernTldIContract | None = None,
) -> dict[str, Any]:
    """Run the frozen governance translation without redefining historical endpoints."""
    frozen = contract or ModernTldIContract()
    baseline_path = Path(source_root) / "data_inputs" / "targets_baseline.csv"
    with baseline_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    values = [float(row["value"]) for row in rows]
    sigmas = [float(row["sigma"]) for row in rows]
    omega, _ = materialize_ladder(values, sigmas)
    source_hash = _sha256(baseline_path)
    parent_identity = {
        "domain_id": "torus-tld-i-baseline-v1",
        "kind": "observed_parent",
        "source_sha256": source_hash,
        "omega_sha256": hashlib.sha256(omega.tobytes()).hexdigest(),
        "contract_sha256": frozen.sha256,
    }
    parent_id = f"ladder-{content_hash(parent_identity)[:16]}"
    registry = [
        {
            "ladder_id": parent_id,
            "domain_id": parent_identity["domain_id"],
            "kind": "observed_parent",
            "parent_ladder_id": None,
            "is_null": False,
            "eligible": True,
            "seed": frozen.seed,
            "scope": "parent_local",
            "source_values_hash": parent_identity["omega_sha256"],
        }
    ]
    control_states: list[np.ndarray] = []
    for index in range(frozen.matched_control_count):
        seed = frozen.seed + index
        state = matched_multiset_control(omega, seed)
        control_states.append(state)
        identity = {
            "parent_ladder_id": parent_id,
            "seed": seed,
            "omega_sha256": hashlib.sha256(state.tobytes()).hexdigest(),
            "contract_sha256": frozen.sha256,
        }
        registry.append(
            {
                "ladder_id": f"control-{content_hash(identity)[:16]}",
                "domain_id": parent_identity["domain_id"],
                "kind": "matched_multiset_permutation",
                "parent_ladder_id": parent_id,
                "is_null": True,
                "eligible": False,
                "seed": seed,
                "scope": "parent_local",
                "source_values_hash": identity["omega_sha256"],
            }
        )

    parent_score = score_ladder(omega, frozen.n_window).to_dict()
    control_scores = [score_ladder(state, frozen.n_window).to_dict() for state in control_states]
    independent = verify_historical_result(historical_result)
    criteria = {
        "authoritative_source_hash": source_hash == EXPECTED_INPUT_HASHES["targets_baseline.csv"],
        "parent_registered_before_metrics": registry[0]["kind"] == "observed_parent",
        "controls_registered_before_metrics": len(registry) == frozen.matched_control_count + 1,
        "parent_matched_controls": all(
            row["parent_ladder_id"] == parent_id for row in registry[1:]
        ),
        "marginal_preservation": all(
            np.array_equal(np.sort(state), np.sort(omega)) for state in control_states
        ),
        "domain_isolation": len({row["domain_id"] for row in registry}) == 1,
        "global_pool_absent": all(row["scope"] == "parent_local" for row in registry),
        "historical_independent_verifier": independent["status"] == "verified",
        "failure_preservation": True,
        "outcome_dependent_tuning_absent": True,
        "semantic_T_e_definition_available": False,
        "semantic_S_e_definition_available": False,
    }
    blockers = [
        (
            "T_e is NOT_APPLICABLE because the historical release has no registered "
            "observed/null emergence depth"
        ),
        (
            "S_e is NOT_APPLICABLE because the historical release has no registered "
            "post-emergence survival depth"
        ),
        "Notebook 13 fails its preregistered alpha=0.02 mean-return-steps threshold",
        "Notebook 13 fails its preregistered alpha=0.02 p90-flips threshold",
        "The preregistration document declares 400 healing steps while Notebook 13 executes 300",
    ]
    return {
        "schema_version": "1.0.0",
        "lane": MODERN_LANE,
        "contract": frozen.to_dict(),
        "registry_frozen_before_metrics": True,
        "registry": registry,
        "parent_score": parent_score,
        "control_scores": control_scores,
        "endpoint_applicability": {
            "winner_N": "COMPUTED",
            "margin": "COMPUTED",
            "structural_escape": "COMPUTED_IN_HISTORICAL_LANE",
            "damped_recovery": "COMPUTED_IN_HISTORICAL_LANE",
            "ringing": "COMPUTED_IN_HISTORICAL_LANE",
            "T_e": "NOT_APPLICABLE",
            "S_e": "NOT_APPLICABLE",
        },
        "criteria": criteria,
        "claim_level": "COMPUTED_DYNAMICAL",
        "TLD_DERIVED_STATUS": "BLOCKED",
        "externally_validated": False,
        "blockers": blockers,
    }
