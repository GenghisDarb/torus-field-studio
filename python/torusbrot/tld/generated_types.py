"""Generated from canonical JSON Schemas. Do not edit by hand."""

from __future__ import annotations

from typing import Any, Literal, Required, TypedDict

SCHEMA_IDS = {
    "independent-verification/v1.schema.json": "https://torus-field-studio.dev/schemas/independent-verification/v1.schema.json",
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


class IndependentVerificationReceipt(TypedDict, total=False):
    schema_version: Required[Literal["1.0.0"]]
    status: Required[Literal["verified", "rejected"]]
    verifier: Required[str]
    result_sha256: Required[Any]
    checks: Required[dict[str, Any]]


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
