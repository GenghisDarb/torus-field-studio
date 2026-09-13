"""Auxiliary registered phase-interval coverage; never changes the primary rule."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..phase.v2 import temporal_cross_spectrum
from .contracts import exact_lower, exact_upper, sha256, write_json
from .generators import generate_trial


def phase_coverage(design_path: Path, contract_path: Path, results: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError('UNCERTAINTY_OUTPUT_EXISTS')
    # An executed primary access receipt is mandatory; this never opens a new bank.
    receipt = json.loads((results / 'access_receipt.json').read_text())
    design = json.loads(design_path.read_text())
    contract = json.loads(contract_path.read_text())
    partition = receipt['partition']
    if partition not in contract['partitions']:
        raise ValueError('UNREGISTERED_UNCERTAINTY_PARTITION')
    if receipt['design_sha256'] != sha256(design_path.read_bytes()):
        raise ValueError('UNCERTAINTY_DESIGN_MISMATCH')
    rows, summaries = [], []
    for family in contract['families']:
        group = []
        for trial in range(design['partitions'][partition]['trials_per_family']):
            raw = generate_trial(design, partition, family, trial)
            arrays = raw['arrays']
            seed = int(np.random.SeedSequence([*raw['seed'], 919]).generate_state(1)[0])
            measured = temporal_cross_spectrum(
                arrays['x'], arrays['y'], arrays['time'], segment_length=64,
                window='boxcar', frequency_index=4, independent_segments=True,
                bootstrap_replicates=contract['replicates'], bootstrap_seed=seed)
            interval = measured['phase_uncertainty']
            error = float(np.angle(np.exp(1j * (raw['truth']['phase_lag'] -
                                               measured['cross_phase']))))
            covered = interval['lower_offset_radians'] <= error <= interval['upper_offset_radians']
            group.append({'family': family, 'trial': trial, 'phase_error': -error,
                          'covered': bool(covered), 'interval': interval})
        count = len(group)
        successes = sum(row['covered'] for row in group)
        summaries.append({'family': family, 'independent_trials': count, 'covered': successes,
                          'coverage': successes/count,
                          'coverage_lower_95': exact_lower(successes, count, .025),
                          'coverage_upper_95': exact_upper(successes, count, .025),
                          'mean_phase_error_radians': float(
                              np.mean([r['phase_error'] for r in group])),
                          'mean_interval_width_radians': float(np.mean([
                              r['interval']['upper_offset_radians'] -
                              r['interval']['lower_offset_radians'] for r in group]))})
        rows.extend(group)
    result = {'contract_sha256': sha256(contract_path.read_bytes()), 'partition': partition,
              'kind': 'AUXILIARY_COVERAGE_DIAGNOSTIC', 'families': summaries, 'rows': rows,
              'multiplicity': 'Pointwise 95% exact intervals; not simultaneous acceptance gates',
              'parameter_changes': False, 'physical_coverage_claim': False}
    write_json(output, result)
    return result
