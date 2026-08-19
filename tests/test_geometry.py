from __future__ import annotations

import numpy as np
from torusbrot.geometry.channels import signed_bidirectional_separation
from torusbrot.geometry.metrology import interior_relative_curvature, measurement_repeat_policy
from torusbrot.geometry.models import ObservableClass
from torusbrot.geometry.scout import geometry_scout
from torusbrot.geometry.synthetic import build_synthetic_fixtures
from torusbrot.schema_validation import load_schema, validate_with_schema

GEOMETRY_SCHEMAS = (
    "boundary-condition",
    "coordinate-system",
    "effective-parent-audit",
    "field-component",
    "field-observation",
    "geometric-scale-registry",
    "geometry-aware-null-registry",
    "geometry-claim-adjudication",
    "geometry-indexed-domain-pack",
    "geometry-operator-registry",
    "geometry-perturbation-registry",
    "geometry-tbx-profile",
    "mask-contract",
    "nested-replicate-registry",
    "operation-depth-registry",
    "parent-registry",
    "projection-registry",
    "representation-agreement",
    "scout-eligibility",
    "structure-channel-registry",
)


def test_all_geometry_schemas_load() -> None:
    assert len(GEOMETRY_SCHEMAS) == 20
    for name in GEOMETRY_SCHEMAS:
        assert load_schema(name)["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_geometry_pack_requires_complete_custody() -> None:
    value = {
        "schema_version": "1.0.0",
        "standard_version": "Geometry-Indexed Domain Pack Standard v1.0",
        "domain_id": "synthetic.wave-v1",
        "source_id": "synthetic-registry",
        "stable_source_identifier": "tfs:synthetic:SYN-03",
        "source_url": "https://torus-field-studio.dev/synthetic/SYN-03",
        "license": "CC0-1.0",
        "raw_source_hashes": ["a" * 64],
        "field_kind": "SCALAR_FIELD_2D",
        "coordinate_system_id": "cartesian-32",
        "boundary_condition_id": "periodic-xy",
        "mask_contract_id": "full-support",
        "missing_data_semantics": "REJECT",
        "field_component_ids": ["scalar"],
        "independent_parent_key": "parent_id",
        "nested_replicate_key": None,
        "experimental_run_key": None,
        "condition_key": None,
        "source_acquisition_identity": "deterministic-seed-300",
        "canonicalization_identity": "float64-preserve-grid",
        "projection_registry_identity": "projection-registry-v1",
        "null_registry_identity": "null-registry-v1",
        "perturbation_registry_identity": "perturbation-registry-v1",
        "domain_baseline_identity": "iid-matched-baseline-v1",
        "claim_ceiling": "COMPUTED_DYNAMICAL",
        "known_limitations": ["synthetic fixture"],
    }
    assert validate_with_schema("geometry-indexed-domain-pack", value) == []
    del value["coordinate_system_id"]
    assert validate_with_schema("geometry-indexed-domain-pack", value)


def test_synthetic_registry_has_exact_required_fixture_set() -> None:
    first = build_synthetic_fixtures(300)
    second = build_synthetic_fixtures(300)
    assert [item.fixture_id for item in first] == [f"SYN-{index:02d}" for index in range(1, 26)]
    assert all(
        np.array_equal(left.field, right.field) for left, right in zip(first, second, strict=True)
    )


def test_scout_authorizes_only_complete_nondegenerate_fields() -> None:
    parents = [np.arange(16, dtype=float).reshape(4, 4) + index for index in range(8)]
    nulls = [[np.rot90(parent), np.flipud(parent)] for parent in parents]
    receipt = geometry_scout(
        domain_id="synthetic.scout",
        parent_fields=parents,
        null_children_by_parent=nulls,
        coordinates_complete=True,
        units_resolved=True,
        orientation_known=True,
        components_registered=True,
        mask_valid=True,
        support_sufficient=True,
        minimum_parents=8,
        projection_justified=True,
        boundary_known=True,
        operation_depth_applicable=False,
        geometric_scale_applicable=True,
        baseline_available=True,
    )
    assert receipt.status.value == "ELIGIBLE"
    assert receipt.closure_authorized
    blocked = geometry_scout(
        domain_id="synthetic.constant",
        parent_fields=[np.ones((4, 4)) for _ in range(8)],
        null_children_by_parent=[[np.ones((4, 4)), np.ones((4, 4))] for _ in range(8)],
        coordinates_complete=True,
        units_resolved=True,
        orientation_known=True,
        components_registered=True,
        mask_valid=True,
        support_sufficient=True,
        minimum_parents=8,
        projection_justified=True,
        boundary_known=True,
        operation_depth_applicable=False,
        geometric_scale_applicable=True,
        baseline_available=True,
    )
    assert blocked.status.value == "INELIGIBLE_DEGENERATE"
    assert not blocked.closure_authorized


def test_signed_separation_is_bidirectional_and_family_corrected() -> None:
    rng = np.random.default_rng(1)
    nulls = rng.normal(scale=0.05, size=(12, 127))
    upper = signed_bidirectional_separation(np.full(12, 1.0), nulls, family_size=2)
    lower = signed_bidirectional_separation(np.full(12, -1.0), nulls, family_size=2)
    assert upper.direction == "UPPER"
    assert lower.direction == "LOWER"
    assert upper.familywise_p <= 0.05
    assert lower.familywise_p <= 0.05


def test_relative_curvature_excludes_endpoints_and_rejects_flatline() -> None:
    coordinates = list(range(6, 15))
    trace = np.asarray([1.5, 1.2, 0.9, 0.5, 0.45, 0.44, 0.43, 0.42, 0.41])
    nulls = np.tile(np.linspace(1.5, 0.5, 9), (20, 1))
    result = interior_relative_curvature(
        trace, coordinates, null_traces=nulls, bootstrap_samples=16
    )
    assert result.endpoint_excluded
    assert result.selected_elbow in coordinates[1:-1]
    assert not result.boundary_pinning
    flat = interior_relative_curvature(np.ones(9), coordinates)
    assert flat.status == "REJECTED_FLATLINE_OR_ZERO_VARIANCE"


def test_repeat_policy_never_uses_timing_average_for_semantics() -> None:
    semantic = measurement_repeat_policy(ObservableClass.DETERMINISTIC_SEMANTIC)
    timing = measurement_repeat_policy(ObservableClass.TIMING_OR_RESOURCE)
    assert semantic["duplicate_clean_replay"] is True
    assert semantic["timing_average_claim_bearing"] is False
    assert timing["causal_authority"] is False
