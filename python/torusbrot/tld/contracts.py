"""Frozen, reviewable TLD I contracts used by the production implementation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ..models import content_hash

TLD_I_DOI = "10.5281/zenodo.18080090"
TLD_I_ARCHIVE_MD5 = "25f26f78bf6c73df1e551983af518e9a"
TLD_I_ARCHIVE_SHA256 = "5bae9af506bd65e74225fc91f869931d70fcd89505cbc672b3538abdfd4b446e"


@dataclass(frozen=True)
class HistoricalTldIContract:
    seed: int = 42
    n_min: int = 7
    n_max: int = 13
    n_center: int = 10
    p_swap_escape: float = 0.02
    max_escape_steps: int = 60
    max_heal_steps_notebook13: int = 300
    max_heal_steps_notebook14: int = 500
    epsilon_heal: float = 16.0
    core_trials: int = 400
    alpha_sweep_trials: int = 250
    notebook14_trace_trials: int = 10
    notebook14_envelope_trials: int = 300
    alpha_sweep: tuple[float, ...] = (0.0, 0.005, 0.01, 0.02, 0.05, 0.1)
    trace_alphas: tuple[float, ...] = (0.02, 0.05)
    envelope_p_swap: tuple[float, ...] = (0.005, 0.01, 0.02, 0.03)

    @property
    def n_window(self) -> tuple[int, ...]:
        return tuple(range(self.n_min, self.n_max + 1))

    @property
    def preregistration(self) -> dict[str, Any]:
        return {
            "escape_rate_min": 0.90,
            "alpha0_return_rate_max": 0.40,
            "alpha002_return_rate_min": 0.95,
            "alpha002_mean_return_steps_max": 120.0,
            "alpha002_p90_flips_max": 5.0,
        }

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["alpha_sweep"] = list(self.alpha_sweep)
        value["trace_alphas"] = list(self.trace_alphas)
        value["envelope_p_swap"] = list(self.envelope_p_swap)
        value["n_window"] = list(self.n_window)
        value["preregistration"] = self.preregistration
        value["declared_max_heal_steps_in_prereg_document"] = 400
        value["known_declaration_mismatch"] = True
        return value

    @property
    def sha256(self) -> str:
        return content_hash(self.to_dict())
