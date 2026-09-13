from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from torusbrot.research.benchmark import run_benchmark
from torusbrot.research.contracts import exact_upper
from torusbrot.research.generators import generate_trial
from torusbrot.research.verify import (
    _check_design,
    _compare,
    _upper,
    independent_derivatives,
    independent_scientific_id,
    reconstruct_trial,
    verify_benchmark,
)


@pytest.fixture(scope='module')
def bank(tmp_path_factory):
    directory = tmp_path_factory.mktemp('independent-verifier')
    source = Path(__file__).resolve().parents[1]/'studies/v0.4.0/reviewed/calibration/design.json'
    design = json.loads(source.read_text())
    design['partitions']['DEVELOPMENT']['trials_per_family'] = 1
    path = directory/'design.json'
    path.write_text(json.dumps(design), encoding='utf-8')
    output = directory/'development'
    run_benchmark(path, 'DEVELOPMENT', output)
    return path, output, design


def _reseal(output):
    # An attacker can recompute local hashes. Scientific reconstruction still
    # must reject manipulated scores, unlike a manifest-only checker.
    content = ''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n'
                      for p in sorted(output.iterdir()) if p.name != 'SHA256SUMS.txt')
    (output/'SHA256SUMS.txt').write_text(content, encoding='utf-8')


def test_verifier_reconstructs_after_production_scoring_disabled(bank, monkeypatch):
    import torusbrot.metrology.v1 as metrology
    import torusbrot.phase.v2 as phase
    import torusbrot.research.benchmark as benchmark

    def forbidden(*args, **kwargs):
        raise AssertionError('Production scientific implementation was called by verifier')

    for module, names in [(benchmark, ['score_trial', 'summarize']),
                          (metrology, ['derivatives']),
                          (phase, ['sampled_winding', 'temporal_cross_spectrum',
                                   'segment_phase_surrogate'])]:
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    path, output, _ = bank
    result = verify_benchmark(path, output, None)
    assert result['status'] == 'VERIFIED'
    assert result['raw_scientific_ids_verified'] == 16
    assert result['independently_recomputed_null_children'] == 4*63
    assert result['EXTERNALLY_VALIDATED'] is False


