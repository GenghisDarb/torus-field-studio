"""Raw generator bank for the frozen, finite observable benchmark.

Generator code supplies arrays and truth only, never a production score. The sealed
partition uses different seeds, sample sizes, phase sampling, and amplitude modulation.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def generate_trial(design: dict, partition: str, family: str, trial: int) -> dict[str, Any]:
    if partition not in design['partitions'] or family not in design['families']:
        raise ValueError('UNREGISTERED_GENERATOR_ID')
    config = design['partitions'][partition]
    if not 0 <= trial < config['trials_per_family']:
        raise ValueError('UNREGISTERED_TRIAL')
    seed = [config['seed_root'], design['families'].index(family), trial]
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed)))
    sealed = partition == 'SEALED_SYNTHETIC_VALIDATION'
    out: dict[str, Any] = {'family': family, 'trial': trial, 'seed': seed,
                           'partition': partition, 'arrays': {}, 'truth': {}}
    if family.startswith('winding'):
        count = int(rng.choice([48, 80, 112] if sealed else [32, 64, 96]))
        theta = np.arange(count) * 2 * np.pi / count
        if sealed:
            theta += 0.15 * np.sin(theta)  # strictly ordered, nonuniform angular grid
        offset = rng.uniform(-np.pi, np.pi)
        amplitude = rng.uniform(0.8, 1.5) * np.ones(count)
        w = -1 if family == 'winding_negative' else 1
        if family in ('winding_zero', 'winding_pair_cancel'):
            w = 0
        phase = theta * w + offset
        if family == 'winding_zero':
            phase = 0.6 * np.sin(theta) + offset
        elif family == 'winding_pair_cancel':
            # Two opposite-charge singularities inside the registered unit circle.
            field = (np.exp(1j * theta) - .2) * np.conj(np.exp(1j * theta) + .2j)
            phase = np.angle(field) + offset
        if family == 'winding_amplitude':
            amplitude *= 1 + .25 * np.cos((3 if sealed else 2) * theta)
        noise_bound = .025
        noise = rng.uniform(0, noise_bound, count) * np.exp(1j * rng.uniform(-np.pi, np.pi, count))
        z = amplitude * np.exp(1j * phase) + noise
        mask = np.ones(count, dtype=bool)
        valid = family not in ('winding_mask', 'winding_zero_amplitude',
                               'winding_branch_ambiguous')
        if family == 'winding_mask':
            mask[count // 3] = False
        if family == 'winding_zero_amplitude':
            z[count // 3] = 0
        if family == 'winding_branch_ambiguous':
            z[1] = -z[0]  # boundary of the branch; cannot assert a unique unwrapping
        out['arrays'] = {'complex_field': z, 'mask': mask, 'theta': theta}
        out['truth'] = {'winding': w if valid else None, 'must_abstain': not valid,
                        'amplitude_noise_bound': noise_bound, 'sampling_admissible': valid}
    elif family.startswith('temporal'):
        count = design['temporal']['segment_length']
        segments = design['temporal']['segment_count']
        x = rng.normal(size=(segments, count))
        epsilon = rng.normal(size=(segments, count))
        if 'colored' in family:
            # Circular FIR within independent segments preserves stationarity there.
            x = x + .5 * np.roll(x, 1, axis=1)
            epsilon = epsilon + .5 * np.roll(epsilon, 1, axis=1)
        coherent = family.endswith('coherent') and not family.endswith('independent')
        rho = design['temporal']['rho_alternative'] if coherent else 0
        # Fixed all-pass phase action on positive frequencies: jointly stationary
        # Gaussian segments, no within-trial parameter fitting or outcome selection.
        spectrum = np.fft.rfft(x, axis=1)
        shifted = spectrum * np.exp(1j * design['temporal']['phase_lag_radians'])
        shifted[:, 0] = spectrum[:, 0]
        shifted[:, -1] = spectrum[:, -1]
        y = rho * np.fft.irfft(shifted, n=count, axis=1) + np.sqrt(1-rho**2) * epsilon
        dt = (.04 if sealed else .05)
        out['arrays'] = {'x': x.ravel(), 'y': y.ravel(),
                         'time': np.arange(count * segments) * dt}
        out['truth'] = {'structure': coherent, 'rho': rho, 'independent_segments': segments,
                        'time_step': dt, 'phase_lag': design['temporal']['phase_lag_radians']}
    else:
        count = int(rng.choice([11, 17] if sealed else [9, 13]))
        x = np.linspace(-2, 3, count) * rng.uniform(.7, 1.4)
        y = np.linspace(-1, 1, count) * rng.uniform(.7, 1.4)
        if sealed:
            x += .1 * np.sin(x)
            y += .05 * np.sin(y)
        xx, yy = np.meshgrid(x, y)
        coefficient = rng.uniform(.5, 2) * rng.choice([-1, 1])
        u, v = -coefficient * yy, coefficient * xx
        curl = 2 * coefficient
        if family in ('vector_constant', 'vector_hole'):
            u, v = np.full_like(xx, coefficient), np.zeros_like(xx)
            curl = 0.0
        elif family == 'vector_shear':
            u, v = coefficient * yy, np.zeros_like(xx)
            curl = -coefficient
        mask = np.ones_like(xx, dtype=bool)
        if family == 'vector_hole':
            mask[count // 2, count // 2] = False
        out['arrays'] = {'x_coordinate': x, 'y_coordinate': y,
                         'values': np.stack([u, v], axis=-1), 'mask': mask}
        out['truth'] = {'curl': curl, 'divergence': 0.0,
                        'coordinate_unit': 'm', 'velocity_unit': 'm/s'}
    return out
