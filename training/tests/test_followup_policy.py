import numpy as np
import torch
from kessel_training.environment import LoaderEnv
from kessel_training.followup_policy import HistoryEnv,HistoryActorCritic,CurriculumBridge,flat
from kessel_training.policy import configure_cpu
from kessel_training.ppo import collect,PPO,PPOConfig


def test_history_advances_once_in_environment_and_resets_only_selected_slots():
    env=HistoryEnv(LoaderEnv(2));model=HistoryActorCritic(16);initial=flat(env.base.observe())
    assert not env.previous.any()
    env.step([[.2,0,0,0],[.2,0,0,0]])
    np.testing.assert_array_equal(env.previous,initial)
    a=model.encode(env.observe());b=model.encode(env.observe());torch.testing.assert_close(a,b)
    previous=env.previous.copy();env.reset(mask=np.array([True,False]));assert not env.previous[0].any();np.testing.assert_array_equal(env.previous[1],previous[1])


def test_history_ppo_uses_130_features_and_finite_updates():
    generator=configure_cpu(7);env=HistoryEnv(LoaderEnv(2));policy=HistoryActorCritic(16)
    rollout=collect(env,policy,4,generator)
    assert rollout.features.shape==(4,2,130)
    stats=PPO(policy,PPOConfig(epochs=1,minibatch=8)).update(rollout,generator)
    assert all(torch.isfinite(p).all() for p in policy.parameters())


def test_training_success_cannot_bypass_failed_heldout_retention():
    bridge=CurriculumBridge();episodes=[{'stage':'carry','stage_success':True} for _ in range(32)]
    report={s:{'valid_starts':True,'evaluations':2,'success_rate':1} for s in ['fill','retract','carry']}
    report['fill']['success_rate']=0
    assert not bridge.gate('carry',episodes,report)['passed']
    report['fill']['success_rate']=1
    assert bridge.gate('carry',[],report)['passed']
