# ruff: noqa: E501 -- forensic evidence strings preserve exact source locations and claims.
"""Generate the append-only v0.3.0 recovery preflight and expected-red audit."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "studies" / "v0.3.0-recovery"
PREFLIGHT = RECOVERY / "preflight"
EXPECTED_RED = RECOVERY / "expected_red"
START_MAIN = "9dfeb016738d01cdf5796c039fab2f88b3a2b5ee"
START_HEAD = "0d5a31609283af5e76fcb02205f618e0edb19fab"
METHOD_V1_COMMIT = "827b3394c0ce8ed414ca57d8e77ef1aaf1a72b1c"
DATASET_V1_COMMIT = "70fa574350ecff8c021ed61ad121c07edb3d581f"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def write_checksums(directory: Path, names: list[str], output_name: str) -> None:
    with (directory / output_name).open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("".join(f"{sha256(directory / name)}  {name}\n" for name in sorted(names)))


def asset(name: str, size: int, digest: str) -> dict[str, Any]:
    return {"name": name, "size_bytes": size, "sha256": digest, "verified": True}


def build_preflight() -> None:
    assets = [
        asset("external-replication-addon.zip", 2016, "15704d7f6d61bb745890f695ca3928e9d5f68068e6733acf2abd7048cd79f8bd"),
        asset("release-manifest-v0.2.2.json", 2563, "1cb0b9508a2cc560a88d5a78e559b56e157dd12656bf9a8ba073a6f099ce812d"),
        asset("sbom.spdx.json", 270807, "c01741ea3b01922fe2856cccbecd77d94a6484b0fc0b7cf6c199f5b115d63211"),
        asset("SHA256SUMS-v0.2.2.txt", 1371, "4c5a6ad136a8e78a2efd9d9019e0854e1be0d88f9b3f685564debff9ab37d63f"),
        asset("torusbrot-0.2.2-py3-none-any.whl", 131283, "eeb191ffe3d53c4f47c05383a28ef45e29b24675216607ec40e41d2b61178e47"),
        asset("torusbrot-0.2.2.tar.gz", 122685, "8b73d46dc6df3c53ceb7cdb6ada687fc3a90d3cd8400d61d777fe1e8770297f7"),
        asset("v021-block-phase-diagnostics.csv", 127986, "76005bddbc724f29f26070d8f6df7838ac2b33cfcd74ab3d08809dc72c108366"),
        asset("v021-closure-null-calibration.csv", 22557, "1c7bf885a6cdc93d33ab89a0bd0726746b0998405b2a92ca318c603b2286eee0"),
        asset("v021-forensic-combined.tbx.zip", 1952453, "186ad2c0e051e027f4b4df4e85fd72eead7c6a44129aa35df5df60572535955c"),
        asset("v021-negative-result-forensic-report.json", 1923, "d1590dde732d8e89c62305261e0b5617ec7a00cc900cc590f6709189373a2d46"),
        asset("v021-negative-result-forensic-report.md", 1628, "7ddda0513a01e4b1ce94c700237f4f7bb1017e52daeb7aa7988f1e32d1337e6c"),
        asset("v021-null-mechanism-diagnostics.csv", 560524, "73d4716f7b2b2c3b66150ae0f99e61bb64f6420a6e42f889f463d8b283365c40"),
        asset("v021-parent-dependence-diagnostics.csv", 23607, "27a70bae7d85063041c6737dfcf2185642997dd066fa2f9aea7f59faf5083bde"),
        asset("v021-power-surface.csv", 35809, "cdcb352c1dd5ebb80c62b21ca9a2b83b5eefce1135211f265443428ffcaa532b"),
        asset("v021-signed-direction-diagnostics.csv", 171654, "2b5a30e7d13e95489d0fd95d3a04f762d27a831a06500914fafb1bdea9865848"),
    ]
    repository_state = {
        "schema_version": "1.0.0",
        "audit_date": "2026-08-20",
        "authoritative_local_path": "<workspace>/work/torus-field-studio",
        "absolute_local_path_redacted_from_tracked_artifact": True,
        "repository": "GenghisDarb/torus-field-studio",
        "origin": "https://github.com/GenghisDarb/torus-field-studio.git",
        "visibility": "PUBLIC",
        "authenticated_account": "GenghisDarb",
        "starting_main": START_MAIN,
        "v0.2.2_tag_object": "b7c579da37ebff32cc2b5cc899662876959d3043",
        "v0.2.2_peeled_commit": START_MAIN,
        "starting_branch": "agent/v0.3.0-geometry-indexed-tld",
        "starting_head": START_HEAD,
        "remote_head": START_HEAD,
        "working_tree_at_start": "CLEAN",
        "ignored_outputs_present": [
            ".venv/",
            "external_cache/",
            "results/",
            "node_modules/",
            "apps/studio/dist/",
            "apps/studio/test-results/",
            "tests/generated-fixtures/",
        ],
        "pr": {
            "number": 5,
            "state": "OPEN",
            "draft": True,
            "mergeable": True,
            "base": START_MAIN,
            "head": START_HEAD,
            "url": "https://github.com/GenghisDarb/torus-field-studio/pull/5",
        },
        "pages": {
            "url": "https://genghisdarb.github.io/torus-field-studio/",
            "http_status": 200,
            "title": "TORUS Field Studio",
        },
        "controllergate": {
            "repository": "GenghisDarb/controllergate-research",
            "mode": "READ_ONLY",
            "expected_head": "38897b79588f3ff4b1b9002eedc299a9bcf05140",
            "modified": False,
        },
    }
    release_custody = {
        "schema_version": "1.0.0",
        "release": "v0.2.2",
        "release_url": "https://github.com/GenghisDarb/torus-field-studio/releases/tag/v0.2.2",
        "tag_commit": START_MAIN,
        "published_asset_count": len(assets),
        "assets": assets,
        "published_SHA256SUMS_verified": True,
        "fresh_wheel_install": {
            "version": "0.2.2",
            "import": "PASS",
            "isolated_environment": True,
        },
        "forensic_bundle_audit": {
            "asset": "v021-forensic-combined.tbx.zip",
            "checked_files": 124,
            "valid": True,
            "warnings": 0,
            "errors": 0,
        },
        "main_local_validation": {
            "python_tests": "44/44 PASS",
            "browser_tests": "6/6 PASS",
            "schema_sync": "PASS",
            "ruff": "PASS",
            "wheel_smoke": "PASS",
            "tracked_content_scan": "PASS",
            "pip_audit": "NO_KNOWN_VULNERABILITIES",
            "pnpm_audit": "NO_KNOWN_VULNERABILITIES",
            "typecheck": "PASS",
            "production_build": "PASS",
            "bundle_budget": "PASS",
        },
    }
    pr5_reproduction = {
        "schema_version": "1.0.0",
        "starting_head": START_HEAD,
        "status": "EXACT_REPRODUCTION",
        "tld_i": {
            "source_sha256": "5bae9af506bd65e74225fc91f869931d70fcd89505cbc672b3538abdfd4b446e",
            "result": "FIRST_PUBLISHED_TLD_RESULT_EXACTLY_REPRODUCED",
            "claim_level": "COMPUTED_DYNAMICAL",
            "TLD_DERIVED": "BLOCKED",
            "tbx_profiles_valid": "3/3",
        },
        "v0.2.1": {
            "source_sha256": "d1b9261c54132f04c374f762f1e5e512af19f95c95fd6bfa1e8ac7e927e3b0b8",
            "scientific_outcome": "HELDOUT_TLD_STUDY_NEGATIVE_UNDER_FROZEN_GATES",
            "T_e": "NOT_OBSERVED",
            "S_e_contiguous": 0.0,
            "winner_N": 9,
            "fourteen_specificity_passed": False,
            "eligible_parent_count": 12,
            "failure_count": 0,
            "independent_disagreements": 0,
            "mutations_rejected": "25/25",
            "TLD_DERIVED": "BLOCKED",
            "EXTERNALLY_VALIDATED": False,
        },
        "method_v1": {
            "freeze_commit": METHOD_V1_COMMIT,
            "selected_method": "METHOD_C_EVIDENCE_VECTOR_NONBINARY",
            "method_manifest_sha256": sha256(ROOT / "studies/v0.3.0-method-freeze/method_freeze_SHA256SUMS.txt"),
            "frozen_method_sha256": sha256(ROOT / "studies/v0.3.0-method-freeze/frozen_revised_method.json"),
            "independent_verification_sha256": sha256(ROOT / "studies/v0.3.0-method-freeze/independent_method_verification.json"),
            "replay_after_canonical_LF_normalization": "BYTE_IDENTICAL",
            "independent_disagreements": 0,
            "mutations_rejected": "20/20",
        },
        "dataset_v1": {
            "freeze_commit": DATASET_V1_COMMIT,
            "selected_source": "Wind Tunnel Experimental Dataset for Wind Farm Control with Scanning Lidar Wake Measurements",
            "doi": "10.5281/zenodo.18731994",
            "archive_sha256": "02d36a05c223a3fe9decb9449ea0e4dc3d8d01877acca18cc0e201c915b1b461",
            "selected_candidate_receipt_sha256": sha256(ROOT / "studies/v0.3.0-field-selection/selected_candidate_receipt.json"),
        },
        "blocked_materialization": {
            "acquisition_count": 4,
            "campaign_count": 1,
            "condition_roles": ["one greedy control", "three distinct yaw interventions"],
            "nested_lidar_samples": 600000,
            "lidar_views_per_acquisition": 2,
            "interacting_turbines": 3,
            "claim_metrics_computed": False,
            "preregistration_created": False,
            "scored_execution_count": 0,
            "field_assay_blocker_sha256": sha256(ROOT / "studies/v0.3.0-field-assay/materialization/field_assay_blocker.json"),
            "scientific_outcome": "GEOMETRY_INDEXED_TLD_HELDOUT_EXECUTION_BLOCKED",
            "TLD_DERIVED": "BLOCKED",
            "EXTERNALLY_VALIDATED": False,
        },
        "pr5_local_validation": {
            "python_tests": "62/62 PASS",
            "browser_tests": "6/6 PASS",
            "schema_sync": "PASS",
            "ruff": "PASS",
            "wheel_smoke": "PASS",
            "security_and_dependency_audits": "PASS",
            "typecheck_build_budget": "PASS",
        },
    }
    workflows = {
        "schema_version": "1.0.0",
        "head": START_HEAD,
        "runs": [
            {"id": 32268520669, "name": "TLD I reproduction", "status": "completed", "conclusion": "success", "url": "https://github.com/GenghisDarb/torus-field-studio/actions/runs/32268520669"},
            {"id": 32268520706, "name": "Held-out TLD study", "status": "completed", "conclusion": "success", "url": "https://github.com/GenghisDarb/torus-field-studio/actions/runs/32268520706"},
            {"id": 32268520772, "name": "CI", "status": "completed", "conclusion": "success", "url": "https://github.com/GenghisDarb/torus-field-studio/actions/runs/32268520772"},
        ],
        "local_remote_reconciliation": "AGREE",
        "unresolved_check_failures": 0,
    }
    immutable = [
        {"evidence_id": "MAIN_V022", "kind": "git_commit", "identity": START_MAIN, "status": "IMMUTABLE_PRESERVED"},
        {"evidence_id": "TAG_V022", "kind": "annotated_tag", "identity": "b7c579da37ebff32cc2b5cc899662876959d3043", "peeled_commit": START_MAIN, "status": "IMMUTABLE_PRESERVED"},
        {"evidence_id": "TLD_I_SOURCE", "kind": "source_archive", "identity": "10.5281/zenodo.18080090", "sha256": "5bae9af506bd65e74225fc91f869931d70fcd89505cbc672b3538abdfd4b446e", "status": "EXACT_REPLAY"},
        {"evidence_id": "V021_SOURCE", "kind": "source_archive", "identity": "10.24432/C5RK5G", "sha256": "d1b9261c54132f04c374f762f1e5e512af19f95c95fd6bfa1e8ac7e927e3b0b8", "status": "EXACT_REPLAY"},
        {"evidence_id": "METHOD_FREEZE_V1", "kind": "git_commit", "identity": METHOD_V1_COMMIT, "status": "APPEND_ONLY_PRESERVED"},
        {"evidence_id": "DATASET_FREEZE_V1", "kind": "git_commit", "identity": DATASET_V1_COMMIT, "status": "APPEND_ONLY_PRESERVED"},
        {"evidence_id": "WIND_SOURCE_V1", "kind": "source_archive", "identity": "10.5281/zenodo.18731994", "sha256": "02d36a05c223a3fe9decb9449ea0e4dc3d8d01877acca18cc0e201c915b1b461", "status": "STRUCTURE_EXPOSED_NO_CLAIM_METRICS"},
        {"evidence_id": "PR5_START", "kind": "git_commit", "identity": START_HEAD, "status": "RECOVERY_BASELINE_PRESERVED"},
    ]
    write_json(PREFLIGHT / "repository_state.json", repository_state)
    write_json(PREFLIGHT / "v022_release_custody.json", release_custody)
    write_json(PREFLIGHT / "pr5_reproduction.json", pr5_reproduction)
    write_json(PREFLIGHT / "pr5_workflow_reconciliation.json", workflows)
    write_jsonl(PREFLIGHT / "immutable_evidence_registry.jsonl", immutable)
    write_checksums(
        PREFLIGHT,
        [
            "repository_state.json",
            "v022_release_custody.json",
            "pr5_reproduction.json",
            "pr5_workflow_reconciliation.json",
            "immutable_evidence_registry.jsonl",
        ],
        "SHA256SUMS.txt",
    )


def finding(
    finding_id: str,
    title: str,
    status: str,
    evidence: list[str],
    consequence: str,
    required_repair: str,
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "title": title,
        "status": status,
        "evidence": evidence,
        "consequence": consequence,
        "required_repair": required_repair,
    }


def expected_red_findings() -> list[dict[str, Any]]:
    defect = "CONFIRMED_DEFECT"
    scope = "CONFIRMED_SCOPE_ERROR"
    mismatch = "CONFIRMED_CONTRACT_CODE_MISMATCH"
    uncalibrated = "CONFIRMED_UNCALIBRATED_COMPONENT"
    return [
        finding("F001", "Fixed parent threshold not power-derived", defect, ["studies/v0.3.0-method-freeze/calibration_preregistration.json: parent_count_per_fixture=12 and minimum_effective_parents=8", "python/torusbrot/geometry/calibration.py:171 passes minimum_parents=8"], "A universal eligibility boundary was frozen without an ICC/effect-size/claim-tier power surface.", "Replace it prospectively with design- and endpoint-specific support derived from dependence and power."),
        finding("F002", "Candidate scoring credited unknown parent support", defect, ["scripts/generate_v030_candidate_selection.py:64 labels each wind acquisition only a prospective parent", "scripts/generate_v030_candidate_selection.py:75 nevertheless awards 15/15 parent points"], "Unknown hierarchy received full inferential-design credit before structure inspection.", "Require verified hierarchy counts before eligibility scoring; unknown receives zero/full-credit prohibition."),
        finding("F003", "Selection tests validate ranking, not eligibility truth", scope, ["tests/test_v030_candidate_selection.py verifies score arithmetic and ranking only", "No pre-freeze assertion validates campaign/run/condition hierarchy"], "A correctly computed score can still rank an inferentially ineligible source first.", "Add structure-probe schemas and fail-closed eligibility assertions before candidate freeze."),
        finding("F004", "Method C versus binary sensitivity mismatch", mismatch, ["studies/v0.3.0-method-freeze/frozen_revised_method.json forbids binary positive and negative", "scripts/materialize_v030_field.py:440-442 invokes exact-sign binary sensitivity and the eight-parent gate"], "A nonbinary evidence container was blocked by a binary population-resolution argument without separating descriptive and population claim tiers.", "Define claim-tier-specific execution and inference boundaries."),
        finding("F005", "Wind-farm acquisitions are not exchangeable parents", scope, ["studies/v0.3.0-field-assay/materialization/domain_translation.json records one control and three interventions", "scripts/materialize_v030_field.py:152-155 assigns all four a common parent abstraction"], "The four condition-level acquisitions do not form repeated exchangeable units for a common-condition estimand.", "Represent campaign, condition, acquisition, and nested samples explicitly and prohibit exchangeable pooling."),
        finding("F006", "S_e/geometric-scale collision", mismatch, ["studies/v0.3.0-method-freeze/S_e_semantics_gate.json defines S_e as persistence/nonredundancy", "studies/v0.3.0-field-assay/materialization/geometric_scale_registry.jsonl calls S_e geometric bin scale"], "The field translation reuses a protected persistence symbol for geometry resolution.", "Reserve S_e for the registered persistence endpoint and use ell for geometric scale."),
        finding("F007", "T_e/elbow conflation risk", mismatch, ["studies/v0.3.0-field-assay/materialization/domain_translation.json makes T_e conditional on an operation-depth elbow", "studies/v0.3.0-method-freeze/T_e_semantics_gate.json requires first registered operation depth where observed/null separation emerges"], "An elbow is not the emergence-depth endpoint.", "Define T_e solely by prospective separation emergence across registered operation depth; report elbows separately."),
        finding("F008", "Closure null pseudoreplication", defect, ["python/torusbrot/geometry/channels.py:162-168 flattens every child from every parent into null_traces", "python/torusbrot/geometry/channels.py:178-180 computes local p from the flattened array"], "Individual null children are treated as population replicates.", "Construct each joint null replicate by drawing one matched child per parent and recomputing the population statistic."),
        finding("F009", "Curvature null distribution is not aggregate-null", defect, ["python/torusbrot/geometry/channels.py:169-173 creates one median child trace per parent", "python/torusbrot/geometry/channels.py:186-190 passes parent medians as null_traces"], "Parent heterogeneity is substituted for the joint null distribution of the population trace.", "Use parent-matched joint aggregate traces for null-standardized curvature."),
        finding("F010", "Hard-coded midpoint complexity penalty", defect, ["python/torusbrot/geometry/channels.py:143-147 adds 0.0015*(N-midpoint)^2"], "The objective structurally favors the middle of N=6..14 and can manufacture an interior winner.", "Remove the penalty and retain raw boundary/tie behavior."),
        finding("F011", "Geometry closure is not a canonical TLD closure operator", uncalibrated, ["python/torusbrot/geometry/channels.py:137-149 uses spectral tail energy plus midpoint penalty", "python/torusbrot/geometry/calibration.py: historical_construct_benchmark runs canonical sequence scoring in parallel"], "No reduction or commutative bridge connects modal tail energy to chi/RMS TLD closure.", "Either prove/test a geometry-TLD bridge or rename the channel as a non-TLD modal statistic."),
        finding("F012", "Representation agreement is misimplemented", defect, ["python/torusbrot/geometry/calibration.py:181-198 calls agreement when two scalar channels on the same representation are significant with the same sign"], "The test does not compare faithful representations or transformation laws.", "Compare registered transformations/representations and preserve invariant/equivariant discrepancies."),
        finding("F013", "Vector rotation is physically incomplete", defect, ["python/torusbrot/geometry/calibration.py:92 uses np.rot90 on the array", "No component rotation or orientation metadata transform follows"], "Coordinates rotate while vector components remain in the old basis.", "Transform coordinates, components, masks, and orientation metadata together."),
        finding("F014", "Silent scalarization and dimensional averaging", defect, ["python/torusbrot/geometry/channels.py:17-23 converts vectors to magnitude and averages leading dimensions", "python/torusbrot/geometry/calibration.py:140-145 repeats the collapse for baselines"], "Direction, time, modality, and nesting can disappear without a projection contract.", "Use typed handlers and reject unregistered dimensional collapse or magnitude conversion."),
        finding("F015", "Spatiotemporal fixtures are not truly spatiotemporal", scope, ["python/torusbrot/geometry/synthetic.py labels SYN-11 and SYN-12 SPATIOTEMPORAL_SCALAR_FIELD", "Both stored arrays are static 32x32 without an explicit time coordinate"], "Time handling, recursive depth, and spatiotemporal nulls were not calibrated.", "Add explicit time axes, temporal operations, and matched spatiotemporal null controls."),
        finding("F016", "Correlation/manifold/topology labels exceed implementation", scope, ["python/torusbrot/geometry/synthetic.py labels correlation geometry and persistent-homology ring", "python/torusbrot/geometry/channels.py implements only binary symmetric graph detection and generic raster summaries"], "Labels imply unsupported topology/manifold/correlation and weighted/directed graph capabilities.", "Implement typed scientific handlers or explicitly downgrade/defer each claim."),
        finding("F017", "Synthetic parents are artificial noisy copies", defect, ["python/torusbrot/geometry/synthetic.py:396-403 generates all parents from one field plus noise", "Graph parents are exact copies"], "The suite does not establish acquisition- or campaign-level independence behavior.", "Generate independent latent parents and explicit multi-campaign/nested hierarchies."),
        finding("F018", "Nested-parent correction was not tested", defect, ["python/torusbrot/geometry/synthetic.py labels SYN-15 nested", "parent_and_null_ensembles still emits 12 nominal parents and geometry_scout counts array length"], "A hierarchy label is not a hierarchical resampling or effective-sample model.", "Execute cluster-aware inference on true nested fixtures."),
        finding("F019", "Negative calibration is too small and easy", uncalibrated, ["studies/v0.3.0-method-freeze/independent_method_verification.json records only four negative challenges and two strict null fixtures", "Binary family false-positive estimate is 1/4=0.25"], "The suite cannot establish a family error bound of 0.05 with useful uncertainty.", "Use at least 12 negative families, adversarial near-nulls, multiple realizations, and confidence intervals."),
        finding("F020", "Synthetic binary target is not TLD-specific", scope, ["python/torusbrot/geometry/synthetic.py marks broadly smooth/correlated/wave fields positive", "No channel-specific TLD bridge defines a universal binary truth"], "Power largely measures generic structure detection rather than TLD discrimination.", "Define truth per structure channel and reserve TLD naming for bridge-passing channels."),
        finding("F021", "Fragility implementation is too weak", defect, ["python/torusbrot/geometry/calibration.py:119-123 requires only shuffle > noise and rotation", "Missing values are mean-filled and resolution uses repeat-based decimation"], "The Boolean rule lacks ensemble uncertainty and masks important perturbation failures.", "Use complete ensembles, masks, anti-aliasing, registered response classes, effect sizes, and intervals."),
        finding("F022", "Absolute scale reappears in synthetic noise", defect, ["python/torusbrot/geometry/synthetic.py:400 uses max(std,1.0)*0.04", "python/torusbrot/geometry/calibration.py:94 uses max(std,1.0)"], "Low-amplitude fields receive unit-dependent noise unrelated to their scale.", "Use a robust relative scale with an explicitly justified numerical floor."),
        finding("F023", "Domain baseline is generic rather than scientific", uncalibrated, ["python/torusbrot/geometry/calibration.py:128-156 uses graph density residual or additive row/column residual"], "Synthetic diagnostics are presented as a general baseline gate without domain-standard models.", "Require a domain-specific conventional baseline contract for claim-bearing field assays."),
        finding("F024", "Independent verifier is summary-level only", defect, ["scripts/verify_geometry_calibration.py:222 loads synthetic_method_results.csv", "It recomputes summaries but not raw projections, null generation, closure, curvature, or perturbations"], "Production preprocessing errors can survive unchanged into verification inputs.", "Start from raw seeds/arrays and independently recompute the full pipeline."),
        finding("F025", "Boundary-pinning flag is ineffective", defect, ["python/torusbrot/geometry/metrology.py:54 selects only coordinates[1:-1]", "python/torusbrot/geometry/metrology.py:92 tests only coordinates[0] and coordinates[-1]"], "The flag cannot detect first-/last-interior pinning and does not report ties.", "Report adjacent-boundary selection, tied minima/peaks, and flat traces explicitly."),
        finding("F026", "Curvature bootstrap is not a clear statistical bootstrap", defect, ["python/torusbrot/geometry/metrology.py:70-76 resamples null traces, subtracts their median from the fixed observed trace, and recenters"], "The procedure is neither a parent bootstrap nor a joint-null population bootstrap.", "Bootstrap independent parents/acquisitions and use matched aggregate-null traces."),
        finding("F027", "Historical construct recovery is parallel, not commutative", uncalibrated, ["python/torusbrot/geometry/calibration.py:238-294 reruns canonical sequence scoring", "No path-graph or 1xM geometry operator is compared under a commutative relationship"], "Legacy recovery does not establish that the geometry statistic extends TLD.", "Implement sequence-to-path embeddings and explicit commutation/recovery tests."),
        finding("F028", "T_e and S_e were never calibrated", uncalibrated, ["studies/v0.3.0-method-freeze/T_e_semantics_gate.json and S_e_semantics_gate.json mark synthetic/historical applicability absent", "Graph diffusion appears only in the later wind-field translation"], "Emergence and persistence endpoints lack controlled calibration.", "Calibrate operation depth and persistence on truth-known fixtures before any field use."),
        finding("F029", "Geometry N-grid inherited without justification", uncalibrated, ["studies/v0.3.0-method-freeze/calibration_preregistration.json freezes N=6..14", "python/torusbrot/geometry/channels.py interprets N as a spectral mode count without construct-specific semantics"], "Historical N labels are reused for a different operator.", "Define geometry N semantics and specificity independently or use a new symbol."),
        finding("F030", "Null family not calibrated on irregular scanning geometry", uncalibrated, ["Synthetic calibration uses regular arrays and binary graphs", "studies/v0.3.0-field-assay/materialization/null_registry.jsonl introduces cyclic/block nulls after method freeze"], "Irregular-binning and scan-path bias are unknown.", "Add irregular-coordinate controls and source-type-specific null-bias tests before freezing nulls."),
        finding("F031", "Unit provenance lacks metrological uncertainty test", uncalibrated, ["studies/v0.3.0-field-assay/materialization/materialization_receipt.json warns NATIVE_NETCDF_UNIT_ATTRIBUTES_ABSENT", "Units are inferred cross-source but no scale-sensitivity execution occurred"], "Plausible units are retained without quantified scale/provenance uncertainty.", "Preserve provenance class and run preregistered scale-sensitivity/metrology controls."),
        finding("F032", "FUP/directional-porosity channel is missing", uncalibrated, ["No fup or line-porosity implementation exists under python/torusbrot/geometry", "PR #5 neither implements nor explicitly gates the channel"], "A roadmap channel was implicitly omitted without an applicability decision.", "Add a separately gated optional channel or an explicit incompatibility/defer receipt."),
        finding("F033", "Method C is an evidence container, not established predictive discrimination", scope, ["studies/v0.3.0-method-freeze/frozen_revised_method.json correctly forbids binary positive/negative", "studies/v0.3.0-method-freeze/method_acceptance_gate.json selects it after binary methods fail"], "Finite nonpooled outputs do not establish a calibrated predictive TLD assay.", "Rename the accepted form INSTRUMENTED_EVIDENCE_VECTOR unless stronger discrimination gates pass."),
        finding("F034", "Claim-source quarantine is incomplete", scope, ["No claim_source_quarantine.jsonl or historical_overclaim_registry.jsonl exists", "Current executable authority does not enumerate strong chat/draft claims and their missing evidence"], "Unsupported historical claims can leak into method interpretation.", "Create an append-only source-authority quarantine with allowed/forbidden use and reopen conditions."),
    ]


def build_expected_red() -> None:
    findings = expected_red_findings()
    statuses = Counter(row["status"] for row in findings)
    audit = {
        "schema_version": "1.0.0",
        "prompt_id": "TFS-PR5-V0.3.0-METHOD-V2-FORENSIC-RECOVERY-PARENT-DESIGN-FIRST-VALID-FIELD-ASSAY-2026-08-19-V1",
        "audit_mode": "EXPECTED_RED_BEFORE_SCIENTIFIC_REPAIR",
        "recovery_base_head": START_HEAD,
        "finding_count": len(findings),
        "status_counts": dict(sorted(statuses.items())),
        "audit_outcome": "EXPECTED_RED_CONFIRMED_34_FINDINGS",
        "scientific_behavior_changed": False,
        "method_v1_rewritten": False,
        "dataset_v1_rewritten": False,
        "wind_farm_claim_metrics_computed": False,
        "green_repairs_authorized_only_after_this_audit_commit": True,
        "findings": findings,
    }
    lines = [
        "# PR #5 v0.3.0 expected-red forensic audit",
        "",
        f"Recovery base: `{START_HEAD}`.",
        "",
        "This audit is intentionally red. It records confirmed limitations before any Method V2 scientific behavior changes. Method Freeze V1, Dataset Freeze V1, the blocked wind-farm materialization, v0.2.1, v0.2.2, and TLD I remain append-only and unchanged.",
        "",
        "| ID | Status | Finding |",
        "| --- | --- | --- |",
    ]
    lines.extend(f"| {row['finding_id']} | `{row['status']}` | {row['title']} |" for row in findings)
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "No new field candidate is selected, no wind-farm claim metric is executed, and no v0.3.0 release is authorized by this audit. The next legal action is append-only Method V2 repair and calibration.",
        ]
    )
    call_graph = {
        "schema_version": "1.0.0",
        "scope": "PR5_START_HEAD",
        "nodes": [
            {"id": "build_fixtures", "symbol": "build_synthetic_fixtures", "location": "python/torusbrot/geometry/synthetic.py:92"},
            {"id": "parent_nulls", "symbol": "parent_and_null_ensembles", "location": "python/torusbrot/geometry/synthetic.py:386"},
            {"id": "evaluate", "symbol": "evaluate_fixture", "location": "python/torusbrot/geometry/calibration.py:159"},
            {"id": "scout", "symbol": "geometry_scout", "location": "python/torusbrot/geometry/scout.py:21"},
            {"id": "projection", "symbol": "field_projection_scores", "location": "python/torusbrot/geometry/channels.py:37"},
            {"id": "scalarize", "symbol": "_scalar_field", "location": "python/torusbrot/geometry/channels.py:16"},
            {"id": "separation", "symbol": "signed_bidirectional_separation", "location": "python/torusbrot/geometry/channels.py:94"},
            {"id": "closure", "symbol": "closure_null_calibration", "location": "python/torusbrot/geometry/channels.py:151"},
            {"id": "modal_trace", "symbol": "modal_closure_trace", "location": "python/torusbrot/geometry/channels.py:137"},
            {"id": "curvature", "symbol": "interior_relative_curvature", "location": "python/torusbrot/geometry/metrology.py:24"},
            {"id": "fragility", "symbol": "_fragility", "location": "python/torusbrot/geometry/calibration.py:64"},
            {"id": "baseline", "symbol": "_baseline_exclusion", "location": "python/torusbrot/geometry/calibration.py:127"},
            {"id": "summary_verifier", "symbol": "verify_geometry_calibration.main", "location": "scripts/verify_geometry_calibration.py:221"},
            {"id": "candidate_selection", "symbol": "generate_v030_candidate_selection.main", "location": "scripts/generate_v030_candidate_selection.py:413"},
            {"id": "materialize", "symbol": "materialize_v030_field.main", "location": "scripts/materialize_v030_field.py:74"},
        ],
        "edges": [
            ["build_fixtures", "evaluate"], ["evaluate", "parent_nulls"], ["evaluate", "scout"], ["evaluate", "projection"], ["projection", "scalarize"], ["evaluate", "separation"], ["evaluate", "closure"], ["closure", "modal_trace"], ["closure", "curvature"], ["evaluate", "fragility"], ["evaluate", "baseline"], ["summary_verifier", "production_generated_CSV"], ["candidate_selection", "metadata_scores"], ["materialize", "frozen_parent_gate_v1"],
        ],
        "critical_defect_paths": [
            "evaluate -> closure -> flattened null children",
            "modal_trace -> undocumented midpoint penalty",
            "projection -> silent scalarization",
            "summary_verifier -> production-generated CSV rather than raw fixtures",
            "candidate_selection -> unknown hierarchy receives full parent score",
        ],
    }
    unit_map = {
        "schema_version": "1.0.0",
        "synthetic_v1": {
            "fixture_families": 25,
            "nominal_parents_per_fixture": 12,
            "construction": "one deterministic field plus independent additive noise; graph parents exact copies",
            "true_acquisition_hierarchy": "ABSENT",
            "nested_fixture_executed_hierarchically": False,
            "null_children_per_nominal_parent": 127,
            "effective_sample_method": "array count only",
        },
        "wind_farm_v1": {
            "campaigns": 1,
            "physical_systems": 1,
            "condition_level_acquisitions": 4,
            "same_condition_replicates": 0,
            "conditions": ["Greedy control", "yaw intervention 1", "yaw intervention 2", "yaw intervention 3"],
            "nested_synchronized_samples": 600000,
            "sensor_views_per_acquisition": 2,
            "interacting_turbines": 3,
            "exchangeable_acquisition_pool": False,
            "samples_promotable_to_parents": False,
            "sensor_views_promotable_to_parents": False,
            "turbines_promotable_to_parents": False,
            "maximum_current_role": "NONCONFIRMATORY_STRUCTURE_EXPOSED_ENGINEERING_PILOT_AFTER_METHOD_V2_FREEZE",
        },
        "population_inference_v1": {
            "minimum_effective_parents": 8,
            "derivation": "FIXED_NOT_POWER_DERIVED",
            "claim_tier_separation": "ABSENT",
            "binary_sign_resolution_used_against_nonbinary_method": True,
        },
    }
    collision_map = {
        "schema_version": "1.0.0",
        "collisions": [
            {"symbol": "S_e", "canonical": "persistence/nonredundancy endpoint", "collision": "geometric Cartesian bin scale", "locations": ["studies/v0.3.0-method-freeze/S_e_semantics_gate.json", "studies/v0.3.0-field-assay/materialization/geometric_scale_registry.jsonl"], "status": "CONFIRMED_CONTRACT_CODE_MISMATCH", "replacement": "ell for geometric scale"},
            {"symbol": "T_e", "canonical": "first registered operation depth where observed/null separation emerges", "collision": "null-calibrated interior curvature elbow", "locations": ["studies/v0.3.0-method-freeze/T_e_semantics_gate.json", "studies/v0.3.0-field-assay/materialization/domain_translation.json"], "status": "CONFIRMED_CONTRACT_CODE_MISMATCH", "replacement": "report elbow separately with no T_e authority"},
            {"symbol": "winner_N", "canonical": "closure/model-order argmin under its own operator", "collision": "historical, temporal, or physical scale interpretation", "locations": ["studies/v0.3.0-method-freeze/N_symbol_collision_audit.json"], "status": "ALREADY_GUARDED_IN_V1_BUT_REQUIRES_V2_REGRESSION", "replacement": "retain winner_N only where its operator is justified"},
            {"symbol": "parent", "canonical": "independent inferential unit under a registered estimand", "collision": "condition-level acquisition in one campaign", "locations": ["scripts/materialize_v030_field.py", "studies/v0.3.0-field-assay/materialization/parent_registry.jsonl"], "status": "CONFIRMED_SCOPE_ERROR", "replacement": "campaign/condition/acquisition/nested-sample hierarchy"},
        ],
    }
    write_json(EXPECTED_RED / "pr5_expected_red.json", audit)
    with (EXPECTED_RED / "pr5_expected_red.md").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    write_jsonl(EXPECTED_RED / "finding_registry.jsonl", findings)
    write_json(EXPECTED_RED / "current_call_graph.json", call_graph)
    write_json(EXPECTED_RED / "current_statistical_unit_map.json", unit_map)
    write_json(EXPECTED_RED / "current_semantic_collision_map.json", collision_map)
    write_checksums(
        EXPECTED_RED,
        [
            "pr5_expected_red.json",
            "pr5_expected_red.md",
            "finding_registry.jsonl",
            "current_call_graph.json",
            "current_statistical_unit_map.json",
            "current_semantic_collision_map.json",
        ],
        "expected_red_SHA256SUMS.txt",
    )


def main() -> None:
    build_preflight()
    build_expected_red()
    print("Generated v0.3.0 recovery preflight and 34-finding expected-red audit.")


if __name__ == "__main__":
    main()
