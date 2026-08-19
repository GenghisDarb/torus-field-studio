"""Geometry-indexed TLD calibration primitives.

The package keeps geometry metrology separate from claim adjudication and from any
ControllerGate repair authority.
"""

from torusbrot.geometry.channels import (
    closure_null_calibration,
    field_projection_scores,
    signed_bidirectional_separation,
)
from torusbrot.geometry.metrology import interior_relative_curvature
from torusbrot.geometry.scout import geometry_scout
from torusbrot.geometry.synthetic import SyntheticFixture, build_synthetic_fixtures

__all__ = [
    "SyntheticFixture",
    "build_synthetic_fixtures",
    "closure_null_calibration",
    "field_projection_scores",
    "geometry_scout",
    "interior_relative_curvature",
    "signed_bidirectional_separation",
]
