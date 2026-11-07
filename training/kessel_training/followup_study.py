"""Predeclared CPU policy/retention comparisons. Never substitutes a reference for a learner."""
import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import torch
from torch.nn import functional as F
from . import checkpoints
from .controller import ReferenceController
from .curriculum import TrainingEnv,STAGES
from .environment import LoaderEnv
from .evaluate import source_identity
from .followup_policy import HistoryEnv,HistoryActorCritic,CurriculumBridge,flat
from .policy import ActorCritic,configure_cpu
from .ppo import PPO,PPOConfig,collect
from .reference_audit import initial_status
from .scenarios import family
from .wm_state import pack

METHODS=('ppo','history_ppo','bridged_curriculum','bc_ppo')
SEEDS=(7,19,41)


def teacher_pairs(count=1024):
    rows=[];seed=0;episodes=[]
    while len(rows)<count:
        env=LoaderEnv(1,seed=seed,scene=family('standard')[0]);controller=ReferenceController(1);start=len(rows)
        while len(rows)<count:
            observation=env.observe();action=controller.act(observation)
            rows.append((flat(observation)[0].copy(),action[0].copy(),int(controller.phase[0])))
            _,_,term,trunc,_=env.step(action)
            if (term|trunc).any():break
        episodes.append({'seed':seed,'split':'train','rows':len(rows)-start,'complete':bool((env.terminated|env.truncated)[0]),'reason':str(env.reason[0])});seed+=1
    return {'observation':np.asarray([r[0] for r in rows]),'action':np.asarray([r[1] for r in rows]),'phase':np.asarray([r[2] for r in rows])},episodes


def raw_observation(features):
    return {'proprio':features[:,:15],'local_height_m':features[:,15:40].reshape(-1,5,5),'range_valid':features[:,40:].reshape(-1,5,5)}


def warm_start(policy,data,seed,updates=500):
    rng=np.random.default_rng(seed);optimiser=torch.optim.Adam(policy.actor.parameters(),lr=.002)
    features=policy.encode(raw_observation(data['observation']));targets=torch.as_tensor(data['action'],dtype=torch.float32)
    counts=np.bincount(data['phase'],minlength=5);weights=1/np.maximum(1,counts[data['phase']]);weights=weights/weights.sum();losses=[]
    for _ in range(updates):
        indices=rng.choice(len(features),256,replace=True,p=weights)
        prediction=policy.actor(features[indices]).tanh();loss=F.mse_loss(prediction,targets[indices])
        if not torch.isfinite(loss):raise FloatingPointError('non-finite reference warm-start')
        optimiser.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(policy.actor.parameters(),.5,error_if_nonfinite=True);optimiser.step();losses.append(float(loss.detach()))
    return {'supervised_minibatches':updates,'reused_training_pairs':updates*256,'unique_reference_pairs':len(features),'phase_counts':counts.tolist(),'first_mse':losses[0],'last_mse':losses[-1],'losses':losses}


