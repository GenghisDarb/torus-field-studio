from pathlib import Path

from torusbrot import DomainPack, LocalBrotRun

ROOT = Path(__file__).parents[1]


def make_result():
    domain = DomainPack.load(ROOT / "examples/tld-parent-null/domain.json")
    run = LocalBrotRun.from_file(ROOT / "examples/tld-parent-null/run-spec.json")
    return run.execute(domain)


def test_registered_metrics_remain_separate() -> None:
    result = make_result()
    point = result.points[len(result.points) // 2]
    assert isinstance(point.closed, bool)
    assert isinstance(point.survived, bool)
    assert point.winner_N is not None
    assert 0 <= point.S_e <= 1
    assert point.T_e is None or point.T_e >= 0


def test_anchoring_improves_reference_similarity() -> None:
    result = make_result()
    width = result.specification.grid.width
    mutation_column = width - 1
    top = result.points[mutation_column]
    bottom = result.points[(result.specification.grid.height - 1) * width + mutation_column]
    assert top.rms_to_parent < bottom.rms_to_parent


def test_claim_never_exceeds_domain_authority() -> None:
    result = make_result()
    assert result.claim_level.name == "COMPUTED_DYNAMICAL"


def test_matched_null_registry_is_deterministic() -> None:
    first = make_result()
    second = make_result()
    assert first.null_registry == second.null_registry
    assert len(first.null_registry) == 12
