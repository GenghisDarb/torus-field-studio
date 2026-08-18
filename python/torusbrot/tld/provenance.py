"""Source registry construction without local path disclosure."""

from __future__ import annotations

from typing import Any

from .contracts import TLD_I_ARCHIVE_MD5, TLD_I_ARCHIVE_SHA256, TLD_I_DOI


def tld_i_source_registry(input_hashes: dict[str, str]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "source_id": "zenodo-18080090",
        "doi": TLD_I_DOI,
        "record_url": "https://zenodo.org/records/18080090",
        "title": (
            "TORUS Ladder Dynamics I: Structural Escape, Damped Healing, and Ringing Diagnostics"
        ),
        "archive": {
            "filename": "TORUS_Zenodo_v1.zip",
            "md5": TLD_I_ARCHIVE_MD5,
            "sha256": TLD_I_ARCHIVE_SHA256,
        },
        "input_sha256": dict(sorted(input_hashes.items())),
        "confirmatory_notebooks": [13, 14],
        "exploratory_notebooks_used_as_evidence": False,
        "license": "MIT",
        "claim_authority_ceiling": "COMPUTED_DYNAMICAL",
    }
