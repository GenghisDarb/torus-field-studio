"""Independent direct-DFT reconstruction of registered phase-interval coverage."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .generators import generate_trial
from .verify import _compare, _direct_fourier_pairs, _upper


def verify_phase_coverage(design_path: Path, contract_path: Path, results: Path,
                          coverage_path: Path, output: Path | None = None) -> dict:
    if output is not None and output.exists():
        raise ValueError('VERIFICATION_OUTPUT_EXISTS')
    design = json.loads(design_path.read_text())
    contract = json.loads(contract_path.read_text())
    receipt = json.loads((results / 'access_receipt.json').read_text())
    partition = receipt['partition']
    if receipt['design_sha256'] != hashlib.sha256(design_path.read_bytes()).hexdigest():
        raise ValueError('UNCERTAINTY_DESIGN_MISMATCH')
    if partition not in contract['partitions']:
        raise ValueError('UNREGISTERED_COVERAGE_PARTITION')
    rows, summaries = [], []
    for family in contract['families']:
        group = []
        for trial in range(design['partitions'][partition]['trials_per_family']):
            raw = generate_trial(design, partition, family, trial)
            arrays = raw['arrays']
            a, b, _ = _direct_fourier_pairs(arrays['x'], arrays['y'], arrays['time'], 64, 4)
            cross = np.conjugate(a)*b
            reference = float(np.angle(np.mean(cross)))
            seed = int(np.random.SeedSequence([*raw['seed'], 919]).generate_state(1)[0])
            rng = np.random.default_rng(seed)
            offsets = []
            for _ in range(contract['replicates']):
                selected = rng.integers(len(cross), size=len(cross))
                angle = np.angle(np.mean(cross[selected])) - reference
                offsets.append(float(np.arctan2(np.sin(angle), np.cos(angle))))
            lower, upper = np.quantile(offsets, [.025, .975])
            error = float(np.angle(np.exp(1j*(raw['truth']['phase_lag']-reference))))
            group.append({'family': family, 'trial': trial, 'phase_error': -error,
                          'covered': bool(lower <= error <= upper),
                          'interval': {'lower_offset_radians': float(lower),
                                       'upper_offset_radians': float(upper),
                                       'reference_phase_radians': reference, 'seed': seed}})
        n = len(group)
        k = sum(r['covered'] for r in group)
        summaries.append({'family': family, 'independent_trials': n, 'covered': k,
                          'coverage': k/n,
                          'coverage_lower_95': 1-_upper(n-k, n, .025),
                          'coverage_upper_95': _upper(k, n, .025),
                          'mean_phase_error_radians': float(np.mean([
                              r['phase_error'] for r in group])),
                          'mean_interval_width_radians': float(np.mean([
                              r['interval']['upper_offset_radians']-
                              r['interval']['lower_offset_radians'] for r in group]))})
        rows.extend(group)
    # Production coverage is not opened until all raw calculations are finished.
    actual = json.loads(coverage_path.read_text())
    expected_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    if actual['contract_sha256'] != expected_hash or actual['partition'] != partition:
        raise ValueError('COVERAGE_CONTRACT_MISMATCH')
    if actual.get('physical_coverage_claim') is not False or actual.get('parameter_changes'):
        raise ValueError('COVERAGE_CLAIM_ESCALATION')
    _compare(summaries, actual['families'])
    if len(rows) != len(actual['rows']):
        raise ValueError('COVERAGE_ROW_COUNT')
    for expected, observed in zip(rows, actual['rows'], strict=True):
        trimmed = {key: observed[key] for key in expected}
        trimmed['interval'] = {key: observed['interval'][key] for key in expected['interval']}
        _compare(expected, trimmed)
    result = {'status': 'VERIFIED', 'valid': True, 'independent_recomputation': True,
              'partition': partition, 'independent_trials': len(rows),
              'bootstrap_children': len(rows)*contract['replicates'],
              'families': summaries, 'production_scoring_imported': False,
              'production_outputs_opened_after_reconstruction': True,
              'shared_assumptions': ['audited generator', 'PCG64 bootstrap indices',
                                     'exchangeable independent segments in synthetic model'],
              'coverage_sha256': hashlib.sha256(coverage_path.read_bytes()).hexdigest(),
              'physical_coverage_claim': False, 'EXTERNALLY_VALIDATED': False}
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n', newline='\n')
    return result
