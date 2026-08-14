import json
from pathlib import Path

from torusbrot.models import validate_domain_pack, validate_run_spec

ROOT = Path(__file__).parents[1]


def test_public_fixtures_validate() -> None:
    domain = json.loads((ROOT / "examples/tld-parent-null/domain.json").read_text(encoding="utf-8"))
    local_path = ROOT / "examples/tld-parent-null/run-spec.json"
    analytic_path = ROOT / "examples/analytic-z14/run-spec.json"
    local = json.loads(local_path.read_text(encoding="utf-8"))
    analytic = json.loads(analytic_path.read_text(encoding="utf-8"))
    assert validate_domain_pack(domain) == []
    assert validate_run_spec(local) == []
    assert validate_run_spec(analytic) == []


def test_invalid_grid_is_rejected() -> None:
    assert "grid.width" in " ".join(
        validate_run_spec(
            {
                "schema_version": "1.0.0",
                "engine": "analytic",
                "seed": 1,
                "grid": {"width": 1, "height": 10},
            }
        )
    )
