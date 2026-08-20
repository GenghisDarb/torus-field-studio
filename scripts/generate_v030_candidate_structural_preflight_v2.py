# ruff: noqa: E501 -- source titles, URLs, and structural evidence are retained verbatim.
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "studies" / "v0.3.0-recovery" / "candidate_selection"
METHOD_FREEZE_COMMIT = "dcaeb72b29fc0d32b002d9b5de0809b13f2ed272"
METHOD_IMPLEMENTATION_COMMIT = "dd17f1f922dea81db474a8c52347a80580d7eead"
CHECKED_AT = "2026-08-20"


def canonical(value: Any, *, pretty: bool = False) -> bytes:
    options: dict[str, Any] = {"sort_keys": True, "ensure_ascii": False, "allow_nan": False}
    if pretty:
        options["indent"] = 2
    else:
        options["separators"] = (",", ":")
    return (json.dumps(value, **options) + "\n").encode()


def write_json(name: str, value: Any) -> None:
    (OUT / name).write_bytes(canonical(value, pretty=True))


def write_jsonl(name: str, rows: list[dict[str, Any]]) -> None:
    (OUT / name).write_bytes(b"".join(canonical(row) for row in rows))


def known(value: int, evidence: str) -> dict[str, Any]:
    return {"status": "VERIFIED", "value": value, "evidence": evidence}


def unknown(reason: str) -> dict[str, Any]:
    return {"status": "UNKNOWN_NO_SCORE", "value": None, "reason": reason}


