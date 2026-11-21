#!/usr/bin/env python3
"""Retain all phase-study data, round candidates, validation and final outcomes."""
import argparse,hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def archive(study,evidence):
    report=json.loads((study/'report.json').read_text())
    if len(report['selection'])!=6 or any(len(cases)!=32 for cases in report['tests'].values()):raise ValueError('study is incomplete')
    evidence.mkdir(parents=True,exist_ok=True)
    for name in ('report.json','plan.json','selection.json'):
        if (evidence/name).exists():raise FileExistsError(name)
        shutil.copyfile(study/name,evidence/name)
    names={c['path'] for c in report['collection']}
    for candidates in report['runs'].values():
        for c in candidates:names.add(c['path']);names.add(c['path']+'.sha256')
    for cases in report['tests'].values():
        for c in cases:names.add(c['path']);names.add(c['path']+'.sha256')
    for p in study.glob('validation-*.json.gz'):names.add(p.name);names.add(p.name+'.sha256')
    for c in report['collection']:names.add(c['path']+'.sha256')
    with zipfile.ZipFile(evidence/'artifacts.zip','x',zipfile.ZIP_DEFLATED) as z:
        for name in sorted(names):z.write(study/name,name)
    with zipfile.ZipFile(evidence/'source.zip','x',zipfile.ZIP_DEFLATED) as z:
        for p in sorted((ROOT/'training/kessel_training').glob('*.py')):z.write(p,'kessel_training/'+p.name)
        for name in ('pyproject.toml','uv.lock'):z.write(ROOT/'training'/name,name)
        for name in ('archive-phase-study.py','replay-phase-study.py','export-phase-demo.py'):z.write(ROOT/'scripts/research'/name,'research/'+name)
    first=min((study/c['path']).stat().st_mtime_ns for cases in report['tests'].values() for c in cases)
    ordering={'kind':'phase-study-consumption-v1','selection_sha256':hashlib.sha256((study/'selection.json').read_bytes()).hexdigest(),'selection_mtime_ns':(study/'selection.json').stat().st_mtime_ns,'first_final_mtime_ns':first,'final_role':'consumed_after_all_six_selections_frozen','validation':report['plan']['validation'],'final':report['plan']['final']}
    if ordering['selection_mtime_ns']>=first:raise AssertionError('final collection preceded frozen selection')
    (evidence/'consumption.json').write_text(json.dumps(ordering,indent=2)+'\n');print('Archived',len(names),'files')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--study',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();archive(a.study,a.evidence)
