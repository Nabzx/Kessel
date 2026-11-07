"""Verify retained policy comparisons and their explicit reference budgets."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'docs/phase-11/policy-followup-evidence'
r=json.loads((root/'report.json').read_text())
assert not r['source']['training_dirty'] and len(r['runs'])==12
assert hashlib.sha256((root/'teacher.npz').read_bytes()).hexdigest()==r['teacher_sha256']
for run in r['runs']:
 c=run['counters'];assert c['online_reference_decisions']+c['offline_reference_decisions']==4096
 chosen=max(run['candidates'],key=lambda x:(tuple(x['score']),x['rollout']))
 assert chosen['sha256']==run['selected']['sha256']
 for item in run['candidates']+run['traces']:
  path=root/item['path'];assert path.is_file()
  assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
 for case in run['test']:
  assert case['initial_payload_kg']==0 and case['valid_start']
  assert not case['full_success'] and case['delivered_kg']==0
print('12 runs: budgets, validation selection, hashes and held-out failures verified')
