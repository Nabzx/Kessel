#!/usr/bin/env python3
"""Re-execute every frozen phase-study final trace without any teacher calls."""
import argparse,gzip,json,sys,zipfile,tempfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'training'))
import numpy as np
import torch
from kessel_training import checkpoints
from kessel_training.phase_study import load_actor,episode
from kessel_training.controller import ReferenceController
from kessel_training.environment import LoaderEnv
from kessel_training.evaluate import source_identity
from kessel_training.policy import configure_cpu
from kessel_training.scenarios import family
from kessel_training.wm_state import pack


def execute(study,output,names=None):
    report=json.loads((study/'report.json').read_text());configure_cpu(7)
    if source_identity()['package_sha256']!=report['plan']['source']['package_sha256']:raise ValueError('exact training source required')
    def forbidden(*_args,**_kwargs):raise AssertionError('teacher queried during evaluation/replay')
    ReferenceController.act=forbidden
    temp=tempfile.TemporaryDirectory();data=study
    if (study/'artifacts.zip').exists():
        data=Path(temp.name)
        with zipfile.ZipFile(study/'artifacts.zip') as z:
            if any(PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts for n in z.namelist()):raise ValueError('unsafe archive member')
            z.extractall(data)
    results=[];validation_decisions=0;trace_decisions=0;maximum_state=0.;maximum_action=0.;maximum_reward=0.
    for name,selected in report['selection'].items():
        if names is not None and name not in names:continue
        actor,state=load_actor(data/selected['path'])
        if state['software']!={'torch':str(torch.__version__),'numpy':np.__version__}:raise ValueError('numerical libraries changed')
        if checkpoints.sha256(data/selected['path'])!=selected['sha256']:raise ValueError('checkpoint hash differs')
        if state['identity']['source_sha256']!=report['plan']['source']['package_sha256']:raise ValueError('checkpoint source differs')
        for expected in selected['validation']:
            actual=episode(expected['seed'],actor)['case']
            for key in ('seed','reason','steps','full_success','delivered_kg','cycle_s'):
                if actual[key]!=expected[key]:raise AssertionError('selected validation differs: '+key)
            validation_decisions+=actual['steps']
        for case in report['tests'][name]:
            path=data/case['path']
            if checkpoints.sha256(path)!=case['sha256']:raise ValueError('trace hash differs')
            raw=json.loads(gzip.decompress(path.read_bytes()));actor.reset();env=LoaderEnv(1,seed=case['seed'],scene=family('standard')[0])
            for row in raw['records']:
                maximum_state=max(maximum_state,float(np.abs(pack(env)[0]-row['state']).max()))
                action=actor.act(env.observe())[0]
                maximum_action=max(maximum_action,float(np.abs(action-row['action']).max()))
                if int(actor.memory.phase[0])!=row['phase']:raise AssertionError('phase replay differs')
                _,reward,_,_,_=env.step(np.asarray([row['action']]))
                maximum_state=max(maximum_state,float(np.abs(pack(env)[0]-row['next_state']).max()))
                maximum_reward=max(maximum_reward,abs(float(reward[0])-row['raw_reward']));trace_decisions+=1
            if len(raw['records'])!=case['steps'] or not (env.terminated|env.truncated).all():raise AssertionError('incomplete final trace')
            if str(env.reason[0])!=case['reason'] or float(env.delivered[0])!=case['delivered_kg']:raise AssertionError('final outcome differs')
        results.append({'run':name,'selected_validation_cases':16,'final_traces':len(report['tests'][name])});print('Replayed',name,flush=True)
    if max(maximum_state,maximum_action,maximum_reward)!=0:raise AssertionError('nonzero replay error')
    result={'kind':'phase-imitation-independent-replay-v1','source':report['plan']['source'],'runs':results,'validation_decisions':validation_decisions,'trace_decisions':trace_decisions,'max_state_error':maximum_state,'max_action_error':maximum_action,'max_raw_reward_error':maximum_reward,'teacher_queries':0}
    output.write_text(json.dumps(result,indent=2)+'\n');temp.cleanup()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--study',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--runs',nargs='+');a=p.parse_args();execute(a.study,a.output,a.runs)
