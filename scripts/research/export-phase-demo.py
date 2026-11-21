#!/usr/bin/env python3
"""Export three predeclared finite recordings only after complete-task admission."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def collision(case):
    return case['reason'] in ('tunnel_wall','tunnel_roof') or case['reason'].startswith('obstacle')


def export(study, output):
    report=json.loads((study/'report.json').read_text())
    methods=[m for m in ('memoryless','phase_memory') if report['admitted'][m]]
    if not methods:
        raise ValueError('no method passed the predeclared three-seed admission gate; no success demo exported')
    method=methods[0]
    if (output/'catalogue.json').exists():
        raise FileExistsError('catalogue already exists; do not replace recorded identity silently')
    selected=json.loads((study/'selection.json').read_text())
    assert selected==report['selection']
    catalogue={'kind':'phase-imitation-recorded-v1','admitted':True,'method':method,'final_cases':96,
        'successes':0,'collisions':0,'recordings':[],'all_cases':[],
        'control_description':'Recorded synthetic: imitation-trained continuous controls'+(' with rule-based phase memory.' if method=='phase_memory' else '. Phase annotations do not control the network.'),
        'disclosure':'The displayed case is the first successful final case for this seed, selected by numerical case order. Aggregate results include all 96 final cases. This is finite recorded playback, not live inference, learned-world-model training or field qualification.',
        'source':report['plan']['source'],'report_sha256':hashlib.sha256((study/'report.json').read_bytes()).hexdigest()}
    for seed in (7,19,41):
        name=f'{method}-{seed}';cases=report['tests'][name]
        good=[c for c in cases if c['full_success'] and c['delivered_kg']>=2000 and c['initial_payload_kg']==0]
        if len(cases)!=32 or len(good)<28 or sum(collision(c) for c in cases)>1:
            raise ValueError('method does not meet all per-seed admission requirements')
        chosen=min(good,key=lambda c:c['seed'])
        path=study/chosen['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=chosen['sha256']:
            raise ValueError('test trace hash differs')
        candidate=selected[name];weights=study/candidate['path']
        if hashlib.sha256(weights.read_bytes()).hexdigest()!=candidate['sha256']:
            raise ValueError('checkpoint identity differs')
        raw=json.loads(gzip.decompress(path.read_bytes()));records=raw['records']
        if not records or len(records)!=chosen['steps']:
            raise ValueError('test trace is incomplete')
        frames=[{'t_s':row['state'][10],'state':row['state'],'action':row['action'],'phase':row['phase'],'wheel_angles_rad':[0,0,0,0]} for row in records]
        last=records[-1]
        frames.append({'t_s':last['next_state'][10],'state':last['next_state'],'action':None,'phase':last['phase'],'wheel_angles_rad':[0,0,0,0]})
        if frames[0]['state'][7]!=0 or frames[-1]['state'][8]<2000:
            raise ValueError('not an empty-start complete delivery')
        payload={'kind':'phase-imitation-recording-v1','case':raw['case'],'training_seed':seed,
            'method':method,'checkpoint_sha256':candidate['sha256'],'frames':frames,
            'wheel_rotation':'not recorded; fixed visual proxy'}
        data=json.dumps(payload,separators=(',',':'),allow_nan=False).encode()
        filename=f'seed-{seed}-case-{chosen["seed"]}.json'
        output.mkdir(parents=True,exist_ok=True);(output/filename).write_bytes(data)
        catalogue['recordings'].append({'training_seed':seed,'case':chosen,'path':filename,
            'sha256':hashlib.sha256(data).hexdigest(),'checkpoint_sha256':candidate['sha256']})
        catalogue['successes']+=len(good);catalogue['collisions']+=sum(collision(c) for c in cases)
        catalogue['all_cases'].extend({'training_seed':seed,**c} for c in cases)
    (output/'catalogue.json').write_text(json.dumps(catalogue,indent=2)+'\n')
    print('Exported admitted',method,'with',catalogue['successes'],'/96 deliveries and three finite recordings')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--study',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();export(a.study,a.output)
