#!/usr/bin/env python3
"""Generate the v0.4.0 critic, operator-lineage, and mathematics audit records."""

from __future__ import annotations

import hashlib
import json
import textwrap
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies" / "v0.4.0"
CRITIC = STUDY / "critic"
OPERATORS = STUDY / "operator_audit"
MATH = STUDY / "math"
PRIOR_ZIP = Path.home() / "Downloads" / "notebook_xv_chirality_orientability_release_candidate.zip"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def write_markdown(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        textwrap.dedent(value).strip() + "\n", encoding="utf-8", newline="\n"
    )


def source_ref(path: str, lines: str, evidence: str) -> dict[str, str]:
    source = ROOT / path
    return {
        "path": path,
        "lines": lines,
        "sha256": sha256(source),
        "evidence": evidence,
    }


def critic_statements() -> list[dict[str, Any]]:
    v2 = "python/torusbrot/geometry/v2.py"
    heldout = "scripts/run_v030_pinball_heldout.py"
    handler = "studies/v0.3.0-recovery/geometry/typed_geometry_handler_registry.jsonl"
    projections = "studies/v0.3.0-recovery/geometry/projection_contracts_v2.jsonl"
    equivariance = "studies/v0.3.0-recovery/geometry/vector_equivariance_tests.json"
    gate = "studies/v0.3.0-recovery/freeze/method_v2_acceptance_gate.json"
    frozen = "studies/v0.3.0-recovery/freeze/frozen_method_v2.json"
    pairs = "studies/v0.3.0-recovery/heldout/materialization/paired_acquisition_registry.jsonl"
    rows = [
        (
            1,
            "Method V2 is only a measurement instrument, not a classifier.",
            "SUPPORTED",
            "The frozen method is an instrumented, nonpredictive evidence vector; its binary and hierarchical gates failed.",
            [
                source_ref(
                    frozen,
                    "1-18",
                    "required_name=INSTRUMENTED_EVIDENCE_VECTOR and binary authority false",
                ),
                source_ref(gate, "1-26", "binary_pass=false; hierarchical_pass=false"),
            ],
        ),
        (
            2,
            "A binary decision boundary is necessarily the next step.",
            "MATHEMATICALLY_INCOMPLETE",
            "Necessity does not follow without a declared estimand, labels, loss, abstention cost, and domain transport model.",
            [],
        ),
        (
            3,
            "v0.3.0 flattened 2D PIV into a 1D list.",
            "CONTRADICTED_BY_V030_CODE",
            "P01 is (y,x,2); P02 is (time,y,x,2), with coordinates, masks, components, time, orientation, and registered IDs.",
            [
                source_ref(heldout, "110-181", "typed P01/P02 constructors"),
                source_ref(v2, "30-47,86-111", "typed geometry contract"),
            ],
        ),
        (
            4,
            "v0.3.0 treated pixels as physics.",
            "SUPPORTED_WITH_SCOPE_CORRECTION",
            "Grid cells enter acquisition-level spatial summaries, but they are registered native samples, never independent systems or population parents.",
            [
                source_ref(
                    pairs,
                    "1-28",
                    "population_independent_system=false and paired acquisition block unit",
                )
            ],
        ),
        (
            5,
            "Nine uncalibrated components remain active.",
            "HISTORICAL_DEFECT_ALREADY_REPAIRED",
            "The nine expected-red defects belonged to the pre-repair path. Typed handlers and representation tests are repaired; universal classification, T_e/S_e, population inference, and domain baselines remain deliberately uncalibrated.",
            [
                source_ref(handler, "1-13", "all typed handlers implemented and regression tested"),
                source_ref(gate, "1-26", "remaining binary/hierarchical failures"),
            ],
        ),
        (
            6,
            "Hard-coded absolute thresholds govern the evidence vector.",
            "CONTRADICTED_BY_V030_CODE",
            "The accepted evidence-vector path uses matched-null calibration and explicitly has no universal binary rule. Absolute values remain only in valid norm/energy/distance roles or numerical comparisons.",
            [
                source_ref(frozen, "1-18", "named nonpooled evidence channels"),
                source_ref(projections, "1-5", "implicit magnitude conversion forbidden"),
            ],
        ),
        (
            7,
            "Twenty-eight blocks were treated as independent physical systems.",
            "CONTRADICTED_BY_V030_CODE",
            "The registry fixes one deposit-level single-system cluster, 28 paired acquisition blocks, and population_independent_system=false.",
            [source_ref(pairs, "1-28", "pair and parent hierarchy")],
        ),
        (
            8,
            "Three eddy-turnover times is the correct universal decorrelation rule.",
            "REQUIRES_PROSPECTIVE_TEST",
            "No source establishes a universal constant. Integral correlation, D/U, spectral periods, spacing, overlap, and effective temporal degrees of freedom must be estimated per source.",
            [],
        ),
        (
            9,
            "Current operators are completely blind to sign.",
            "CONTRADICTED_BY_V030_CODE",
            "The claim-bearing vector path reports signed mean curl and signed graph cycle traces, and tests the signed normal component under reflection.",
            [
                source_ref(v2, "269-285,345-368", "signed curl and signed three-cycle trace"),
                source_ref(equivariance, "1-8", "reflection signed component test passes"),
            ],
        ),
        (
            10,
            "Absolute differencing is the active v0.3.0 PIV operator.",
            "CONTRADICTED_BY_V030_CODE",
            "The scored PIV path uses component coherence, signed curl, curl energy/coherence, and divergence energy. Absolute differences appear only in equivariance disagreement reporting and an explicitly descriptive cross-stream ratio.",
            [
                source_ref(v2, "269-285", "active vector channel equations"),
                source_ref(
                    heldout, "193-206,315-323", "transform error audit and descriptive ratio"
                ),
            ],
        ),
        (
            11,
            "A pi phase flip is predicted at N=14.",
            "SOURCE_NOT_FOUND",
            "No authority-A/B/C TLD source derives this prediction. A prior-exposed local prototype scans imposed parity patterns, which is not a derivation.",
            [],
        ),
        (
            12,
            "pi/7 per step produces a parity inversion at N=14.",
            "MATHEMATICALLY_INCONSISTENT",
            "Fourteen pi/7 rotations total 2pi. Ordinary U(1) rotation preserves orientation; parity requires a separate reflection/conjugation action.",
            [],
        ),
        (
            13,
            "A 28-step double cover follows from the Klein-bottle claim.",
            "MATHEMATICALLY_INCOMPLETE",
            "The orientable double cover of a Klein bottle is a torus, but topology alone supplies no discretization or 14/28 step law.",
            [],
        ),
        (
            14,
            "A principal U(1) bundle can encode the proposed parity inversion.",
            "MATHEMATICALLY_INCONSISTENT",
            "U(1) acts orientation-preservingly. A parity component requires O(2)=U(1) semidirect Z2, an equivalent real orientation bundle, or separately justified structure.",
            [],
        ),
        (
            15,
            "c1=0 proves anomaly cancellation.",
            "MATHEMATICALLY_INCOMPLETE",
            "c1=0 only addresses a specified complex line bundle's first Chern class. An anomaly statement needs field content, base, connection, symmetry, and an anomaly calculation; nonorientability is normally tracked by w1.",
            [],
        ),
        (
            16,
            "The supplied Chiral Phase-Flip Operator was previously completed and dispatched.",
            "SUPPORTED_WITH_SCOPE_CORRECTION",
            "A hashable local release-candidate package implements imposed parity scans, so a prototype was completed. No immutable publication or dispatch receipt was found, and it is neither canonical nor confirmatory.",
            [],
        ),
        (
            17,
            "The operator is already canonical TORUS/TLD mathematics.",
            "SOURCE_NOT_FOUND",
            "The exact public TLD I-XIV lineage contains no calibrated U(1), O(2)/Z2, spinor, or orientation-bundle method. Prototype labels cannot create canonical authority.",
            [],
        ),
        (
            18,
            "A quick PIV or Talbot prototype can test it confirmatorily.",
            "REQUIRES_PROSPECTIVE_TEST",
            "Outcome-exposed PIV/Talbot prototypes are development diagnostics. Confirmation requires a frozen method, untouched eligible source, preregistration, one authorized execution, and independent raw verification.",
            [],
        ),
    ]
    result = []
    for number, statement, classification, adjudication, evidence in rows:
        result.append(
            {
                "statement_id": f"CRITIC_{number:02d}",
                "statement": statement,
                "classification": classification,
                "adjudication": adjudication,
                "evidence": evidence,
                "critic_authority": "E_OUTSIDE_ADVICE",
                "claim_authority": "AUDIT_FINDING_NOT_PHYSICAL_VALIDATION",
            }
        )
    return result


