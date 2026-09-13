"""Executable fixed-estimator benchmark; sealed-bank access requires a method seal."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from ..metrology.v1 import Hierarchy, RectilinearVectorField, derivatives
from ..phase.v2 import sampled_winding, segment_phase_surrogate, temporal_cross_spectrum
from .contracts import exact_lower, exact_upper, scientific_id, sha256, write_json, write_manifest
from .generators import generate_trial

IMPLEMENTATIONS = ['metrology/v1.py', 'metrology/temporal.py', 'phase/v2.py',
                   'research/contracts.py', 'research/generators.py', 'research/benchmark.py']


def implementation_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parents[1]
    return {name: sha256((root / name).read_bytes()) for name in IMPLEMENTATIONS}


def seal_method(design_path: Path, calibration_path: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError('METHOD_FREEZE_ALREADY_EXISTS')
    summary = json.loads((calibration_path / 'summary.json').read_text())
    if summary['partition'] != 'CALIBRATION':
        raise ValueError('CALIBRATION_PARTITION_REQUIRED')
    value = {'method_id': 'CONVENTIONAL_OBSERVABLE_TOOLING_V1',
             'design_sha256': sha256(design_path.read_bytes()),
             'calibration_summary_sha256': sha256((calibration_path / 'summary.json').read_bytes()),
             'implementations': implementation_hashes(), 'candidate_revision': 1,
             'calibration_decision': 'FREEZE_FIXED_ESTIMATORS_WITH_REPORTED_LIMITATIONS',
             'sealed_outcomes_accessed': False, 'prospective_authorized': False,
             'temporal_window': 'boxcar', 'classification_threshold': 'analytic; no tuning'}
    write_json(output, value)
    return value


def score_trial(design: dict, raw: dict) -> dict:
    family, arrays, truth = raw['family'], raw['arrays'], raw['truth']
    result: dict = {'family': family, 'trial': raw['trial'], 'seed': raw['seed'],
                    'partition': raw['partition'], 'truth': truth,
                    'raw_scientific_id': scientific_id({'generator': design['design_id'],
                                                       'seed': raw['seed']}, arrays),
                    'null_children': 0, 'abstained': False, 'correct': False}
    if family.startswith('winding'):
        measurement = sampled_winding(
            arrays['complex_field'], mask=arrays['mask'],
            amplitude_noise_bound=truth['amplitude_noise_bound'],
            amplitude_floor=design['winding']['amplitude_floor'],
            branch_margin=design['winding']['branch_margin'],
            sampling_admissible=truth['sampling_admissible'])
        abstained = measurement['winding'] is None
        correct = abstained if truth['must_abstain'] else (
            not abstained and abs(measurement['winding'] - truth['winding']) < 1e-10)
        z = arrays['complex_field']
        baseline = None
        if not truth['must_abstain']:
            phases = np.unwrap(np.angle(np.r_[z, z[0]]))
            baseline = float((phases[-1] - phases[0]) / (2 * np.pi))
        # Endpoint links telescope; its near-zero phase is an intentional ablation.
        product_argument = None
        if np.all(abs(z) > 0):
            unit = z / abs(z)
            product_argument = float(np.angle(np.prod(np.roll(unit, -1) * unit.conj())))
        result.update(measurement=measurement, abstained=abstained, correct=bool(correct),
                      conventional_baseline=baseline, endpoint_product_phase=product_argument,
                      amplitude_only_winding=0.0 if not truth['must_abstain'] else None)
    elif family.startswith('temporal'):
        cfg = design['temporal']
        kwargs = {'segment_length': cfg['segment_length'], 'window': 'boxcar',
                  'frequency_index': cfg['registered_frequency_bin'],
                  'independent_segments': True, 'time_unit': 's'}
        estimate = temporal_cross_spectrum(arrays['x'], arrays['y'], arrays['time'], **kwargs)
        coherence = estimate['magnitude_squared_coherence']
        threshold = 1 - cfg['false_alarm_alpha'] ** (1 / (cfg['segment_count'] - 1))
        detected = coherence is not None and coherence > threshold
        rng = np.random.default_rng(np.random.SeedSequence([*raw['seed'], 917]))
        children = []
        for _ in range(cfg['null_children_per_experiment']):
            surrogate = segment_phase_surrogate(arrays['y'], segment_length=cfg['segment_length'],
                                                seed=int(rng.integers(0, 2**32)))
            child = temporal_cross_spectrum(arrays['x'], surrogate, arrays['time'], **kwargs)
            children.append(child['magnitude_squared_coherence'])
        # Null quantiles are surrogate quantiles, never a sampling confidence interval.
        result.update(measurement={'coherence': coherence, 'threshold': threshold,
                                   'phase_radians': estimate['cross_phase'],
                                   'frequency_hz': estimate['dominant_frequency'],
                                   'segment_count': estimate['segment_count']},
                      abstained=coherence is None, correct=bool(detected == truth['structure']),
                      detected=bool(detected), conventional_baseline=coherence,
                      null_children=len(children), null_values=children,
                      surrogate_tail_fraction=(1 + sum(x >= coherence for x in children)) /
                      (1 + len(children)) if coherence is not None else None,
                      null_quantiles=np.quantile(children, [.025, .5, .975]).tolist(),
                      null_quantiles_kind='SURROGATE_DISTRIBUTION_NOT_SAMPLING_CI')
    else:
        field = RectilinearVectorField(
            arrays['values'], arrays['x_coordinate'], arrays['y_coordinate'], arrays['mask'],
            coordinate_unit='m', velocity_unit='m/s',
            hierarchy=Hierarchy('synthetic-latent-system', 'generator', str(raw['seed'])),
            projection_id='REGISTERED_RAW_VECTOR')
        derived = derivatives(field)
        curl = derived.curl[derived.support]
        divergence = derived.divergence[derived.support]
        error = max(float(np.max(abs(curl - truth['curl']))),
                    float(np.max(abs(divergence - truth['divergence']))))
        values = np.where(arrays['mask'][..., None], arrays['values'], 0)
        legacy = np.gradient(values[..., 1], axis=1) - np.gradient(values[..., 0], axis=0)
        result.update(measurement={'curl_mean': float(np.mean(curl)),
                                   'divergence_mean': float(np.mean(divergence)),
                                   'max_absolute_error': error,
                                   'supported_cells': int(derived.support.sum()),
                                   'cells': int(derived.support.size),
                                   'unit': derived.derivative_unit},
                      correct=error < 1e-10, conventional_baseline=truth['curl'],
                      legacy_index_curl_mean=float(np.mean(legacy[arrays['mask']])))
    return result


def summarize(design: dict, partition: str, rows: list[dict]) -> dict:
    groups: dict[str, list] = defaultdict(list)
    for row in rows:
        groups[row['family']].append(row)
    delta = design['confidence']['delta_per_bound']
    summaries = []
    for family in design['families']:
        group = groups[family]
        count = len(group)
        correct = sum(row['correct'] for row in group)
        abstained = sum(row['abstained'] for row in group)
        intended_abstention = family in ('winding_mask', 'winding_zero_amplitude',
                                         'winding_branch_ambiguous')
        summaries.append({'family': family, 'independent_trials': count,
                          'correct': correct, 'errors': count-correct,
                          'error_upper_exact': exact_upper(count-correct, count, delta),
                          'correctness_lower_exact': exact_lower(correct, count, delta),
                          'abstentions': abstained, 'coverage': 1 - abstained/count,
                          'intended_abstention_control': intended_abstention,
                          'conditional_error': (sum(not r['correct'] and not r['abstained']
                                                    for r in group) / (count-abstained))
                          if count > abstained else None,
                          'unconditional_accuracy': correct/count,
                          'null_children': sum(r['null_children'] for r in group),
                          'gate_pass': exact_upper(count-correct, count, delta) <= .05 and
                          exact_lower(correct, count, delta) >= .9 and
                          (intended_abstention or abstained/count <= .1)})
    return {'design_id': design['design_id'], 'partition': partition,
            'independent_trials': len(rows), 'families': summaries,
            'null_children': sum(r['null_children'] for r in rows),
            'all_precision_gates_pass': all(g['gate_pass'] for g in summaries),
            'null_type_I_scope': 'temporal independence and registered winding-zero generator only',
            'uncertainty': '32 allocated one-sided exact bounds; no physical population CI',
            'baseline': 'Conventional estimators are the method; no TLD incremental gain asserted',
            'TLD_ADDED_VALUE_STATUS': 'NO_ADDED_VALUE_DEMONSTRATED',
            'TLD_DERIVED': 'BLOCKED', 'EXTERNALLY_VALIDATED': False,
            'prospective_authorized': False}


def run_benchmark(design_path: Path, partition: str, output: Path,
                  freeze_path: Path | None = None) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError('OUTPUT_EXISTS_REFUSE_SCIENTIFIC_OVERWRITE')
    design = json.loads(design_path.read_text())
    if partition not in design['partitions']:
        raise ValueError('UNREGISTERED_PARTITION')
    if partition == 'SEALED_SYNTHETIC_VALIDATION':
        if freeze_path is None:
            raise ValueError('METHOD_FREEZE_REQUIRED')
        freeze = json.loads(freeze_path.read_text())
        if freeze['implementations'] != implementation_hashes():
            raise ValueError('IMPLEMENTATION_CHANGED_AFTER_FREEZE')
        if freeze['design_sha256'] != sha256(design_path.read_bytes()):
            raise ValueError('DESIGN_CHANGED_AFTER_FREEZE')
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'access_receipt.json', {
        'partition': partition, 'design_sha256': sha256(design_path.read_bytes()),
        'implementation_hashes': implementation_hashes(),
        'method_seal_sha256': sha256(freeze_path.read_bytes()) if freeze_path else None,
        'kind': 'DETERMINISTIC_BENCHMARK_NOT_REAL_SCORED_EVENT'})
    rows = []
    with (output / 'trials.jsonl').open('w', encoding='utf-8', newline='\n') as stream:
        for family in design['families']:
            for trial in range(design['partitions'][partition]['trials_per_family']):
                row = score_trial(design, generate_trial(design, partition, family, trial))
                stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
                rows.append(row)
            stream.flush()
    summary = summarize(design, partition, rows)
    write_json(output / 'summary.json', summary)
    write_manifest(output)
    return summary
