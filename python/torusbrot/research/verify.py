"""Independent reconstruction of the registered synthetic benchmark.

Only the audited raw generator is shared with production. No production scoring,
derivative, phase, null, summary, identity or interval function is imported.
Production result files are opened only after all independent calculations finish.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path, PurePosixPath

import numpy as np

from .generators import generate_trial

_FAMILIES = (
    'winding_zero', 'winding_positive', 'winding_negative', 'winding_pair_cancel',
    'winding_amplitude', 'winding_mask', 'winding_zero_amplitude', 'winding_branch_ambiguous',
    'temporal_independent', 'temporal_coherent', 'temporal_colored_independent',
    'temporal_colored_coherent', 'vector_solid_rotation', 'vector_constant', 'vector_hole',
    'vector_shear',
)
_ABSTENTION = {'winding_mask', 'winding_zero_amplitude', 'winding_branch_ambiguous'}


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def _sha(payload):
    return hashlib.sha256(payload).hexdigest()


def independent_scientific_id(contract: dict, arrays: dict) -> str:
    digest = hashlib.sha256(_json_bytes(contract))
    for name in sorted(arrays):
        array = np.asarray(arrays[name])
        if array.dtype.hasobject:
            raise ValueError('OBJECT_ARRAY_FORBIDDEN')
        little = np.ascontiguousarray(array.astype(array.dtype.newbyteorder('<')))
        digest.update(_json_bytes({'name': name, 'dtype': little.dtype.str, 'shape': little.shape}))
        digest.update(little.tobytes(order='C'))
    return digest.hexdigest()


def _upper(errors: int, trials: int, delta: float) -> float:
    """Independent exact binomial inversion using integer combinations and fsum."""
    if not 0 <= errors <= trials or trials < 1 or not 0 < delta < 1:
        raise ValueError('INVALID_BINOMIAL_COUNTS')
    if errors == trials:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(70):
        p = (lo+hi)/2
        probability = math.fsum(math.comb(trials, j)*p**j*(1-p)**(trials-j)
                                for j in range(errors+1))
        if probability > delta:
            lo = p
        else:
            hi = p
    return (lo+hi)/2


def _check_design(design: dict) -> None:
    if tuple(design['families']) != _FAMILIES:
        raise ValueError('UNREGISTERED_FAMILY_OR_ORDER')
    if design['winding']['operator'] != 'phase.v2.sampled_winding':
        raise ValueError('UNREGISTERED_OPERATOR_SUBSTITUTION')
    if design['temporal']['operator'] != 'phase.v2.temporal_cross_spectrum':
        raise ValueError('UNREGISTERED_OPERATOR_SUBSTITUTION')
    if design['metrology']['operator'] != 'metrology.v1.derivatives':
        raise ValueError('UNREGISTERED_OPERATOR_SUBSTITUTION')
    cfg = design['confidence']
    if cfg['null_children_are_trials'] is not False:
        raise ValueError('NULL_CHILDREN_ARE_NOT_INDEPENDENT_TRIALS')
    if cfg['procedure'] != 'one-sided exact Clopper-Pearson':
        raise ValueError('UNREGISTERED_CONFIDENCE_PROCEDURE')
    if cfg['allocated_bounds'] != 2*len(_FAMILIES):
        raise ValueError('MULTIPLICITY_ALLOCATION_MISMATCH')
    if not math.isclose(cfg['delta_per_bound']*cfg['allocated_bounds'],
                        cfg['familywise_delta'], rel_tol=1e-14):
        raise ValueError('CONFIDENCE_BUDGET_MISMATCH')
    temporal = design['temporal']
    if not 0 < temporal['registered_frequency_bin'] < temporal['segment_length']/2:
        raise ValueError('INTERIOR_REGISTERED_FREQUENCY_REQUIRED')
    if temporal['segment_count'] < 2 or not 0 < temporal['false_alarm_alpha'] < 1:
        raise ValueError('INVALID_TEMPORAL_CONTRACT')
    roots = [partition['seed_root'] for partition in design['partitions'].values()]
    if len(roots) != len(set(roots)):
        raise ValueError('VALIDATION_BANK_REUSE')


def _phase_measurement(z, mask, noise, floor, margin, sampling):
    valid = np.asarray(mask) & np.isfinite(z) & (abs(z) > max(noise, floor))
    if not valid.all():
        return {'status': 'INDETERMINATE', 'winding': None, 'continuous_winding': None,
                'valid_sample_count': int(valid.sum()),
                'reason': 'INCOMPLETE_OR_UNIDENTIFIABLE_LOOP_PHASE'}
    phases = [math.atan2(float(a.imag), float(a.real)) for a in z]
    increments = [(phases[(i+1) % len(z)]-phases[i]+math.pi) % (2*math.pi)-math.pi
                  for i in range(len(z))]
    bounds = [math.asin(noise/abs(a)) for a in z]
    clearance = [math.pi-abs(d)-bounds[i]-bounds[(i+1) % len(z)]-margin
                 for i, d in enumerate(increments)]
    ambiguous = sum(c <= 0 for c in clearance)
    winding = None if ambiguous else round(math.fsum(increments)/(2*math.pi))
    result = {'status': 'INDETERMINATE' if ambiguous else 'ESTIMATED', 'winding': winding,
              'continuous_winding': winding if sampling else None,
              'valid_sample_count': len(z), 'ambiguous_edge_count': ambiguous,
              'minimum_branch_clearance_radians': min(clearance)}
    if not ambiguous:
        result['increments_radians'] = increments
    return result


def _direct_fourier_pairs(x, y, time, length, bin_index):
    if len(x) != len(y) or len(x) != len(time) or len(x) % length:
        raise ValueError('TEMPORAL_SUPPORT_MISMATCH')
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('MISSING_TEMPORAL_SUPPORT')
    dt = float(np.median(np.diff(time)))
    if dt <= 0 or not np.allclose(np.diff(time)/dt, 1, rtol=1e-7, atol=0):
        raise ValueError('IRREGULAR_OR_REORDERED_TIME')
    angles = -2*math.pi*bin_index*np.arange(length)/length
    basis = np.cos(angles)+1j*np.sin(angles)
    left = x.reshape(-1, length)
    right = y.reshape(-1, length)
    a = np.sum((left-left.mean(axis=1)[:, None])*basis, axis=1)
    b = np.sum((right-right.mean(axis=1)[:, None])*basis, axis=1)
    return a, b, bin_index/(length*dt)


def _coherence(a, b):
    cross = np.mean(np.conjugate(a)*b)
    denominator = np.mean(abs(a)**2)*np.mean(abs(b)**2)
    if denominator == 0:
        return None, None
    return float(np.clip(abs(cross)**2/denominator, 0, 1)), float(np.angle(cross))


def independent_derivatives(values, x, y, mask):
    """Explicit derivatives of three Lagrange basis polynomials; no linear solve."""
    vector = np.asarray(values)
    x, y, mask = np.asarray(x), np.asarray(y), np.asarray(mask)
    if vector.shape != (len(y), len(x), 2) or mask.shape != vector.shape[:-1]:
        raise ValueError('COORDINATE_SUPPORT_MISMATCH')
    for coordinate in (x, y):
        difference = np.diff(coordinate)
        if not np.isfinite(coordinate).all() or not (
            np.all(difference > 0) or np.all(difference < 0)
        ):
            raise ValueError('INVALID_COORDINATE_AXIS')
    curl = np.full(mask.shape, np.nan)
    divergence = np.full(mask.shape, np.nan)
    support = np.zeros(mask.shape, dtype=bool)

    def stencil(axis, i):
        start = min(max(i-1, 0), len(axis)-3)
        indices = list(range(start, start+3))
        points = axis[indices]
        weights = []
        for j in range(3):
            others = [k for k in range(3) if k != j]
            numerator = 2*axis[i]-points[others[0]]-points[others[1]]
            denominator = (points[j]-points[others[0]])*(points[j]-points[others[1]])
            weights.append(numerator/denominator)
        return indices, np.array(weights)

    x_stencils = [stencil(x, i) for i in range(len(x))]
    y_stencils = [stencil(y, i) for i in range(len(y))]
    for iy in range(len(y)):
        for ix in range(len(x)):
            xi, wx = x_stencils[ix]
            yi, wy = y_stencils[iy]
            if not mask[iy, xi].all() or not mask[yi, ix].all():
                continue
            along_x = np.sum(vector[iy, xi]*wx[:, None], axis=0)
            along_y = np.sum(vector[yi, ix]*wy[:, None], axis=0)
            curl[iy, ix] = along_x[1]-along_y[0]
            divergence[iy, ix] = along_x[0]+along_y[1]
            support[iy, ix] = True
    return curl, divergence, support


def reconstruct_trial(design: dict, raw: dict) -> dict:
    """Reconstruct scores from supplied raw arrays and validate generator truth."""
    family, arrays, truth = raw['family'], raw['arrays'], raw['truth']
    identity = independent_scientific_id({'generator': design['design_id'], 'seed': raw['seed']},
                                         arrays)
    row = {'family': family, 'trial': raw['trial'], 'partition': raw['partition'],
           'seed': raw['seed'], 'raw_scientific_id': identity, 'truth': truth,
           'null_children': 0, 'abstained': False}
    if family.startswith('winding'):
        expected_w = -1 if family == 'winding_negative' else (
            0 if family in {'winding_zero', 'winding_pair_cancel'} else 1)
        expected_abstain = family in _ABSTENTION
        if truth['winding'] != (None if expected_abstain else expected_w):
            raise ValueError('GENERATOR_TRUTH_MISMATCH')
        if truth['must_abstain'] != expected_abstain:
            raise ValueError('ABSTENTION_TRUTH_MISMATCH')
        measurement = _phase_measurement(arrays['complex_field'], arrays['mask'],
                                         truth['amplitude_noise_bound'],
                                         design['winding']['amplitude_floor'],
                                         design['winding']['branch_margin'],
                                         truth['sampling_admissible'])
        abstained = measurement['winding'] is None
        row.update(measurement=measurement, abstained=abstained,
                   correct=abstained if expected_abstain else measurement['winding'] == expected_w,
                   conventional_baseline=None if expected_abstain else float(expected_w),
                   amplitude_only_winding=None if expected_abstain else 0.0)
    elif family.startswith('temporal'):
        cfg = design['temporal']
        structure = family in {'temporal_coherent', 'temporal_colored_coherent'}
        if truth['structure'] != structure or truth['independent_segments'] != cfg['segment_count']:
            raise ValueError('TEMPORAL_TRUTH_OR_UNIT_MISMATCH')
        a, b, frequency = _direct_fourier_pairs(
            arrays['x'], arrays['y'], arrays['time'], cfg['segment_length'],
            cfg['registered_frequency_bin'])
        coherence, phase = _coherence(a, b)
        threshold = -math.expm1(math.log(cfg['false_alarm_alpha'])/(len(a)-1))
        detected = coherence is not None and coherence > threshold
        # Raw null Fourier coefficients transform analytically. Each child draws
        # exactly the registered K x (L/2+1) phase array. No production surrogate.
        rng = np.random.default_rng(np.random.SeedSequence([*raw['seed'], 917]))
        children = []
        for _ in range(cfg['null_children_per_experiment']):
            child_seed = int(rng.integers(0, 2**32))
            phases = np.random.default_rng(child_seed).uniform(
                -np.pi, np.pi, (len(a), cfg['segment_length']//2+1))
            phased = b*np.exp(1j*phases[:, cfg['registered_frequency_bin']])
            children.append(_coherence(a, phased)[0])
        row.update(measurement={'coherence': coherence, 'phase_radians': phase,
                                'frequency_hz': frequency, 'threshold': threshold,
                                'segment_count': len(a)},
                   correct=detected == structure, detected=detected, abstained=coherence is None,
                   conventional_baseline=coherence, null_children=len(children),
                   null_values=children,
                   null_quantiles=np.quantile(children, [.025, .5, .975]).tolist(),
                   surrogate_tail_fraction=(1+sum(child >= coherence for child in children)) /
                   (len(children)+1), null_quantiles_kind='SURROGATE_DISTRIBUTION_NOT_SAMPLING_CI')
    else:
        curl, divergence, support = independent_derivatives(
            arrays['values'], arrays['x_coordinate'], arrays['y_coordinate'], arrays['mask'])
        supported_curl, supported_div = curl[support], divergence[support]
        if family in {'vector_constant', 'vector_hole'}:
            expected_curl = 0.0
        elif family == 'vector_shear':
            expected_curl = -float((arrays['values'][-1, 0, 0]-arrays['values'][0, 0, 0]) /
                                   (arrays['y_coordinate'][-1]-arrays['y_coordinate'][0]))
        else:
            expected_curl = float(2*(arrays['values'][0, -1, 1]-arrays['values'][0, 0, 1]) /
                                  (arrays['x_coordinate'][-1]-arrays['x_coordinate'][0]))
        if not math.isclose(truth['curl'], expected_curl, abs_tol=1e-12, rel_tol=1e-12):
            raise ValueError('VECTOR_GENERATOR_TRUTH_MISMATCH')
        error = max(float(np.max(abs(supported_curl-expected_curl))),
                    float(np.max(abs(supported_div))))
        row.update(measurement={'curl_mean': float(np.mean(supported_curl)),
                                'divergence_mean': float(np.mean(supported_div)),
                                'max_absolute_error': error, 'supported_cells': int(support.sum()),
                                'cells': support.size, 'unit': 's^-1'},
                   correct=error < 1e-10, conventional_baseline=expected_curl)
    return row


def _compare(expected, observed, path='root', *, tolerance=2e-10):
    if isinstance(expected, dict):
        if not isinstance(observed, dict):
            raise ValueError(f'SCIENTIFIC_MISMATCH:{path}:type')
        for key, value in expected.items():
            if key not in observed:
                raise ValueError(f'SCIENTIFIC_MISMATCH:{path}.{key}:missing')
            _compare(value, observed[key], f'{path}.{key}', tolerance=tolerance)
    elif isinstance(expected, list):
        if not isinstance(observed, list) or len(expected) != len(observed):
            raise ValueError(f'SCIENTIFIC_MISMATCH:{path}:length')
        for i, (first, second) in enumerate(zip(expected, observed, strict=True)):
            _compare(first, second, f'{path}[{i}]', tolerance=tolerance)
    elif isinstance(expected, (float, np.floating)):
        if isinstance(observed, bool) or not isinstance(observed, (int, float)):
            raise ValueError(f'SCIENTIFIC_MISMATCH:{path}:numeric_type')
        if not math.isfinite(observed) or not math.isclose(expected, observed,
                                                          rel_tol=tolerance, abs_tol=tolerance):
            raise ValueError(f'SCIENTIFIC_MISMATCH:{path}:numeric')
    elif type(expected) is bool:
        if observed is not expected:
            raise ValueError(f'SCIENTIFIC_MISMATCH:{path}:boolean')
    elif isinstance(expected, (int, np.integer)) and isinstance(observed, bool):
        raise ValueError(f'SCIENTIFIC_MISMATCH:{path}:integer_type')
    elif expected != observed:
        raise ValueError(f'SCIENTIFIC_MISMATCH:{path}:identity')


def _check_claims(value):
    if not isinstance(value, dict):
        if isinstance(value, list):
            for item in value:
                _check_claims(item)
        return
    prohibited = {
        'EXTERNALLY_VALIDATED': False, 'external_replication': False,
        'prospective_authorized': False, 'arbitrary_local_gauge_invariant': False,
        'global_phase_invariant': True, 'scalar_link_holonomy_trivial': True,
        'physical_nonorientable_space_established': False, 'null_children_are_trials': False,
    }
    for key, item in value.items():
        if key in prohibited and item is not prohibited[key]:
            raise ValueError(f'SEMANTIC_CLAIM_ESCALATION:{key}')
        if key == 'TLD_DERIVED' and item != 'BLOCKED':
            raise ValueError('SEMANTIC_CLAIM_ESCALATION:TLD_DERIVED')
        if key in {'T_e', 'S_e', 'winner_N'} and item is not None:
            raise ValueError(f'UNREGISTERED_ENDPOINT:{key}')
        _check_claims(item)


def _manifest(directory):
    expected = {}
    for line in (directory/'SHA256SUMS.txt').read_text().splitlines():
        digest, name = line.split('  ', 1)
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
            raise ValueError('UNSAFE_MANIFEST_PATH')
        if name in expected:
            raise ValueError('DUPLICATE_MANIFEST_PATH')
        actual_path = directory.joinpath(*path.parts)
        if (actual_path.is_symlink() or
                not actual_path.resolve().is_relative_to(directory.resolve())):
            raise ValueError('UNSAFE_MANIFEST_PATH')
        if _sha(actual_path.read_bytes()) != digest:
            raise ValueError('SOURCE_HASH_MISMATCH')
        expected[name] = digest
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()
              and p.name != 'SHA256SUMS.txt'}
    if set(expected) != actual:
        raise ValueError('MANIFEST_MEMBER_MISMATCH')
    return expected


def _independent_summary(design, partition, rows):
    groups = []
    delta = design['confidence']['delta_per_bound']
    for family in _FAMILIES:
        subset = [r for r in rows if r['family'] == family]
        count = len(subset)
        correct = sum(bool(row['correct']) for row in subset)
        abstentions = sum(bool(row['abstained']) for row in subset)
        error_upper = _upper(count-correct, count, delta)
        lower = 1-_upper(count-correct, count, delta)
        groups.append({'family': family, 'independent_trials': count, 'correct': correct,
                       'errors': count-correct, 'error_upper_exact': error_upper,
                       'correctness_lower_exact': lower, 'abstentions': abstentions,
                       'coverage': 1-abstentions/count,
                       'intended_abstention_control': family in _ABSTENTION,
                       'conditional_error': sum(not r['correct'] and not r['abstained']
                                                for r in subset)/(count-abstentions)
                       if count > abstentions else None, 'unconditional_accuracy': correct/count,
                       'null_children': sum(r['null_children'] for r in subset),
                       'gate_pass': error_upper <= .05 and lower >= .9 and
                       (family in _ABSTENTION or abstentions/count <= .1)})
    return {'design_id': design['design_id'], 'partition': partition,
            'independent_trials': len(rows), 'families': groups,
            'null_children': sum(row['null_children'] for row in rows),
            'all_precision_gates_pass': all(row['gate_pass'] for row in groups),
            'TLD_ADDED_VALUE_STATUS': 'NO_ADDED_VALUE_DEMONSTRATED', 'TLD_DERIVED': 'BLOCKED',
            'EXTERNALLY_VALIDATED': False, 'prospective_authorized': False}


def verify_benchmark(
    design_path: Path, result_directory: Path, output: Path | None,
    *, expected_design_sha256: str | None = None, freeze_path: Path | None = None,
) -> dict:
    """Verify an ALREADY EXECUTED bank. This function never creates a new bank.

    An externally supplied expected design hash anchors custody independently of
    the result receipt. Otherwise verification establishes internal hash agreement
    only. A sealed bank requires the exact method seal used by production.
    """
    design_path, result_directory = Path(design_path), Path(result_directory)
    if output is not None:
        output = Path(output)
        if output.exists():
            raise ValueError('VERIFIER_OUTPUT_EXISTS')
        if output.resolve().is_relative_to(result_directory.resolve()):
            raise ValueError('VERIFIER_OUTPUT_MUST_NOT_MUTATE_INPUT_PACKAGE')
    receipt = json.loads((result_directory/'access_receipt.json').read_text())
    design_bytes = design_path.read_bytes()
    digest = _sha(design_bytes)
    if digest != receipt['design_sha256'] or (
        expected_design_sha256 is not None and digest != expected_design_sha256
    ):
        raise ValueError('DESIGN_EXPECTATION_MISMATCH_NO_RESEAL')
    design = json.loads(design_bytes)
    _check_design(design)
    partition = receipt['partition']
    if partition not in design['partitions']:
        raise ValueError('UNREGISTERED_PARTITION')
    root = Path(__file__).resolve().parents[1]
    required = {'metrology/v1.py', 'phase/v2.py', 'research/contracts.py',
                'research/generators.py', 'research/benchmark.py'}
    if not required <= set(receipt['implementation_hashes']):
        raise ValueError('INCOMPLETE_IMPLEMENTATION_CUSTODY')
    for name, expected in receipt['implementation_hashes'].items():
        path = PurePosixPath(name)
        if '..' in path.parts or path.is_absolute() or ':' in name or '\\' in name:
            raise ValueError('UNSAFE_IMPLEMENTATION_PATH')
        if _sha(root.joinpath(*path.parts).read_bytes()) != expected:
            raise ValueError(f'IMPLEMENTATION_CUSTODY_MISMATCH:{name}')
    if partition == 'SEALED_SYNTHETIC_VALIDATION':
        if freeze_path is None:
            raise ValueError('METHOD_SEAL_REQUIRED_FOR_SEALED_VERIFICATION')
        seal_bytes = Path(freeze_path).read_bytes()
        seal = json.loads(seal_bytes)
        if _sha(seal_bytes) != receipt['method_seal_sha256']:
            raise ValueError('METHOD_SEAL_HASH_MISMATCH')
        if (seal['design_sha256'] != digest or
                seal['implementations'] != receipt['implementation_hashes']):
            raise ValueError('METHOD_SEAL_CONTRACT_MISMATCH')
    # Do not read trials or summary until independent arrays and calculations exist.
    expected_rows = [reconstruct_trial(design, generate_trial(design, partition, family, trial))
                     for family in _FAMILIES
                     for trial in range(design['partitions'][partition]['trials_per_family'])]
    expected_summary = _independent_summary(design, partition, expected_rows)
    manifest = _manifest(result_directory)
    observed_rows = [json.loads(line) for line in
                     (result_directory/'trials.jsonl').read_text().splitlines()]
    observed_summary = json.loads((result_directory/'summary.json').read_text())
    _check_claims(observed_rows)
    _check_claims(observed_summary)
    _compare(expected_rows, observed_rows, 'trials')
    _compare(expected_summary, observed_summary, 'summary')
    result = {
        'status': 'VERIFIED', 'valid': True, 'independent_recomputation': True,
        'verifier_id': 'INDEPENDENT_RAW_RECONSTRUCTION_V1',
        'partition': partition, 'design_sha256': digest,
        'external_design_hash_supplied': expected_design_sha256 is not None,
        'raw_scientific_ids_verified': len(expected_rows),
        'independent_calculation_rows': len(expected_rows),
        'independently_recomputed_null_children': expected_summary['null_children'],
        'source_manifest': manifest,
        'independent_summary': expected_summary,
        'production_outputs_opened_after_reconstruction': True,
        'shared_assumptions': ['audited raw generator and NumPy PCG64/SeedSequence',
                               'registered physical and sampling contracts',
                               'independent experiments in the specified synthetic model'],
        'independent_implementations': ['scalar atan2 phase increments',
                                       'explicit Lagrange derivatives and complete support',
                                       'direct single-bin DFT and analytic phase-surrogate action',
                                       'raw byte scientific ID',
                                       'integer-combination binomial inversion',
                                       'count/coverage/abstention and claim adjudication'],
        'limitations': ['Shared generator means independent model validity is not established',
                        'Hash agreement does not prove source freshness or lack of prior exposure',
                        'Verification by the same project is not independent external replication'],
        'EXTERNALLY_VALIDATED': False,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(_json_bytes(result))
    return result
