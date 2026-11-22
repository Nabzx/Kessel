#!/usr/bin/env python3
"""Independently replay learned action sequences and calibration physics, without teachers."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'training'))
import numpy as np
from kessel_lab.runtime import checkpoint,environment
from kessel_training.controller import ReferenceController
from kessel_training.evaluate import source_identity
from kessel_training.policy import configure_cpu
from kessel_training.wm_state import pack


def execute(study,calibration,output):
    configure_cpu(7);report=json.loads((study/'report.json').read_text())
    if source_identity()['package_sha256']!=report['plan']['source']['package_sha256']:raise ValueError('training source differs')
    def forbidden(*args,**kwargs):raise AssertionError('teacher called during learned replay')
    ReferenceController.act=forbidden
    counts={'shift_cases':0,'calibration_cases':0,'policy_queries':0,'calibration_physics_decisions':0}
    max_action=0.;max_state=0.;checkpoint_ids={}
    def verify(raw,source,physics=False):
        nonlocal max_action,max_state
        actor,sha=checkpoint(source);checkpoint_ids[source]=sha
        replay,_=environment(raw['scenario']['family'],raw['scenario']['seed']) if physics else (None,None)
        for frame in raw['frames'][:-1]:
            obs={k:np.asarray([v]) for k,v in frame['observation'].items()}
            action=actor.act(obs)[0];max_action=max(max_action,float(np.abs(action-frame['action']).max()))
            if int(actor.memory.phase[0])!=frame['phase']:raise AssertionError('phase replay differs')
            counts['policy_queries']+=1
            if physics:
                max_state=max(max_state,float(np.abs(pack(replay)[0]-frame['state']).max()))
                replay.step([frame['action']]);max_state=max(max_state,float(np.abs(pack(replay)[0]-frame['next_state']).max()))
                counts['calibration_physics_decisions']+=1
    with zipfile.ZipFile(study/'traces.zip') as z:
        for case in report['cases']:
            if case['source']=='reference':continue
            raw=z.read(case['trace'])
            if hashlib.sha256(raw).hexdigest()!=case['sha256']:raise ValueError('trace hash differs')
            verify(json.loads(gzip.decompress(raw)),case['source']);counts['shift_cases']+=1
    with zipfile.ZipFile(calibration/'calibration.zip') as z:
        for name in z.namelist():verify(json.loads(z.read(name)),'phase_memory-7',True);counts['calibration_cases']+=1
    if max_action!=0 or max_state!=0:raise AssertionError('nonzero action/physical replay error')
    result={**counts,'checkpoints':checkpoint_ids,'max_action_error':max_action,'max_calibration_state_error':max_state,
            'teacher_queries':0,'new_held_out_cases':0,'role':'verification of consumed cases, not another generalisation test'}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,required=True);p.add_argument('--calibration',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();execute(a.study,a.calibration,a.output)
