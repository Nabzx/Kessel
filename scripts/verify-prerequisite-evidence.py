"""Check prerequisite evidence identities, accounting and trajectory continuity."""

import gzip
import hashlib
import json
import math
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    repo = Path(__file__).resolve().parents[1]
    root = repo / 'docs/phase-11/prerequisite-evidence'
    manifest = json.loads((root / 'files.json').read_text())
    assert {p.name for p in root.iterdir() if p.is_file()} == set(manifest) | {'files.json'}
    for name, digest in manifest.items():
        assert (root / name).resolve().is_relative_to(root.resolve())
        assert sha(root / name) == digest, f'changed prerequisite evidence: {name}'
    report = json.loads((root / 'report.json').read_text())
    assert report['schema'] == 'learning-prerequisites-v1'
    assert not report['source']['training_dirty']
    assert report['protocol']['task_training_updates'] == 0
    old_root = repo / 'docs/phase-11/policy-followup-evidence'
    assert sha(old_root / 'report.json') == report['original_report_sha256']
    old = json.loads((old_root / 'report.json').read_text())
    coverage = report['teacher_coverage']
    assert sha(old_root / 'teacher.npz') == report['teacher_sha256'] == old['teacher_sha256']
    assert coverage['episodes'] == old['teacher_episodes']
    assert sum(coverage['phase_counts']) == sum(x['rows'] for x in coverage['episodes']) == coverage['rows']
    assert coverage['unique_teacher_reference_decisions'] == coverage['reconstruction_diagnostic_decisions'] == coverage['rows']
    assert len(coverage['observation_min']) == len(coverage['observation_max']) == 65
    assert all(-1 <= low <= high <= 1 for low, high in zip(coverage['action_min'], coverage['action_max']))
    comparisons = report['candidate_comparisons']
    expected = {(r['seed'], label) for r in old['runs'] if r['method'] == 'bc_ppo'
                for label in report['protocol']['candidate_labels']}
    assert {(r['training_seed'], r['candidate']) for r in comparisons} == expected
    assert len(comparisons) == len(expected)
    probes = list(report['reference_stage_probes'])
    for comparison in comparisons:
        run = next(r for r in old['runs'] if r['seed'] == comparison['training_seed'] and r['method'] == 'bc_ppo')
        candidate = next(c for c in run['candidates'] if c['label'] == comparison['candidate'])
        assert sha(old_root / comparison['checkpoint']) == comparison['checkpoint_sha256'] == candidate['sha256']
        assert comparison['retained_complete_validation'] == candidate['validation']
        assert abs(sum(comparison['per_action_mse']) / 4 - comparison['training_pair_action_mse']) < 1e-12
        assert sum(p['rows'] for p in comparison['per_phase']) == coverage['rows']
        phase_mse = sum(p['rows'] * p['action_mse'] for p in comparison['per_phase']) / coverage['rows']
        assert abs(phase_mse - comparison['training_pair_action_mse']) < 1e-12
        assert len(comparison['latent_action_std']) == 4
        assert all(math.isfinite(x) and x > 0 for x in comparison['latent_action_std'])
        selected_probes = comparison.get('stage_probes', [])
        if comparison['training_seed'] == report['protocol']['stage_probe_training_seed']:
            assert {(p['stage'], p['seed']) for p in selected_probes} == {
                (stage, seed) for stage in report['protocol']['stages'] for seed in report['protocol']['evaluation_seeds']}
        else:
            assert not selected_probes
        probes.extend(selected_probes)
    assert len(probes) == 24
    for probe in probes:
        trace = json.loads(gzip.decompress((root / probe['trace']).read_bytes()))
        assert len(trace['records']) == probe['steps'] > 0
        assert {k: v for k, v in trace.items() if k != 'records'} == {k: v for k, v in probe.items() if k != 'trace'}
        assert trace['max_mass_residual_kg'] < 1e-7
        assert trace['records'][0]['state'][7] == trace['initial_payload_kg']
        assert trace['records'][0]['t_s'] == 0
        for previous, current in zip(trace['records'], trace['records'][1:]):
            assert previous['next_state'] == current['state']
            assert previous['t_s'] < current['t_s']
        assert abs(trace['records'][-1]['next_state'][8] - trace['delivered_kg']) < 1e-9
        assert trace['full_success'] == (trace['stage'] == 'complete' and trace['initial_payload_kg'] == 0 and trace['reason'] == 'success')
    smokes = report['cpu_execution_smokes']
    assert sum(s['counts']['environment_steps'] for s in smokes) == report['protocol']['timing_smoke_reference_decisions']
    assert sum(s['counts']['rollouts'] for s in smokes) == report['protocol']['timing_smoke_rollouts']
    assert all(s['source'] == report['source'] for s in smokes)
    assert all(s['counts']['environment_steps'] == s['num_envs'] * s['rollout_steps'] * s['counts']['rollouts'] for s in smokes)
    print(f'Prerequisite evidence verified: {len(comparisons)} candidate comparisons, {len(probes)} stage traces and {len(smokes)} bounded smokes')


if __name__ == '__main__':
    verify()
