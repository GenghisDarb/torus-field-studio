# ruff: noqa: E501 -- frozen source titles and audit prose remain verbatim.
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "studies" / "v0.3.0-field-selection"
METHOD_FREEZE_COMMIT = "827b3394c0ce8ed414ca57d8e77ef1aaf1a72b1c"

DIMENSIONS = {
    "stable_source_and_byte_custody": 15,
    "clear_license_and_redistribution": 10,
    "geometry_indexed_raw_data": 15,
    "multiple_independent_parents_or_runs": 15,
    "natural_coordinates_and_units": 10,
    "geometry_aware_null_viability": 10,
    "domain_baseline_availability": 10,
    "faithful_multiple_projections": 5,
    "compute_feasibility": 5,
    "external_replication_feasibility": 5,
}


def dump_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def dump_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    lines = [json.dumps(value, sort_keys=True, separators=(",", ":")) for value in values]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


def source_file(name: str, size: int, md5: str) -> dict[str, Any]:
    return {"name": name, "size_bytes": size, "published_md5": md5}


def candidates() -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": "wind_farm_scanning_lidar_wakes",
            "title": "Wind Tunnel Experimental Dataset for Wind Farm Control with Scanning Lidar Wake Measurements",
            "category": "independently_discovered_stronger_candidate",
            "doi": "10.5281/zenodo.18731994",
            "stable_source": "https://zenodo.org/records/18731994",
            "metadata_api": "https://zenodo.org/api/records/18731994",
            "license": "CC-BY-4.0",
            "raw_data_status": "PUBLIC_NOT_ACCESSED_BEFORE_DATASET_FREEZE",
            "source_files": [
                source_file("Multiple Wake.zip", 607488674, "fe1ccca62ad418f682b0dfae4f97a515"),
                source_file("LICENSE.txt", 1033, "4b5dac56b6af4b437f77f2cd1757c6d8"),
                source_file("README.md", 4486, "78b1f3923739af43156b5eccc99cd391"),
                source_file("TestMatrix.xlsx", 14113, "e5a4ab27620b89e01f4a5eb953cbe026"),
            ],
            "geometry_metadata": {
                "raw_fields": ["R2D2/vLOS", "R2D3/vLOS", "ux", "uy"],
                "coordinates": ["x", "y", "z", "AvgPosition"],
                "physical_system": "three scaled wind turbines in a controlled wind tunnel",
                "source_format": "one NetCDF-4 file per experiment inside the archive",
            },
            "parent_metadata": "one DATA_test_X.nc acquisition is a prospective independent parent; independence must be verified after custody",
            "baseline_metadata": "the test matrix records inflow, yaw, power-demand, and wake-mixing conditions, permitting a frozen control baseline",
            "projection_metadata": "two measured lidar line-of-sight fields and source-provided reconstructed velocity components",
            "metadata_only_notes": [
                "README and record metadata were inspected; no NetCDF member or test-matrix value was accessed",
                "record archive name 'Multiple Wake.zip' differs from README text 'Single Wake.zip'; Phase O must fail closed if inventory cannot reconcile this documentation defect",
            ],
            "dimensions": {
                "stable_source_and_byte_custody": 15,
                "clear_license_and_redistribution": 10,
                "geometry_indexed_raw_data": 15,
                "multiple_independent_parents_or_runs": 15,
                "natural_coordinates_and_units": 8,
                "geometry_aware_null_viability": 10,
                "domain_baseline_availability": 10,
                "faithful_multiple_projections": 5,
                "compute_feasibility": 5,
                "external_replication_feasibility": 4,
            },
            "automatic_exclusions": [],
        },
        {
            "candidate_id": "structured_light_patterns",
            "title": "Structured Light Patterns",
            "category": "structured_light_raw_two_dimensional_images",
            "doi": "10.5281/zenodo.14002229",
            "stable_source": "https://zenodo.org/records/14002229",
            "license": "MIT",
            "raw_data_status": "PUBLIC_NOT_ACCESSED_BEFORE_DATASET_FREEZE",
            "source_files": [
                source_file("Data.tar.gz", 1913898327, "738288963abbeffaafe366a5d9c2850f")
            ],
            "geometry_metadata": {
                "raw_fields": ["intensity images", "photocount TIFF frames"],
                "coordinates": ["pixel row", "pixel column"],
                "known_state_metadata": ["density matrix", "superposition coefficients"],
            },
            "parent_metadata": "many prepared optical states with 2,000-frame photocount files for pure states",
            "baseline_metadata": "background and Gaussian calibration acquisitions are described",
            "projection_metadata": "image intensity, photocount distribution, and registered state metadata",
            "metadata_only_notes": ["archive was not downloaded or listed"],
            "dimensions": {
                "stable_source_and_byte_custody": 15,
                "clear_license_and_redistribution": 10,
                "geometry_indexed_raw_data": 15,
                "multiple_independent_parents_or_runs": 15,
                "natural_coordinates_and_units": 5,
                "geometry_aware_null_viability": 10,
                "domain_baseline_availability": 10,
                "faithful_multiple_projections": 5,
                "compute_feasibility": 4,
                "external_replication_feasibility": 5,
            },
            "automatic_exclusions": [],
        },
        {
            "candidate_id": "actuated_fluidic_pinball_piv",
            "title": "On the turbulent wake of the actuated fluidic pinball: dataset",
            "category": "experimental_two_dimensional_velocity_fields",
            "doi": "10.5281/zenodo.20794709",
            "stable_source": "https://zenodo.org/records/20794709",
            "license": "CC-BY-4.0",
            "raw_data_status": "PUBLIC_NOT_ACCESSED_BEFORE_DATASET_FREEZE",
            "source_files": [
                source_file("ExperimentalDataset.zip", 1333197134, "6629a8e110b1682b9361de37d8be4afb"),
                source_file("URANSDataset.zip", 226542913, "567f6c2602da4174df7e278e380c9012"),
                source_file("README.txt", 3692, "3327aa1fe31312da883bfc484dd8ede5"),
            ],
            "geometry_metadata": {
                "raw_fields": ["experimental multi-frame PIV velocity fields"],
                "conditions": "multiple symmetric actuation conditions",
                "uncertainty": "measurement uncertainties are included",
            },
            "parent_metadata": "one separately acquired actuation condition is a prospective parent; replicate structure is not explicit in landing metadata",
            "baseline_metadata": "unforced p=0 acquisition and force measurements are described by the associated open paper",
            "projection_metadata": "velocity components and geometry-preserving derived vorticity",
            "metadata_only_notes": ["experimental and numerical archives are separable"],
            "dimensions": {
                "stable_source_and_byte_custody": 15,
                "clear_license_and_redistribution": 10,
                "geometry_indexed_raw_data": 15,
                "multiple_independent_parents_or_runs": 11,
                "natural_coordinates_and_units": 8,
                "geometry_aware_null_viability": 10,
                "domain_baseline_availability": 10,
                "faithful_multiple_projections": 5,
                "compute_feasibility": 4,
                "external_replication_feasibility": 4,
            },
            "automatic_exclusions": [],
        },
        {
            "candidate_id": "cylinder_array_piv",
            "title": "Turbulent Flow Behind Cylinder Arrays",
            "category": "experimental_two_dimensional_velocity_fields",
            "doi": "10.5281/zenodo.16794036",
            "stable_source": "https://zenodo.org/records/16794036",
            "license": "CC-BY-4.0",
            "raw_data_status": "PUBLIC_NOT_ACCESSED_BEFORE_DATASET_FREEZE",
            "source_files": [
                source_file("CylinderArrays.mat", 12968316376, "41d1c99251043bfcfb46006989cb96d6")
            ],
            "geometry_metadata": {
                "raw_fields": ["u", "v"],
                "coordinates": ["x in mm", "y in mm"],
                "conditions": "nine H/D by V/D cylinder-array geometries",
            },
            "parent_metadata": "nine separately specified array configurations with 15 s PIV acquisitions at 200 Hz",
            "baseline_metadata": "published domain comparison across the nine configurations",
            "projection_metadata": "velocity vector, magnitude, and geometry-preserving vorticity",
            "metadata_only_notes": ["single 13.0 GB MATLAB object makes full reproduction costly"],
            "dimensions": {
                "stable_source_and_byte_custody": 15,
                "clear_license_and_redistribution": 10,
                "geometry_indexed_raw_data": 15,
                "multiple_independent_parents_or_runs": 15,
                "natural_coordinates_and_units": 10,
                "geometry_aware_null_viability": 10,
                "domain_baseline_availability": 8,
                "faithful_multiple_projections": 5,
                "compute_feasibility": 0,
                "external_replication_feasibility": 4,
            },
            "automatic_exclusions": [],
        },
        {
            "candidate_id": "nbse2_4dstem_temperature_series",
            "title": "Spatial correlations of charge density wave order across the transition in 2H-NbSe2",
            "category": "open_topological_field_dataset",
            "doi": "10.5281/zenodo.17823449",
            "stable_source": "https://zenodo.org/records/17823449",
            "license": "CC-BY-NC-SA-4.0",
            "raw_data_status": "PUBLIC_NOT_ACCESSED_BEFORE_DATASET_FREEZE",
            "source_files": [{"name": "14 published members", "size_bytes": 14342120945}],
            "geometry_metadata": {
                "raw_fields": ["4D-STEM diffraction field over real-space probe positions"],
                "conditions": "20, 25, 27, 29, 31, 33, 35, 37, 40, 45, and 300 K",
            },
            "parent_metadata": "eleven temperature acquisitions; exact scan independence requires materialization",
            "baseline_metadata": "300 K condition is a natural high-temperature baseline",
            "projection_metadata": "real-space diffraction-derived field and reciprocal-space intensity field",
            "metadata_only_notes": ["14.3 GB and MATLAB-oriented reproduction reduce feasibility"],
            "dimensions": {
                "stable_source_and_byte_custody": 15,
                "clear_license_and_redistribution": 10,
                "geometry_indexed_raw_data": 15,
                "multiple_independent_parents_or_runs": 15,
                "natural_coordinates_and_units": 6,
                "geometry_aware_null_viability": 10,
                "domain_baseline_availability": 10,
                "faithful_multiple_projections": 5,
                "compute_feasibility": 0,
                "external_replication_feasibility": 3,
            },
            "automatic_exclusions": [],
        },
        {
            "candidate_id": "single_cylinder_piv_re413",
            "title": "Particle image velocimetry data of flow past a cylinder",
            "category": "experimental_two_dimensional_velocity_fields",
            "doi": "10.5281/zenodo.20765567",
            "stable_source": "https://zenodo.org/records/20765567",
            "license": "CC-BY-4.0",
            "raw_data_status": "PUBLIC_NOT_ACCESSED_BEFORE_DATASET_FREEZE",
            "source_files": [
                source_file("cylinder_vel.mat", 1082404799, "4cc876439c48f7970afa477ea17d217a")
            ],
            "geometry_metadata": {
                "raw_fields": ["u in m/s", "v in m/s"],
                "coordinates": ["x in m", "y in m"],
                "mask_semantics": "exact zero denotes cylinder and laser-shadow masks",
            },
            "parent_metadata": "one documented time series from one acquisition",
            "baseline_metadata": "canonical cylinder-wake baseline",
            "projection_metadata": "velocity vector, magnitude, and geometry-preserving vorticity",
            "metadata_only_notes": ["a single acquisition cannot support the frozen independent-parent gate"],
            "dimensions": {
                "stable_source_and_byte_custody": 15,
                "clear_license_and_redistribution": 10,
                "geometry_indexed_raw_data": 15,
                "multiple_independent_parents_or_runs": 0,
                "natural_coordinates_and_units": 10,
                "geometry_aware_null_viability": 10,
                "domain_baseline_availability": 10,
                "faithful_multiple_projections": 5,
                "compute_feasibility": 4,
                "external_replication_feasibility": 4,
            },
            "automatic_exclusions": ["NO_INDEPENDENT_PARENT_MODEL"],
        },
        {
            "candidate_id": "rotating_quantum_wave_turbulence",
            "title": "Experimental data for Rotating quantum wave turbulence",
            "category": "rotating_quantum_wave_turbulence",
            "doi": "10.5281/zenodo.7525698",
            "stable_source": "https://zenodo.org/records/7525698",
            "license": "CC-BY-4.0",
            "raw_data_status": "PUBLIC_MINIMAL_FIGURE_SUPPORT_DATA_NOT_ACCESSED",
            "source_files": [{"name": "15 figure-specific members", "size_bytes": 1442854}],
            "geometry_metadata": {
                "raw_fields": "minimal CSV and Fig2c archive supporting publication figures",
                "coordinates": "no stable multidimensional spatial-coordinate contract in record metadata",
            },
            "parent_metadata": "spectrometer series exist but independent geometry-field parents are not documented",
            "baseline_metadata": "experiment-specific reference spectra",
            "projection_metadata": "publication-aligned spectrometer and figure tables",
            "metadata_only_notes": ["well-custodied data, but not a raw geometry-indexed field pack for the frozen method"],
            "dimensions": {
                "stable_source_and_byte_custody": 15,
                "clear_license_and_redistribution": 10,
                "geometry_indexed_raw_data": 2,
                "multiple_independent_parents_or_runs": 7,
                "natural_coordinates_and_units": 5,
                "geometry_aware_null_viability": 3,
                "domain_baseline_availability": 8,
                "faithful_multiple_projections": 1,
                "compute_feasibility": 5,
                "external_replication_feasibility": 3,
            },
            "automatic_exclusions": ["RAW_GEOMETRY_DATA_UNAVAILABLE", "METHOD_INCOMPATIBLE"],
        },
        {
            "candidate_id": "second_sound_attenuation",
            "title": "Data for Second sound attenuation near quantum criticality",
            "category": "second_sound_attenuation_data",
            "doi": "10.5281/zenodo.5767197",
            "stable_source": "https://zenodo.org/records/5767197",
            "license": "CC-BY-4.0",
            "raw_data_status": "PUBLIC_FIGURE_WORKBOOKS_NOT_ACCESSED",
            "source_files": [{"name": "13 figure-specific XLSX workbooks", "size_bytes": 5098491}],
            "geometry_metadata": {
                "raw_fields": "figure-support workbooks",
                "coordinates": "no frozen multidimensional field coordinates in landing metadata",
            },
            "parent_metadata": "independent raw acquisition parents are not documented",
            "baseline_metadata": "domain baselines exist in the publication but are figure aligned",
            "projection_metadata": "requires publication-specific workbook interpretation",
            "metadata_only_notes": ["not the exact MIT 2024 direct-imaging experiment"],
            "dimensions": {
                "stable_source_and_byte_custody": 15,
                "clear_license_and_redistribution": 10,
                "geometry_indexed_raw_data": 3,
                "multiple_independent_parents_or_runs": 0,
                "natural_coordinates_and_units": 5,
                "geometry_aware_null_viability": 2,
                "domain_baseline_availability": 7,
                "faithful_multiple_projections": 1,
                "compute_feasibility": 5,
                "external_replication_feasibility": 3,
            },
            "automatic_exclusions": [
                "RAW_GEOMETRY_DATA_UNAVAILABLE",
                "NO_INDEPENDENT_PARENT_MODEL",
                "METHOD_INCOMPATIBLE",
            ],
        },
        {
            "candidate_id": "mit_2024_direct_second_sound_imaging",
            "title": "Thermography of the superfluid transition in a strongly interacting Fermi gas",
            "category": "exact_mit_2024_direct_second_sound_imaging",
            "doi": "10.1126/science.adg3430",
            "stable_source": "https://doi.org/10.1126/science.adg3430",
            "license": "RAW_MEASUREMENT_LICENSE_NOT_FOUND",
            "raw_data_status": "NO_PUBLIC_RAW_NUMERIC_OR_IMAGE_ARCHIVE_FOUND",
            "source_files": [],
            "geometry_metadata": {"raw_fields": "publication figures only in discovered public sources"},
            "parent_metadata": "not publicly materializable",
            "baseline_metadata": "reported normal-fluid and superfluid comparisons",
            "projection_metadata": "would require figure extraction",
            "metadata_only_notes": ["MIT News images are not raw measurements and are CC-BY-NC-ND"],
            "dimensions": {
                "stable_source_and_byte_custody": 5,
                "clear_license_and_redistribution": 0,
                "geometry_indexed_raw_data": 0,
                "multiple_independent_parents_or_runs": 0,
                "natural_coordinates_and_units": 0,
                "geometry_aware_null_viability": 0,
                "domain_baseline_availability": 8,
                "faithful_multiple_projections": 0,
                "compute_feasibility": 0,
                "external_replication_feasibility": 0,
            },
            "automatic_exclusions": [
                "RAW_NUMERIC_DATA_UNAVAILABLE",
                "LICENSE_UNRESOLVED",
                "NO_INDEPENDENT_PARENT_MODEL",
                "NO_GEOMETRY_AWARE_NULL",
                "REQUIRES_OCR_OR_FIGURE_TRACING",
            ],
        },
        {
            "candidate_id": "atmospheric_turbulence_wavefront_tiff",
            "title": "Raw data for Direct Observation of Atmospheric Turbulence with a Video-rate Wide-field Wavefront Sensor",
            "category": "optical_field_image_data",
            "doi": "10.5281/zenodo.11063896",
            "stable_source": "https://zenodo.org/records/11063896",
            "license": "UNRESOLVED_IN_METADATA_AUDIT",
            "raw_data_status": "PUBLIC_NOT_ACCESSED_BEFORE_DATASET_FREEZE",
            "source_files": [{"name": "13 TIFF segments", "size_bytes": 49500000000}],
            "geometry_metadata": {"raw_fields": "wide-field TIFF sequence", "coordinates": "pixel index only in landing metadata"},
            "parent_metadata": "13 segments of one named acquisition, not 13 independent parents",
            "baseline_metadata": "hardware calibration requires repository-specific interpretation",
            "projection_metadata": "wavefront reconstruction requires external code",
            "metadata_only_notes": ["49.5 GB total and a single segmented acquisition"],
            "dimensions": {
                "stable_source_and_byte_custody": 15,
                "clear_license_and_redistribution": 0,
                "geometry_indexed_raw_data": 15,
                "multiple_independent_parents_or_runs": 0,
                "natural_coordinates_and_units": 3,
                "geometry_aware_null_viability": 8,
                "domain_baseline_availability": 4,
                "faithful_multiple_projections": 4,
                "compute_feasibility": 0,
                "external_replication_feasibility": 1,
            },
            "automatic_exclusions": ["LICENSE_UNRESOLVED", "NO_INDEPENDENT_PARENT_MODEL"],
        },
        {
            "candidate_id": "nanograv_15yr_pair_geometry",
            "title": "NANOGrav 15-Year Data Set pair/correlation geometry",
            "category": "PRIOR_EXPOSED_DIAGNOSTIC_CANDIDATE",
            "doi": "10.5281/zenodo.7967584",
            "stable_source": "https://nanograv.org/15yr-data-release",
            "license": "PUBLIC_RELEASE_TERMS_VARY_BY_ARTIFACT",
            "raw_data_status": "PRIOR_EXPOSED_DIAGNOSTIC_ONLY",
            "source_files": [],
            "geometry_metadata": {"raw_fields": "pulsar pair/correlation geometry"},
            "parent_metadata": "pulsars and pair structure",
            "baseline_metadata": "noise and overlap-reduction baselines",
            "projection_metadata": "pair, sky, and correlation representations",
            "metadata_only_notes": ["local NANOGrav GEO01-GEO10 artifacts predate v0.3.0"],
            "dimensions": {
                "stable_source_and_byte_custody": 15,
                "clear_license_and_redistribution": 5,
                "geometry_indexed_raw_data": 15,
                "multiple_independent_parents_or_runs": 15,
                "natural_coordinates_and_units": 10,
                "geometry_aware_null_viability": 10,
                "domain_baseline_availability": 10,
                "faithful_multiple_projections": 5,
                "compute_feasibility": 4,
                "external_replication_feasibility": 4,
            },
            "automatic_exclusions": ["PRIOR_OUTCOME_EXPOSURE"],
        },
    ]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = candidates()
    for row in rows:
        unknown = set(row["dimensions"]) - set(DIMENSIONS)
        if unknown:
            raise SystemExit(f"Unknown scoring dimensions for {row['candidate_id']}: {unknown}")
        for dimension, maximum in DIMENSIONS.items():
            value = row["dimensions"][dimension]
            if not 0 <= value <= maximum:
                raise SystemExit(f"Out-of-range score {row['candidate_id']} {dimension}={value}")
        row["subtotal"] = sum(row["dimensions"].values())
        row["automatic_penalty"] = -100 * len(row["automatic_exclusions"])
        row["total"] = row["subtotal"] + row["automatic_penalty"]
        row["eligible"] = not row["automatic_exclusions"]

    ranked = sorted(
        rows,
        key=lambda row: (
            row["eligible"],
            row["total"],
            row["dimensions"]["multiple_independent_parents_or_runs"],
            row["dimensions"]["stable_source_and_byte_custody"],
            row["dimensions"]["geometry_aware_null_viability"],
            row["dimensions"]["domain_baseline_availability"],
            row["dimensions"]["compute_feasibility"],
        ),
        reverse=True,
    )
    eligible = [row for row in ranked if row["eligible"]]
    if not eligible:
        raise SystemExit("No eligible outcome-blind field candidate")
    selected = eligible[0]
    if selected["candidate_id"] != "wind_farm_scanning_lidar_wakes":
        raise SystemExit(f"Unexpected selected candidate: {selected['candidate_id']}")

    registry_rows = []
    for row in rows:
        registry_rows.append({key: value for key, value in row.items() if key not in {"dimensions", "subtotal", "automatic_penalty", "total", "eligible"}})
    dump_jsonl(OUT / "candidate_metadata_registry.jsonl", registry_rows)
    dump_json(
        OUT / "candidate_scores.json",
        {
            "schema_version": "1.0.0",
            "method_freeze_commit": METHOD_FREEZE_COMMIT,
            "outcome_data_used": False,
            "dimension_maxima": DIMENSIONS,
            "automatic_penalty_per_exclusion": -100,
            "tie_break_order": [
                "multiple_independent_parents_or_runs",
                "stable_source_and_byte_custody",
                "geometry_aware_null_viability",
                "domain_baseline_availability",
                "simpler_full_reproduction",
                "lower_compute",
            ],
            "scores": [
                {
                    "candidate_id": row["candidate_id"],
                    "dimensions": row["dimensions"],
                    "subtotal": row["subtotal"],
                    "automatic_exclusions": row["automatic_exclusions"],
                    "automatic_penalty": row["automatic_penalty"],
                    "total": row["total"],
                    "eligible": row["eligible"],
                    "eligible_rank": eligible.index(row) + 1 if row in eligible else None,
                }
                for row in ranked
            ],
            "selected_candidate_id": selected["candidate_id"],
        },
    )
    dump_jsonl(
        OUT / "candidate_exclusions.jsonl",
        [
            {
                "candidate_id": row["candidate_id"],
                "excluded": True,
                "issue_codes": row["automatic_exclusions"],
                "automatic_penalty": row["automatic_penalty"],
                "reason": row["metadata_only_notes"],
            }
            for row in rows
            if row["automatic_exclusions"]
        ],
    )
    dump_json(
        OUT / "prior_exposure_audit.json",
        {
            "schema_version": "1.0.0",
            "audit_scope": [
                "repository working tree",
                "repository git history",
                "provided Codex text attachments",
                "v0.2.1 held-out selection artifacts",
            ],
            "search_mode": "exact DOI, record ID, and title fragments; no candidate raw data",
            "selected_candidate": {
                "candidate_id": selected["candidate_id"],
                "exact_source_found_in_prior_program": False,
                "prior_outcome_exposure": False,
                "eligible_as_fresh_heldout": True,
            },
            "known_prior_exposure": [
                {
                    "candidate_id": "nanograv_15yr_pair_geometry",
                    "prior_outcome_exposure": True,
                    "evidence": "studies/heldout-v0.2.1 contains NANOGrav GEO01-GEO10 and registered assay references",
                    "classification": "PRIOR_EXPOSED_DIAGNOSTIC_CANDIDATE",
                }
            ],
            "other_exact_candidate_sources_found_in_prior_program": [],
            "generic_domain_discussion_is_not_counted_as_exact_outcome_exposure": True,
        },
    )
    dump_json(
        OUT / "selected_candidate_receipt.json",
        {
            "schema_version": "1.0.0",
            "selection_state": "IRREVOCABLY_SELECTED_PENDING_FREEZE_COMMIT",
            "candidate_id": selected["candidate_id"],
            "title": selected["title"],
            "doi": selected["doi"],
            "license": selected["license"],
            "outcome_data_used_for_selection": False,
            "raw_measurement_archive_accessed": False,
            "metadata_documents_accessed": [
                "Zenodo record metadata",
                "README.md (documentation only; published MD5 78b1f3923739af43156b5eccc99cd391)",
            ],
            "selected_score": selected["subtotal"],
            "runner_up": {"candidate_id": eligible[1]["candidate_id"], "score": eligible[1]["subtotal"]},
            "selection_rule": "highest eligible prespecified metadata-only score; tie-breakers not required",
            "method_freeze_commit": METHOD_FREEZE_COMMIT,
            "selected_method": "METHOD_C_EVIDENCE_VECTOR_NONBINARY",
            "candidate_substitution_after_dataset_freeze": "FORBIDDEN",
            "materialization_failure_outcome": "V030_GEOMETRY_FIELD_ASSAY_EXECUTION_BLOCKED",
            "documentation_risk": "archive-name mismatch between the deposited file and README must be reconciled by byte inventory or fail closed",
        },
    )
    dump_json(
        OUT / "selected_candidate_source_plan.json",
        {
            "schema_version": "1.0.0",
            "candidate_id": selected["candidate_id"],
            "doi": selected["doi"],
            "record_url": selected["stable_source"],
            "metadata_api": selected["metadata_api"],
            "license": selected["license"],
            "acquisition_authorized_only_after_dataset_freeze_push": True,
            "required_files": selected["source_files"],
            "primary_measurement_archive": "Multiple Wake.zip",
            "acquisition_order": ["LICENSE.txt", "README.md", "TestMatrix.xlsx", "Multiple Wake.zip"],
            "custody_checks": [
                "HTTPS source identity and DOI resolve",
                "exact published byte size",
                "exact published MD5",
                "locally computed SHA-256",
                "safe archive paths with no absolute paths, traversal, links, or duplicate names",
                "complete member inventory before NetCDF access",
                "one DATA_test_X.nc member per declared experiment",
                "NetCDF structural and coordinate integrity",
                "test-matrix to NetCDF one-to-one reconciliation",
            ],
            "raw_value_firewall": "do not open any NetCDF variable or TestMatrix cell until the dataset-freeze commit is pushed",
            "failure_policy": "record failure and return V030_GEOMETRY_FIELD_ASSAY_EXECUTION_BLOCKED; never substitute another candidate",
        },
    )


if __name__ == "__main__":
    main()
