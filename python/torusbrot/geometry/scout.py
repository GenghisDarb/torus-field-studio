from __future__ import annotations

import hashlib
from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from torusbrot.geometry.models import ScoutReceipt, ScoutStatus

FloatArray = NDArray[np.float64]


def _receipt_id(domain_id: str, arrays: Sequence[FloatArray]) -> str:
    digest = hashlib.sha256(domain_id.encode())
    for array in arrays:
        digest.update(np.asarray(array, dtype=np.float64).tobytes())
    return f"scout-{digest.hexdigest()[:16]}"


def geometry_scout(
    *,
    domain_id: str,
    parent_fields: Sequence[FloatArray],
    null_children_by_parent: Sequence[Sequence[FloatArray]],
    coordinates_complete: bool,
    units_resolved: bool,
    orientation_known: bool,
    components_registered: bool,
    mask_valid: bool,
    support_sufficient: bool,
    minimum_parents: int,
    projection_justified: bool,
    boundary_known: bool,
    operation_depth_applicable: bool,
    geometric_scale_applicable: bool,
    baseline_available: bool,
    source_bytes_verified: bool = True,
    sensitivity_adequate: bool | None = None,
    nested_replicates_identified: bool = True,
    failure_ledger_active: bool = True,
) -> ScoutReceipt:
    arrays = [np.asarray(field, dtype=np.float64) for field in parent_fields]
    materialized = bool(arrays) and source_bytes_verified
    finite = bool(arrays) and all(np.all(np.isfinite(field)) for field in arrays)
    nonconstant = finite and all(float(np.var(field)) > 0.0 for field in arrays)
    parent_support = len(arrays) >= minimum_parents
    null_complete = len(null_children_by_parent) == len(arrays) and all(
        len(children) >= 2
        and all(np.all(np.isfinite(np.asarray(child, dtype=np.float64))) for child in children)
        for children in null_children_by_parent
    )
    checks: dict[str, bool | str] = {
        "source_bytes_verified": source_bytes_verified,
        "materialized": materialized,
        "coordinates_complete": coordinates_complete,
        "units_resolved": units_resolved,
        "orientation_known": orientation_known,
        "components_registered": components_registered,
        "mask_valid": mask_valid,
        "missingness_within_bounds": finite,
        "nondegenerate": nonconstant,
        "variance_finite": finite,
        "support_sufficient": support_sufficient,
        "resolution_sufficient": support_sufficient,
        "independent_parent_support": parent_support,
        "effective_parent_support": parent_support,
        "nested_replicates_identified": nested_replicates_identified,
        "null_ensemble_complete": null_complete,
        "nulls_finite": null_complete,
        "projection_deterministic": True,
        "projection_not_outcome_selected": projection_justified,
        "projection_justified": projection_justified,
        "boundary_conditions_known": boundary_known,
        "operation_depth_applicable": operation_depth_applicable,
        "geometric_scale_applicable": geometric_scale_applicable,
        "domain_baseline_materializable": baseline_available,
        "failure_ledger_active": failure_ledger_active,
        "sensitivity_adequate": (
            "NOT_APPLICABLE" if sensitivity_adequate is None else sensitivity_adequate
        ),
    }
    failure_codes: list[str] = []
    status = ScoutStatus.ELIGIBLE
    if not materialized:
        status = ScoutStatus.MATERIALIZATION_BLOCKED
        failure_codes.append("SOURCE_OR_FIELD_NOT_MATERIALIZED")
    elif not coordinates_complete or not orientation_known or not boundary_known:
        status = ScoutStatus.INELIGIBLE_COORDINATE_AMBIGUITY
        failure_codes.append("COORDINATE_OR_BOUNDARY_AMBIGUITY")
    elif not units_resolved:
        status = ScoutStatus.INELIGIBLE_UNIT_AMBIGUITY
        failure_codes.append("UNIT_AMBIGUITY")
    elif not finite or not nonconstant or not mask_valid or not support_sufficient:
        status = ScoutStatus.INELIGIBLE_DEGENERATE
        failure_codes.append("FIELD_DEGENERATE_OR_SUPPORT_INVALID")
    elif not parent_support:
        status = ScoutStatus.INELIGIBLE_PARENT_SUPPORT
        failure_codes.append("INDEPENDENT_PARENT_SUPPORT_INSUFFICIENT")
    elif not null_complete:
        status = ScoutStatus.INELIGIBLE_NULL_INCOMPLETE
        failure_codes.append("MATCHED_NULL_ENSEMBLE_INCOMPLETE")
    elif not projection_justified:
        status = ScoutStatus.INELIGIBLE_PROJECTION_UNJUSTIFIED
        failure_codes.append("PROJECTION_UNJUSTIFIED_OR_OUTCOME_SELECTED")
    elif not operation_depth_applicable and not geometric_scale_applicable:
        status = ScoutStatus.INELIGIBLE_OPERATION_DEPTH_NOT_APPLICABLE
        failure_codes.append("NO_REGISTERED_OPERATION_DEPTH_OR_GEOMETRIC_SCALE")
    elif not baseline_available:
        status = ScoutStatus.INELIGIBLE_BASELINE_UNAVAILABLE
        failure_codes.append("DOMAIN_BASELINE_UNAVAILABLE")
    elif sensitivity_adequate is False:
        status = ScoutStatus.MATERIALIZATION_BLOCKED
        failure_codes.append("INSTRUMENT_SENSITIVITY_INADEQUATE_INCONCLUSIVE")
    elif not components_registered or not nested_replicates_identified or not failure_ledger_active:
        status = ScoutStatus.MATERIALIZATION_BLOCKED
        failure_codes.append("REGISTRY_OR_FAILURE_LEDGER_INCOMPLETE")
    total = max(len(parent_fields), 1)
    materialized_fraction = sum(np.all(np.isfinite(field)) for field in arrays) / total
    return ScoutReceipt(
        scout_id=_receipt_id(domain_id, arrays),
        domain_id=domain_id,
        status=status,
        closure_authorized=status == ScoutStatus.ELIGIBLE,
        checks=checks,
        materialized_fraction=float(materialized_fraction),
        effective_parent_count=float(len(arrays)),
        orbit_length_summary=None,
        failure_codes=failure_codes,
    )