def operator_rows() -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]
]:
    common = {
        "historically_executed": True,
        "prospectively_validated": False,
        "gauge_invariant": "NOT_APPLICABLE",
        "claim_authority": "V030_MEASUREMENT_CHANNEL_ONLY",
    }
    signed = [
        {
            "operator_id": "V030_SIGNED_MEAN_CURL_2D",
            "source": "python/torusbrot/geometry/v2.py:269",
            "exact_equation_or_code": "curl = dv_dx - du_dy; signed_mean_curl = mean(curl[mask])",
            "authority": "A_V030_TAGGED_SOURCE",
            "input_type": "VectorField2D",
            "output_type": "signed scalar",
            "sign_preserved": True,
            "phase_preserved": False,
            "orientation_preserved": True,
            "coordinate_invariant_or_equivariant": "proper-rotation invariant; reflection pseudoscalar behavior not claim-calibrated",
            "null_calibrated": True,
            "known_defect": "global mean can cancel opposite local chirality",
            "current_status": "ACTIVE_V030",
            **common,
        },
        {
            "operator_id": "V030_SIGNED_MEAN_CURL_TEMPORAL_MEDIAN",
            "source": "python/torusbrot/geometry/v2.py:305",
            "exact_equation_or_code": "median over per-frame signed_mean_curl",
            "authority": "A_V030_TAGGED_SOURCE",
            "input_type": "SpatiotemporalVectorField",
            "output_type": "signed scalar summary",
            "sign_preserved": True,
            "phase_preserved": False,
            "orientation_preserved": True,
            "coordinate_invariant_or_equivariant": "proper-rotation invariant",
            "null_calibrated": False,
            "known_defect": "temporal ordering and phase lag are lost in median summary",
            "current_status": "ACTIVE_V030",
            **common,
        },
        {
            "operator_id": "V030_SIGNED_THREE_CYCLE_TRACE",
            "source": "python/torusbrot/geometry/v2.py:345",
            "exact_equation_or_code": "trace(A @ A @ A)",
            "authority": "A_V030_TAGGED_SOURCE",
            "input_type": "WeightedGraphGeometry or DirectedGraphGeometry",
            "output_type": "signed scalar",
            "sign_preserved": True,
            "phase_preserved": False,
            "orientation_preserved": "GRAPH_DIRECTION_ONLY",
            "coordinate_invariant_or_equivariant": "node-relabel invariant",
            "null_calibrated": False,
            "known_defect": None,
            "current_status": "ACTIVE_V030",
            **common,
        },
        {
            "operator_id": "V030_POINT_PATH_WINDING",
            "source": "python/torusbrot/geometry/v2.py:735",
            "exact_equation_or_code": "sum(wrap(diff(atan2(y-ybar,x-xbar)))) / (2*pi)",
            "authority": "A_V030_TAGGED_SOURCE",
            "input_type": "ordered closed planar point path",
            "output_type": "signed winding scalar",
            "sign_preserved": True,
            "phase_preserved": "ANGULAR_COORDINATE_ONLY",
            "orientation_preserved": True,
            "coordinate_invariant_or_equivariant": "translation/proper-rotation invariant; reflection sign-equivariant",
            "null_calibrated": True,
            "known_defect": "not a complex-field plaquette or local winding operator",
            "current_status": "ACTIVE_V030_BOUNDED",
            **common,
        },
        {
            "operator_id": "LEGACY_SCALARIZATION",
            "source": "python/torusbrot/geometry/channels.py:16",
            "exact_equation_or_code": "vector -> norm; while ndim>2: mean(axis=0)",
            "authority": "A_V030_TAGGED_SOURCE_BUT_EXCLUDED_FROM_METHOD_V2",
            "input_type": "untyped array",
            "output_type": "scalar 2D field",
            "sign_preserved": False,
            "phase_preserved": False,
            "orientation_preserved": False,
            "coordinate_invariant_or_equivariant": False,
            "null_calibrated": False,
            "known_defect": "silent vector magnitude and leading-axis average",
            "current_status": "LEGACY_EXPORT_NOT_CLAIM_BEARING_V030_PIV",
            **common,
        },
    ]
    phase = [
        {
            "operator_id": "V030_COMPLEX_PHASE_FIELD",
            "source": None,
            "exact_equation_or_code": None,
            "authority": "NONE",
            "input_type": "complex field",
            "output_type": "phase links/holonomy",
            "sign_preserved": "NOT_IMPLEMENTED",
            "phase_preserved": "NOT_IMPLEMENTED",
            "orientation_preserved": "NOT_IMPLEMENTED",
            "gauge_invariant": "NOT_IMPLEMENTED",
            "coordinate_invariant_or_equivariant": "NOT_IMPLEMENTED",
            "null_calibrated": False,
            "historically_executed": False,
            "prospectively_validated": False,
            "claim_authority": "ABSENT",
            "known_defect": "capability missing",
            "current_status": "MISSING",
        },
        {
            "operator_id": "TLD_PHASE_RANDOMIZATION_NULL",
            "source": "studies/v0.4.0/lineage/tld_operator_lineage.jsonl",
            "exact_equation_or_code": "FFT amplitude preserved with randomized phase in selected historical nulls",
            "authority": "A_PUBLIC_NOTEBOOK_SOURCE",
            "input_type": "real scalar field",
            "output_type": "real surrogate",
            "sign_preserved": False,
            "phase_preserved": False,
            "orientation_preserved": False,
            "gauge_invariant": "NOT_APPLICABLE",
            "coordinate_invariant_or_equivariant": "spectrum preserving only",
            "null_calibrated": "HISTORICAL_DOMAIN_SPECIFIC",
            "historically_executed": True,
            "prospectively_validated": False,
            "claim_authority": "HISTORICAL_NULL_ONLY",
            "known_defect": "phase destruction is not phase measurement",
            "current_status": "HISTORICAL",
        },
        {
            "operator_id": "PRIOR_XV_IMPOSED_PARITY_SCAN",
            "source": "external local release-candidate zip",
            "exact_equation_or_code": "preselected even/odd alternating signs and 14/28 cover factors",
            "authority": "E_PRIOR_EXPOSED_PROTOTYPE",
            "input_type": "rung log-values",
            "output_type": "residual scan",
            "sign_preserved": "IMPOSED_NOT_INFERRED",
            "phase_preserved": False,
            "orientation_preserved": False,
            "gauge_invariant": False,
            "coordinate_invariant_or_equivariant": False,
            "null_calibrated": "LIMITED_PERMUTATION",
            "historically_executed": True,
            "prospectively_validated": False,
            "claim_authority": "DIAGNOSTIC_ONLY",
            "known_defect": "privileges 14/28 and substitutes sign patterns for a physical orientation action",
            "current_status": "QUARANTINED_PRIOR_EXPOSURE",
            "source_archive_sha256": sha256(PRIOR_ZIP) if PRIOR_ZIP.exists() else None,
        },
    ]
    orientation = [
        {
            "operator_id": "V030_ROTATE_VECTOR_90",
            "source": "python/torusbrot/geometry/v2.py:416",
            "exact_equation_or_code": "raster k=-1; (u,v)->(-v,u); coordinates/mask/orientation transformed",
            "authority": "A_V030_TAGGED_SOURCE",
            "input_type": "2D or spatiotemporal vector field",
            "output_type": "typed vector field",
            "sign_preserved": True,
            "phase_preserved": False,
            "orientation_preserved": True,
            "gauge_invariant": "NOT_APPLICABLE",
            "coordinate_invariant_or_equivariant": "proper-rotation equivariant",
            "null_calibrated": False,
            "historically_executed": True,
            "prospectively_validated": False,
            "claim_authority": "REPRESENTATION_TEST",
            "known_defect": None,
            "current_status": "ACTIVE_V030",
        },
        {
            "operator_id": "V030_REFLECT_VECTOR_Y",
            "source": "python/torusbrot/geometry/v2.py:451",
            "exact_equation_or_code": "flip y raster; v->-v; y coordinate->-y",
            "authority": "A_V030_TAGGED_SOURCE",
            "input_type": "VectorField2D",
            "output_type": "typed vector field",
            "sign_preserved": True,
            "phase_preserved": False,
            "orientation_preserved": "REFLECTION_RECORDED",
            "gauge_invariant": "NOT_APPLICABLE",
            "coordinate_invariant_or_equivariant": "reflection equivariant",
            "null_calibrated": False,
            "historically_executed": True,
            "prospectively_validated": False,
            "claim_authority": "REPRESENTATION_TEST",
            "known_defect": "spatiotemporal reflection handler not registered",
            "current_status": "ACTIVE_V030_2D_ONLY",
        },
        {
            "operator_id": "V030_ORIENTATION_METADATA",
            "source": "python/torusbrot/geometry/v2.py:30",
            "exact_equation_or_code": "orientation: str | None",
            "authority": "A_V030_TAGGED_SOURCE",
            "input_type": "TypedGeometry",
            "output_type": "metadata",
            "sign_preserved": "NOT_AN_OPERATOR",
            "phase_preserved": False,
            "orientation_preserved": "DECLARED_ONLY",
            "gauge_invariant": "NOT_APPLICABLE",
            "coordinate_invariant_or_equivariant": "NOT_ESTIMATED",
            "null_calibrated": False,
            "historically_executed": True,
            "prospectively_validated": False,
            "claim_authority": "CUSTODY_METADATA",
            "known_defect": "metadata alone is not an orientation bundle or monodromy estimator",
            "current_status": "ACTIVE_V030",
        },
    ]
    topology = [
        {
            "claim_id": "KLEIN_TO_14_28",
            "claim": "Klein bottle topology derives a 14/28 law",
            "source_authority": "E_PRIOR_PROTOTYPE_OR_CRITIC",
            "status": "MATHEMATICALLY_INCOMPLETE",
            "reason": "double-cover topology supplies no rung count, period, or discretization",
        },
        {
            "claim_id": "U1_PARITY",
            "claim": "U(1) holonomy is a parity detector",
            "source_authority": "E_CRITIC",
            "status": "MATHEMATICALLY_INCONSISTENT",
            "reason": "U(1) is orientation preserving",
        },
        {
            "claim_id": "C1_NONORIENTABILITY",
            "claim": "c1 detects the proposed nonorientability",
            "source_authority": "E_CRITIC",
            "status": "MATHEMATICALLY_INCONSISTENT",
            "reason": "w1 is the real orientation obstruction; c1 classifies complex line-bundle twisting",
        },
        {
            "claim_id": "W1_WITHOUT_BUNDLE",
            "claim": "w1 may be inferred without a declared orientation bundle",
            "source_authority": "F_NEW_INFERENCE",
            "status": "FORBIDDEN",
            "reason": "transition functions and their determinant signs are required",
        },
        {
            "claim_id": "SPINOR_4PI",
            "claim": "4pi return follows for ordinary scalar/vector fields",
            "source_authority": "E_CRITIC",
            "status": "MATHEMATICALLY_INCONSISTENT",
            "reason": "4pi return requires a justified double-valued/spinorial representation",
        },
    ]
    lineage_path = STUDY / "lineage" / "tld_operator_lineage.jsonl"
    historical = [
        json.loads(line) for line in lineage_path.read_text(encoding="utf-8").splitlines() if line
    ]

    def occurrence(row: dict[str, Any]) -> dict[str, Any]:
        code = row["exact_code_or_equation"]
        lowered = code.lower()
        true_complex_phase = any(
            token in lowered
            for token in (
                "np.angle",
                "np.fft",
                "fft2",
                "phase_random",
                "phase_scrambl",
                "1j",
                "complex",
            )
        )
        return {
            "operator_id": (
                f"TLD_{row['release']}_N{row['notebook']:02d}_C{row['cell_index']}_"
                f"L{row['source_line']}_{row['category'].upper()}"
            ),
            "source": (
                f"public TLD {row['release']} Notebook {row['notebook']} "
                f"cell {row['cell_index']} line {row['source_line']}"
            ),
            "exact_equation_or_code": code,
            "authority": row["authority"],
            "input_type": "HISTORICAL_NOTEBOOK_VALUE_OR_ARRAY_NOT_PROMOTED_TO_TYPED_PHASE_FIELD",
            "output_type": "HISTORICAL_NOTEBOOK_INTERMEDIATE_OR_DIAGNOSTIC",
            "sign_preserved": row["sign_preserved"],
            "phase_preserved": bool(row["phase_preserved"] and true_complex_phase),
            "orientation_preserved": "NOT_ESTABLISHED",
            "gauge_invariant": "NOT_ESTABLISHED",
            "coordinate_invariant_or_equivariant": "NOT_ESTABLISHED",
            "null_calibrated": "SOURCE_SPECIFIC_OR_NOT_ESTABLISHED",
            "historically_executed": row["historically_executed"],
            "prospectively_validated": row["prospectively_validated"],
            "claim_authority": row["claim_authority"],
            "known_defect": (
                "lexical 'phase' denotes a workflow/process phase, not complex phase"
                if row["category"] == "complex_amplitude_or_phase" and not true_complex_phase
                else None
            ),
            "current_status": "HISTORICAL_TLD_OCCURRENCE_NOT_V040_METHOD_AUTHORITY",
            "release": row["release"],
            "notebook": row["notebook"],
            "category": row["category"],
        }

    signed.extend(
        occurrence(row)
        for row in historical
        if row["category"] in {"absolute_value", "signed_difference", "divergence"}
    )
    phase.extend(
        occurrence(row) for row in historical if row["category"] == "complex_amplitude_or_phase"
    )
    orientation.extend(occurrence(row) for row in historical if row["category"] == "reflection")
    topology.extend(
        {
            **occurrence(row),
            "record_kind": "HISTORICAL_CYCLIC_ADJACENCY_OPERATOR_OCCURRENCE",
            "topology_claim_authority": "NONE_FROM_CYCLIC_ADJACENCY_ALONE",
        }
        for row in historical
        if row["category"] == "cyclic_adjacency"
    )
    return signed, phase, orientation, topology


