import math

import numpy as np
import pytest

from kessel_training.contracts import LoaderConfig, canonical_json, physical_to_three, validate_actions


def test_coordinate_basis_preserves_direction_and_handedness():
    basis = physical_to_three(np.eye(3))
    np.testing.assert_array_equal(basis[0], [1, 0, 0])
    np.testing.assert_array_equal(basis[2], [0, 1, 0])
    np.testing.assert_array_equal(np.cross(basis[0], basis[1]), basis[2])
    assert np.linalg.det(basis) == 1


@pytest.mark.parametrize("actions", [[[0, 0, 0]], [[0, 0, 0, 1.01]], [[0, math.nan, 0, 0]], [[math.inf, 0, 0, 0]]])
def test_invalid_actions_are_rejected(actions):
    with pytest.raises(ValueError):
        validate_actions(actions, 1)


def test_signed_controls_and_bounds_are_preserved():
    np.testing.assert_array_equal(validate_actions([[-1, 1, 0, 0]], 1), [[-1, 1, 0, 0]])


@pytest.mark.parametrize("kwargs", [{"substeps": 0}, {"substeps": 1.5}, {"payload_kg": -1}, {"decision_s": math.nan}, {"boom_max_rad": -0.2}])
def test_invalid_physical_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        LoaderConfig(**kwargs)


def test_configuration_hash_and_finite_json():
    assert LoaderConfig().physical_step_s == 0.02
    assert LoaderConfig().digest() != LoaderConfig(payload_kg=100).digest()
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})
    with pytest.raises(ValueError):
        canonical_json({"x": math.nan})
