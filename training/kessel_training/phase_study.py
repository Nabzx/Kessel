"""ADR-0061 shared-data imitation comparison. No teacher control during evaluation."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch.nn import functional as F

from . import checkpoints
from .contracts import canonical_json
from .controller import ReferenceController
from .environment import LoaderEnv
from .evaluate import source_identity
from .full_cycle import collision, full_score
from .phase_memory import PhaseActor, features
from .policy import configure_cpu
from .scenarios import family
from .wm_state import pack

METHODS = ('memoryless', 'phase_memory')
SEEDS = (7, 19, 41)
VALIDATION = list(range(108100, 108116))
FINAL = list(range(209800, 209832))


def write_json(path, value):
    if path.exists():
        raise FileExistsError(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n'); temporary.replace(path)


def episode(seed, actor=None, collect=False, record=False):
    if collect and not 0 <= seed <= 99999:
        raise ValueError('teacher queries are restricted to training scenes')
    if not collect and actor is None:
        raise ValueError('evaluation requires an actor; no reference fallback')
    env = LoaderEnv(1, seed=seed, scene=family('standard')[0])
    teacher = ReferenceController(1) if collect or actor is None else None
    if actor is not None:
        actor.reset()
    data, trace, steps, residual = [], [], 0, 0.
    while True:
        obs = env.observe()
        target = teacher.act(obs) if teacher is not None else None
        action = target if actor is None else actor.act(obs)
        if collect:
            if actor is not None and not np.array_equal(actor.memory.phase, teacher.phase):
                raise AssertionError('observation memory differs from teacher phase')
            data.append({'features': features(obs)[0].tolist(), 'action': target[0].tolist(), 'phase': int(teacher.phase[0])})
        state = pack(env)[0].tolist() if record else None
        _, reward, term, trunc, _ = env.step(action); steps += 1
        residual = max(residual, abs(float((env.pile.mass()+env.payload+env.delivered+env.spilled-env.pile.initial_mass)[0])))
        if record:
            trace.append({'state': state, 'action': action[0].tolist(), 'phase': int(actor.memory.phase[0]) if actor is not None else int(teacher.phase[0]), 'next_state': pack(env)[0].tolist(), 'raw_reward': float(reward[0])})
        if (term | trunc).any():
            break
    if residual > 1e-7:
        raise AssertionError('ledger diverged')
    case = {'seed': seed, 'stage': 'complete', 'initial_payload_kg': 0., 'steps': steps,
        'reason': str(env.reason[0]), 'full_success': str(env.reason[0]) == 'success',
        'delivered_kg': float(env.delivered[0]), 'peak_load_kg': float(env.peak_load[0]),
        'cycle_s': float(env.elapsed[0]), 'max_mass_residual_kg': residual}
    return {'case': case, 'data': data, 'records': trace}


def save_episode(path, seed, actor=None, collect=False, record=False):
    identity = {'seed': seed, 'collect': collect, 'record': record, 'actor': 'reference_teacher' if actor is None else hashlib.sha256(str(actor.conditioned).encode()+b''.join(v.detach().numpy().tobytes() for v in actor.state_dict().values())).hexdigest()}
    if path.exists():
        digest = path.with_suffix(path.suffix+'.sha256').read_text().strip()
        if checkpoints.sha256(path) != digest:
            raise ValueError('cached episode changed')
        cached = json.loads(gzip.decompress(path.read_bytes()))
        if cached['identity'] != identity:
            raise ValueError('cached episode identity differs')
        return cached
    result = episode(seed, actor, collect, record)
    result['identity'] = identity
    payload = gzip.compress(canonical_json(result).encode(), mtime=0)
    temporary = path.with_suffix(path.suffix+'.tmp'); temporary.write_bytes(payload); temporary.replace(path)
    path.with_suffix(path.suffix+'.sha256').write_text(checkpoints.sha256(path)+'\n')
    return result


def load_actor(path):
    state = checkpoints.load(path)
    actor = PhaseActor(state['method'] == 'phase_memory'); actor.load_state_dict(state['actor'])
    actor.eval(); return actor, state


def fit(directory, method, seed, round_index, data, previous=None, updates=None, on_checkpoint=None):
    target = 1500 if round_index == 0 else 750
    if updates is not None:
        target = updates
    directory.mkdir(parents=True, exist_ok=True)
    generator = configure_cpu(seed)
    actor = PhaseActor(method == 'phase_memory')
    optimiser = torch.optim.Adam(actor.parameters(), lr=.001)
    done, losses = 0, []
    identity = {'source_sha256': source_identity()['package_sha256'], 'method': method, 'seed': seed, 'round': round_index,
                'data_sha256': __import__('hashlib').sha256(canonical_json(data).encode()).hexdigest(), 'target_updates': target}
    if previous is not None:
        old = checkpoints.load(previous)
        if old['method'] != method or old['identity']['seed'] != seed or old['identity']['source_sha256'] != identity['source_sha256']:
            raise ValueError('previous-round policy identity differs')
        actor.load_state_dict(old['actor']); optimiser.load_state_dict(old['optimiser'])
        generator.set_state(old['generator'])
    pointer = directory/'latest.json'
    if pointer.exists():
        selected = json.loads(pointer.read_text())
        if checkpoints.sha256(directory/selected['path']) != selected['sha256']:
            raise ValueError('training checkpoint pointer differs')
        old = checkpoints.load(directory/selected['path'])
        if old['software'] != {'torch': str(torch.__version__), 'numpy': np.__version__}:
            raise ValueError('resume numerical libraries differ')
        if old['identity'] != identity:
            raise ValueError('training resume identity changed')
        actor.load_state_dict(old['actor']); optimiser.load_state_dict(old['optimiser'])
        generator.set_state(old['generator']); done, losses = old['updates'], old['losses']
    x = torch.tensor([d['features'] for d in data], dtype=torch.float32)
    phases = torch.tensor([d['phase'] for d in data], dtype=torch.long)
    y = torch.tensor([d['action'] for d in data], dtype=torch.float32)
    counts = torch.bincount(phases, minlength=5)
    weights = 1/counts[phases].float(); weights /= weights.sum()
    while done < target:
        stop = min(done+250, target)
        for _ in range(done, stop):
            indices = torch.multinomial(weights, 512, replacement=True, generator=generator)
            prediction = actor(x[indices], phases[indices]); loss = F.mse_loss(prediction, y[indices])
            optimiser.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(actor.parameters(), 1., error_if_nonfinite=True); optimiser.step()
            if not torch.isfinite(loss):
                raise FloatingPointError('nonfinite imitation loss')
            losses.append(float(loss.detach()))
        done = stop
        path = directory/f'update-{done:06}.pt'
        digest = checkpoints.save(path, {'kind': 'phase-imitation-v1', 'identity': identity, 'method': method,
            'actor': actor.state_dict(), 'optimiser': optimiser.state_dict(), 'generator': generator.get_state(),
            'updates': done, 'losses': losses, 'phase_counts': counts.tolist(),
            'software': {'torch': str(torch.__version__), 'numpy': np.__version__}})
        tmp = pointer.with_suffix('.tmp'); tmp.write_text(json.dumps({'path': path.name, 'sha256': digest})+'\n'); tmp.replace(pointer)
        if on_checkpoint is not None:
            on_checkpoint(done)
    return directory/f'update-{target:06}.pt'


def study(output, reservation):
    output.mkdir(parents=True, exist_ok=True)
    source = source_identity()
    if source['training_dirty']:
        raise ValueError('commit training source before study')
    reserved = json.loads(reservation.read_text())
    if not reserved['verified']:
        raise ValueError('unverified reservation')
    plan = {'kind': 'phase-imitation-v1', 'source': source, 'reservation_sha256': checkpoints.sha256(reservation),
        'validation': VALIDATION, 'final': FINAL, 'methods': list(METHODS), 'seeds': list(SEEDS),
        'updates': [1500, 750, 750, 750], 'teacher_cap': 120000, 'wall_cap_s': 5400, 'test_reserve_s': 600}
    plan_path = output/'plan.json'
    if plan_path.exists():
        original = json.loads(plan_path.read_text()); plan['source'] = original['source']
        if original != plan or source['package_sha256'] != original['source']['package_sha256']:
            raise ValueError('source/plan changed')
    else:
        write_json(plan_path, plan)
    started = time.perf_counter()
    clock = output/'clock.json'
    elapsed_before = json.loads(clock.read_text())['elapsed_s'] if clock.exists() else 0.
    def charge():
        clock.write_text(json.dumps({'elapsed_s': elapsed_before+time.perf_counter()-started})+'\n')
    def allowed(test=False):
        return elapsed_before+time.perf_counter()-started < 5400-(0 if test else 600)
    data, collection, runs = [], [], {f'{m}-{s}': [] for m in METHODS for s in SEEDS}
    for i in range(4):
        if not allowed():
            break
        if i == 0:
            tasks = [(f'teacher-{s}', s, None) for s in range(19000, 19032)]
        else:
            tasks = []
            for name in runs:
                actor, _ = load_actor(output/runs[name][-1]['path'])
                for seed in range(19100+(i-1)*16, 19108+(i-1)*16):
                    tasks.append((f'round-{i}-{name}-{seed}', seed, actor))
        for name, seed, actor in tasks:
            if not allowed():
                raise RuntimeError('collection wall cap; retain committed cases')
            path = output/(name+'.json.gz')
            result = save_episode(path, seed, actor, collect=True, record=True)
            data.extend(result['data']); collection.append(result['case'] | {'path': path.name, 'sha256': checkpoints.sha256(path), 'teacher_queries': result['case']['steps']})
            if sum(c['steps'] for c in collection) > 120000:
                raise RuntimeError('teacher budget exceeded')
            charge()
        print('Round',i,'shared pairs',len(data),'phase coverage',np.bincount([d['phase'] for d in data],minlength=5).tolist(),flush=True)
        for method in METHODS:
            for seed in SEEDS:
                name = f'{method}-{seed}'; previous = output/runs[name][-1]['path'] if runs[name] else None
                def progress(_):
                    charge()
                    if not allowed():
                        raise RuntimeError('fit wall cap; last optimiser transaction retained')
                checkpoint = fit(output/f'round-{i}-{name}', method, seed, i, data, previous, on_checkpoint=progress)
                actor, state = load_actor(checkpoint)
                cases = []
                for scenario in VALIDATION:
                    if not allowed():
                        raise RuntimeError('validation wall cap; partial candidate cannot select')
                    result = save_episode(output/f'validation-{i}-{name}-{scenario}.json.gz', scenario, actor)
                    cases.append(result['case']); charge()
                candidate = {'round': i, 'path': checkpoint.relative_to(output).as_posix(),
                    'sha256': checkpoints.sha256(checkpoint), 'validation': cases, 'score': full_score(cases),
                    'updates': state['updates'], 'last_loss': state['losses'][-1]}
                runs[name].append(candidate)
                print(name,'round',i,'validation',candidate['score'],flush=True)
        write_json(output/f'round-{i}-report.json', {'runs': runs, 'collection': collection}) if not (output/f'round-{i}-report.json').exists() else None
    if not all(runs.values()):
        raise RuntimeError('no selectable complete candidate')
    selection = {name: max(candidates, key=lambda c: tuple(c['score'])) for name, candidates in runs.items()}
    selection_path = output/'selection.json'
    if selection_path.exists() and json.loads(selection_path.read_text()) != selection:
        raise ValueError('frozen selection changed')
    if not selection_path.exists():
        write_json(selection_path, selection)
    tests = {}
    for name, candidate in selection.items():
        actor, _ = load_actor(output/candidate['path']); tests[name] = []
        for seed in FINAL:
            if not allowed(True):
                raise RuntimeError('final wall cap; retain incomplete cases without admission')
            path = output/f'final-{name}-{seed}.json.gz'
            result = save_episode(path, seed, actor, record=True)
            tests[name].append(result['case'] | {'path': path.name, 'sha256': checkpoints.sha256(path)}); charge()
        print('Final',name,full_score(tests[name]),flush=True)
    report = {'plan': plan, 'collection': collection, 'runs': runs, 'selection': selection, 'tests': tests,
        'teacher_queries': sum(c['teacher_queries'] for c in collection),
        'collection_decisions': sum(c['steps'] for c in collection),
        'supervised_updates': sum(c['updates'] for candidates in runs.values() for c in candidates),
        'validation_decisions': sum(c['steps'] for candidates in runs.values() for candidate in candidates for c in candidate['validation']),
        'test_decisions': sum(c['steps'] for cases in tests.values() for c in cases),
        'admitted': {m: all(full_score(tests[f'{m}-{s}'])[0] >= 28 and sum(collision(c) for c in tests[f'{m}-{s}']) <= 1 for s in SEEDS) for m in METHODS},
        'elapsed_s': elapsed_before+time.perf_counter()-started}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Admission',report['admitted'],flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--reservation',type=Path,required=True)
    args = parser.parse_args();study(args.output,args.reservation)
