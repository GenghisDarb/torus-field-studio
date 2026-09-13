import math

import numpy as np
import pytest
from torusbrot.research.contracts import exact_lower, exact_upper, scientific_id, zero_error_trials


def test_exact_zero_error_feasibility():
    assert zero_error_trials(0.05, 0.05) == 59
    assert exact_upper(0, 20) > 0.05
    assert exact_upper(0, 59) <= 0.05
    assert exact_upper(0, 512, 0.05 / 32) < 0.05
    assert zero_error_trials(0.05, 0.05 / 32) == 126


def test_binomial_inversion_and_duality():
    # For one success in two trials: F(1;2,p)=1-p^2.
    assert exact_upper(1, 2, 0.05) == pytest.approx(math.sqrt(0.95))
    assert exact_lower(2, 2, 0.05) == pytest.approx(math.sqrt(0.05))
    assert exact_upper(2, 2) == 1
    with pytest.raises(ValueError):
        exact_upper(0, 0)


def test_portable_semantic_array_identity():
    values = np.array([1.0, 2.0], dtype='<f8')
    assert scientific_id({'operator': 'v1'}, {'x': values}) == scientific_id(
        {'operator': 'v1'}, {'x': values.astype('>f8')})
    assert scientific_id({'operator': 'v1'}, {'x': values}) != scientific_id(
        {'operator': 'v1'}, {'x': values + 1})
    assert scientific_id({'operator': 'v1'}, {'x': values}) != scientific_id(
        {'operator': 'v2'}, {'x': values})
