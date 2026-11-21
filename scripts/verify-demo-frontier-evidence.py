"""Verify compact sensor, scenario, model and runtime research evidence."""

import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / 'docs/phase-11/demo-frontier-evidence'
manifest = json.loads((folder / 'files.json').read_text())
for relative, expected in manifest.items():
    path = root / relative
    assert path.resolve().is_relative_to(root.resolve())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, relative
r = json.loads((folder / 'report.json').read_text())
assert r['schema'] == 'demo-frontier-audit-v1' and not r['source']['training_dirty']
assert len(r['source']['package_sha256']) == 64 and r['source']['git_commit']
assert r['sensor_protocol']['executed_reference_decisions'] == 9 * 2 * 32
assert len(r['sensors']) == 4
for row in r['sensors']:
    assert 0 <= row['valid_samples'] <= row['possible_samples'] == 1600
    assert all(row[k] <= 1e-12 for k in ('physics_max_error_vs_clean', 'communications_physics_max_error', 'communications_observation_max_error'))
assert r['seed_inventory']['errors'] == []
assert all(not c['reservation_verified'] for c in r['seed_inventory']['candidates'].values())
for card in r['scorecards']:
    name = {'reference-cycle-v1': 'reference', 'curriculum-followup-v1': 'curriculum', 'rl-study-v1-full-7': 'loader'}[card['run_id']]
    path = root / f'data/experiments/{name}-v1.json'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == card['bundle_sha256']
    bundle = json.loads(path.read_text())
    assert len(card['cases']) == len(bundle['episodes'])
    for case, episode in zip(card['cases'], bundle['episodes']):
        assert case['name'] == episode['name'] and case['outcome'] == episode['outcome']
        assert case['delivered_kg'] == episode['metrics']['delivered_kg']
        assert case['initial_payload_kg'] == episode['records'][0]['state'][7]
        assert case['complete_empty_start_success'] == (episode['outcome'] == 'success' and case['initial_payload_kg'] == 0)
path = root / 'docs/phase-11/world-followup-evidence/report.json'
assert hashlib.sha256(path.read_bytes()).hexdigest() == r['world_model_report_sha256']
wm = json.loads(path.read_text())
for name, summary in r['world_models'].items():
    for key in ('position_mae_m', 'mass_balance_mae_kg', 'reward_mae'):
        assert summary[key] == wm['models'][name]['raw']['one_step']['natural'][key]
    assert summary['supported_horizon'] == wm['models'][name]['raw']['calibration']['supported_horizon']
for name, event in r['event_failures'].items():
    assert all(value == wm['events']['test'][name][key] for key, value in event.items())
treatments = wm['assistance']['treatments']
assert r['assistance']['full_cycle_successes'] == sum(c['full_success'] for t in treatments for c in t['test'])
assert r['assistance']['critic_updates'] == sum(a['critic_update'] is not None for t in treatments for a in t['auxiliary_records'])
assert r['assistance']['imagined_transitions'] == sum(a['branches']['imagined_transitions'] for t in treatments for a in t['auxiliary_records'])
for filename in ('observation-record', 'evidence-admission'):
    contract = json.loads((root / f'docs/research/demo-contracts/{filename}.json').read_text())
    assert contract['status'] == 'research_proposal_not_implemented'
print('Demo frontier evidence verified: fixed-action sensor boundaries, provisional reservations, nine recorded cases and retained model facts')