@pytest.mark.parametrize('mutation', [
    'wrong_raw_hash', 'pure_link_as_winding', 'wrong_threshold', 'null_child_count',
    'zero_filled_hole', 'local_gauge_invariance', 'zero_phase_filled', 'negative_omitted',
    'phase_uncertainty_as_sampling_ci', 'null_pooling', 'frames_as_parents',
    'external_validation', 'always_abstain_success', 'wrong_units', 'winner_N_collision',
])
def test_resealed_scientific_mutations_are_rejected(bank, tmp_path, mutation):
    path, source, _ = bank
    output = tmp_path/'mutation'
    shutil.copytree(source, output)
    rows = [json.loads(line) for line in (output/'trials.jsonl').read_text().splitlines()]
    summary = json.loads((output/'summary.json').read_text())
    by_family = {row['family']: row for row in rows}
    if mutation == 'wrong_raw_hash':
        rows[0]['raw_scientific_id'] = '0'*64
    elif mutation == 'pure_link_as_winding':
        by_family['winding_positive']['measurement']['winding'] = 0
    elif mutation == 'wrong_threshold':
        by_family['temporal_independent']['measurement']['threshold'] = .8
    elif mutation == 'null_child_count':
        by_family['temporal_independent']['null_children'] += 1
    elif mutation == 'zero_filled_hole':
        row = by_family['vector_hole']['measurement']
        row['supported_cells'] = row['cells']-1
    elif mutation == 'local_gauge_invariance':
        by_family['winding_positive']['measurement']['arbitrary_local_gauge_invariant'] = True
    elif mutation == 'zero_phase_filled':
        by_family['winding_zero_amplitude']['measurement']['winding'] = 1
    elif mutation == 'negative_omitted':
        rows = [row for row in rows if row['family'] != 'winding_negative']
    elif mutation == 'phase_uncertainty_as_sampling_ci':
        by_family['temporal_independent']['null_quantiles_kind'] = 'POPULATION_CONFIDENCE_INTERVAL'
    elif mutation == 'null_pooling':
        by_family['temporal_independent']['null_values'].reverse()
    elif mutation == 'frames_as_parents':
        summary['independent_trials'] *= 1024
    elif mutation == 'external_validation':
        summary['EXTERNALLY_VALIDATED'] = True
    elif mutation == 'always_abstain_success':
        for group in summary['families']:
            group['coverage'] = 0
            group['gate_pass'] = True
    elif mutation == 'wrong_units':
        by_family['vector_solid_rotation']['measurement']['unit'] = 'mm/s'
    elif mutation == 'winner_N_collision':
        by_family['temporal_coherent']['winner_N'] = 14
    (output/'trials.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    (output/'summary.json').write_text(json.dumps(summary))
    _reseal(output)
    with pytest.raises(ValueError,
                       match='SCIENTIFIC_MISMATCH|CLAIM_ESCALATION|UNREGISTERED_ENDPOINT'):
        verify_benchmark(path, output, None)


def test_wrong_manifest_rejected_and_expectations_not_rewritten(bank, tmp_path):
    path, source, _ = bank
    output = tmp_path/'corrupt'
    shutil.copytree(source, output)
    manifest_before = (output/'SHA256SUMS.txt').read_bytes()
    with (output/'trials.jsonl').open('a') as stream:
        stream.write('{}\n')
    with pytest.raises(ValueError, match='SOURCE_HASH_MISMATCH'):
        verify_benchmark(path, output, None)
    assert (output/'SHA256SUMS.txt').read_bytes() == manifest_before


def test_relocation_and_json_serialization_do_not_change_scientific_result(bank, tmp_path):
    path, source, _ = bank
    output = tmp_path/'relocated'
    shutil.copytree(source, output)
    moved_design = tmp_path/'moved_design.json'
    shutil.copyfile(path, moved_design)
    result = verify_benchmark(moved_design, output, None)
    assert result['status'] == 'VERIFIED'
    raw = json.loads((output/'summary.json').read_text())
    (output/'summary.json').write_text(json.dumps(raw, sort_keys=True, indent=4))
    _reseal(output)
    assert verify_benchmark(moved_design, output, None)['status'] == 'VERIFIED'


def test_design_reseal_cannot_override_external_freeze(bank, tmp_path):
    path, source, _ = bank
    output = tmp_path/'resealed'
    shutil.copytree(source, output)
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    design = json.loads(path.read_text())
    design['temporal']['false_alarm_alpha'] = .05
    altered = tmp_path/'design.json'
    altered.write_text(json.dumps(design))
    receipt = json.loads((output/'access_receipt.json').read_text())
    receipt['design_sha256'] = hashlib.sha256(altered.read_bytes()).hexdigest()
    (output/'access_receipt.json').write_text(json.dumps(receipt))
    _reseal(output)
    with pytest.raises(ValueError, match='EXPECTATION_MISMATCH_NO_RESEAL'):
        verify_benchmark(altered, output, None, expected_design_sha256=expected)


@pytest.mark.parametrize('change', ['operator', 'bank_reuse', 'nulls_as_trials',
                                    'wrong_multiplicity'])
def test_registered_contract_mutations_rejected(bank, change):
    design = copy.deepcopy(bank[2])
    if change == 'operator':
        design['winding']['operator'] = 'phase.v1.u1_plaquette_metrics'
    elif change == 'bank_reuse':
        design['partitions']['SEALED_SYNTHETIC_VALIDATION']['seed_root'] = (
            design['partitions']['CALIBRATION']['seed_root'])
    elif change == 'nulls_as_trials':
        design['confidence']['null_children_are_trials'] = True
    else:
        design['confidence']['allocated_bounds'] = 1
    with pytest.raises(ValueError):
        _check_design(design)


def test_independent_raw_identity_byte_exact_but_unit_semantics_separate():
    array = np.array([1., 2.])
    little = independent_scientific_id({'unit': 'm'}, {'x': array})
    big = independent_scientific_id({'unit': 'm'}, {'x': array.astype('>f8')})
    assert little == big
    assert little != independent_scientific_id({'unit': 'mm'}, {'x': array*1000})
    assert little != independent_scientific_id({'unit': 'm'}, {'x': np.nextafter(array, 3)})


def test_independent_derivatives_accept_equivalent_units_and_spatial_transforms():
    x, y = np.arange(5)*2., np.arange(5)*.5
    xx, yy = np.meshgrid(x, y)
    velocity = np.stack([-yy, xx], axis=-1)
    mask = np.ones(xx.shape, dtype=bool)
    curl, div, support = independent_derivatives(velocity, x, y, mask)
    assert np.allclose(curl[support], 2)
    assert np.allclose(div[support], 0)
    converted = independent_derivatives(velocity*1000, x*1000, y*1000, mask)[0]
    assert np.allclose(converted, curl)
    reflected = velocity.copy()
    reflected[..., 1] *= -1
    reflection = independent_derivatives(reflected, x, -y, mask)[0]
    assert np.allclose(reflection, -curl)
    moved = np.swapaxes(velocity, 0, 1)
    rotated = np.stack([-moved[..., 1], moved[..., 0]], axis=-1)
    rotation = independent_derivatives(rotated, -y, x, mask.T)[0]
    assert np.allclose(rotation, curl.T)
    omitted = independent_derivatives(moved, -y, x, mask.T)[0]
    assert not np.allclose(omitted, curl.T)


def test_independent_counterexample_rejects_missing_spacing_and_zero_fill():
    x, y = np.arange(5)*2., np.arange(5)*.5
    xx, yy = np.meshgrid(x, y)
    field = np.stack([-yy, xx], axis=-1)
    mask = np.ones(xx.shape, dtype=bool)
    correct = independent_derivatives(field, x, y, mask)[0]
    index = independent_derivatives(field, np.arange(5), np.arange(5), mask)[0]
    assert np.allclose(correct, 2)
    assert np.allclose(index, 2.5)
    constant = np.stack([np.ones_like(xx), np.zeros_like(xx)], axis=-1)
    mask[2, 2] = False
    _, _, support = independent_derivatives(constant, x, y, mask)
    assert not support[2, 1] and not support[1, 2]
    filled = constant.copy()
    filled[2, 2] = 0
    fabricated = independent_derivatives(filled, x, y, np.ones_like(mask))[0]
    assert np.max(abs(fabricated)) > 0


@pytest.mark.parametrize('n,k', [(20, 0), (59, 0), (128, 2), (512, 5), (512, 511)])
def test_independent_interval_inversion_and_finite_precision(n, k):
    assert _upper(k, n, .05) == pytest.approx(exact_upper(k, n, .05), abs=1e-12)
    if n == 20:
        assert _upper(k, n, .05) > .05
    if n == 59:
        assert _upper(k, n, .05) < .05


def test_truth_fabrication_is_rejected_from_raw_generator_model(bank):
    design = bank[2]
    raw = generate_trial(design, 'DEVELOPMENT', 'winding_negative', 0)
    raw['truth']['winding'] = 14
    with pytest.raises(ValueError, match='TRUTH_MISMATCH'):
        reconstruct_trial(design, raw)
    with pytest.raises(ValueError, match='boolean'):
        _compare({'correct': True}, {'correct': 1})
