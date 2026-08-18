from __future__ import annotations

from pathlib import Path

from .bundle import FieldResult
from .kernels import AnalyticKernel, LadderKernel
from .models import ClaimLevel, DomainPack, MatchedNullPolicy, RunSpec


class AnalyticRun:
    def __init__(self, specification: RunSpec):
        if specification.engine != "analytic":
            raise ValueError("AnalyticRun requires engine=analytic")
        self.specification = specification

    @classmethod
    def from_file(cls, path: str | Path) -> AnalyticRun:
        return cls(RunSpec.from_file(path))

    def execute(self) -> FieldResult:
        kernel = AnalyticKernel(self.specification)
        return FieldResult.from_run(
            specification=self.specification,
            points=kernel.generate(),
            kernel_id=kernel.kernel_id,
            claim_level=ClaimLevel.ILLUSTRATIVE_ANALYTIC,
            domain=None,
            null_registry=[],
            failures=kernel.failures,
        )


class LocalBrotRun:
    def __init__(self, specification: RunSpec):
        if specification.engine != "local_brot":
            raise ValueError("LocalBrotRun requires engine=local_brot")
        self.specification = specification

    @classmethod
    def from_file(cls, path: str | Path) -> LocalBrotRun:
        return cls(RunSpec.from_file(path))

    @classmethod
    def from_yaml(cls, path: str | Path) -> LocalBrotRun:
        """Compatibility alias; v0.1 specifications use JSON syntax."""
        return cls.from_file(path)

    def execute(
        self,
        domain: DomainPack,
        null_policy: MatchedNullPolicy | None = None,
    ) -> FieldResult:
        if domain.domain_id != self.specification.domain_id:
            raise ValueError(
                f"Run domain {self.specification.domain_id!r} does not match {domain.domain_id!r}"
            )
        policy = null_policy or self.specification.null_policy
        kernel = LadderKernel(self.specification, domain, policy)
        requested = self.specification.claim_level
        claim_level = min(requested, domain.claim_authority, ClaimLevel.TLD_DERIVED)
        return FieldResult.from_run(
            specification=self.specification,
            points=kernel.generate(),
            kernel_id=kernel.kernel_id,
            claim_level=ClaimLevel(claim_level),
            domain=domain,
            null_registry=kernel.null_registry(),
            failures=kernel.failures,
        )
