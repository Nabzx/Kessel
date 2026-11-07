"""Bounded world-model follow-up with retained raw failures and charged data."""
import argparse
from dataclasses import asdict,replace
import json
from pathlib import Path
import time
import numpy as np
import torch
from . import checkpoints
from .controller import ReferenceController
from .constrained_model import ConstrainedModel,FilterConfig
from .evaluate import source_identity
from .followup_data import SensorProfile,SensorEnv,collect_targeted,coverage,save_data,setup_episode,EVENTS
from .followup_models import fit_state,fit_observable,fit_events
from .followup_study import evaluate
from .imagination import admissibility
from .model_assisted import ModelAssistedTrainer
from .policy import configure_cpu
from .train import TrainConfig,Trainer
from .wm_evaluate import metrics,open_loop,calibrate,gate_report,simple_prediction,errors
from .world_model import save_model


def write(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def event_thresholds(probability,truth):
    thresholds=[]
    for j in range(len(EVENTS)):
        choices=[]
        for threshold in np.linspace(.05,.95,19):
            pred=probability[:,j]>=threshold;actual=truth[:,j].astype(bool);tp=int((pred&actual).sum());fp=int((pred&~actual).sum());fn=int((~pred&actual).sum())
            choices.append((2*tp/max(1,2*tp+fp+fn),float(threshold)))
        thresholds.append(max(choices)[1])
    return thresholds


def event_report(probability,arrays,episodes,thresholds):
    result={};targets=arrays['event_targets'].astype(bool)
    for j,name in enumerate(EVENTS):
        p=probability[:,j];pred=p>=thresholds[j];actual=targets[:,j];tp=int((pred&actual).sum());fp=int((pred&~actual).sum());fn=int((~pred&actual).sum());timing=[]
        for episode in episodes:
            sl=slice(episode['start'],episode['stop']);a=np.flatnonzero(actual[sl]);b=np.flatnonzero(pred[sl])
            timing.append({'episode':episode['id'],'kind':episode['kind'],'actual_first_step':int(a[0]) if len(a) else None,'predicted_first_step':int(b[0]) if len(b) else None,'timing_error_s':float((b[0]-a[0])*.1) if len(a) and len(b) else None})
        result[name]={'threshold':thresholds[j],'threshold_split':'validation','actual':int(actual.sum()),'predicted':int(pred.sum()),'true_positive':tp,'false_positive':fp,'false_negative':fn,'precision':tp/max(1,tp+fp),'recall':tp/max(1,tp+fn),'brier':float(np.mean((p-actual)**2)),'timing':timing}
    danger=targets[:,1]|targets[:,3];stop=(probability[:,1]>=thresholds[1])|(probability[:,3]>=thresholds[3])
    result['stop_tradeoff']={'false_safe':int((danger&~stop).sum()),'conservative_false_stop':int((~danger&stop).sum()),'rows':len(danger)}
    return result


def reliability(model,validation,test,gate):
    v=model.predict(validation['state'],validation['action']);p=model.predict(test['state'],test['action']);ve=errors(v,validation['next_state'],validation['reward'],validation['events']);te=errors(p,test['next_state'],test['reward'],test['events'])
    # Marginal empirical interval is distinct from ensemble disagreement.
    q=float(np.quantile(ve['position_m'],.95,method='higher'));bins=[];edges=np.quantile(v['disagreement'],[0,.25,.5,.75,1])
    for i in range(4):
        mask=(p['disagreement']>=edges[i])&((p['disagreement']<=edges[i+1]) if i==3 else (p['disagreement']<edges[i+1]))
        bins.append({'validation_score_bounds':[float(edges[i]),float(edges[i+1])],'test_rows':int(mask.sum()),'test_position_mae_m':float(te['position_m'][mask].mean()) if mask.any() else None,'test_high_error_fraction':float(te['high_error'][mask].mean()) if mask.any() else None})
    valid,reasons=admissibility(test['state'],p['next_state'],p['reward']);envelope=p['input_envelope']
    return {'raw_score_bins':bins,'empirical_position_interval':{'calibration_split':'validation','nominal_coverage':.95,'radius_m':q,'test_coverage':float((te['position_m']<=q).mean()),'claim':'marginal position residual interval; no joint-state safety guarantee'},'uncertainty_gate':gate_report(model,test,gate),'physical_admissibility':{'accepted':int(valid.sum()),'rejected':int((~valid).sum()),'reasons':{k:int(x.sum()) for k,x in reasons.items()}},'input_envelope_max':float(envelope.max())}


def balanced_metrics(model,data):
    prediction=model.predict(data['state'],data['action']);natural=metrics(prediction,data);per=[]
    for regime in np.unique(data['regime']):
        mask=data['regime']==regime;part={k:v[mask] for k,v in data.items()};pred={k:v[mask] for k,v in prediction.items() if isinstance(v,np.ndarray) and len(v)==len(mask)};m=metrics(pred,part);per.append(m)
    return {'natural':natural,'equal_regime_macro':{key:float(np.mean([m[key] for m in per])) for key in ('position_mae_m','pile_height_mae_m','reward_mae','mass_balance_mae_kg')},'note':'Equal-regime macro and unweighted synthetic-corpus metrics are reported separately.'}


class Baseline:
    def __init__(self,kind):self.kind=kind
    def predict(self,state,action):return simple_prediction(state,action,self.kind)


def sensor_study():
    profiles={'clean':SensorProfile(),'delay':SensorProfile(2),'dropout':SensorProfile(dropout=.4),'occlusion':SensorProfile(occlusion=.35),'combined':SensorProfile(2,.25,.15,.01),'recovery':SensorProfile(2,1,.15,.01)};results=[]
    for seed_index in (0,1):
        for name,profile in profiles.items():
            env,controller,identity=setup_episode('test',seed_index,'reference');env=SensorEnv(env.base,profile);missing=0;steps=0
            for step in range(400):
                if name=='recovery' and step==20:env.profile=replace(env.profile,dropout=0)
                obs=env.observe();missing+=int((~obs['range_valid'].astype(bool)).sum());action=controller.act(obs);_,_,term,trunc,_=env.step(action);steps+=1
                if (term|trunc).any():break
            results.append({'profile':name,'seed':identity['seed'],'initial_profile':asdict(profile),'recovery_step':20 if name=='recovery' else None,'steps':steps,'missing_range_cells':missing,'reason':str(env.reason[0]),'delivered_kg':float(env.delivered[0]),'local_actuation_active':True,'network_required':False})
    # Pairwise equality is also covered by a masked-reset regression test.
    return {'controller':'conventional observation-only reference','profiles':results,'communications':'No profile changes local actuation when communications are unavailable.'}


def run(output,epochs=40):
    output=Path(output);output.mkdir(parents=True,exist_ok=False);configure_cpu(101);source=source_identity()
    if source['training_dirty']:raise ValueError('commit training sources before retained experiment')
    started=time.perf_counter();datasets={};manifests={}
    for split,budget in [('train',4096),('validation',1536),('test',1536)]:
        data,episodes=collect_targeted(split,budget);datasets[split]=(data,episodes);manifests[split]=save_data(output/'datasets',split,data,episodes)
    ood,oe=collect_targeted('test',512,seed_offset=1000,pile_family='steep');save_data(output/'datasets','ood-steep',ood,oe)
    train,episodes=datasets['train'];validation,ve=datasets['validation'];test,te=datasets['test']
    report={'schema':'world-followup-v1','source':source,'plan':'ADR-0049','benchmark_reference_decisions':7680,'datasets':manifests,'models':{},'baselines':{}}
    for name in ('persistence','kinematic'):
        baseline=Baseline(name);report['baselines'][name]={'one_step':balanced_metrics(baseline,test),'open_loop':open_loop(baseline,test,te)}
    for name,material,multistep in [('raw',False,False),('material',True,False),('multistep_material',True,True)]:
        model,fit=fit_state(train,validation,episodes,material=material,multistep=multistep,epochs=epochs);path=output/(name+'.pt');digest=save_model(path,model,fit);write(output/(name+'-training.json'),fit);filtered=ConstrainedModel(model,FilterConfig());gate=calibrate(model,validation,ve);fgate=calibrate(filtered,validation,ve)
        report['models'][name]={'path':path.name,'sha256':digest,'fit':fit,'raw':{'one_step':balanced_metrics(model,test),'open_loop':open_loop(model,test,te),'calibration':gate,'reliability':reliability(model,validation,test,gate),'ood_steep':{'metrics':balanced_metrics(model,ood),'reliability':reliability(model,validation,ood,gate)}},'explicit_bounded_filter':{'configuration':asdict(FilterConfig()),'one_step':balanced_metrics(filtered,test),'open_loop':open_loop(filtered,test,te),'calibration':fgate,'reliability':reliability(filtered,validation,test,fgate)}}
        write(output/'report.partial.json',report)
    observable,ofit=fit_observable(train,validation,epochs);op=observable.predict(test['observation'],test['action']);valid=test['next_observation'][:,40:].astype(bool);difference=op['observation'][:,:40]-test['next_observation'][:,:40]
    odigest=checkpoints.save(output/'observable.pt',{'kind':'observable-dynamics-v1','weights':observable.state_dict(),'training':ofit});report['observable']={'sha256':odigest,'fit':ofit,'test':{'proprio_mae':float(np.abs(difference[:,:15]).mean()),'valid_range_mae_m':float(np.abs(difference[:,15:40])[valid].mean()) if valid.any() else None,'validity_accuracy':float(((op['observation'][:,40:]>=.5)==valid).mean()),'reward_mae':float(np.abs(op['reward']-test['reward']).mean())},'hidden_material_prediction':None}
    events,efit=fit_events(train,epochs);thresholds=event_thresholds(events.predict(validation['state'],validation['action']),validation['event_targets']);edigest=checkpoints.save(output/'events.pt',{'kind':'event-dynamics-v1','weights':events.state_dict(),'training':efit});report['events']={'sha256':edigest,'fit':efit,'test':event_report(events.predict(test['state'],test['action']),test,te,thresholds)};report['sensors']=sensor_study()
    # New corpus and fresh model. No benchmark weights initialise this comparison.
    small,se=collect_targeted('train',768,seed_offset=5000);cal,ce=collect_targeted('validation',256,seed_offset=5000,kinds=('blocked','contact_static','spill','prepared_delivery','stuck'))
    save_data(output/'assistance-data','train',small,se);save_data(output/'assistance-data','validation',cal,ce)
    fresh,ffit=fit_state(small,cal,se,material=True,multistep=True,epochs=epochs);fpath=output/'assistance.pt';fdigest=save_model(fpath,fresh,ffit);fresh_filter=ConstrainedModel(fresh,FilterConfig());fgate=calibrate(fresh_filter,cal,ce);payload=checkpoints.load(fpath);treatments=[]
    for seed in (7,19,41):
        for assisted in (False,True):
            config=TrainConfig(seed=seed,num_envs=4,hidden=64,rollout_steps=64,updates=12 if assisted else 16,max_wall_s=120,curriculum=False,shaping=False,randomise_training=True)
            trainer=ModelAssistedTrainer(config,payload,fdigest,fgate,asdict(FilterConfig())) if assisted else Trainer(config);t=time.perf_counter()
            for _ in range(config.updates):trainer.iterate()
            path=output/f'comparison-{seed}-{int(assisted)}.pt';digest=checkpoints.save(path,trainer.state());cases=[evaluate(trainer.policy,s) for s in (200000,200001)]
            treatments.append({'seed':seed,'assisted':assisted,'weights':path.name,'sha256':digest,'offline_reference_decisions':1024 if assisted else 0,'online_reference_decisions':trainer.counters['environment_steps'],'counters':trainer.counters,'auxiliary_records':getattr(trainer,'auxiliary_records',[]),'training_wall_s':time.perf_counter()-t,'test':cases})
    report['assistance']={'model_sha256':fdigest,'model_fit':ffit,'validation_gate':fgate,'offline_collection':{'train':768,'calibration':256,'fresh_source':True},'treatments':treatments,'role':'critic-only auxiliary values; imagined samples never enter PPO likelihood ratios','benchmark_r_and_d_reference_decisions':7680,'evaluation_cost':'Dataset validation is charged offline; test episodes and sensor study are separately reported, never reused for training.'}
    report['total_wall_s']=time.perf_counter()-started;report['limits']=['Synthetic height-field contact model; no granular fracture/cohesion fidelity','Observation dynamics are a local-feature baseline, not a perception stack','Disagreement, empirical residual intervals, filters and physical guards are distinct','No deployed-machine validation or autonomous proficiency claim'];write(output/'report.json',report);return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--epochs',type=int,default=40);args=parser.parse_args();run(args.output,args.epochs)
