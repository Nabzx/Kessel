from kessel_training.audit_demo_frontier import scan_seed_references, sensor_probe
import numpy as np


def test_missing_seed_metadata_does_not_certify_a_fresh_reservation(tmp_path):
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data/used.json').write_text('{"seed": 209900}')
    result = scan_seed_references(tmp_path)
    assert result['candidates']['final_test']['explicit_reference_hits']
    assert not result['candidates']['validation']['reservation_verified']


def test_sensor_dropout_preserves_fixed_actions_but_not_observations():
    clean, clean_states, clean_obs = sensor_probe({}, False)
    dropped, dropped_states, dropped_obs = sensor_probe({'dropout': 1.0}, True)
    np.testing.assert_array_equal(clean_states, dropped_states)
    assert not np.array_equal(clean_obs, dropped_obs)
    assert clean['valid_samples'] == 1600 and dropped['valid_samples'] == 0
