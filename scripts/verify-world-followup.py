"""Integrity and budget checks independent of the training runtime."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'docs/phase-11/world-followup-evidence'
for name,digest in json.loads((root/'integrity.json').read_text()).items():
 assert (root/name).is_relative_to(root)
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
r=json.loads((root/'report.json').read_text());assert not r['source']['training_dirty']
for model in r['models'].values():
 assert model['fit']['normalisers_fitted_on']=='training_only'
 assert not model['fit']['source']['training_dirty']
 assert hashlib.sha256((root/model['path']).read_bytes()).hexdigest()==model['sha256']
for run in r['assistance']['treatments']:
 assert run['online_reference_decisions']+run['offline_reference_decisions']==4096
 assert all(not c['full_success'] and c['initial_payload_kg']==0 for c in run['test'])
assert r['assistance']['offline_collection']['fresh_source']
assert r['observable']['hidden_material_prediction'] is None
print('World-model hashes, clean source, observable boundary and equal reference budgets verified')
