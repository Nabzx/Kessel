import numpy as np
import torch
from kessel_training.followup_study import teacher_pairs,warm_start,save_policy,load_policy,score
from kessel_training.policy import ActorCritic,configure_cpu


def test_teacher_budget_contains_only_training_pairs_and_is_repeatable():
    a,episodes=teacher_pairs(24);b,_=teacher_pairs(24)
    assert a['observation'].shape==(24,65) and a['action'].shape==(24,4)
    assert sum(e['rows'] for e in episodes)==24 and all(e['split']=='train' and e['seed']<100000 for e in episodes)
    for key in a:np.testing.assert_array_equal(a[key],b[key])


def test_reference_warm_start_counts_unique_and_reused_pairs_separately():
    configure_cpu(7);policy=ActorCritic(8);data,_=teacher_pairs(24)
    report=warm_start(policy,data,7,updates=2)
    assert report['unique_reference_pairs']==24 and report['reused_training_pairs']==512
    assert np.isfinite(report['last_mse'])


def test_followup_checkpoint_roundtrip_preserves_architecture_and_identity(tmp_path):
    configure_cpu(7);policy=ActorCritic(8);path=tmp_path/'policy.pt'
    digest=save_policy(path,policy,{'git_commit':'test'},'ppo',7,0,{'online_reference_decisions':0})
    loaded,identity=load_policy(path)
    assert identity['architecture']=='local65' and len(digest)==64
    for a,b in zip(policy.parameters(),loaded.parameters()):torch.testing.assert_close(a,b)
