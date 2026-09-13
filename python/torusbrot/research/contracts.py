"""Portable identities and exact finite-trial uncertainty for the reviewed study."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def scientific_id(contract: dict, arrays: dict[str, np.ndarray]) -> str:
    """Relocation-invariant identity; binds dtype, shape and raw little-endian values."""
    h = hashlib.sha256(json_bytes(contract))
    for name, value in sorted(arrays.items()):
        array = np.asarray(value)
        if array.dtype.hasobject:
            raise ValueError("OBJECT_ARRAY_FORBIDDEN")
        array = np.ascontiguousarray(array.astype(array.dtype.newbyteorder("<")))
        h.update(json_bytes({"name": name, "dtype": array.dtype.str, "shape": array.shape}))
        h.update(array.tobytes())
    return h.hexdigest()


def zero_error_trials(target_upper: float, delta: float) -> int:
    if not 0 < target_upper < 1 or not 0 < delta < 1:
        raise ValueError("INVALID_CONFIDENCE_DESIGN")
    return math.ceil(math.log(delta) / math.log1p(-target_upper))


def _binomial_cdf(k: int, n: int, p: float) -> float:
    if p <= 0:
        return 1.0
    if p >= 1:
        return float(k >= n)
    logs = [math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1)
            + j * math.log(p) + (n - j) * math.log1p(-p) for j in range(k + 1)]
    peak = max(logs)
    return min(1.0, math.exp(peak) * math.fsum(math.exp(v - peak) for v in logs))


def exact_upper(errors: int, trials: int, delta: float = 0.05) -> float:
    """One-sided Clopper-Pearson inversion; n counts independent experiments."""
    if trials < 1 or not 0 <= errors <= trials or not 0 < delta < 1:
        raise ValueError("INVALID_BINOMIAL_COUNTS")
    if errors == trials:
        return 1.0
    if errors == 0:
        return -math.expm1(math.log(delta) / trials)
    low, high = errors / trials, 1.0
    for _ in range(64):
        middle = (low + high) / 2
        if _binomial_cdf(errors, trials, middle) > delta:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def exact_lower(successes: int, trials: int, delta: float = 0.05) -> float:
    return 1.0 - exact_upper(trials - successes, trials, delta)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def write_manifest(directory: Path) -> str:
    entries = {p.relative_to(directory).as_posix(): sha256(p.read_bytes())
               for p in sorted(directory.rglob("*"))
               if p.is_file() and p.name != "SHA256SUMS.txt"}
    payload = "".join(f"{value}  {name}\n" for name, value in entries.items()).encode()
    (directory / "SHA256SUMS.txt").write_bytes(payload)
    return sha256(payload)
