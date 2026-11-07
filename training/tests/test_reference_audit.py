from dataclasses import replace
import numpy as np
import pytest
from kessel_training.environment import LoaderEnv, SceneConfig
from kessel_training.reference_audit import initial_status, trace
from kessel_training.scenarios import family


def test_reference_trace_replays_actions_and_conserves_each_transfer():
    result=trace(family('standard')[0])
    assert result['outcome']=='success' and not result['learned_policy']
    assert result['independent_max_state_error']<1e-10
    assert result['max_mass_residual_kg']<1e-7
    assert {'loaded_kg','delivered_kg','success'} <= {e['kind'] for e in result['events']}
    assert all(e['t_s']>0 for e in result['events'] if e['kind'].endswith('_kg'))


def test_pile_families_repeat_and_conserve_their_declared_integral():
    shapes=[]
    for name in ('legacy','low','ridge','rubble','steep'):
        a=LoaderEnv(1,seed=7,scene=SceneConfig(pile_family=name));b=LoaderEnv(1,seed=7,scene=SceneConfig(pile_family=name))
        np.testing.assert_array_equal(a.pile.height,b.pile.height)
        assert np.all(a.pile.height>=0)
        assert abs(a.pile.mass()[0]-a.pile.initial_mass[0])<1e-8
        shapes.append(a.pile.height.copy())
    assert all(not np.array_equal(shapes[0],s) for s in shapes[1:])
    with pytest.raises(ValueError):SceneConfig(pile_family='invented')


def test_invalid_start_is_classified_before_any_action():
    env=LoaderEnv(1,scene=SceneConfig(obstacles=((-1,1,-1,1),)))
    assert initial_status(env)[0]['classification']=='invalid_start'
    assert env.steps[0]==0
    result=trace(env.scene)
    assert result['outcome']=='invalid_start' and not result['records']
