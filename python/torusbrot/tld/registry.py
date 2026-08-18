"""Registry-first identity materialization for TLD parents and controls."""

from __future__ import annotations

from typing import Any

from ..models import content_hash
from .contracts import HistoricalTldIContract


def build_registries(
    *, baseline_sha256: str, values_sha256: str, contract: HistoricalTldIContract
) -> dict[str, list[dict[str, Any]]]:
    canonicalization = {
        "row_order": "source_csv_order",
        "omega": "natural_log(value)",
        "sigma_omega": "sigma/value",
    }
    canonicalization_hash = content_hash(canonicalization)
    perturbation_hash = content_hash(
        {
            "operator": "historical_notebook13_adjacent_order_mutation",
            "p_swap": contract.p_swap_escape,
            "seed": contract.seed,
        }
    )
    parent_identity = {
        "domain_id": "torus-tld-i-baseline-v1",
        "kind": "observed_parent",
        "source_values_hash": values_sha256,
        "canonicalization_hash": canonicalization_hash,
    }
    parent_id = f"ladder-{content_hash(parent_identity)[:16]}"
    parent = {
        "ladder_id": parent_id,
        "domain_id": "torus-tld-i-baseline-v1",
        "kind": "observed_parent",
        "parent_ladder_id": None,
        "omega_construction_rule": "natural_log(value), source row order",
        "adjacency_topology": "ordered_path",
        "is_null": False,
        "eligible": True,
        "seed": contract.seed,
        "source_values_hash": values_sha256,
        "canonicalization_hash": canonicalization_hash,
        "perturbation_contract_hash": perturbation_hash,
        "notes": "Registered before endpoint computation; source CSV SHA-256 " + baseline_sha256,
    }
    control_identity = {"parent": parent_id, "kind": "alpha_zero_mechanistic_control"}
    control = {
        "ladder_id": f"control-{content_hash(control_identity)[:16]}",
        "domain_id": "torus-tld-i-baseline-v1",
        "kind": "alpha_zero_mechanistic_control",
        "parent_ladder_id": parent_id,
        "omega_construction_rule": "same parent, healing alpha=0.0",
        "adjacency_topology": "ordered_path",
        "is_null": True,
        "eligible": False,
        "seed": contract.seed,
        "source_values_hash": values_sha256,
        "canonicalization_hash": canonicalization_hash,
        "perturbation_contract_hash": perturbation_hash,
        "notes": "Historical mechanistic control; not a modern matched structural null",
    }
    return {"parents": [parent], "ladders": [parent], "controls": [control]}