def hierarchy(
    candidate_id: str,
    *,
    campaigns: dict[str, Any],
    systems: dict[str, Any],
    acquisitions: dict[str, Any],
    conditions: dict[str, Any],
    same_condition_replicates: dict[str, Any],
    nested_samples: dict[str, Any],
    modal_views: dict[str, Any],
    components: dict[str, Any],
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "campaign_count": campaigns,
        "independent_specimen_or_system_count": systems,
        "independent_acquisition_count": acquisitions,
        "condition_count": conditions,
        "same_condition_replicate_count": same_condition_replicates,
        "nested_sample_count": nested_samples,
        "sensor_or_modal_view_count": modal_views,
        "field_component_count": components,
        "unknown_counts_awarded_full_score": False,
        "nested_samples_promoted_to_independent_parents": False,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    probes = [
        {
            "candidate_id": "actuated_fluidic_pinball_piv",
            "title": "Dataset of: On the turbulent wake of the actuated fluidic pinball: Dynamics, bifurcations and control authority",
            "doi": "10.5281/zenodo.20794709",
            "metadata_url": "https://zenodo.org/api/records/20794709",
            "license": "CC-BY-4.0",
            "record_revision": 4,
            "record_modified": "2026-06-24T10:12:04.295559+00:00",
            "files": [
                {"name": "ExperimentalDataset.zip", "size_bytes": 1333197134, "md5": "6629a8e110b1682b9361de37d8be4afb"},
                {"name": "URANSDataset.zip", "size_bytes": 226542913, "md5": "567f6c2602da4174df7e278e380c9012"},
                {"name": "README.txt", "size_bytes": 3692, "md5": "3327aa1fe31312da883bfc484dd8ede5"},
            ],
            "structural_probe": {
                "record_metadata_bytes": "JSON metadata only",
                "readme_bytes": 3692,
                "zip_range_bytes": 71785,
                "zip_entry_count": 59,
                "hdf5_acquisition_member_count": 57,
                "unactuated_reference_acquisition_count": 28,
                "actuated_or_primary_acquisition_count": 29,
                "unique_registered_actuation_values": 28,
                "actuation_range": [-2.8, 2.6],
                "zip_inventory_sha256": "08e2a765fd542f0b4d8e92b846f6963f4bde9bfee8cdc05ab3cddded5811c522",
                "field_shapes": "Ny x Nx x Nsnap; exact dimensions intentionally not opened before selection",
                "field_components": ["U", "V"],
                "coordinates": ["X", "Y"],
                "attributes": ["CaseName", "p", "Nsnapshots"],
                "reference_pairing": "README states every _zero_ file is an unactuated reference acquired immediately before its actuated case",
            },
            "inspection_mode": "METADATA_README_AND_ZIP_CENTRAL_DIRECTORY_ONLY",
            "raw_hdf5_field_payload_accessed": False,
            "field_statistics_computed": False,
            "TLD_channels_computed": False,
            "closure_computed": False,
            "null_separation_computed": False,
            "source_power_computed": False,
            "outcome_informed_projection": False,
        },
        {
            "candidate_id": "structured_light_patterns",
            "title": "Structured Light Patterns",
            "doi": "10.5281/zenodo.14002229",
            "metadata_url": "https://zenodo.org/api/records/14002229",
            "license": "MIT",
            "record_revision": 4,
            "record_modified": "2024-10-28T15:23:33.603387+00:00",
            "files": [{"name": "Data.tar.gz", "size_bytes": 1913898327, "md5": "738288963abbeffaafe366a5d9c2850f"}],
            "structural_probe": {"raw_fields": ["HDF5 intense-state images", "TIFF photocount frames"], "nested_frames_per_pure_state_file": 2000, "background_file": True, "calibration_frames": 1, "independent_acquisition_repeats_per_state": "UNKNOWN"},
            "inspection_mode": "ZENODO_RECORD_DESCRIPTION_ONLY",
            "raw_hdf5_field_payload_accessed": False,
            "field_statistics_computed": False,
            "TLD_channels_computed": False,
            "closure_computed": False,
            "null_separation_computed": False,
            "source_power_computed": False,
            "outcome_informed_projection": False,
        },
        {
            "candidate_id": "cylinder_array_piv",
            "title": "Turbulent Flow Behind Cylinder Arrays",
            "doi": "10.5281/zenodo.16794036",
            "metadata_url": "https://zenodo.org/api/records/16794036",
            "license": "CC-BY-4.0",
            "record_revision": 6,
            "record_modified": "2025-08-11T13:33:46.336500+00:00",
            "files": [{"name": "CylinderArrays.mat", "size_bytes": 12968316376, "md5": "41d1c99251043bfcfb46006989cb96d6"}],
            "structural_probe": {"array_configurations": 9, "acquisition_seconds_per_configuration": 15, "sampling_hz": 200, "field_components": ["u", "v"], "coordinates": ["x_mm", "y_mm"], "same_configuration_repeats": 0},
            "inspection_mode": "ZENODO_RECORD_DESCRIPTION_ONLY",
            "raw_hdf5_field_payload_accessed": False,
            "field_statistics_computed": False,
            "TLD_channels_computed": False,
            "closure_computed": False,
            "null_separation_computed": False,
            "source_power_computed": False,
            "outcome_informed_projection": False,
        },
        {
            "candidate_id": "nbse2_4dstem_temperature_series",
            "title": "Spatial correlations of charge density wave order across the transition in 2H-NbSe2",
            "doi": "10.5281/zenodo.17823449",
            "metadata_url": "https://zenodo.org/api/records/17823449",
            "license": "CC-BY-NC-SA-4.0",
            "record_revision": 8,
            "record_modified": "2026-01-06T14:17:28.256737+00:00",
            "files": [{"name": "11 temperature Data_XXK.mat members plus code and two peak lists", "size_bytes": 14342120945, "member_count": 14}],
            "structural_probe": {"specimen_count": 1, "temperature_acquisitions": 11, "temperatures_K": [20, 25, 27, 29, 31, 33, 35, 37, 40, 45, 300], "same_temperature_repeats": 0, "geometry": "4D-STEM diffraction field over real-space probe positions"},
            "inspection_mode": "ZENODO_RECORD_DESCRIPTION_AND_FILE_INVENTORY_ONLY",
            "raw_hdf5_field_payload_accessed": False,
            "field_statistics_computed": False,
            "TLD_channels_computed": False,
            "closure_computed": False,
            "null_separation_computed": False,
            "source_power_computed": False,
            "outcome_informed_projection": False,
        },
        {
            "candidate_id": "single_cylinder_piv_re413",
            "title": "Particle image velocimetry (PIV) data of flow past a cylinder",
            "doi": "10.5281/zenodo.20765567",
            "metadata_url": "https://zenodo.org/api/records/20765567",
            "license": "CC-BY-4.0",
            "record_revision": 8,
            "record_modified": "2026-07-06T14:31:44.131970+00:00",
            "files": [{"name": "cylinder_vel.mat", "size_bytes": 1082404799, "md5": "4cc876439c48f7970afa477ea17d217a"}],
            "structural_probe": {"acquisitions": 1, "field_components": ["u_m_per_s", "v_m_per_s"], "coordinates": ["x_m", "y_m"], "sampling_hz": 20, "mask_semantics": "exact zeros denote cylinder and laser-shadow masks"},
            "inspection_mode": "ZENODO_RECORD_DESCRIPTION_ONLY",
            "raw_hdf5_field_payload_accessed": False,
            "field_statistics_computed": False,
            "TLD_channels_computed": False,
            "closure_computed": False,
            "null_separation_computed": False,
            "source_power_computed": False,
            "outcome_informed_projection": False,
        },
        {
            "candidate_id": "wind_farm_scanning_lidar_wakes",
            "title": "Wind Tunnel Experimental Dataset for Wind Farm Control with Scanning Lidar Wake Measurements",
            "doi": "10.5281/zenodo.18731994",
            "license": "CC-BY-4.0",
            "structural_probe": {"campaigns": 1, "condition_acquisitions": 4, "same_condition_repeats": 0, "modalities": 2, "field_components": 2},
            "inspection_mode": "PREVIOUSLY_MATERIALIZED_NONCONFIRMATORY_PILOT",
            "raw_hdf5_field_payload_accessed": True,
            "candidate_role": "FORBIDDEN_FOR_CONFIRMATORY_SELECTION",
            "field_statistics_computed": True,
            "TLD_channels_computed": False,
            "closure_computed": False,
            "null_separation_computed": False,
            "source_power_computed": False,
            "outcome_informed_projection": False,
        },
    ]
    legacy = [
        ("rotating_quantum_wave_turbulence", "10.5281/zenodo.7525698", "RAW_GEOMETRY_DATA_UNAVAILABLE"),
        ("second_sound_attenuation", "10.5281/zenodo.5767197", "RAW_GEOMETRY_DATA_UNAVAILABLE"),
        ("mit_2024_direct_second_sound_imaging", "10.1126/science.adg3430", "RAW_NUMERIC_DATA_UNAVAILABLE"),
        ("atmospheric_turbulence_wavefront_tiff", "10.5281/zenodo.11063896", "NO_INDEPENDENT_PARENT_MODEL"),
        ("nanograv_15yr_pair_geometry", "10.5281/zenodo.7967584", "PRIOR_OUTCOME_EXPOSURE"),
    ]
    for candidate_id, doi, reason in legacy:
        probes.append(
            {
                "candidate_id": candidate_id,
                "doi": doi,
                "inspection_mode": "PRIOR_METADATA_REGISTRY_RECONCILIATION_ONLY",
                "structural_probe": {"verified_field_hierarchy": "NOT_ESTABLISHED_FOR_METHOD_V2", "primary_exclusion": reason},
                "raw_hdf5_field_payload_accessed": False,
                "field_statistics_computed": False,
                "TLD_channels_computed": False,
                "closure_computed": False,
                "null_separation_computed": False,
                "source_power_computed": False,
                "outcome_informed_projection": False,
            }
        )

    hierarchies = [
        hierarchy(
            "actuated_fluidic_pinball_piv",
            campaigns=unknown("record and README do not enumerate campaign dates"),
            systems=known(1, "one physical fluidic-pinball apparatus"),
            acquisitions=known(57, "57 HDF5 acquisition members in verified ZIP central directory"),
            conditions=known(29, "28 p values plus the distinct p=-1.4 upward case"),
            same_condition_replicates=known(28, "28 _zero_ unactuated reference acquisitions, each acquired immediately before an actuated case"),
            nested_samples=unknown("Nsnapshots is registered but its attribute value was not opened before selection"),
            modal_views=known(1, "one experimental planar PIV modality"),
            components=known(2, "README registers U and V without scalarization"),
        ),
        hierarchy(
            "structured_light_patterns",
            campaigns=unknown("not stated"),
            systems=known(1, "one structured-light preparation/imaging apparatus described"),
            acquisitions=unknown("archive member inventory was not opened"),
            conditions=unknown("many states are described but exact state-file count is not verified"),
            same_condition_replicates=unknown("2,000 TIFF frames are nested within a state file, not verified acquisition repeats"),
            nested_samples=known(2000, "each pure-state photocount TIFF file has 2,000 frames"),
            modal_views=known(2, "intense image and photocount representations"),
            components=known(1, "scalar intensity per image"),
        ),
        hierarchy(
            "cylinder_array_piv",
            campaigns=unknown("not stated"),
            systems=known(1, "one cylinder-array experiment"),
            acquisitions=known(9, "nine separately configured 15-second PIV datasets"),
            conditions=known(9, "nine H/D-by-V/D configurations"),
            same_condition_replicates=known(0, "one acquisition per configuration in record description"),
            nested_samples=known(3000, "15 seconds at 200 Hz per configuration"),
            modal_views=known(1, "planar PIV"),
            components=known(2, "u and v"),
        ),
        hierarchy(
            "nbse2_4dstem_temperature_series",
            campaigns=unknown("not stated"),
            systems=known(1, "one 24 nm NbSe2 flake specimen"),
            acquisitions=known(11, "one deposited raw 4D-STEM member per listed temperature"),
            conditions=known(11, "11 temperatures"),
            same_condition_replicates=known(0, "one member per temperature"),
            nested_samples=unknown("probe-position dimensions not opened"),
            modal_views=known(1, "4D-STEM"),
            components=known(1, "diffraction intensity field"),
        ),
        hierarchy(
            "single_cylinder_piv_re413",
            campaigns=unknown("not stated"),
            systems=known(1, "one cylinder/water-channel system"),
            acquisitions=known(1, "one time-series MAT object"),
            conditions=known(1, "one Re=413 condition"),
            same_condition_replicates=known(0, "one acquisition"),
            nested_samples=unknown("time dimension not opened"),
            modal_views=known(1, "planar PIV"),
            components=known(2, "u and v"),
        ),
        hierarchy(
            "wind_farm_scanning_lidar_wakes",
            campaigns=known(1, "materialized nonconfirmatory pilot"),
            systems=known(1, "one three-turbine facility system"),
            acquisitions=known(4, "four condition acquisitions"),
            conditions=known(4, "one baseline plus three yaw interventions"),
            same_condition_replicates=known(0, "no repeated acquisition at the same yaw"),
            nested_samples=known(150000, "synchronized samples per acquisition"),
            modal_views=known(2, "R2D2 and R2D3"),
            components=known(2, "ux and uy"),
        ),
    ]
    for candidate_id, _, _ in legacy:
        hierarchies.append(
            hierarchy(
                candidate_id,
                campaigns=unknown("not established"),
                systems=unknown("not established"),
                acquisitions=unknown("not established"),
                conditions=unknown("not established"),
                same_condition_replicates=unknown("not established"),
                nested_samples=unknown("not established"),
                modal_views=unknown("not established"),
                components=unknown("not established"),
            )
        )

    eligibility = [
        {"candidate_id": "actuated_fluidic_pinball_piv", "maximum_eligible_tier": 2, "tier_name": "WITHIN_CAMPAIGN_REPEATED_ACQUISITION_ASSAY", "eligible": True, "population_generalization": False, "TLD_DERIVED_default": "BLOCKED", "basis": "57 acquisition files and 28 repeated unactuated references; campaign count remains unknown"},
        {"candidate_id": "structured_light_patterns", "maximum_eligible_tier": 1, "tier_name": "SINGLE_FIELD_INSTANCE_ASSAY", "eligible": True, "population_generalization": False, "TLD_DERIVED_default": "BLOCKED", "basis": "raw image fields exist; frames are nested and independent acquisition repeats are unknown"},
        {"candidate_id": "cylinder_array_piv", "maximum_eligible_tier": 1, "tier_name": "SINGLE_FIELD_INSTANCE_ASSAY", "eligible": False, "population_generalization": False, "TLD_DERIVED_default": "BLOCKED", "basis": "structurally Tier 1 but 13.0 GB single-object materialization exceeds the frozen local feasibility bound"},
        {"candidate_id": "nbse2_4dstem_temperature_series", "maximum_eligible_tier": 1, "tier_name": "SINGLE_FIELD_INSTANCE_ASSAY", "eligible": False, "population_generalization": False, "TLD_DERIVED_default": "BLOCKED", "basis": "structurally Tier 1 on one specimen but 14.3 GB materialization exceeds the frozen local feasibility bound"},
        {"candidate_id": "single_cylinder_piv_re413", "maximum_eligible_tier": 1, "tier_name": "SINGLE_FIELD_INSTANCE_ASSAY", "eligible": True, "population_generalization": False, "TLD_DERIVED_default": "BLOCKED", "basis": "one geometry-indexed acquisition; no repeated-acquisition inference"},
        {"candidate_id": "wind_farm_scanning_lidar_wakes", "maximum_eligible_tier": None, "tier_name": "NONCONFIRMATORY_PILOT_ONLY", "eligible": False, "population_generalization": False, "TLD_DERIVED_default": "BLOCKED", "basis": "outcome-exposed source role is permanently nonconfirmatory under Method V2 freeze"},
    ]
    for candidate_id, _, reason in legacy:
        eligibility.append({"candidate_id": candidate_id, "maximum_eligible_tier": 0, "tier_name": "SOURCE_CUSTODY_ONLY", "eligible": False, "population_generalization": False, "TLD_DERIVED_default": "BLOCKED", "basis": reason})

    score_dimensions = {
        "source_quality": 20,
        "geometry_quality": 20,
        "inferential_design": 30,
        "method_compatibility": 20,
        "compute_feasibility": 10,
    }
    score_values = {
        "actuated_fluidic_pinball_piv": ([20, 19, 27, 19, 9], []),
        "structured_light_patterns": ([20, 16, 9, 15, 7], []),
        "cylinder_array_piv": ([20, 20, 12, 18, 0], ["CURRENT_COMPUTE_FEASIBILITY_BOUND_EXCEEDED"]),
        "nbse2_4dstem_temperature_series": ([17, 19, 12, 17, 0], ["CURRENT_COMPUTE_FEASIBILITY_BOUND_EXCEEDED"]),
        "single_cylinder_piv_re413": ([20, 20, 6, 19, 8], []),
        "wind_farm_scanning_lidar_wakes": ([20, 19, 6, 19, 9], ["NONCONFIRMATORY_OUTCOME_EXPOSED_SOURCE"]),
        "rotating_quantum_wave_turbulence": ([18, 3, 0, 2, 10], ["RAW_GEOMETRY_DATA_UNAVAILABLE", "METHOD_INCOMPATIBLE"]),
        "second_sound_attenuation": ([18, 3, 0, 2, 10], ["RAW_GEOMETRY_DATA_UNAVAILABLE", "NO_INDEPENDENT_PARENT_MODEL"]),
        "mit_2024_direct_second_sound_imaging": ([3, 0, 0, 0, 0], ["RAW_NUMERIC_DATA_UNAVAILABLE", "LICENSE_UNRESOLVED"]),
        "atmospheric_turbulence_wavefront_tiff": ([8, 15, 0, 9, 0], ["NO_INDEPENDENT_PARENT_MODEL", "CURRENT_COMPUTE_FEASIBILITY_BOUND_EXCEEDED"]),
        "nanograv_15yr_pair_geometry": ([12, 18, 0, 18, 9], ["PRIOR_OUTCOME_EXPOSURE"]),
    }
    scores = []
    keys = list(score_dimensions)
    for candidate_id, (values, exclusions) in score_values.items():
        dimensions = dict(zip(keys, values, strict=True))
        scores.append(
            {
                "candidate_id": candidate_id,
                "dimensions": dimensions,
                "subtotal": sum(values),
                "automatic_exclusions": exclusions,
                "eligible": not exclusions,
                "unknown_counts_awarded_full_score": False,
            }
        )
    scores.sort(key=lambda row: (-int(row["eligible"]), -row["subtotal"], row["candidate_id"]))
    exclusion_rows = [
        {"candidate_id": row["candidate_id"], "exclusion": exclusion, "automatic": True}
        for row in scores
        for exclusion in row["automatic_exclusions"]
    ]
    receipt = {
        "schema_version": "2.0.0",
        "candidate_id": "actuated_fluidic_pinball_piv",
        "title": probes[0]["title"],
        "doi": probes[0]["doi"],
        "license": probes[0]["license"],
        "source_archive": probes[0]["files"][0],
        "selected_design_tier": 2,
        "selected_design_tier_name": "WITHIN_CAMPAIGN_REPEATED_ACQUISITION_ASSAY",
        "maximum_claim": "CALIBRATED_WITHIN_CAMPAIGN_ASSAY_WITHOUT_POPULATION_GENERALIZATION",
        "method_id": "METHOD_V2_C_EVIDENCE_VECTOR",
        "method_mode": "INSTRUMENTED_EVIDENCE_VECTOR",
        "method_freeze_commit": METHOD_FREEZE_COMMIT,
        "method_implementation_commit_after_nonconfirmatory_pilot_audit": METHOD_IMPLEMENTATION_COMMIT,
        "selection_basis": "highest eligible separated-dimension score with verified repeated-acquisition hierarchy",
        "selected_score": next(row["subtotal"] for row in scores if row["candidate_id"] == "actuated_fluidic_pinball_piv"),
        "raw_measurement_archive_accessed": False,
        "metadata_readme_and_zip_directory_bytes_only": True,
        "outcome_data_used_for_selection": False,
        "field_statistics_computed": False,
        "candidate_substitution_after_freeze_commit": "FORBIDDEN",
        "source_acquisition_authorized_only_after_freeze_commit": True,
        "TLD_DERIVED_default": "BLOCKED",
        "EXTERNALLY_VALIDATED": False,
        "selection_commit_subject": "Freeze structurally eligible geometry field candidate",
        "selection_commit": "RECORDED_IN_POST_PUSH_RECEIPT",
    }
    score_document = {
        "schema_version": "2.0.0",
        "checked_at": CHECKED_AT,
        "method_freeze_commit": METHOD_FREEZE_COMMIT,
        "outcome_data_used": False,
        "score_dimension_maxima": score_dimensions,
        "dimensions_separated": True,
        "unknown_counts_receive_full_score": False,
        "selection_order": [row["candidate_id"] for row in scores],
        "scores": scores,
        "selected_candidate_id": receipt["candidate_id"],
    }
    write_jsonl("candidate_structural_probe_registry.jsonl", probes)
    write_jsonl("candidate_hierarchy_registry.jsonl", hierarchies)
    write_jsonl("candidate_design_tier_eligibility.jsonl", eligibility)
    write_json("candidate_scores_v2.json", score_document)
    write_jsonl("candidate_exclusions_v2.jsonl", exclusion_rows)
    write_json("selected_candidate_receipt_v2.json", receipt)
    generated = sorted(path for path in OUT.iterdir() if path.is_file())
    digest = hashlib.sha256(b"".join(path.read_bytes() for path in generated)).hexdigest()
    print(
        json.dumps(
            {
                "selected_candidate": receipt["candidate_id"],
                "design_tier": receipt["selected_design_tier"],
                "candidate_count": len(probes),
                "eligible_count": sum(row["eligible"] for row in scores),
                "generated_digest": digest,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
