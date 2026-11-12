import pytest

from kessel_training.inspect_prerequisites import observation_aliases, stage_environment, stage_probe


def test_unobserved_geometry_changes_do_not_invent_sensor_measurements():
    rows = observation_aliases()
    assert all(r['initial_valid'] and r['same_initial_observation'] for r in rows)
    assert len({r['scenario_sha256'] for r in rows}) == 3


def test_prepared_stage_payload_is_explicit_and_conserved():
    for stage, expected in [('fill', 0), ('retract', 1500), ('carry', 2200), ('complete', 0)]:
        env = stage_environment(stage, 100000)
        assert env.payload[0] == expected
        env._assert_finite()
    with pytest.raises(ValueError):
        stage_environment('invented', 100000)


def test_stage_initialised_reference_retracts_without_claiming_a_full_cycle():
    result = stage_probe('retract', 100000)
    assert result['initial_payload_kg'] == 1500
    assert result['prepared_start'] and result['stage_success']
    assert not result['full_success']
    assert result['delivered_kg'] == 0
    assert result['max_mass_residual_kg'] < 1e-7
