from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
DOWNLOADS = HOME / "Downloads"
OUT = ROOT / "studies" / "v0.3.0-method-freeze"
SOURCE_BUNDLE = (
    DOWNLOADS
    / "ControllerGate_TLD_1-44_Historical_Architecture_Recovery_Source_Bundle_2026-07-17.zip"
)
CONTROLLERGATE = ROOT / "external_cache" / "controllergate-research-readonly-38897b7"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )


def source(
    source_id: str,
    title: str,
    location: str,
    authority_level: str,
    authority_scope: str,
    digest: str,
    *,
    bytes_count: int | None = None,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "title": title,
        "location": location,
        "authority_level": authority_level,
        "authority_scope": authority_scope,
        "sha256": digest,
        "bytes": bytes_count,
        "limitations": limitations or [],
    }


def adjudication(
    statement_id: str,
    statement: str,
    classification: str,
    authority: list[str],
    finding: str,
    executable_disposition: str,
) -> dict[str, Any]:
    return {
        "statement_id": statement_id,
        "statement": statement,
        "classification": classification,
        "authority_source_ids": authority,
        "finding": finding,
        "executable_disposition": executable_disposition,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = (
        HOME / ".codex" / "attachments" / "6205e578-2a07-4583-b860-163863e7696d" / "pasted-text.txt"
    )
    added_advice = (
        HOME / ".codex" / "attachments" / "e8ef4787-f598-41b9-9063-150fe274c64c" / "pasted-text.txt"
    )
    family_audit = DOWNLOADS / "TORUS Program Family Audit and Lexicon.docx"
    brot_plan = (
        DOWNLOADS
        / "TB_03_TB_04_TORUS_Brot_ToT_BROT_plan_summary_with_TB_01_TB_02_Unified_breakdown.txt"
    )
    brot_notebooks = DOWNLOADS / "TORUS_BROT_-_ToT_BROT notebooks.txt"
    brot_rules = DOWNLOADS / "TORUS-Brot and ToT-Brot development rules and tips.txt"
    chat_part1 = next(DOWNLOADS.glob("*advanced_development_chat_archive_part_1.txt"))
    tld_i_source = ROOT / "external_cache" / "zenodo" / "18080090" / "TORUS_Zenodo_v1.zip"
    release_manifest = (
        ROOT
        / "results"
        / "v0.3.0"
        / "preflight"
        / "fresh-v022-release-20260819"
        / "release-manifest-v0.2.2.json"
    )
    v021_adjudication = (
        ROOT
        / "results"
        / "v0.3.0"
        / "preflight"
        / "v021-replay-20260819"
        / "adjudication"
        / "scientific_adjudication.json"
    )
    claim_envelope = CONTROLLERGATE / "docs" / "CLAIM_ENVELOPE.md"
    batch103_contract = CONTROLLERGATE / "configs" / "batch103_prompt_contract.json"
    closure_mode = CONTROLLERGATE / "controllergate" / "topology" / "tld_closure_mode.py"
    clean_track = CONTROLLERGATE / "controllergate" / "topology" / "tld_clean_track.py"

    expected_file_hashes = {
        protocol: "31956fffc82711c555de6249396ba681fe1369cf72ef224dc593be6b68669b99",
        added_advice: "1e01588384729d921145a3694fc08f2fc579983e78ac04798c7e30f8df17843c",
        SOURCE_BUNDLE: "c32609066a7d86934a9a6e8b62d57fd335e51a14c8fdebcb95bb7d1584c6438b",
        family_audit: "b790e3f0fb8865c681af9516f7590f6e77af0f6cc94c1d058fa733a4ea0a81a7",
        brot_plan: "54d08ae75d6ed66c45ae9f32ffb220d24ad41c836ced8f15674736e6466231c7",
        brot_notebooks: "eb71b670a68b9518f14e08084d443033c85fc589161c1603d549f41481fc64ab",
        brot_rules: "4af64343cd55301206f13477d5a9af023e961a6ff0c3a0d324441629d7f5da25",
        chat_part1: "9f2c98c549dfc22c72ae0e76d48ff194cb7fa8f227ea20b49fe5717e75a838e8",
        tld_i_source: "5bae9af506bd65e74225fc91f869931d70fcd89505cbc672b3538abdfd4b446e",
        release_manifest: "1cb0b9508a2cc560a88d5a78e559b56e157dd12656bf9a8ba073a6f099ce812d",
        claim_envelope: "404d24a4a345bb7a1017212878369ae1106e81b07bec9180a2976f3e48d571df",
        batch103_contract: "e14935e749014d38bfaf9a372c81f78aa371dbf40f874bce26d180248e7e9524",
        closure_mode: "098869b255b5c21e86447b77ab13867a579056a9489e5e8111467f8af0d0d65b",
        clean_track: "e8c5d932cb3e1e1ed2a8e023655a5ad5fc4b49129e42e14e343d6d83ade0f353",
    }
    observed_file_hashes = {path: sha256(path) for path in expected_file_hashes}
    mismatches = [
        str(path)
        for path, expected in expected_file_hashes.items()
        if observed_file_hashes[path] != expected
    ]
    if mismatches:
        raise SystemExit(f"Source-custody mismatch: {mismatches}")

    wanted_members = {
        "formal_lexicon": "sources/Formal Lexicon of TORUS Ladder Dynamics.txt",
        "errata_map": "sources/Mislabeling & Notation History (Errata Map).txt",
        "technical_standards_v21": (
            "sources/Technical Standards and Input Protocol for TORUS Ladder Dynamics "
            "Notebooks v2.1.docx"
        ),
        "tld_history_1_11": (
            "sources/Detailed Breakdown of Notebooks 1�11 "
            "(Pre-Torus Ladder Dynamics I notebooks).txt"
        ),
        "tld_history_12_14": (
            "sources/Detailed Breakdown of Notebooks 12-14 "
            "(Pre- and Torus Ladder Dynamics I notebooks)(1).txt"
        ),
        "outside_study_ledger": (
            "sources/ControllerGate Development Chats 3-5 plus Outside Study Assessments(3).txt"
        ),
    }
    expected_member_hashes = {
        "formal_lexicon": "0647bf37cb735cf70e9dffd449624435ba13ec46b1253fd9763820394d80e5b8",
        "errata_map": "258ebb5ee662ef3defbde4e42e1e5452c6b72fa4514f1c8a9dbaa7bbe1c1bbb3",
        "technical_standards_v21": "0b525a3da659cda048fac4a8e062252872ca7ac97c46620345aea6bbf9d03a29",
        "tld_history_1_11": "c657e4da46f628cfe1353f1e3b4107dc9bbe93aba62ddb390df939e9da51e5ec",
        "tld_history_12_14": "25000196642117477739922cbeaf69e7b823b1bd3a0c84916084fe6578c0d4d2",
    }
    member_hashes: dict[str, str] = {}
    member_sizes: dict[str, int] = {}
    with zipfile.ZipFile(SOURCE_BUNDLE) as archive:
        names = archive.namelist()
        for source_id, wanted in wanted_members.items():
            if wanted not in names:
                if source_id == "tld_history_1_11":
                    matches = [
                        name
                        for name in names
                        if name.startswith("sources/Detailed Breakdown of Notebooks 1")
                        and "11" in name
                    ]
                else:
                    matches = [name for name in names if Path(name).name == Path(wanted).name]
                if len(matches) != 1:
                    raise SystemExit(f"Cannot resolve source-bundle member {source_id}: {matches}")
                wanted_members[source_id] = matches[0]
            data = archive.read(wanted_members[source_id])
            member_hashes[source_id] = sha256_bytes(data)
            member_sizes[source_id] = len(data)
    for source_id, expected in expected_member_hashes.items():
        if member_hashes[source_id] != expected:
            raise SystemExit(f"Source-bundle member mismatch: {source_id}")

    sources = [
        source(
            "v030_protocol",
            "TFS v0.3.0 geometry-indexed TLD milestone protocol",
            "<ATTACHMENT>/6205e578.../pasted-text.txt",
            "E",
            "task governance, gates, deliverables, and claim vocabulary",
            observed_file_hashes[protocol],
            bytes_count=protocol.stat().st_size,
            limitations=["user-supplied protocol; not evidence of a scientific outcome"],
        ),
        source(
            "added_outside_advice",
            "Additional outside advice supplied during v0.3.0",
            "<ATTACHMENT>/e8ef4787.../pasted-text.txt",
            "E",
            "candidate design advice requiring line-by-line adjudication",
            observed_file_hashes[added_advice],
            bytes_count=added_advice.stat().st_size,
            limitations=[
                "not authoritative; contains unsupported exact physical and historical claims"
            ],
        ),
        source(
            "tld_source_bundle",
            "ControllerGate TLD 1-44 historical architecture recovery source bundle",
            "<LOCAL_DOWNLOADS>/ControllerGate_TLD_1-44_Historical_Architecture_Recovery_Source_Bundle_2026-07-17.zip",
            "A",
            "immutable custody container for embedded levels B-D sources",
            observed_file_hashes[SOURCE_BUNDLE],
            bytes_count=SOURCE_BUNDLE.stat().st_size,
        ),
        source(
            "formal_lexicon",
            "Formal Lexicon of TORUS Ladder Dynamics",
            f"<TLD_SOURCE_BUNDLE>::{wanted_members['formal_lexicon']}",
            "B",
            "T_e, S_e, winner_N, TORUS-BROT, and claim semantics",
            member_hashes["formal_lexicon"],
            bytes_count=member_sizes["formal_lexicon"],
        ),
        source(
            "errata_map",
            "Mislabeling & Notation History / Errata Map",
            f"<TLD_SOURCE_BUNDLE>::{wanted_members['errata_map']}",
            "B",
            "legacy-to-current terminology corrections",
            member_hashes["errata_map"],
            bytes_count=member_sizes["errata_map"],
        ),
        source(
            "technical_standards_v21",
            "Technical Standards & Input Protocol for TLD v2.1",
            f"<TLD_SOURCE_BUNDLE>::{wanted_members['technical_standards_v21']}",
            "B",
            "historical one-dimensional method governance",
            member_hashes["technical_standards_v21"],
            bytes_count=member_sizes["technical_standards_v21"],
            limitations=["v2.1 does not directly standardize spatial grids or general fields"],
        ),
        source(
            "tld_history_1_11",
            "Detailed Breakdown of Notebooks 1-11",
            f"<TLD_SOURCE_BUNDLE>::{wanted_members['tld_history_1_11']}",
            "C",
            "operator lineage and prior-exposure audit",
            member_hashes["tld_history_1_11"],
            bytes_count=member_sizes["tld_history_1_11"],
        ),
        source(
            "tld_history_12_14",
            "Detailed Breakdown of Notebooks 12-14",
            f"<TLD_SOURCE_BUNDLE>::{wanted_members['tld_history_12_14']}",
            "C",
            "TLD I operator and execution lineage",
            member_hashes["tld_history_12_14"],
            bytes_count=member_sizes["tld_history_12_14"],
        ),
        source(
            "outside_study_ledger",
            "ControllerGate development chats and outside-study assessments",
            f"<TLD_SOURCE_BUNDLE>::{wanted_members['outside_study_ledger']}",
            "D",
            "historical proposal and critique context only",
            member_hashes["outside_study_ledger"],
            bytes_count=member_sizes["outside_study_ledger"],
            limitations=["development record; statements require executable corroboration"],
        ),
        source(
            "tld_i_public_release",
            "TLD I Zenodo source release",
            "<REPOSITORY_IGNORED>/external_cache/zenodo/18080090/TORUS_Zenodo_v1.zip",
            "A",
            "published executable TLD I inputs and notebooks",
            observed_file_hashes[tld_i_source],
            bytes_count=tld_i_source.stat().st_size,
        ),
        source(
            "tfs_v022_release",
            "TORUS Field Studio v0.2.2 release manifest",
            "<REPOSITORY_IGNORED>/results/v0.3.0/preflight/fresh-v022-release-20260819/release-manifest-v0.2.2.json",
            "A",
            "v0.2.2 immutable release boundary",
            observed_file_hashes[release_manifest],
            bytes_count=release_manifest.stat().st_size,
        ),
        source(
            "v021_exact_replay",
            "Fresh v0.2.1 held-out replay scientific adjudication",
            "<REPOSITORY_IGNORED>/results/v0.3.0/preflight/v021-replay-20260819/adjudication/scientific_adjudication.json",
            "C",
            "exact replay outcome and endpoint boundary",
            sha256(v021_adjudication),
            bytes_count=v021_adjudication.stat().st_size,
        ),
        source(
            "controllergate_claim_envelope",
            "ControllerGate current claim envelope at Batch103 HEAD",
            "<CONTROLLERGATE_READ_ONLY>/docs/CLAIM_ENVELOPE.md",
            "A",
            "current product, AMDS, memory, scoring, and self-maintenance boundaries",
            observed_file_hashes[claim_envelope],
            bytes_count=claim_envelope.stat().st_size,
        ),
        source(
            "batch103_contract",
            "ControllerGate Batch103 prompt contract",
            "<CONTROLLERGATE_READ_ONLY>/configs/batch103_prompt_contract.json",
            "A",
            "Batch103 exact source and release custody",
            observed_file_hashes[batch103_contract],
            bytes_count=batch103_contract.stat().st_size,
        ),
        source(
            "controllergate_closure_mode",
            "ControllerGate TLD closure-mode implementation",
            "<CONTROLLERGATE_READ_ONLY>/controllergate/topology/tld_closure_mode.py",
            "C",
            "current noncanonical elbow proposal status",
            observed_file_hashes[closure_mode],
            bytes_count=closure_mode.stat().st_size,
        ),
        source(
            "controllergate_clean_track",
            "ControllerGate TLD clean-track implementation",
            "<CONTROLLERGATE_READ_ONLY>/controllergate/topology/tld_clean_track.py",
            "C",
            "winner_N_elbow historical recovery status",
            observed_file_hashes[clean_track],
            bytes_count=clean_track.stat().st_size,
        ),
        source(
            "program_family_audit",
            "TORUS Program Family Audit and Lexicon",
            "<LOCAL_DOWNLOADS>/TORUS Program Family Audit and Lexicon.docx",
            "E",
            "outside synthesis of TORUS program vocabulary and boundaries",
            observed_file_hashes[family_audit],
            bytes_count=family_audit.stat().st_size,
            limitations=["outside audit; not the canonical formal lexicon"],
        ),
        source(
            "brot_plan_summary",
            "TORUS-BROT / ToT-BROT plan summary",
            "<LOCAL_DOWNLOADS>/TB_03_TB_04_TORUS_Brot_ToT_BROT_plan_summary_with_TB_01_TB_02_Unified_breakdown.txt",
            "D",
            "development definitions and lineage",
            observed_file_hashes[brot_plan],
            bytes_count=brot_plan.stat().st_size,
        ),
        source(
            "brot_notebook_notes",
            "TORUS-BROT / ToT-BROT notebook notes",
            "<LOCAL_DOWNLOADS>/TORUS_BROT_-_ToT_BROT notebooks.txt",
            "D",
            "development notebook notes",
            observed_file_hashes[brot_notebooks],
            bytes_count=brot_notebooks.stat().st_size,
        ),
        source(
            "brot_development_rules",
            "TORUS-BROT and ToT-BROT development rules and tips",
            "<LOCAL_DOWNLOADS>/TORUS-Brot and ToT-Brot development rules and tips.txt",
            "D",
            "development heuristics requiring higher-authority corroboration",
            observed_file_hashes[brot_rules],
            bytes_count=brot_rules.stat().st_size,
        ),
        source(
            "advanced_chat_part1",
            "TORUS-BROT / ToT-BROT advanced development chat archive part 1",
            "<LOCAL_DOWNLOADS>/...advanced_development_chat_archive_part_1.txt",
            "D",
            "pilot telemetry and design history",
            observed_file_hashes[chat_part1],
            bytes_count=chat_part1.stat().st_size,
            limitations=["pilot-specific observations are not universal method constants"],
        ),
        source(
            "v030_codex_inference",
            "v0.3.0 implementation inferences",
            "<REPOSITORY>/implementation and calibration artifacts",
            "F",
            "new candidate methods, synthetic fixtures, and calibration conclusions",
            "NOT_APPLICABLE_UNTIL_ARTIFACT_FREEZE",
            limitations=["cannot override Levels A-C; must be tested before freeze"],
        ),
    ]
    write_jsonl(OUT / "source_authority_registry.jsonl", sources)

    audit = [
        adjudication(
            "four_lane_separation",
            "Four-lane separation is a valid governance architecture.",
            "SUPPORTED_WITH_SCOPE_CORRECTION",
            ["v030_protocol", "controllergate_claim_envelope"],
            "Separate custody, metrology, adjudication, and action authority; the labels are a new governance design, not a recovered law.",
            "Implement as an authority firewall and never treat lane agreement as physical validation.",
        ),
        adjudication(
            "torus_brot_navigation",
            "TORUS-BROT is navigation or visualization rather than physical evidence by itself.",
            "SUPPORTED",
            ["formal_lexicon", "brot_plan_summary", "v030_protocol"],
            "The constructed analytic family may aid navigation and sensitivity visualization but cannot establish a physical 14-fold law.",
            "Exclude TORUS-BROT presets from confirmatory evidence channels.",
        ),
        adjudication(
            "torus_tot_brot_distinction",
            "TORUS-BROT and ToT-BROT are distinct.",
            "SUPPORTED",
            ["formal_lexicon", "brot_plan_summary", "brot_notebook_notes"],
            "ToT-BROT requires explicit coupled-system or inter-projection invariants; multiple views of one field are insufficient.",
            "Do not label a geometry pack ToT-BROT without registered coupled invariants and null tests.",
        ),
        adjudication(
            "geometry_indexed_domain_packs",
            "Geometry-indexed domain packs are already part of canonical TLD v2.1.",
            "CONTRADICTED",
            ["technical_standards_v21", "v030_protocol"],
            "v2.1 is one-dimensional; geometry-indexed packs are a new v3 extension with a documented migration boundary.",
            "Create a new versioned standard and preserve v2.1 unchanged.",
        ),
        adjudication(
            "absolute_1e9_current_failure",
            "A claim-bearing absolute 1e-9 curvature threshold is currently active in TFS.",
            "NOT_FOUND",
            ["tfs_v022_release", "v030_codex_inference"],
            "The repository audit found 1e-9 only as numerical denominator/variance floors, not a claim-bearing curvature prominence gate.",
            "Do not import 1e-9; retain a mutation that rejects any future claim-bearing absolute threshold.",
        ),
        adjudication(
            "scale_relative_prominence",
            "Scale-relative or null-standardized curvature is preferable to an uncalibrated absolute prominence.",
            "REQUIRES_PROSPECTIVE_TEST",
            ["controllergate_closure_mode", "controllergate_clean_track", "v030_protocol"],
            "The current ControllerGate elbow is explicitly noncanonical and the historical formula was not recovered.",
            "Calibrate a small candidate family on synthetic and historical controls before any freeze.",
        ),
        adjudication(
            "shot_noise_floor",
            "Shot-noise or variance-floor analysis is required for every observable.",
            "SUPPORTED_WITH_SCOPE_CORRECTION",
            ["v030_protocol", "added_outside_advice"],
            "Variance-floor analysis is relevant to noisy numeric observables, not deterministic semantic assertions.",
            "Route only NOISY_NUMERIC measurements through registered variance-floor analysis.",
        ),
        adjudication(
            "dev_urandom_whitening",
            "A 50 MB /dev/urandom run established a negative result and exposed whitening concerns.",
            "PLAUSIBLE_UNVERIFIED",
            ["outside_study_ledger", "v030_protocol"],
            "Historical discussion supports the claim, but no raw bytes, executable code, and verified result artifact were admitted into this audit.",
            "Keep out of method calibration and claim-bearing baselines.",
        ),
        adjudication(
            "cpu_jitter_200mb_positive",
            "A positive 200 MB CPU-jitter 1/14 result was completed and verified.",
            "NOT_FOUND",
            ["outside_study_ledger", "v030_protocol", "added_outside_advice"],
            "Only a proposed retry was located; no exact raw dataset, code, hashes, or verified result artifact was found.",
            "Prohibit the claim until a complete custody chain and independent verification exist.",
        ),
        adjudication(
            "cpu_jitter_10mb_1069",
            "A 10 MB entropy_drift_pure.py run verified normalized autocorrelation rho(lag 18)=106.9%.",
            "NOT_FOUND",
            ["added_outside_advice", "outside_study_ledger"],
            "No source file, raw data, hash, executable result, normalization definition, or independent verification was found.",
            "Exclude from all contracts and publications.",
        ),
        adjudication(
            "ensemble_averaged_probes",
            "All probes should be ensemble averaged.",
            "CONTRADICTED",
            ["v030_protocol", "added_outside_advice"],
            "Repeated randomized probes are conditional on noise, flakiness, stochastic behavior, timing, resources, or a registered perturbation family.",
            "Use clean replay plus duplicate clean replay for deterministic semantic assertions.",
        ),
        adjudication(
            "n6_boundary_attraction",
            "N=6 boundary attraction is a universal structural finding.",
            "SUPPORTED_WITH_SCOPE_CORRECTION",
            ["advanced_chat_part1", "added_outside_advice"],
            "A pilot record reports nine-way minimum ties for 74% of evaluated ladders, which can pin naive argmin to N=6; this is pilot-specific degeneracy evidence.",
            "Detect flat/tied traces and report boundary rate; do not treat N=6 as a structural scale.",
        ),
        adjudication(
            "every_n6_orbit_two",
            "Every N=6 winner has orbit length exactly two.",
            "PLAUSIBLE_UNVERIFIED",
            ["advanced_chat_part1", "added_outside_advice"],
            "Short orbits are discussed, but an exact universal orbit-length distribution was not recovered.",
            "Measure orbit length in Scout; do not hardcode two.",
        ),
        adjudication(
            "orbit_length_scout",
            "Orbit length is a useful pre-closure eligibility diagnostic.",
            "SUPPORTED_WITH_SCOPE_CORRECTION",
            ["advanced_chat_part1", "v030_protocol"],
            "Orbit length can diagnose degeneracy but has no historically validated universal cutoff.",
            "Report it and calibrate any threshold on synthetic/historical controls.",
        ),
        adjudication(
            "eligibility_before_closure",
            "Eligibility must be established before closure or emergence is computed.",
            "SUPPORTED",
            ["technical_standards_v21", "v030_protocol"],
            "Unmaterialized, degenerate, ambiguous, under-supported, or null-incomplete fields cannot support closure claims.",
            "Make GeometryScoutV1 a hard upstream gate.",
        ),
        adjudication(
            "structured_fragility_repair_validation",
            "Structured fragility can directly validate or authorize a ControllerGate repair.",
            "CONTRADICTED",
            ["controllergate_claim_envelope", "added_outside_advice", "v030_protocol"],
            "Structured fragility may support metrology, but topology/metrology has no source ownership, patch, count, or terminal authority.",
            "Export shadow evidence only; preserve the ControllerGate authority firewall.",
        ),
        adjudication(
            "materialization_2143",
            "21.43 percent materialization is a universal pass threshold or bottleneck constant.",
            "NOT_FOUND",
            ["outside_study_ledger", "controllergate_claim_envelope", "v030_protocol"],
            "No calibrated universal threshold was found; materialization is domain- and cohort-specific.",
            "Do not encode 21.43%; report actual eligible support and calibrated requirements.",
        ),
        adjudication(
            "static_amds_confidence",
            "Static AMDS confidence thresholds are established for geometry-TLD evidence.",
            "NOT_FOUND",
            ["controllergate_claim_envelope", "batch103_contract", "added_outside_advice"],
            "AMDS prospective effectiveness is NOT_ESTABLISHED and no cross-domain geometry-TLD confidence calibration was found.",
            "No AMDS threshold may enter the TFS method or ControllerGate transfer as validated.",
        ),
        adjudication(
            "single_run_timing_attribution",
            "A single timing or resource run can establish causal attribution.",
            "CONTRADICTED",
            ["v030_protocol", "added_outside_advice", "controllergate_claim_envelope"],
            "Timing is telemetry requiring randomized repeated measurement and still cannot establish source ownership by itself.",
            "Keep timing non-authoritative and require causal evidence through the owning domain contract.",
        ),
        adjudication(
            "destruction_slogan",
            "Real structure survives its own destruction.",
            "NON_EXECUTABLE_METAPHOR",
            ["program_family_audit", "v030_protocol", "added_outside_advice"],
            "Arbitrary destruction can remove valid structure; support requires matched nulls, registered fragility, meaningful perturbations, faithful representations, and baseline exclusion.",
            "Use the executable five-part support rule, never the slogan.",
        ),
        adjudication(
            "winner_n_elbow",
            "winner_N_elbow is a recovered canonical historical formula.",
            "CONTRADICTED",
            ["controllergate_closure_mode", "controllergate_clean_track", "added_outside_advice"],
            "Current code labels the proposal noncanonical and historical recovery NOT_ESTABLISHED/NOT_RECOVERED.",
            "Treat interior-only relative curvature as a new candidate subject to calibration.",
        ),
        adjudication(
            "endpoint_curvature",
            "Endpoint-padded curvature on N=6..14 is valid for elbow selection.",
            "CONTRADICTED",
            ["added_outside_advice", "v030_codex_inference"],
            "A centered second difference requires both neighbors, so only N=7..13 are eligible without a separately justified boundary model.",
            "Exclude endpoints and mutation-test against padding leakage.",
        ),
        adjudication(
            "instrument_sensitivity_gate",
            "Insufficient registered instrument sensitivity should yield INCONCLUSIVE rather than NEGATIVE.",
            "SUPPORTED_WITH_SCOPE_CORRECTION",
            ["added_outside_advice", "v030_codex_inference"],
            "The metrological principle is sound when units, response, noise floor, and target band are registered; the supplied PAT/Talbot/TCXO numbers were not independently verified.",
            "Provide an optional domain-specific sensitivity contract; import no -45/-25 dB constants.",
        ),
        adjudication(
            "pat_db_thresholds",
            "The -45 dB to -25 dB PAT sideband interval is an established TFS-wide standard.",
            "NOT_FOUND",
            ["added_outside_advice"],
            "No authoritative source, instrument calibration, or executable contract for these numbers was located.",
            "Exclude the exact interval from the geometry method.",
        ),
        adjudication(
            "uncalibrated_modality_average",
            "Numerically averaging uncalibrated modalities yields a valid global confidence score.",
            "CONTRADICTED",
            ["added_outside_advice", "v030_codex_inference"],
            "Incomparable scores lack a common estimand and calibration.",
            "Report an evidence vector unless a registered cross-modal calibration or hierarchical model is validated.",
        ),
        adjudication(
            "logical_intersection_only",
            "Different modalities may interface only through logical intersection.",
            "SUPPORTED_WITH_SCOPE_CORRECTION",
            ["added_outside_advice", "v030_codex_inference"],
            "Logical intersection is a safe default, not a universal theorem; calibrated hierarchical models may later be valid.",
            "Freeze separate evidence channels for v0.3.0 and forbid uncalibrated numeric pooling.",
        ),
        adjudication(
            "controlleraudit_only_writer",
            "ControllerAudit is the sole writer of every ControllerGate terminal success state.",
            "SUPPORTED_WITH_SCOPE_CORRECTION",
            ["controllergate_claim_envelope", "batch103_contract", "added_outside_advice"],
            "Current canonical promotion requires a ControllerAudit receipt; the broader universal wording was not exhaustively proven across all historical states.",
            "State only the current scoped promotion requirement and preserve downstream count/repair gates.",
        ),
        adjudication(
            "measurement_repeat_policy_v1",
            "MeasurementRepeatPolicyV1 should separate stochastic/resource observables from deterministic semantics.",
            "SUPPORTED_WITH_SCOPE_CORRECTION",
            ["v030_protocol", "added_outside_advice"],
            "The partition is sound, but deterministic semantics require an authorized run and duplicate clean replay when claim-bearing, not necessarily a literal sterile container in every local test.",
            "Implement observable classes with registered repeat, randomization, and replay policies.",
        ),
    ]
    write_json(
        OUT / "outside_advice_adjudication.json",
        {
            "schema_version": "1.0.0",
            "authority_rule": "Level E advice cannot enter an executable contract without scoped support from higher authority or prospective calibration.",
            "allowed_classifications": [
                "SUPPORTED",
                "SUPPORTED_WITH_SCOPE_CORRECTION",
                "PLAUSIBLE_UNVERIFIED",
                "CONTRADICTED",
                "NOT_FOUND",
                "NON_EXECUTABLE_METAPHOR",
                "ALREADY_IMPLEMENTED",
                "IMPLEMENTED_BUT_NOT_VALIDATED",
                "REQUIRES_PROSPECTIVE_TEST",
            ],
            "statements": audit,
        },
    )

    historical_claims = [
        {
            "claim_id": "tld_i_exact_reproduction",
            "claim": "The first published TLD result is exactly reproduced.",
            "status": "SUPPORTED",
            "authority_level": "A/C",
            "source_ids": ["tld_i_public_release", "tfs_v022_release"],
            "claim_ceiling": "COMPUTED_DYNAMICAL",
        },
        {
            "claim_id": "v021_heldout_negative",
            "claim": "The v0.2.1 preregistered positive-persistence projection failed on the Beijing PM2.5 dataset.",
            "status": "SUPPORTED",
            "authority_level": "A/C",
            "source_ids": ["v021_exact_replay", "tfs_v022_release"],
            "claim_ceiling": "COMPUTED_DYNAMICAL",
        },
        {
            "claim_id": "te_se_winner_semantics",
            "claim": "T_e, S_e, and winner_N are distinct and winner_N cannot backfill emergence.",
            "status": "SUPPORTED",
            "authority_level": "B",
            "source_ids": ["formal_lexicon", "errata_map", "technical_standards_v21"],
        },
        {
            "claim_id": "controllergate_batch103_boundary",
            "claim": "Product Beta RC is blocked; prospective effectiveness and memory are not established; production readiness and self-maintaining software are false/not demonstrated.",
            "status": "SUPPORTED",
            "authority_level": "A",
            "source_ids": ["controllergate_claim_envelope", "batch103_contract"],
        },
        {
            "claim_id": "geometry_method_historical",
            "claim": "A canonical geometry-indexed TLD method already exists historically.",
            "status": "CONTRADICTED",
            "authority_level": "B/C",
            "source_ids": ["technical_standards_v21", "controllergate_closure_mode"],
        },
        {
            "claim_id": "external_validation",
            "claim": "TLD I or TFS v0.2.x establishes external physical validation.",
            "status": "CONTRADICTED",
            "authority_level": "A/B",
            "source_ids": ["tfs_v022_release", "formal_lexicon"],
        },
    ]
    write_jsonl(OUT / "historical_claim_audit.jsonl", historical_claims)

    unsupported_statuses = {
        "PLAUSIBLE_UNVERIFIED",
        "CONTRADICTED",
        "NOT_FOUND",
        "NON_EXECUTABLE_METAPHOR",
        "IMPLEMENTED_BUT_NOT_VALIDATED",
        "REQUIRES_PROSPECTIVE_TEST",
    }
    unsupported = [
        {
            "statement_id": item["statement_id"],
            "classification": item["classification"],
            "statement": item["statement"],
            "frozen_method_status": "EXCLUDED_PENDING_CALIBRATION"
            if item["classification"] == "REQUIRES_PROSPECTIVE_TEST"
            else "EXCLUDED",
            "reopen_condition": item["executable_disposition"],
        }
        for item in audit
        if item["classification"] in unsupported_statuses
    ]
    write_jsonl(OUT / "unsupported_claims_registry.jsonl", unsupported)

    usage = {
        "schema_version": "1.0.0",
        "authority_order": ["A", "B", "C", "D", "E", "F"],
        "source_count": len(sources),
        "adjudicated_statement_count": len(audit),
        "historical_claim_count": len(historical_claims),
        "unsupported_statement_count": len(unsupported),
        "source_selection": "filename and relevant-section search before content reads; no blind bulk archive loading",
        "source_bundle_members_read": list(wanted_members.values()),
        "formal_lexicon_body_available": True,
        "technical_standard_v21_body_available": True,
        "candidate_dataset_search_performed": False,
        "candidate_raw_values_inspected": False,
        "method_freeze_commit_pushed": False,
        "limitations": [
            "The outside Program Family Audit is Level E and was not substituted for the Level B formal lexicon.",
            "Development-chat pilot percentages are scoped to their recorded pilot only.",
            "No new field candidate was searched, selected, or inspected during this audit.",
        ],
    }
    write_json(OUT / "source_usage_manifest.json", usage)

    source_sums = [
        f"{item['sha256']}  {item['source_id']}  {item['location']}"
        for item in sources
        if len(item["sha256"]) == 64
    ]
    (OUT / "SHA256SUMS_SOURCE.txt").write_text("\n".join(source_sums) + "\n", encoding="utf-8")
    print(f"Wrote {len(sources)} sources and adjudicated {len(audit)} advice statements.")


if __name__ == "__main__":
    main()