@torch.no_grad()
def evaluate(policy,seed,stage='complete',history=False,record=False):
    scene=family('standard')[0]
    if stage=='complete':base=LoaderEnv(1,seed=seed,scene=scene)
    else:
        base=TrainingEnv(1,seed=seed,scene=scene,curriculum=True,shaping=False)
        base.stage_index=STAGES.index(stage);base.base.scene=base._scene();base.reset(seed=seed)
    env=HistoryEnv(base) if history else base
    controller=ReferenceController(1) if policy is None else None
    initial=float(env.payload[0]);status=initial_status(env)[0];records=[];steps=0
    if not status['valid']:return {'seed':seed,'stage':stage,'valid_start':False,'reason':'invalid_start','steps':0,'initial_payload_kg':initial,'delivered_kg':0,'stage_success':False,'full_success':False,'records':[]}
    while True:
        observation=env.observe();action=controller.act(observation) if controller else policy.sample(policy.encode(observation),deterministic=True)['action'].numpy()
        if record:records.append({'t_s':float(env.elapsed[0]),'state':pack(env)[0].tolist(),'observation':flat({k:v for k,v in observation.items() if k!='previous'})[0].tolist(),'wheel_angles_rad':env.wheel_angles[0].tolist(),'action':action[0].tolist()})
        _,reward,term,trunc,info=env.step(action);steps+=1
        if record:
            records[-1].update(reward=float(reward[0]),transfer={k:float(info['transfer'][k][0]) for k in ('loaded_kg','delivered_kg','spilled_kg')})
        if (term|trunc).any():break
    if record:records.append({'t_s':float(env.elapsed[0]),'state':pack(env)[0].tolist(),'observation':flat(env.base.observe() if history else env.observe())[0].tolist(),'wheel_angles_rad':env.wheel_angles[0].tolist(),'action':None,'reward':None,'transfer':None})
    return {'seed':seed,'split':'validation' if 100000<=seed<110000 else 'test','stage':stage,'valid_start':True,'initial_payload_kg':initial,
        'reason':str(env.reason[0]),'steps':steps,'stage_success':str(env.reason[0]) in ('stage_success','success'),'full_success':str(env.reason[0])=='success' and initial==0,
        'delivered_kg':float(env.delivered[0]),'spilled_kg':float(env.spilled[0]),'peak_load_kg':float(env.peak_load[0]),'cycle_s':float(env.elapsed[0]),'records':records}


def retention(policy,history=False):
    cases={};steps=0
    for stage in STAGES:
        rows=[evaluate(policy,seed,stage,history) for seed in (100000,100001)];steps+=sum(r['steps'] for r in rows)
        cases[stage]={'evaluations':len(rows),'valid_starts':all(r['valid_start'] for r in rows),'success_rate':sum(r['stage_success'] for r in rows)/len(rows),'cases':rows}
    return cases,steps


def score(cases):return (sum(c['delivered_kg'] for c in cases),sum(c['full_success'] for c in cases),-sum(c['reason'] in ('tunnel_wall','tunnel_roof') or c['reason'].startswith('obstacle') for c in cases))


def save_policy(path,policy,source,method,seed,rollout,counters):
    return checkpoints.save(path,{'kind':'followup-policy-v1','architecture':'history130' if isinstance(policy,HistoryActorCritic) else 'local65','hidden':policy.hidden,'actor_critic':policy.state_dict(),'source':source,'method':method,'seed':seed,'rollout':rollout,'counters':dict(counters)})


def load_policy(path):
    data=checkpoints.load(path)
    if data.get('kind')!='followup-policy-v1':raise ValueError('follow-up policy kind differs')
    policy=(HistoryActorCritic if data['architecture']=='history130' else ActorCritic)(data['hidden']);policy.load_state_dict(data['actor_critic'],strict=True);policy.eval();return policy,data


