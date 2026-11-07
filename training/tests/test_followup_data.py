import numpy as np
from kessel_training.environment import LoaderEnv
from kessel_training.followup_data import SensorEnv,SensorProfile,collect_targeted,coverage,setup_episode
from kessel_training.wm_state import pack


def test_communications_cannot_change_observations_or_physics():
    a=SensorEnv(LoaderEnv(2,seed=7),SensorProfile(2,.25,.1,.02,False));b=SensorEnv(LoaderEnv(2,seed=7),SensorProfile(2,.25,.1,.02,True))
    for _ in range(8):
        a.step(np.tile([.2,0,0,0],(2,1)));b.step(np.tile([.2,0,0,0],(2,1)))
        np.testing.assert_array_equal(pack(a),pack(b))
        for key in a.observe():np.testing.assert_array_equal(a.observe()[key],b.observe()[key])


def test_delayed_range_is_masked_until_available_and_reset_does_not_leak():
    env=SensorEnv(LoaderEnv(2),SensorProfile(range_latency_steps=2))
    assert not env.observe()['range_valid'].any()
    env.step(np.zeros((2,4)));assert not env.observe()['range_valid'].any()
    env.step(np.zeros((2,4)));assert env.observe()['range_valid'].all();assert (env.observe()['proprio'][:,11]>=.19).all()
    env.reset(mask=np.array([True,False]));assert not env.observe()['range_valid'][0].any();assert env.observe()['range_valid'][1].all()


def test_targeted_prepared_delivery_is_explicit_and_conserves_initial_material():
    env,_,identity=setup_episode('train',4,'prepared_delivery')
    assert identity['prepared_start'] and identity['initial_payload_kg']==2200
    env.base._assert_finite()
    rows,episodes=collect_targeted('train',20);report,weights=coverage(rows)
    assert len(rows['reward'])==20 and len(weights)==20 and np.isfinite(weights).all()
    assert all(e['split']=='train' and e['seed']<100000 for e in episodes)
