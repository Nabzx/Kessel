#!/usr/bin/env python3
"""Calibration-only forecast gates and all-case drift on frozen-policy shift traces."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
import zipfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'training'))
import numpy as np
import torch
from kessel_lab.runtime import Run
from kessel_training import checkpoints
from kessel_training.followup_models import ObservationModel
from kessel_training.kinematics import components
from kessel_training.policy import configure_cpu
from kessel_training.wm_evaluate import metrics,open_loop,calibrate,gate_report,errors,simple_prediction
from kessel_training.world_model import load_model
from kessel_training.environment import PROPRIO_NAMES


def flat(obs):return np.concatenate((obs['proprio'],np.asarray(obs['local_height_m']).ravel(),np.asarray(obs['range_valid']).ravel()))


def data(episodes):
    rows=[];meta=[]
    for episode in episodes:
        start=len(rows);frames=episode['frames'];outcome=episode['outcome'];episode_id=len(meta)
        for i,frame in enumerate(frames[:-1]):
            state=np.asarray(frame['state']);following=np.asarray(frame['next_state']);transfer=sum(frame['transfer'].values())
            geometry=components(state[None,:3],state[None,4:7]);mouth=geometry['mouth'][0]
            xy=np.floor((mouth-state[79:81])/.5).astype(int)
            height=state[15:79].reshape(8,8)[tuple(np.clip(xy,0,7))] if ((xy>=0)&(xy<8)).all() else 0.
            contact=height>geometry['bucket_height'][0] or transfer>1e-6
            terminal=i==len(frames)-2;collision=terminal and outcome['collision'];stuck=terminal and outcome['reason']=='stuck'
            events=[terminal and outcome['reason']!='time_limit',terminal and outcome['reason']=='time_limit',contact,collision]
            next_observation=frames[i+1].get('observation')
            rows.append({'state':state,'next_state':following,'action':frame['action'],'reward':frame['reward'],
                         'events':events,'regime':3 if collision or stuck else 2 if transfer>1e-6 else 1 if contact else 0,
                         'episode_id':episode_id,'step':i,'observation':flat(frame['observation']),
                         'next_observation':flat(next_observation) if next_observation is not None else np.zeros(65),
                         'observable_target_present':next_observation is not None})
        meta.append({'id':episode_id,'start':start,'stop':len(rows),'family':episode['scenario']['family'],
                     'seed':episode['scenario']['seed'],'reason':outcome['reason']})
    return {k:np.asarray([r[k] for r in rows]) for k in rows[0]},meta


class Baseline:
    def __init__(self,name):self.name=name
    def predict(self,state,action):return simple_prediction(state,action,self.name)


def execute(study,output,calibration_only=False):
    output.mkdir(parents=True,exist_ok=True);configure_cpu(7);started=time.perf_counter()
    protocol=ROOT/'docs/phase-11/world-model-shift-protocol.md'
    files={}
    for name in ('multistep_material','observable'):
        path=ROOT/f'docs/phase-11/world-followup-evidence/{name}.pt'
        sha=checkpoints.sha256(path)
        if sha!=path.with_suffix('.pt.sha256').read_text().strip():raise ValueError('model hash differs')
        files[name]=sha
    plan={'protocol_sha256':hashlib.sha256(protocol.read_bytes()).hexdigest(),'models':files,'new_model_updates':0,'actor_updates':0,
          'calibration_seeds':list(range(108400,108408)),'test_source':'phase_memory-7 from all 104 shift episodes',
          'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if (output/'report.json').exists(): raise FileExistsError('completed evaluation already exists')
    if (output/'plan.json').exists():
        if json.loads((output/'plan.json').read_text())!=plan: raise ValueError('resumed protocol or source differs')
    else: (output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    calibration=[]
    families=('nominal','nominal','low','ridge','rubble','steep','blocked','range_dropout')
    if (output/'calibration-manifest.json').exists():
        manifest=json.loads((output/'calibration-manifest.json').read_text())
        if hashlib.sha256((output/'calibration.zip').read_bytes()).hexdigest()!=manifest['sha256']:raise ValueError('calibration archive differs')
        with zipfile.ZipFile(output/'calibration.zip') as z:
            calibration=[json.loads(z.read(f'{seed}.json')) for seed in plan['calibration_seeds']]
    else:
        with zipfile.ZipFile(output/'calibration.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
            for seed,family in zip(plan['calibration_seeds'],families):
                run=Run(family,seed,'phase_memory-7')
                while not run.done:run.step()
                row={'scenario':run.scenario,'outcome':run.outcome(),'frames':run.records+[run.frame()]}
                calibration.append(row);z.writestr(f'{seed}.json',json.dumps(row,separators=(',',':')))
                print('Calibrated corpus',family,seed,run.outcome()['reason'],flush=True)
        (output/'calibration-manifest.json').write_text(json.dumps({'sha256':hashlib.sha256((output/'calibration.zip').read_bytes()).hexdigest(),'seeds':plan['calibration_seeds']},indent=2)+'\n')
    if calibration_only:
        print('Calibration retained; no test traces opened',flush=True);return
    validation,ve=data(calibration)
    report=json.loads((study/'report.json').read_text());test_episodes=[]
    with zipfile.ZipFile(study/'traces.zip') as z:
        for case in report['cases']:
            if case['source']=='phase_memory-7':
                raw=z.read(case['trace'])
                if hashlib.sha256(raw).hexdigest()!=case['sha256']:raise ValueError('test trace hash differs')
                test_episodes.append(json.loads(gzip.decompress(raw)))
    test,te=data(test_episodes);model,_=load_model(ROOT/'docs/phase-11/world-followup-evidence/multistep_material.pt')
    gate=calibrate(model,validation,ve);vp=model.predict(validation['state'],validation['action'])
    interval=float(np.quantile(errors(vp,validation['next_state'],validation['reward'],validation['events'])['position_m'],.95,method='higher'))
    results={}
    for name,method in [('persistence',Baseline('persistence')),('kinematic',Baseline('kinematic')),('privileged_multistep_material',model)]:
        p=method.predict(test['state'],test['action']);results[name]={'one_step':metrics(p,test),'open_loop':open_loop(method,test,te)}
    families_report=[]
    for family in sorted(set(e['family'] for e in te)):
        ids=[e['id'] for e in te if e['family']==family];mask=np.isin(test['episode_id'],ids);part={k:v[mask] for k,v in test.items()}
        p=model.predict(part['state'],part['action']);e=errors(p,part['next_state'],part['reward'],part['events'])
        families_report.append({'family':family,'rows':int(mask.sum()),'gate':gate_report(model,part,gate),
                                'position_interval_coverage':float((e['position_m']<=interval).mean()),'metrics':metrics(p,part)})
    weights=checkpoints.load(ROOT/'docs/phase-11/world-followup-evidence/observable.pt')['weights']
    observable=ObservationModel(weights['input_mean'],weights['input_scale'],weights['target_mean'],weights['target_scale']);observable.load_state_dict(weights);observable.eval()
    present=test['observable_target_present'].astype(bool);obs=test['observation'][present];target=test['next_observation'][present]
    predicted=observable.predict(obs,test['action'][present])['observation'];valid=target[:,40:].astype(bool)
    observed={'rows':len(obs),'excluded_terminal_rows':int((~present).sum()),
              'proprio_mae_by_field':{name:float(np.abs(predicted[:,i]-target[:,i]).mean()) for i,name in enumerate(PROPRIO_NAMES)},
              'valid_range_mae_m':float(np.abs(predicted[:,15:40]-target[:,15:40])[valid].mean()),
              'range_validity_accuracy':float(((predicted[:,40:]>=.5)==valid).mean()),'hidden_material_prediction':None}
    coverage={'calibration_episodes':len(ve),'test_episodes':len(te),
              'test_collision_episodes':sum(e['reason'] in ('tunnel_wall','tunnel_roof') or e['reason'].startswith('obstacle') for e in te),
              'test_stuck_episodes':sum(e['reason']=='stuck' for e in te),'new_training_episodes':0,
              'collision_training_goal':128,'stuck_training_goal':128,'training_goal_met':False,
              'test_regime_rows':np.bincount(test['regime'],minlength=4).tolist()}
    qualifies=gate['supported_horizon']>=1 and all(r['gate']['accepted'] and r['gate']['accepted_high_error_fraction']<=.1 for r in families_report if r['family']!='blocked')
    result={'plan':plan,'calibration_decisions':len(validation['state']),'reused_test_decisions':len(test['state']),
            'coverage':coverage,'methods':results,'observable':observed,'calibration_gate':gate,
            'position_interval':{'calibration_only':True,'radius_m':interval,'nominal_coverage':.95,'claim':'marginal empirical residual, not a safety bound'},
            'families':families_report,'assistance_qualified':bool(qualifies),'assisted_updates':0,
            'assistance_decision':'requires a separate matched-budget experiment' if qualifies else 'no-go: forecast gate fails on the working-policy task',
            'wall_s':time.perf_counter()-started}
    (output/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(result['assistance_decision'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--calibration-only',action='store_true');a=p.parse_args();execute(a.study,a.output,a.calibration_only)