def run(output,seeds=SEEDS,methods=METHODS,updates=16,bc_updates=500):
    output=Path(output);output.mkdir(parents=True,exist_ok=False);source=source_identity()
    if source['training_dirty']:raise ValueError('commit the training package before retained experiments')
    all_started=time.perf_counter();teacher,teacher_episodes=teacher_pairs();np.savez_compressed(output/'teacher.npz',**teacher)
    report={'schema':'policy-followup-v1','source_mode':'recorded_synthetic','source':source,'plan':'ADR-0049','budget_reference_decisions':4096,'teacher_episodes':teacher_episodes,'teacher_sha256':checkpoints.sha256(output/'teacher.npz'),'runs':[],'reference':[]}
    for seed in seeds:
        for method in methods:
            generator=configure_cpu(seed);history=method=='history_ppo';policy=(HistoryActorCritic if history else ActorCritic)(64)
            base=TrainingEnv(4,seed=seed,scene=family('standard')[0],curriculum=True,shaping=True) if method=='bridged_curriculum' else LoaderEnv(4,seed=seed,scene=family('standard')[0])
            env=HistoryEnv(base) if history else base;algorithm=PPO(policy,PPOConfig());bridge=CurriculumBridge();directory=output/f'{method}-{seed}';directory.mkdir()
            counters={'online_reference_decisions':0,'offline_reference_decisions':1024 if method=='bc_ppo' else 0,'optimiser_updates':0,'completed_episodes':0,'full_successes':0};curve=[];candidates=[];evaluation_steps=0;training_s=0
            def candidate(label,rollout):
                nonlocal evaluation_steps
                path=directory/(label+'.pt');digest=save_policy(path,policy,source,method,seed,rollout,counters)
                cases=[evaluate(policy,s,history=history) for s in (100000,100001)];evaluation_steps+=sum(c['steps'] for c in cases)
                candidates.append({'label':label,'path':str(path),'sha256':digest,'rollout':rollout,'validation':cases,'score':score(cases)})
            candidate('initial',0)
            supervision=None
            if method=='bc_ppo':
                started=time.perf_counter();supervision=warm_start(policy,teacher,seed,bc_updates);training_s+=time.perf_counter()-started;candidate('warm-start',0)
            count=min(updates,12 if method=='bc_ppo' else 16)
            for rollout_index in range(1,count+1):
                started=time.perf_counter();batch=collect(env,policy,64,generator);stats=algorithm.update(batch,generator);training_s+=time.perf_counter()-started
                counters['online_reference_decisions']+=4*64;counters['optimiser_updates']+=stats['minibatch_updates'];counters['completed_episodes']+=len(batch.episodes);counters['full_successes']+=sum(e['reason']=='success' for e in batch.episodes)
                transition=None
                if method=='bridged_curriculum':
                    gate=bridge.gate(base.stage,batch.episodes,{})
                    if gate['training_episodes']==32 and gate['training_success_rate']>=.7:
                        heldout,steps=retention(policy);evaluation_steps+=steps;transition=bridge.advance(base,[],heldout,rollout_index)
                curve.append({'rollout':rollout_index,**counters,'mean_step_reward':float(batch.rewards.mean()),'stage':base.stage if isinstance(base,TrainingEnv) else 'complete','transition':transition,'update':{k:v for k,v in stats.items() if k!='minibatches'}})
            candidate('final',count)
            selected=max(enumerate(candidates),key=lambda item:(tuple(item[1]['score']),item[0]))[1]
            chosen,identity=load_policy(selected['path']);heldout,steps=retention(chosen,history);evaluation_steps+=steps
            tests=[evaluate(chosen,s,history=history,record=True) for s in (200000,200001)];evaluation_steps+=sum(c['steps'] for c in tests)
            traces=[]
            for test in tests:
                path=directory/f'test-{test["seed"]}.json.gz';path.write_bytes(gzip.compress(json.dumps(test,separators=(',',':'),allow_nan=False).encode(),mtime=0));traces.append({'path':str(path),'sha256':checkpoints.sha256(path),'seed':test['seed'],'reason':test['reason'],'steps':test['steps']})
            row={'method':method,'seed':seed,'network':policy.description(),'counters':counters,'training_wall_s':training_s,'evaluation_reference_steps':evaluation_steps,'supervision':supervision,'curve':curve,'gates':bridge.records,'retention':heldout,'candidates':candidates,'selected':selected,'selection_rule':'maximum validation delivered kg, then full successes, then fewer collisions; ties prefer later candidate; no test selection','test':[dict(c,records=None) for c in tests],'traces':traces}
            report['runs'].append(row);(output/'report.partial.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(method,seed,'test',[(c['reason'],round(c['delivered_kg'])) for c in tests],flush=True)
    for seed in (200000,200001):report['reference'].append(evaluate(None,seed,record=False))
    report['total_wall_s']=time.perf_counter()-all_started;report['limits']='Bounded synthetic study, not calibrated machinery or deployment. Prepared subtasks are separate from empty-start full cycles. BC is reference-supervised, not pure RL.'
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);args=p.parse_args();run(args.output)
