"""Generated from canonical JSON Schemas. Do not edit by hand."""

from __future__ import annotations

from typing import Any, Literal, Required, TypedDict

SCHEMA_IDS = {
    "boundary-condition/v1.schema.json": "https://torus-field-studio.dev/schemas/boundary-condition/v1.schema.json",
    "coordinate-system/v1.schema.json": "https://torus-field-studio.dev/schemas/coordinate-system/v1.schema.json",
    "effective-parent-audit/v1.schema.json": "https://torus-field-studio.dev/schemas/effective-parent-audit/v1.schema.json",
    "field-component/v1.schema.json": "https://torus-field-studio.dev/schemas/field-component/v1.schema.json",
    "field-observation/v1.schema.json": "https://torus-field-studio.dev/schemas/field-observation/v1.schema.json",
    "geometric-scale-registry/v1.schema.json": "https://torus-field-studio.dev/schemas/geometric-scale-registry/v1.schema.json",
    "geometry-aware-null-registry/v1.schema.json": "https://torus-field-studio.dev/schemas/geometry-aware-null-registry/v1.schema.json",
    "geometry-claim-adjudication/v1.schema.json": "https://torus-field-studio.dev/schemas/geometry-claim-adjudication/v1.schema.json",
    "geometry-indexed-domain-pack/v1.schema.json": "https://torus-field-studio.dev/schemas/geometry-indexed-domain-pack/v1.schema.json",
    "geometry-operator-registry/v1.schema.json": "https://torus-field-studio.dev/schemas/geometry-operator-registry/v1.schema.json",
    "geometry-perturbation-registry/v1.schema.json": "https://torus-field-studio.dev/schemas/geometry-perturbation-registry/v1.schema.json",
    "geometry-tbx-profile/v1.schema.json": "https://torus-field-studio.dev/schemas/geometry-tbx-profile/v1.schema.json",
    "independent-verification/v1.schema.json": "https://torus-field-studio.dev/schemas/independent-verification/v1.schema.json",
    "mask-contract/v1.schema.json": "https://torus-field-studio.dev/schemas/mask-contract/v1.schema.json",
    "nested-replicate-registry/v1.schema.json": "https://torus-field-studio.dev/schemas/nested-replicate-registry/v1.schema.json",
    "operation-depth-registry/v1.schema.json": "https://torus-field-studio.dev/schemas/operation-depth-registry/v1.schema.json",
    "parent-registry/v1.schema.json": "https://torus-field-studio.dev/schemas/parent-registry/v1.schema.json",
    "projection-registry/v1.schema.json": "https://torus-field-studio.dev/schemas/projection-registry/v1.schema.json",
    "representation-agreement/v1.schema.json": "https://torus-field-studio.dev/schemas/representation-agreement/v1.schema.json",
    "scout-eligibility/v1.schema.json": "https://torus-field-studio.dev/schemas/scout-eligibility/v1.schema.json",
    "structure-channel-registry/v1.schema.json": "https://torus-field-studio.dev/schemas/structure-channel-registry/v1.schema.json",
    "tld-claim-adjudication/v1.schema.json": "https://torus-field-studio.dev/schemas/tld-claim-adjudication/v1.schema.json",
    "tld-domain-pack/v1.schema.json": "https://torus-field-studio.dev/schemas/tld-domain-pack/v1.schema.json",
    "tld-endpoint-table/v1.schema.json": "https://torus-field-studio.dev/schemas/tld-endpoint-table/v1.schema.json",
    "tld-ladder-registry/v1.schema.json": "https://torus-field-studio.dev/schemas/tld-ladder-registry/v1.schema.json",
    "tld-perturbation-contract/v1.schema.json": "https://torus-field-studio.dev/schemas/tld-perturbation-contract/v1.schema.json",
    "tld-preregistration-result/v1.schema.json": "https://torus-field-studio.dev/schemas/tld-preregistration-result/v1.schema.json",
    "tld-release-source/v1.schema.json": "https://torus-field-studio.dev/schemas/tld-release-source/v1.schema.json",
    "tld-run-contract/v1.schema.json": "https://torus-field-studio.dev/schemas/tld-run-contract/v1.schema.json",
    "tld-tbx-profile/v1.schema.json": "https://torus-field-studio.dev/schemas/tld-tbx-profile/v1.schema.json",
    "tld-trajectory-trace/v1.schema.json": "https://torus-field-studio.dev/schemas/tld-trajectory-trace/v1.schema.json",
}


