import numpy as np
import pytest
import torch
from kessel_training.controller import ReferenceController
from kessel_training.environment import LoaderEnv
from kessel_training.phase_memory import PhaseMemory,PhaseActor,features
from kessel_training.phase_study import fit,episode,load_actor
from kessel_training.scenarios import family
from kessel_training.policy import configure_cpu


def test_memory_matches_reference_on_complete_observed_trajectory():
    env=LoaderEnv(1,seed=108000,scene=family('standard')[0]);control=ReferenceController(1);memory=PhaseMemory()
    while True:
        obs=env.observe();action=control.act(obs)
        np.testing.assert_array_equal(memory.update(obs),control.phase)
        _,_,t,x,_=env.step(action)
        if (t|x).any():break
    assert env.reason[0]=='success' and memory.phase[0]==4


def test_masked_phase_cannot_affect_memoryless_actions_and_initial_weights_match():
    configure_cpu(7);a=PhaseActor(False)
    configure_cpu(7);b=PhaseActor(True)
    for k,v in a.state_dict().items():torch.testing.assert_close(v,b.state_dict()[k],rtol=0,atol=0)
    local=features(LoaderEnv(1,seed=7).observe())
    torch.testing.assert_close(a(local,torch.tensor([0])),a(local,torch.tensor([4])),rtol=0,atol=0)
    assert not torch.equal(b(local,torch.tensor([0])),b(local,torch.tensor([4])))


def test_evaluation_has_no_teacher_queries(monkeypatch):
    configure_cpu(7);actor=PhaseActor()
    monkeypatch.setattr(ReferenceController,'act',lambda *_:pytest.fail('teacher queried in evaluation'))
    result=episode(108100,actor,record=True)
    assert result['case']['steps']>0 and len(result['records'])==result['case']['steps']
    assert result['data']==[]


def test_fit_resume_preserves_weights_and_generator(tmp_path):
    local=features(LoaderEnv(1,seed=7).observe())[0].tolist()
    data=[{'features':local,'action':[.2,0,.1,-.2],'phase':i} for i in range(5)]
    a=fit(tmp_path/'a','phase_memory',7,0,data,updates=3)
    b=fit(tmp_path/'b','phase_memory',7,0,data,updates=3)
    # A completed fit resumes idempotently without optimiser work.
    again=fit(tmp_path/'b','phase_memory',7,0,data,updates=3)
    pa,sa=load_actor(a);pb,sb=load_actor(again)
    for k,v in pa.state_dict().items():torch.testing.assert_close(v,pb.state_dict()[k],rtol=0,atol=0)
    assert sa['losses']==sb['losses']
    with pytest.raises(ValueError,match='identity'):
        fit(tmp_path/'b','phase_memory',7,0,data,updates=4)


def test_interrupted_optimiser_transaction_resumes_exactly(tmp_path):
    local=features(LoaderEnv(1,seed=7).observe())[0].tolist()
    data=[{'features':local,'action':[.2,0,.1,-.2],'phase':i} for i in range(5)]
    a=fit(tmp_path/'a','phase_memory',7,0,data,updates=500)
    def interrupt(_):raise InterruptedError('transaction')
    with pytest.raises(InterruptedError):fit(tmp_path/'b','phase_memory',7,0,data,updates=500,on_checkpoint=interrupt)
    b=fit(tmp_path/'b','phase_memory',7,0,data,updates=500)
    pa,sa=load_actor(a);pb,sb=load_actor(b)
    for k,v in pa.state_dict().items():torch.testing.assert_close(v,pb.state_dict()[k],rtol=0,atol=0)
    assert sa['losses']==sb['losses']
    torch.testing.assert_close(sa['generator'],sb['generator'],rtol=0,atol=0)


def test_teacher_calls_and_fallback_forbidden_on_final_cases():
    with pytest.raises(ValueError,match='training scenes'):episode(209800,PhaseActor(),collect=True)
    with pytest.raises(ValueError,match='no reference fallback'):episode(209800)
