#!/usr/bin/env python3
"""Verify measured phase-study evidence and bind any demo to admitted results."""
import gzip,hashlib,json,statistics,struct,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'docs/phase-11/phase-memory-evidence';DEMO=ROOT/'docs/phase-11/phase-memory-demo'


def sha(data):return hashlib.sha256(data).hexdigest()
def collision(c):return c['reason'] in ('tunnel_wall','tunnel_roof') or c['reason'].startswith('obstacle')
def score(cases):
    good=[c for c in cases if c['full_success'] and c['reason']=='success' and c['delivered_kg']>=2000]
    return[len(good),-sum(collision(c) for c in cases),-statistics.mean(c['cycle_s'] for c in good) if good else 0.]


def verify():
    manifest=json.loads((E/'files.json').read_text())
    for name,digest in manifest.items():assert sha((E/name).read_bytes())==digest,name
    report=json.loads((E/'report.json').read_text());selection=json.loads((E/'selection.json').read_text());audit=json.loads((E/'reservation.json').read_text())
    assert report['plan']['source']['training_dirty'] is False
    assert audit['verified'] and not audit['archive_audit']['hits'] and not audit['archive_audit']['failures'] and not audit['zip_hits'] and not audit['zip_errors']
    assert sha((E/'reservation.json').read_bytes())==report['plan']['reservation_sha256']
    assert report['plan']['validation']==audit['validation']==list(range(108200,108216))
    assert report['plan']['final']==audit['final']==list(range(207600,207632))
    assert selection==report['selection'] and len(selection)==6
    assert len(report['collection'])==176
    assert report['collection_decisions']==report['teacher_queries']==sum(c['steps'] for c in report['collection'])<=120000
    assert report['supervised_updates']==22500
    assert report['validation_decisions']==sum(c['steps'] for runs in report['runs'].values() for run in runs for c in run['validation'])
    assert report['test_decisions']==sum(c['steps'] for cases in report['tests'].values() for c in cases)
    identities={c['seed']:c['starts']['complete']['state_float64_sha256'] for c in audit['archive_audit']['identities'] if c['split']=='final_test'}
    with zipfile.ZipFile(E/'artifacts.zip') as archive:
        for item in report['collection']:
            data=archive.read(item['path']);assert sha(data)==item['sha256'];raw=json.loads(gzip.decompress(data))
            assert raw['identity']['collect'] and 0<=raw['case']['seed']<=99999
            assert len(raw['data'])==len(raw['records'])==raw['case']['steps']==item['teacher_queries']
            assert all(len(d['features'])==65 and 0<=d['phase']<5 for d in raw['data'])
        for name,candidates in report['runs'].items():
            assert len(candidates)==4
            for i,c in enumerate(candidates):
                assert c['round']==i and c['updates']==(1500 if i==0 else 750)
                assert c['score']==score(c['validation'])
                assert [v['seed'] for v in c['validation']]==report['plan']['validation']
                assert sha(archive.read(c['path']))==c['sha256']==archive.read(c['path']+'.sha256').decode().strip()
            assert max(candidates,key=lambda c:tuple(c['score']))==selection[name]
            tests=report['tests'][name];assert len(tests)==32 and [c['seed'] for c in tests]==report['plan']['final']
            for c in tests:
                data=archive.read(c['path']);assert sha(data)==c['sha256'];raw=json.loads(gzip.decompress(data));rows=raw['records']
                assert not raw['identity']['collect'] and raw['data']==[]
                assert len(rows)==c['steps'] and c['initial_payload_kg']==0 and rows[0]['state'][7]==0
                assert sha(struct.pack('<102d',*rows[0]['state']))==identities[c['seed']]
                for a,b in zip(rows,rows[1:]):assert a['next_state']==b['state']
                assert rows[-1]['next_state'][8]==c['delivered_kg'] and c['max_mass_residual_kg']<1e-7
    for method in ('memoryless','phase_memory'):
        admitted=all(score(report['tests'][f'{method}-{seed}'])[0]>=28 and sum(collision(c) for c in report['tests'][f'{method}-{seed}'])<=1 for seed in (7,19,41))
        assert admitted==report['admitted'][method]
    ordering=json.loads((E/'consumption.json').read_text());assert ordering['selection_mtime_ns']<ordering['first_final_mtime_ns']
    replay=json.loads((E/'independent-replay.json').read_text());assert replay['teacher_queries']==0
    assert sum(r['selected_validation_cases'] for r in replay['runs'])==96 and sum(r['final_traces'] for r in replay['runs'])==192
    assert replay['max_state_error']==replay['max_action_error']==replay['max_raw_reward_error']==0
    assert replay['trace_decisions']==report['test_decisions']
    with zipfile.ZipFile(E/'source.zip') as z:
        digest=hashlib.sha256()
        for name in sorted(n for n in z.namelist() if n.startswith('kessel_training/') and n.endswith('.py')):digest.update(Path(name).name.encode());digest.update(z.read(name))
        assert digest.hexdigest()==report['plan']['source']['package_sha256']
    admitted=[m for m in ('memoryless','phase_memory') if report['admitted'][m]]
    if admitted:
        catalogue=json.loads((DEMO/'catalogue.json').read_text());assert catalogue['admitted'] and catalogue['method']==admitted[0]
        assert catalogue['report_sha256']==sha((E/'report.json').read_bytes()) and catalogue['final_cases']==96 and len(catalogue['recordings'])==3
        method=admitted[0];assert catalogue['successes']==sum(score(report['tests'][f'{method}-{s}'])[0] for s in (7,19,41))
        for record in catalogue['recordings']:
            data=(DEMO/record['path']).read_bytes();assert sha(data)==record['sha256'];actual=json.loads(data)
            assert actual['frames'][0]['state'][7]==0 and actual['frames'][-1]['state'][8]>=2000
            selected=selection[f'{method}-{record["training_seed"]}'];assert record['checkpoint_sha256']==actual['checkpoint_sha256']==selected['sha256']
            good=[c for c in report['tests'][f'{method}-{record["training_seed"]}'] if c['full_success']]
            assert actual['case']['seed']==min(c['seed'] for c in good)
    print('Phase study verified: six policies, 192 final cases, teacher-free independent replay and admission-bound demo')


if __name__=='__main__':verify()
