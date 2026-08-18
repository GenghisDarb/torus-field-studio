from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

from .schema_validation import validate_with_schema


class ClaimLevel(IntEnum):
    ILLUSTRATIVE_ANALYTIC = 0
    COMPUTED_DYNAMICAL = 1
    TLD_DERIVED = 2
    EXTERNALLY_VALIDATED = 3

    @classmethod
    def parse(cls, value: str | ClaimLevel) -> ClaimLevel:
        return value if isinstance(value, cls) else cls[value]


def canonical_json(value: Any, *, pretty: bool = False) -> bytes:
    options: dict[str, Any] = {"sort_keys": True, "ensure_ascii": False, "allow_nan": False}
    if pretty:
        options.update(indent=2)
    else:
        options.update(separators=(",", ":"))
    return (json.dumps(value, **options) + "\n").encode()


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _load_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_dir():
        source = source / "domain.json"
    return json.loads(source.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class DomainPack:
    domain_id: str
    title: str
    ladder: tuple[float, ...]
    claim_authority: ClaimLevel = ClaimLevel.COMPUTED_DYNAMICAL
    description: str = ""
    source: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0.0"

    @classmethod
    def load(cls, path: str | Path) -> DomainPack:
        data = _load_json(path)
        errors = validate_domain_pack(data)
        if errors:
            raise ValueError("Invalid domain pack: " + "; ".join(errors))
        return cls(
            domain_id=data["domain_id"],
            title=data["title"],
            ladder=tuple(float(value) for value in data["ladder"]),
            claim_authority=ClaimLevel.parse(data["claim_authority"]),
            description=data.get("description", ""),
            source=data.get("source", {}),
            schema_version=data["schema_version"],
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["ladder"] = list(self.ladder)
        result["claim_authority"] = self.claim_authority.name
        return result

    @property
    def sha256(self) -> str:
        return content_hash(self.to_dict())


@dataclass(frozen=True)
class MatchedNullPolicy:
    kind: str = "preserve_multiset_shuffle"
    count: int = 12
    seed: int = 1407

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None) -> MatchedNullPolicy:
        value = value or {}
        return cls(
            kind=str(value.get("kind", "preserve_multiset_shuffle")),
            count=int(value.get("count", 12)),
            seed=int(value.get("seed", 1407)),
        )

    @classmethod
    def from_file(cls, path: str | Path) -> MatchedNullPolicy:
        return cls.from_mapping(_load_json(path))


@dataclass(frozen=True)
class ClassificationRules:
    separation_threshold: float = 0.08
    nss_threshold: float = 1.0
    survival_threshold: float = 0.6
    recovery_threshold: float = 0.78
    escape_threshold: float = 0.46

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None) -> ClassificationRules:
        value = value or {}
        parsed = {key: float(value.get(key, default)) for key, default in asdict(cls()).items()}
        return cls(**parsed)


@dataclass(frozen=True)
class GridSpec:
    width: int = 56
    height: int = 40


@dataclass(frozen=True)
class RunSpec:
    engine: str
    seed: int
    domain_id: str
    claim_level: ClaimLevel
    grid: GridSpec
    parameters: dict[str, Any]
    classification_rules: ClassificationRules
    null_policy: MatchedNullPolicy
    schema_version: str = "1.0.0"

    @classmethod
    def from_file(cls, path: str | Path) -> RunSpec:
        data = _load_json(path)
        errors = validate_run_spec(data)
        if errors:
            raise ValueError("Invalid run specification: " + "; ".join(errors))
        return cls(
            engine=data["engine"],
            seed=int(data["seed"]),
            domain_id=data.get("domain_id", "unregistered"),
            claim_level=ClaimLevel.parse(data.get("claim_level", "COMPUTED_DYNAMICAL")),
            grid=GridSpec(**data["grid"]),
            parameters=data.get("parameters", {}),
            classification_rules=ClassificationRules.from_mapping(data.get("classification_rules")),
            null_policy=MatchedNullPolicy.from_mapping(data.get("null_policy")),
            schema_version=data["schema_version"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine": self.engine,
            "seed": self.seed,
            "domain_id": self.domain_id,
            "claim_level": self.claim_level.name,
            "grid": asdict(self.grid),
            "parameters": self.parameters,
            "classification_rules": asdict(self.classification_rules),
            "null_policy": asdict(self.null_policy),
        }

    @property
    def sha256(self) -> str:
        return content_hash(self.to_dict())


@dataclass
class FieldPoint:
    index: int
    grid_x: int
    grid_y: int
    x: float
    y: float
    classification: str
    eligible: bool
    emerged: bool
    separated_from_null: bool
    closed: bool
    survived: bool
    escaped_from_reference: bool
    recovered: bool | None
    winner_N: int | None
    T_e: int | None
    S_e: float
    UI: float
    NSS: float
    SEP: float
    rms_to_parent: float
    iterations: int
    parent_id: str
    null_policy_id: str
    trace: list[dict[str, float | int | str]]
    failure_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FailureRecord:
    failure_id: str
    category: str
    stage: str
    message: str
    grid_x: int | None = None
    grid_y: int | None = None
    coordinate: dict[str, float] | None = None
    recoverable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuditReport:
    valid: bool
    run_id: str
    checked_files: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    @property
    def issue_codes(self) -> tuple[str, ...]:
        return tuple(error.partition(":")[0] for error in self.errors)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["issue_codes"] = list(self.issue_codes)
        return result


def validate_domain_pack(data: dict[str, Any]) -> list[str]:
    errors = validate_with_schema("domain-pack", data)
    ladder = data.get("ladder", [])
    if isinstance(ladder, list) and any(
        isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value)
        for value in ladder
    ):
        errors.append("ladder: every value must be finite")
    return errors


def validate_run_spec(data: dict[str, Any]) -> list[str]:
    return validate_with_schema("run-spec", data)