def main() -> None:
    statements = critic_statements()
    write_jsonl(CRITIC / "critic_statement_registry.jsonl", statements)
    counts = Counter(row["classification"] for row in statements)
    adjudication = {
        "schema_version": "tfs-v040-critic-adjudication-v1",
        "statement_count": len(statements),
        "classification_counts": dict(sorted(counts.items())),
        "flattening_finding": "CONTRADICTED_BY_V030_CODE",
        "sign_blindness_finding": "CONTRADICTED_BY_V030_CODE_WITH_NARROW_REAL_GAPS",
        "temporal_independence_finding": "CONTRADICTED_BY_V030_REGISTRY",
        "phase_orientation_finding": "LOCAL_AND_TEMPORAL_PHASE_PLUS_O2_MONODROMY_REMAIN_UNCALIBRATED",
        "TLD_DERIVED": "BLOCKED",
        "EXTERNALLY_VALIDATED": False,
        "statements": statements,
    }
    write_json(CRITIC / "critic_adjudication.json", adjudication)
    table = "\n".join(
        f"| {row['statement_id']} | {row['classification']} | {row['statement']} |"
        for row in statements
    )
    write_markdown(
        CRITIC / "critic_adjudication.md",
        f"""
        # Critic statement adjudication

        The outside critic is useful as a hypothesis source, not as authority. The v0.3.0
        scored path did not flatten PIV, did retain signed channels, and did not promote
        28 acquisition pairs into independent systems. Its real gap is narrower: local
        chirality cancellation, temporal phase/cross-spectrum, complex-field holonomy,
        and orientation-reversing monodromy are not calibrated.

        | ID | Classification | Statement |
        |---|---|---|
        {table}

        No statement establishes a physical parity flip, a privileged 14/28 period,
        TLD derivation, external validation, or a topology detection.
    """,
    )
    write_json(
        CRITIC / "remaining_valid_concerns.json",
        {
            "remaining_gaps": [
                "signed local curl distribution and positive/negative circulation separation",
                "spatial chirality-domain topology and cancellation detection",
                "complex-field phase links, local holonomy, and masked singularity policy",
                "cross-component and temporal cross-spectral phase",
                "O(2)/Z2 transition-data model with gauge-invariant parity monodromy",
                "source-specific temporal-dependence and instrument metrology",
                "selective/nonbinary calibration with type-I, false-sign, and false-parity control",
            ],
            "remaining_v030_method_limitations": [
                "universal binary TLD classifier",
                "universal hierarchical multi-channel rule",
                "general-geometry T_e and S_e",
                "universal population inference",
                "universal domain baselines",
            ],
        },
    )
    write_json(
        CRITIC / "forbidden_promotions.json",
        {
            "forbidden": [
                "phase plot -> parity",
                "parity -> Klein bottle",
                "Klein bottle -> TORUS proof",
                "14 -> universal law",
                "28 -> double-cover validation",
                "U(1) -> parity",
                "c1=0 -> anomaly cancellation",
                "4pi -> spinor evidence without spinor input",
                "diagnostic prototype -> confirmatory evidence",
                "TLD lineage -> TLD_DERIVED phase method",
                "one system -> population inference",
                "decorrelated frames -> independent parents",
            ]
        },
    )

    signed, phase, orientation, topology = operator_rows()
    write_jsonl(OPERATORS / "signed_operator_registry.jsonl", signed)
    write_jsonl(OPERATORS / "phase_operator_registry.jsonl", phase)
    write_jsonl(OPERATORS / "orientation_operator_registry.jsonl", orientation)
    write_jsonl(OPERATORS / "topology_claim_registry.jsonl", topology)
    write_json(
        OPERATORS / "absolute_value_information_loss.json",
        {
            "valid_uses": [
                "norm",
                "energy",
                "unsigned residual",
                "distance",
                "amplitude",
                "numerical disagreement magnitude",
            ],
            "invalid_as_sole_channel_for": [
                "orientation",
                "phase",
                "handedness",
                "sign",
                "parity",
                "transport direction",
                "local winding",
            ],
            "v030_active_piv": {
                "silent_vector_magnitude": False,
                "silent_time_average_in_P02_storage": False,
                "temporal_summary_order_loss": True,
                "signed_channel_present": True,
            },
            "legacy_export": {
                "path": "python/torusbrot/geometry/channels.py",
                "silent_vector_magnitude": True,
                "silent_leading_axis_average": True,
                "claim_bearing_v030_piv_path": False,
            },
        },
    )
    write_json(
        OPERATORS / "v030_phase_information_audit.json",
        {
            "P01": {
                "shape": "(y,x,2)",
                "signed_components": True,
                "time": "temporal mean by preregistered projection",
                "local_phase": False,
            },
            "P02": {
                "shape": "(time,y,x,2)",
                "signed_components": True,
                "time_coordinates": True,
                "reported_channels": "median per-frame vector summaries",
                "temporal_order_retained_in_typed_input": True,
                "temporal_phase_retained_in_reported_channels": False,
            },
            "preserved": [
                "coordinates",
                "mask",
                "u/v components",
                "time",
                "orientation metadata",
                "signed mean curl",
                "proper-rotation equivariance",
                "2D vector reflection",
            ],
            "lost_or_missing": [
                "local curl sign distribution",
                "spatial chirality domains",
                "complex phase",
                "cross-component phase",
                "temporal cross-spectrum",
                "phase lag",
                "parity-change event",
                "orientation-bundle monodromy",
            ],
            "flattening": False,
            "completely_sign_blind": False,
            "O2_parity_estimator": False,
        },
    )
    write_json(
        OPERATORS / "missing_operator_capabilities.json",
        {
            "required_before_phase_method": [
                "complex-valued typed field or explicitly reconstructed analytic-signal contract",
                "local U(1) link and plaquette holonomy with zero/mask policy",
                "signed local curl/circulation distributions",
                "temporal cross-spectrum with sampling and stationarity gates",
                "explicit O(2) transition records before any parity-monodromy inference",
                "matched spectrum-preserving phase and orientation nulls",
                "reflection, rotation, gauge, time-reversal, boundary, mask, sampling, and instrument tests",
            ]
        },
    )

    source_audit = {
        "schema_version": "tfs-v040-chiral-source-audit-v1",
        "authoritative_TLD_I_XIV_phase_method_found": False,
        "prior_exposed_prototype": {
            "archive": str(PRIOR_ZIP),
            "sha256": sha256(PRIOR_ZIP) if PRIOR_ZIP.exists() else None,
            "status": "LOCAL_RELEASE_CANDIDATE_NOT_IMMUTABLE_PUBLIC_AUTHORITY",
            "implemented": "imposed alternating-sign/parity scans and hard-coded single-14/double-28 cover labels",
            "not_implemented": "gauge-derived U(1) links, inferred O(2) transition parity, w1 evaluation, blind period selection, prospective field validation",
        },
        "source_conclusion": "No canonical chiral specification was recovered; a new method can only be independently derived and calibrated.",
    }
    write_json(MATH / "chiral_spec_source_audit.json", source_audit)

    models = [
        {
            "model": "MODEL_0_SIGNED_VECTOR_BASELINE",
            "input": "registered real vector field",
            "local_invariant": "signed curl/circulation and divergence",
            "orientation_action": "push-forward of coordinates and vector components",
            "gauge": "not applicable",
            "parity_authority": "pseudoscalar sign only under declared reflection; no bundle monodromy",
            "c1": "not applicable",
            "w1": "not applicable without transition bundle",
            "spinor": False,
            "status": "MATHEMATICALLY_WELL_DEFINED_BUT_INCOMPLETE_FOR_PHASE",
        },
        {
            "model": "MODEL_1_U1_PHASE_LINK",
            "input": "nonzero complex scalar samples on oriented adjacency/plaquettes",
            "local_invariant": "plaquette product of normalized phase links",
            "orientation_action": "oriented boundary reversal/conjugation changes holonomy sign",
            "gauge": "local U(1) gauge cancels around closed loop",
            "parity_authority": "none by itself",
            "c1": "applicable only with declared complex line bundle and global patching",
            "w1": "not the U(1) invariant",
            "spinor": False,
            "status": "MATHEMATICALLY_WELL_DEFINED",
        },
        {
            "model": "MODEL_2_O2_Z2_MONODROMY",
            "input": "explicit O(2) transition elements (theta,s) on oriented edges/charts",
            "local_invariant": "loop determinant product s_loop; rotation holonomy only up to conjugacy/gauge",
            "orientation_action": "s=-1, commonly acting by complex conjugation",
            "gauge": "edge transitions transform by endpoint O(2) frames; loop conjugacy class retained",
            "parity_authority": "yes for declared transition bundle",
            "c1": "not primary nonorientability obstruction",
            "w1": "evaluation on loop equals reflection parity",
            "spinor": False,
            "status": "MATHEMATICALLY_WELL_DEFINED_BUT_NOT_INFERABLE_FROM_UNANNOTATED_FIELDS",
        },
        {
            "model": "MODEL_3_SPINOR_DOUBLE_VALUED",
            "input": "explicitly justified spinor or lifted frame state",
            "local_invariant": "representation-dependent lifted holonomy",
            "orientation_action": "requires Pin/Spin convention",
            "gauge": "representation-specific",
            "parity_authority": "only under declared Pin/Spin structure",
            "c1": "not sufficient",
            "w1": "orientation prerequisite/obstruction depends on structure",
            "spinor": True,
            "status": "NOT_APPLICABLE_TO_ORDINARY_V030_SCALAR_OR_VECTOR_FIELDS",
        },
        {
            "model": "MODEL_4_NULL_NO_TOPOLOGY",
            "input": "matched field preserving amplitude spectrum/nuisance while randomizing target phase/orientation relation",
            "local_invariant": "none by construction",
            "orientation_action": "matched to tested representation",
            "gauge": "same processing as parent",
            "parity_authority": "null reference only",
            "c1": "not inferred",
            "w1": "not inferred",
            "spinor": False,
            "status": "REQUIRED_CONTROL_FAMILY",
        },
    ]
    write_json(MATH / "model_class_comparison.json", {"models": models})
    write_markdown(
        MATH / "chiral_spec_corrections.md",
        """
        # Corrections to the proposed chiral specification

        1. U(1) rotation is orientation preserving; it cannot alone represent parity.
        2. Fourteen increments of pi/7 total 2pi. Seven total pi; twenty-eight total 4pi.
        3. A parity bit must be an explicit Z2/O(2) transition action, not a relabeled phase.
        4. The Klein bottle's orientable double cover being a torus does not select 14 or 28 samples.
        5. w1, not c1, is the ordinary obstruction to orientability of a real bundle.
        6. c1=0 is not an anomaly calculation.
        7. A 4pi return is representation evidence only when a spinorial/double-valued state is justified.
        8. The prior Notebook XV package imposed parity patterns and privileged 14/28; it is a quarantined diagnostic prototype, not canonical mathematics.

        These are conditional derivations under declared representations, not a theorem about
        TORUS, TLD, a physical system, or a universal period.
    """,
    )
    write_markdown(
        MATH / "U1_phase_link_derivation.md",
        r"""
        # U(1) phase-link derivation

        Let nonzero complex samples be `z_i = rho_i exp(i theta_i)` on vertices of an
        oriented graph. Define `q_ij = z_j conjugate(z_i) / |z_j conjugate(z_i)|`.
        Under a local frame change `z_i -> exp(i chi_i) z_i`,
        `q_ij -> exp(i(chi_j-chi_i)) q_ij`. The ordered product around a closed
        plaquette cancels every endpoint gauge factor. However, because these links
        are derived from vertex values alone, the same product telescopes identically
        to one wherever every vertex is nonzero. Its principal `H_p` is therefore
        algebraically trivial, not a nontrivial connection holonomy.

        The discrete winding is `w_p = sum wrap(Arg(q_ij))/(2pi)`. Integer meaning
        requires a nonzero continuous boundary field and adequate sampling; an edge
        increment near the branch cut makes the discrete estimate instrument-limited.
        It is invariant to a global phase offset, but an arbitrary vertex-wise U(1)
        rephasing can change branch assignments. Nontrivial locally gauge-invariant
        holonomy requires independently supplied connection links, not pure-gauge
        links reconstructed only from `z`.
        Plaquettes touching a zero, missing sample, or undeclared interpolation are
        ineligible. A coordinate reflection reverses boundary orientation; complex
        conjugation also reverses phase. The implementation must freeze whether either
        or both actions define the representation.

        This construction measures U(1) winding. It does not produce a parity bit,
        nonorientability, 14-step law, 28-step law, or spinorial 4pi return.
    """,
    )
    write_markdown(
        MATH / "O2_Z2_monodromy_derivation.md",
        r"""
        # O(2) / Z2 monodromy derivation

        Write an O(2) transition as `(theta,s)`, with `s` in `{+1,-1}`, and freeze
        `(theta,s)*(phi,t) = (theta + s phi mod 2pi, s t)`. On a complex coordinate,
        `(theta,+1)` acts as `z -> exp(i theta) z`; `(theta,-1)` acts as
        `z -> exp(i theta) conjugate(z)`. Edge transitions must be measured or supplied
        by a declared chart/frame registration; an unannotated complex or vector field
        does not identify them.

        Under endpoint frame changes, edge transitions transform by the usual endpoint
        gauge action and closed-loop monodromy changes by conjugacy. The determinant
        product `s_loop` is conjugacy invariant. `s_loop=-1` is an orientation-reversing
        loop and evaluates the first Stiefel-Whitney obstruction on that loop. For an
        orientation-reversing conjugacy class, a raw rotation angle is not generally a
        gauge-invariant scalar, so the parity bit is the robust result unless a stronger
        gauge anchor is preregistered.

        One reflection gives `s_loop=-1`; two give `+1`. The orientation double cover is
        the cover associated with the kernel of this Z2 character: a reversing loop
        closes only after two lifts. This says "twice the loop", not 28 samples and not
        a universal physical period.
    """,
    )
    write_markdown(
        MATH / "double_cover_semantics.md",
        """
        # Double-cover and 14/28 semantics

        Arithmetic is exact: pi/7 x 7 = pi, pi/7 x 14 = 2pi, and pi/7 x 28 = 4pi.

        - Ordinary complex scalar: 2pi returns the phase; 4pi is two ordinary returns.
        - Ordinary vector: 2pi returns the vector; pi reverses its arrow.
        - Director: pi returns the unoriented axis because n and -n are identified.
        - Spinor: a 2pi rotation can change sign and a 4pi rotation can return the state,
          but only in an explicitly justified spinor representation.
        - O(2) orientation bundle: return depends on the Z2 reflection product, not on
          accumulating an ordinary U(1) angle alone.

        Fourteen and twenty-eight receive no privileged score. A blind period search
        must include the frozen neighboring family, and a targeted lane has no authority
        without an independent theory source.
    """,
    )
    write_markdown(
        MATH / "characteristic_class_applicability.md",
        """
        # Characteristic-class applicability

        `w1(E)` lies in first cohomology with Z2 coefficients for a real vector bundle
        and is the obstruction to orientability. Its evaluation requires a declared
        orientation bundle or transition functions. It cannot be inferred from an
        orientation label alone.

        `c1(L)` lies in second integral cohomology for a complex line bundle and records
        U(1) twisting/curvature under the required global assumptions. It is not the
        standard classifier of real nonorientability. `c1=0` neither supplies a missing
        orientation bundle nor proves anomaly cancellation. Any anomaly claim requires
        a specified theory and separate calculation, absent here.
    """,
    )
    write_json(
        MATH / "claim_boundary.json",
        {
            "established": [
                "U1 plaquette holonomy is gauge invariant for eligible nonzero closed plaquettes",
                "O2 loop determinant is a gauge/conjugacy-invariant parity bit when transition data are declared",
                "w1 is the applicable orientation obstruction for the declared real bundle",
                "pi/7 arithmetic",
            ],
            "not_established": [
                "physical U1 field in TLD",
                "physical O2 orientation bundle in TLD",
                "spinor applicability",
                "14 or 28 specificity",
                "Klein-bottle detection",
                "anomaly cancellation",
                "TORUS confirmation",
                "TLD_DERIVED phase method",
                "external validation",
            ],
            "TLD_DERIVED": "BLOCKED",
            "EXTERNALLY_VALIDATED": False,
        },
    )

    for directory in (CRITIC, OPERATORS, MATH):
        files = [
            path
            for path in directory.rglob("*")
            if path.is_file() and path.name != "SHA256SUMS.txt"
        ]
        (directory / "SHA256SUMS.txt").write_text(
            "".join(
                f"{sha256(path)}  {path.relative_to(directory).as_posix()}\n"
                for path in sorted(files)
            ),
            encoding="utf-8",
            newline="\n",
        )


if __name__ == "__main__":
    main()
