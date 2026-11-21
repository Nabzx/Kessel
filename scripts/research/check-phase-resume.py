#!/usr/bin/env python3
"""Prove completed-study recovery performs no new teacher, episode or optimiser work."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'training'))
import torch
from kessel_training import phase_study
from kessel_training.controller import ReferenceController


def check(study,evidence):
    before=json.loads((study/'report.json').read_text());selection_sha=hashlib.sha256((study/'selection.json').read_bytes()).hexdigest()
    def forbidden(*_args,**_kwargs):raise AssertionError('completed resume attempted new episode/teacher/optimiser work')
    phase_study.episode=forbidden;ReferenceController.act=forbidden;torch.optim.Adam.step=forbidden
    phase_study.study(study,(evidence/'reservation.json').resolve())
    after=json.loads((study/'report.json').read_text())
    keys=('teacher_queries','collection_decisions','supervised_updates','validation_decisions','test_decisions')
    result={'kind':'phase-study-completed-resume-v1','counter_deltas':{k:after[k]-before[k] for k in keys},
        'selection_unchanged':before['selection']==after['selection'] and selection_sha==hashlib.sha256((study/'selection.json').read_bytes()).hexdigest(),
        'test_outcomes_unchanged':before['tests']==after['tests'],'new_episode_teacher_and_optimiser_calls_blocked':True}
    assert not any(result['counter_deltas'].values()) and result['selection_unchanged'] and result['test_outcomes_unchanged']
    (evidence/'resume-check.json').write_text(json.dumps(result,indent=2)+'\n');print('Resume verified: zero new episodes, teacher queries or optimiser updates')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--study',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();check(a.study,a.evidence)
