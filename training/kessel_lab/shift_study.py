"""Frozen-policy, all-case shift evaluation with independently replayed traces."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import time
import zipfile

import numpy as np
import torch
from kessel_training.contracts import canonical_json
from kessel_training.evaluate import source_identity
from kessel_training.policy import configure_cpu
from kessel_training.wm_state import pack
from .runtime import ROOT, FAMILIES, SOURCES, Run, environment, digest


def execute(output, reservation):
    certificate=json.loads(reservation.read_text())
    if certificate['verified'] is not True: raise ValueError('fresh reservation required')
    output.mkdir(parents=True,exist_ok=False);configure_cpu(7)
    protocol=ROOT/'docs/adr/0062-interactive-synthetic-runtime.md'
    package={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob('*.py'))}
    plan={'kind':'frozen-policy-shift-v1','seeds':list(range(206200,206208)),
          'families':list(FAMILIES),'sources':list(SOURCES),'source':source_identity(),
          'lab_files':package,'protocol_sha256':hashlib.sha256(protocol.read_bytes()).hexdigest(),
          'reservation_sha256':hashlib.sha256(reservation.read_bytes()).hexdigest(),
          'software':{'torch':str(torch.__version__),'numpy':np.__version__},
          'policy_updates':0,'teacher_queries_for_learned':0,'selection':'all frozen ADR-0061 phase-memory actors; no new selection'}
    (output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    rows=[];summaries=[];started=time.perf_counter();maximum_state=0.;maximum_action=0.
    with zipfile.ZipFile(output/'traces.zip','w',compression=zipfile.ZIP_STORED) as archive:
        for family in FAMILIES:
            for source in SOURCES:
                cases=[];latencies=[]
                for seed in plan['seeds']:
                    run=Run(family,seed,source)
                    while not run.done: run.step()
                    # Second instance re-executes actions without using any controller.
                    replay,_=environment(family,seed)
                    for record in run.records:
                        maximum_state=max(maximum_state,float(np.abs(pack(replay)[0]-record['state']).max()))
                        replay.step([record['action']])
                        maximum_state=max(maximum_state,float(np.abs(pack(replay)[0]-record['next_state']).max()))
                    if maximum_state != 0.: raise AssertionError('independent trace replay differs')
                    payload={'identity':run.identity,'scenario':run.scenario,'source':source,
                             'checkpoint_sha256':run.checkpoint_sha256,'outcome':run.outcome(),
                             'frames':run.records+[run.frame()]}
                    data=gzip.compress(canonical_json(payload).encode(),mtime=0)
                    path=f'{family}/{source}-{seed}.json.gz';archive.writestr(path,data)
                    row={'family':family,'seed':seed,'source':source,'identity':run.identity,
                         'scenario':run.scenario,'checkpoint_sha256':run.checkpoint_sha256,
                         'trace':path,'sha256':hashlib.sha256(data).hexdigest(),**run.outcome()}
                    rows.append(row);cases.append(row);latencies.extend(run.inference_us)
                good=[r for r in cases if r['full_success']]
                summary={'family':family,'source':source,'cases':len(cases),'successes':len(good),
                         'collisions':sum(r['collision'] for r in cases),'reasons':dict(Counter(r['reason'] for r in cases)),
                         'all_case_mean_s':float(np.mean([r['cycle_s'] for r in cases])),
                         'successful_mean_s':float(np.mean([r['cycle_s'] for r in good])) if good else None,
                         'inference_us':{'count':len(latencies),'median':float(np.median(latencies)),
                                         'p95':float(np.quantile(latencies,.95)),'max':max(latencies)}}
                summaries.append(summary);print(f'{family} {source}: {len(good)}/8; collisions {summary["collisions"]}',flush=True)
    admission={f:all(r['successes']>=7 and r['collisions']==0 for r in summaries if r['family']==f and r['source']!='reference') for f in FAMILIES}
    report={'plan':plan,'cases':rows,'summaries':summaries,'family_admission':admission,
            'max_independent_state_error':maximum_state,'independent_replay_decisions':sum(r['decisions'] for r in rows),
            'evaluation_decisions':sum(r['decisions'] for r in rows),'active_wall_s':time.perf_counter()-started,
            'max_mass_residual_kg':max(r['max_mass_residual_kg'] for r in rows),
            'trace_archive_sha256':hashlib.sha256((output/'traces.zip').read_bytes()).hexdigest()}
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('Completed',len(rows),'cases',report['evaluation_decisions'],'decisions',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--reservation',type=Path,required=True)
    a=p.parse_args();execute(a.output,a.reservation)
