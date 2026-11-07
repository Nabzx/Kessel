import numpy as np
import torch
from kessel_training.followup_data import collect_targeted
from kessel_training.followup_models import fit_state,fit_observable,fit_events
from kessel_training.followup_world_study import event_thresholds,event_report
from kessel_training.policy import configure_cpu


def test_boundary_aware_multistep_material_backward_is_finite():
    configure_cpu(101)
    train,episodes=collect_targeted('train',100,kinds=('contact_static','spill','prepared_delivery'))
    val,_=collect_targeted('validation',32,kinds=('contact_static',))
    model,report=fit_state(train,val,episodes,material=True,multistep=True,epochs=1)
    assert report['horizons_trained']==[1,2,4] and report['optimiser_updates']>0
    prediction=model.predict(val['state'],val['action'])
    assert np.isfinite(prediction['next_state']).all()
    assert all(i< len(episodes) for b in report['episode_bootstraps'] for i in b['episode_draws'])


def test_observable_model_has_no_privileged_state_input_and_finite_masked_loss():
    configure_cpu(101);train,_=collect_targeted('train',64,kinds=('impaired_range',));val,_=collect_targeted('validation',24)
    model,report=fit_observable(train,val,epochs=1)
    assert model.net[0].in_features==69 and report['normalisers_fitted_on']=='training_only'
    pred=model.predict(val['observation'],val['action'])
    assert pred['observation'].shape==(24,65) and np.isfinite(pred['observation']).all()
    modified=dict(train);modified['state']=train['state']+1000
    other,_=fit_observable(modified,val,epochs=1)
    for k,v in model.state_dict().items():torch.testing.assert_close(v,other.state_dict()[k],rtol=0,atol=0)


def test_event_thresholds_use_validation_and_report_false_safe_cases():
    configure_cpu(211);train,ep=collect_targeted('train',64,kinds=('stuck','blocked'));model,_=fit_events(train,epochs=1)
    probabilities=model.predict(train['state'],train['action']);thresholds=event_thresholds(probabilities,train['event_targets'])
    report=event_report(probabilities,train,ep,thresholds)
    assert report['collision']['threshold_split']=='validation' and report['stop_tradeoff']['rows']==64