class GeometryBoundaryCondition(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    boundary_condition_id: Required[str]
    axis_conditions: Required[list[dict[str, Any]]]
    source_basis: Required[str]
    padding_allowed: Required[bool]


class GeometryCoordinateSystem(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    coordinate_system_id: Required[str]
    axes: Required[list[dict[str, Any]]]
    reference_frame: Required[str]
    grid_regularity: Required[
        Literal["REGULAR", "IRREGULAR", "GRAPH", "MANIFOLD", "NOT_APPLICABLE"]
    ]
    orientation: Required[str]
    periodicity: Required[list[bool]]


class GeometryEffectiveParentAudit(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    audit_id: Required[str]
    nominal_parent_count: Required[int]
    eligible_parent_count: Required[int]
    effective_parent_count: Required[float]
    nested_replicate_count: Required[int]
    dependence_method: Required[str]
    minimum_required: Required[float]
    status: Required[Literal["PASS", "FAIL", "INCONCLUSIVE"]]


class GeometryFieldComponent(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    component_id: Required[str]
    name: Required[str]
    unit: Required[str]
    role: Required[Literal["SCALAR", "VECTOR_COMPONENT", "TENSOR_COMPONENT", "CATEGORY", "WEIGHT"]]
    orientation: Required[str | None]
    value_semantics: Required[str]


class GeometryFieldObservation(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    observation_id: Required[str]
    domain_id: Required[str]
    parent_id: Required[str]
    replicate_id: Required[str | None]
    run_id: Required[str | None]
    condition_id: Required[str | None]
    component_ids: Required[list[str]]
    array_sha256: Required[str]
    shape: Required[list[int]]
    dtype: Required[str]
    mask_id: Required[str | None]
    acquisition_identity: Required[str]


class GeometryScaleRegistry(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    registry_id: Required[str]
    symbol: Required[Literal["ell"]]
    unit: Required[str]
    scales: Required[list[float]]
    selection_rule: Required[str]


class GeometryAwareNullRegistry(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    registry_id: Required[str]
    selection_timing: Required[Literal["PRE_OUTCOME_REGISTERED"]]
    families: Required[list[dict[str, Any]]]


class GeometryClaimAdjudication(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    run_id: Required[str]
    method_id: Required[str]
    method_mode: Required[
        Literal["BINARY_STRICT", "BINARY_HIERARCHICAL", "NONBINARY_EVIDENCE_VECTOR"]
    ]
    scout_status: Required[Literal["ELIGIBLE", "INELIGIBLE", "INCONCLUSIVE"]]
    channel_results: Required[dict[str, Any]]
    scientific_outcome: Required[
        Literal[
            "V030_GEOMETRY_INDEXED_METHOD_NOT_ESTABLISHED",
            "GEOMETRY_INDEXED_TLD_HELDOUT_POSITIVE_UNDER_FROZEN_GATES",
            "GEOMETRY_INDEXED_TLD_HELDOUT_NEGATIVE_UNDER_FROZEN_GATES",
            "GEOMETRY_INDEXED_TLD_HELDOUT_MIXED_WITH_EXACT_COMPONENTS",
            "GEOMETRY_INDEXED_TLD_HELDOUT_EXECUTION_BLOCKED",
            "GEOMETRY_INDEXED_TLD_HELDOUT_INVALIDATED_BY_PROTOCOL",
            "GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY",
        ]
    ]
    T_e: Required[int | str | None]
    S_e: Required[float | str | None]
    winner_N: Required[int | str | None]
    geometric_scale: Required[float | str | None]
    TLD_DERIVED: Required[Literal["SUPPORTED", "BLOCKED", "NOT_APPLICABLE"]]
    EXTERNALLY_VALIDATED: Required[Literal[False]]
    claim_ceiling: Required[Literal["DESCRIPTIVE", "COMPUTED_DYNAMICAL", "CALIBRATED_ASSAY"]]
    blockers: Required[list[str]]


class GeometryIndexedDomainPack(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    standard_version: Required[Literal["Geometry-Indexed Domain Pack Standard v1.0"]]
    domain_id: Required[str]
    source_id: Required[str]
    stable_source_identifier: Required[str]
    source_url: Required[str]
    license: Required[str]
    raw_source_hashes: Required[list[str]]
    field_kind: Required[
        Literal[
            "SEQUENCE_1D",
            "SCALAR_FIELD_2D",
            "VECTOR_FIELD_2D",
            "SCALAR_VOLUME_3D",
            "VECTOR_VOLUME_3D",
            "SPATIOTEMPORAL_SCALAR_FIELD",
            "SPATIOTEMPORAL_VECTOR_FIELD",
            "POINT_CLOUD",
            "MANIFOLD_SAMPLES",
            "GRAPH_GEOMETRY",
            "CORRELATION_GEOMETRY",
            "MULTIMODAL_COUPLED_FIELD",
        ]
    ]
    coordinate_system_id: Required[str]
    boundary_condition_id: Required[str]
    mask_contract_id: Required[str]
    missing_data_semantics: Required[
        Literal["REJECT", "MASK", "REGISTERED_IMPUTATION", "NOT_APPLICABLE"]
    ]
    field_component_ids: Required[list[str]]
    independent_parent_key: Required[str]
    nested_replicate_key: Required[str | None]
    experimental_run_key: Required[str | None]
    condition_key: Required[str | None]
    source_acquisition_identity: Required[str]
    canonicalization_identity: Required[str]
    projection_registry_identity: Required[str]
    null_registry_identity: Required[str]
    perturbation_registry_identity: Required[str]
    domain_baseline_identity: Required[str]
    claim_ceiling: Required[
        Literal["DESCRIPTIVE", "COMPUTED_DYNAMICAL", "CALIBRATED_ASSAY", "EXTERNAL_VALIDATION"]
    ]
    known_limitations: Required[list[str]]


class GeometryOperatorRegistry(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    registry_id: Required[str]
    operators: Required[list[dict[str, Any]]]


class GeometryPerturbationRegistry(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    registry_id: Required[str]
    selection_timing: Required[Literal["PRE_OUTCOME_REGISTERED"]]
    perturbations: Required[list[dict[str, Any]]]


class GeometryTbxProfile(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    profile_id: Required[Literal["geometry-tbx-v1"]]
    required_member_roles: Required[list[str]]
    forbidden_claims: Required[list[str]]
    independent_verifier_required: Required[Literal[True]]
    raw_arrays_required: Required[Literal[True]]
    registry_hashes_required: Required[Literal[True]]


class IndependentVerificationReceipt(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    status: Required[Literal["verified", "rejected"]]
    verifier: Required[str]
    result_sha256: Required[Any]
    checks: Required[dict[str, Any]]


class GeometryMaskContract(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    mask_id: Required[str]
    semantics: Required[
        Literal["VALID_SUPPORT", "INVALID_SUPPORT", "REGION_OF_INTEREST", "NOT_APPLICABLE"]
    ]
    true_means: Required[Literal["INCLUDE", "EXCLUDE", "NOT_APPLICABLE"]]
    mask_sha256: Required[str | None]
    selection_timing: Required[
        Literal["SOURCE_DEFINED", "PRE_OUTCOME_REGISTERED", "NOT_APPLICABLE"]
    ]
    mutable_after_freeze: Required[Literal[False]]


class GeometryNestedReplicateRegistry(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    registry_id: Required[str]
    nested_replicate_key: Required[str | None]
    replicates: Required[list[dict[str, Any]]]


class GeometryOperationDepthRegistry(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    registry_id: Required[str]
    symbol: Required[Literal["r"]]
    depths: Required[list[int]]
    recursive_semantics: Required[str]
    te_applicable: Required[bool]


class GeometryParentRegistry(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    registry_id: Required[str]
    independent_parent_key: Required[str]
    parents: Required[list[dict[str, Any]]]


class GeometryProjectionRegistry(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    registry_id: Required[str]
    projections: Required[list[dict[str, Any]]]


class GeometryRepresentationAgreement(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    agreement_id: Required[str]
    projection_ids: Required[list[str]]
    faithful_projection_count: Required[int]
    effect_direction_agreement: Required[bool]
    rank_agreement: Required[float | None]
    mode_agreement: Required[bool | None]
    tolerance_rule: Required[str]
    status: Required[Literal["PASS", "FAIL", "INCONCLUSIVE"]]


class GeometryScoutEligibility(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    scout_id: Required[str]
    domain_id: Required[str]
    checks: Required[dict[str, Any]]
    materialized_fraction: Required[float]
    effective_parent_count: Required[float]
    orbit_length_summary: Required[dict[str, Any] | None]
    closure_authorized: Required[bool]
    status: Required[Literal["ELIGIBLE", "INELIGIBLE", "INCONCLUSIVE"]]
    failure_codes: Required[list[str]]


class GeometryStructureChannelRegistry(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    registry_id: Required[str]
    channels: Required[list[dict[str, Any]]]
    fusion_policy: Required[
        Literal["STRICT_CONJUNCTION", "HIERARCHICAL_GATE", "EVIDENCE_VECTOR_NO_NUMERIC_POOLING"]
    ]


class TldClaimAdjudication(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    lane: Required[str]
    claim_level: Required[Literal["COMPUTED_DYNAMICAL", "TLD_DERIVED"]]
    tld_derived_status: Required[Literal["PERMITTED", "BLOCKED", "NOT_APPLICABLE"]]
    externally_validated: Required[Literal[False]]
    blockers: Required[list[str]]
    forbidden_claims: Required[list[str]]


class TldDomainPack(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    domain_id: Required[str]
    doi: Required[Literal["10.5281/zenodo.18080090"]]
    source_input: Required[Literal["targets_baseline.csv"]]
    source_sha256: Required[Any]
    row_order: Required[Literal["source_csv_order"]]
    rows: Required[list[dict[str, Any]]]
    canonicalization: Required[Literal["none; preserve source scalar bytes and row order"]]
    ladderization: Required[Literal["omega=natural_log(value); sigma_omega=sigma/value"]]
    adjacency_topology: Required[Literal["ordered_path"]]
    units: Required[Literal["dimensionless"]]
    duplicate_policy: Required[Literal["preserve source rows"]]
    missing_value_policy: Required[Literal["reject"]]
    claim_authority: Required[Literal["COMPUTED_DYNAMICAL"]]
    license: Required[str]


class TldEndpointTable(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    rows: Required[list[dict[str, Any]]]


class TldLadderRegistry(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    ladders: Required[list[dict[str, Any]]]


class TldPerturbationContract(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    contract_id: Required[str]
    escape_operator: Required[str]
    healing_operator: Required[str]
    p_swap: Required[float]
    epsilon: Required[float]
    alphas: Required[list[float]]
    max_escape_steps: Required[int]
    max_heal_steps: Required[int]
    seed_policy: Required[str]


class TldPreregistrationResult(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    contract_sha256: Required[Any]
    criteria: Required[dict[str, Any]]
    passed: Required[int]
    failed: Required[int]


class TldReleaseSourceRegistry(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    source_id: Required[str]
    doi: Required[Literal["10.5281/zenodo.18080090"]]
    record_url: Required[str]
    title: Required[str]
    archive: Required[dict[str, Any]]
    input_sha256: Required[dict[str, Any]]
    confirmatory_notebooks: Required[Literal[[13, 14]]]
    exploratory_notebooks_used_as_evidence: Required[Literal[False]]
    license: Required[str]
    claim_authority_ceiling: Required[Literal["COMPUTED_DYNAMICAL"]]


class TldRunContract(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    lane: Required[
        Literal["HISTORICAL_PUBLISHED_RELEASE_REPRODUCTION", "MODERN_V21_COMPLIANCE_EXTENSION"]
    ]
    doi: Required[Literal["10.5281/zenodo.18080090"]]
    contract_sha256: Required[Any]
    seed: Required[int]
    n_window: Required[list[int]]
    n_center: Required[int]
    operators: Required[dict[str, Any]]
    trials: Required[dict[str, Any]]
    claim_ceiling: Required[Literal["COMPUTED_DYNAMICAL", "TLD_DERIVED"]]


class TldTbxProfileDeclaration(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    profile: Required[Literal["tld-i-historical-v1", "tld-i-combined-v1", "tld-i-modern-v21"]]
    lane: Required[str]
    required_members: Required[list[str]]
    classification_precedes_rendering: Required[Literal[True]]
    interpolation_used_for_metrics: Required[Literal[False]]


class TldTrajectoryTrace(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    rows: Required[list[dict[str, Any]]]
