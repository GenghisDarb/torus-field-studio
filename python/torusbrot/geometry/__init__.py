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
from torusbrot.geometry.v2 import (
    GeometryKind,
    PathEmbedding,
    TypedGeometry,
    aggregate_modal_trace_audit,
    anti_alias_downsample_2d,
    ball_porosity,
    curvature_audit_v2,
    dual_concentration_operator_norm,
    extract_path_sequence,
    fup_applicability_gate,
    joint_parent_null_distribution,
    line_porosity,
    modal_residual_trace,
    path_tld_closure,
    point_cloud_winding_coherence,
    point_cloud_winding_number,
    reflect_vector_field_y,
    rotate_vector_field_90,
    typed_projection_scores,
    validate_typed_geometry,
)

__all__ = [
    "SyntheticFixture",
    "GeometryKind",
    "PathEmbedding",
    "TypedGeometry",
    "aggregate_modal_trace_audit",
    "anti_alias_downsample_2d",
    "ball_porosity",
    "build_synthetic_fixtures",
    "closure_null_calibration",
    "curvature_audit_v2",
    "dual_concentration_operator_norm",
    "extract_path_sequence",
    "field_projection_scores",
    "fup_applicability_gate",
    "geometry_scout",
    "interior_relative_curvature",
    "joint_parent_null_distribution",
    "line_porosity",
    "modal_residual_trace",
    "path_tld_closure",
    "point_cloud_winding_coherence",
    "point_cloud_winding_number",
    "reflect_vector_field_y",
    "rotate_vector_field_90",
    "signed_bidirectional_separation",
    "typed_projection_scores",
    "validate_typed_geometry",
]
