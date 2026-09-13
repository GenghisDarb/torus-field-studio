import json
from pathlib import Path

import numpy as np
from torusbrot.research.generators import generate_trial

DESIGN = json.loads((Path(__file__).resolve().parents[1] /
                     'studies/v0.4.0/reviewed/calibration/design.json').read_text())


def test_generator_partitions_and_typed_truth():
    for family in DESIGN['families']:
        first = generate_trial(DESIGN, 'DEVELOPMENT', family, 0)
        same = generate_trial(DESIGN, 'DEVELOPMENT', family, 0)
        # Sealed outcomes deliberately NOT generated during development tests.
        next_trial = generate_trial(DESIGN, 'DEVELOPMENT', family, 1)
        assert first['seed'] != next_trial['seed']
        for key, value in first['arrays'].items():
            assert np.array_equal(value, same['arrays'][key])
        assert first['truth']
