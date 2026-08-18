from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMA_PATHS = {
    "claim-boundary": "claim-boundary/v1.schema.json",
    "domain-pack": "domain-pack/v1.schema.json",
    "failure": "evidence/failure-v1.schema.json",
    "field-table": "field-table/v1.schema.json",
    "local-brot": "local-brot/v1.schema.json",
    "run-spec": "run-spec/v1.schema.json",
    "tbx": "tbx/v1.schema.json",
    "tld-claim-adjudication": "tld-claim-adjudication/v1.schema.json",
    "tld-domain-pack": "tld-domain-pack/v1.schema.json",
    "tld-endpoint-table": "tld-endpoint-table/v1.schema.json",
    "tld-independent-verification": "independent-verification/v1.schema.json",
    "tld-ladder-registry": "tld-ladder-registry/v1.schema.json",
    "tld-perturbation-contract": "tld-perturbation-contract/v1.schema.json",
    "tld-preregistration-result": "tld-preregistration-result/v1.schema.json",
    "tld-release-source": "tld-release-source/v1.schema.json",
    "tld-run-contract": "tld-run-contract/v1.schema.json",
    "tld-tbx-profile": "tld-tbx-profile/v1.schema.json",
    "tld-trajectory-trace": "tld-trajectory-trace/v1.schema.json",
}


@cache
def load_schema(name: str) -> dict[str, Any]:
    try:
        relative_path = SCHEMA_PATHS[name]
    except KeyError as error:
        raise ValueError(f"Unknown schema: {name}") from error
    resource = files("torusbrot.schemas").joinpath(relative_path)
    return json.loads(resource.read_text(encoding="utf-8"))


@cache
def schema_registry() -> Registry:
    registry = Registry()
    for name in SCHEMA_PATHS:
        schema = load_schema(name)
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return registry


@cache
def validator(name: str) -> Draft202012Validator:
    schema = load_schema(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=schema_registry())


def validate_with_schema(name: str, value: Any) -> list[str]:
    errors = sorted(validator(name).iter_errors(value), key=lambda error: list(error.absolute_path))
    result: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        result.append(f"{location}: {error.message}")
    return result
