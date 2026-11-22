"""Verify complete shift coverage, provenance, trace ledgers and honest admission."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import zipfile

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'docs/phase-11/shift-evidence'

def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def verify():
    report=json.loads((E/'report.json').read_text());plan=report['plan']
    reservation=json.loads((E/'reservation.json').read_text())
    assert reservation['verified'] and not reservation['zip_hits'] and not reservation['zip_errors']
    assert plan['reservation_sha256']==sha((E/'reservation.json').read_bytes())
    assert plan['protocol_sha256']==sha((ROOT/'docs/adr/0062-interactive-synthetic-runtime.md').read_bytes())
    assert plan['policy_updates']==plan['teacher_queries_for_learned']==0
    assert plan['seeds']==list(range(206200,206208))
    expected={(f,s,seed) for f in plan['families'] for s in plan['sources'] for seed in plan['seeds']}
    assert len(expected)==416
    assert {(r['family'],r['source'],r['seed']) for r in report['cases']}==expected
    assert len(report['cases'])==416
    selection=json.loads((ROOT/'docs/phase-11/phase-memory-evidence/selection.json').read_text())
    assert sha((E/'traces.zip').read_bytes())==report['trace_archive_sha256']
    decisions=0;maximum_mass=0.
    with zipfile.ZipFile(E/'traces.zip') as z:
        assert set(z.namelist())=={r['trace'] for r in report['cases']}
        for case in report['cases']:
            raw=z.read(case['trace']);assert sha(raw)==case['sha256']
            trace=json.loads(gzip.decompress(raw));assert trace['identity']==case['identity']
            assert trace['scenario']==case['scenario'] and trace['source']==case['source']
            model=None if case['source']=='reference' else selection[case['source']]['sha256']
            assert model==case['checkpoint_sha256']==trace['checkpoint_sha256']
            assert trace['outcome']=={k:case[k] for k in trace['outcome']}
            assert case['done'] and case['initial_payload_kg']==0 and case['decisions']<=600
            frames=trace['frames'];assert len(frames)==case['decisions']+1
            assert sha(struct.pack('<102d',*frames[0]['state']))==case['scenario']['initial_state_sha256']
            assert frames[0]['state'][7]==0 and frames[-1]['state'][8]==case['delivered_kg']
            assert case['full_success']==(case['reason']=='success')
            if case['full_success']:assert not case['collision'] and case['delivered_kg']>=2000
            for i,frame in enumerate(frames):
                s=frame['state'];assert len(s)==102 and all(math.isfinite(v) for v in s)
                residual=abs(sum(s[15:79])*.25*s[81]+sum(s[7:10])-s[82]);maximum_mass=max(maximum_mass,residual)
                if i<len(frames)-1:
                    assert frame['next_state']==frames[i+1]['state']
                    assert len(frame['action'])==4 and all(math.isfinite(a) and abs(a)<=1 for a in frame['action'])
                    assert math.isfinite(frame['reward']) and 0<=frame['phase']<=4
            decisions+=case['decisions']
    assert maximum_mass<1e-7 and report['max_mass_residual_kg']<1e-7
    assert decisions==report['evaluation_decisions']==report['independent_replay_decisions']<=249600
    assert report['max_independent_state_error']==0
    for summary in report['summaries']:
        cases=[r for r in report['cases'] if (r['family'],r['source'])==(summary['family'],summary['source'])]
        assert len(cases)==summary['cases']==8
        assert sum(r['full_success'] for r in cases)==summary['successes']
        assert sum(r['collision'] for r in cases)==summary['collisions']
        assert sum(summary['reasons'].values())==8
    for family in plan['families']:
        rows=[r for r in report['summaries'] if r['family']==family and r['source']!='reference']
        assert report['family_admission'][family]==all(r['successes']>=7 and r['collisions']==0 for r in rows)
    with zipfile.ZipFile(E/'source.zip') as source:
        for name,digest in plan['lab_files'].items():assert sha(source.read('training/kessel_lab/'+name))==digest
    files=json.loads((E/'files.json').read_text())
    for name,digest in files.items():assert sha((ROOT/name).read_bytes())==digest,name
    model=json.loads((ROOT/'docs/phase-11/working-policy-model-evidence/report.json').read_text())
    assert model['plan']['new_model_updates']==model['plan']['actor_updates']==model['assisted_updates']==0
    assert model['coverage']['test_episodes']==104
    assert model['calibration_decisions']<=4800
    assert len(model['families'])==13 and model['observable']['excluded_terminal_rows']==104
    if not model['assistance_qualified']:assert model['assistance_decision'].startswith('no-go')
    log_report=json.loads((ROOT/'docs/phase-11/continuation-evidence/recorder.json').read_text())
    assert sha((ROOT/'docs/phase-11/continuation-evidence/shadow.jsonl').read_bytes())==log_report['sha256']
    assert log_report['applied_machine_commands']==0 and log_report['explicit_tail_recovery'] and log_report['quota_preserves_records']
    qa=json.loads((ROOT/'docs/phase-11/live-demo/evidence/report.json').read_text())
    assert not qa['errors'] and len(qa['profiles'])==3 and qa['nominal']['full_success'] and not qa['blocked']['full_success']
    print(f'PASS: all 416 shift cases, {decisions} decisions, exact replay, source archives and local runtime evidence')

if __name__=='__main__':verify()
