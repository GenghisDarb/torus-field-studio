from pathlib import Path

from torusbrot import AnalyticRun

ROOT = Path(__file__).parents[1]


def test_known_analytic_points_are_classified() -> None:
    result = AnalyticRun.from_file(ROOT / "examples/analytic-z14/run-spec.json").execute()
    center = min(result.points, key=lambda point: abs(point.x) + abs(point.y))
    edge = max(result.points, key=lambda point: point.x)
    assert center.classification == "BOUNDED"
    assert edge.classification == "ESCAPED"
    assert result.claim_level.name == "ILLUSTRATIVE_ANALYTIC"


def test_analytic_run_is_deterministic() -> None:
    first = AnalyticRun.from_file(ROOT / "examples/analytic-z14/run-spec.json").execute()
    second = AnalyticRun.from_file(ROOT / "examples/analytic-z14/run-spec.json").execute()
    assert first.run_id == second.run_id
    first_points = [point.to_dict() for point in first.points]
    second_points = [point.to_dict() for point in second.points]
    assert first_points == second_points
