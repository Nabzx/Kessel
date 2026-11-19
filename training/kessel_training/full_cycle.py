"""Bounded ADR-0057 full-cycle comparison with provenance-bound evaluation."""
import argparse
from dataclasses import asdict, dataclass
import gzip
import hashlib
import json
from pathlib import Path
import signal
import statistics
import time

import numpy as np
import torch

from . import checkpoints
from .contracts import canonical_json
from .evaluate import source_identity
from .five_stage import FiveStageEnv, STAGES, advancement_gate
from .policy import ActorCritic, configure_cpu
from .ppo import PPO, PPOConfig, collect
from .retraction_pilot import PilotRun
from .scenarios import family
from .telemetry import scan
from .wm_state import pack

VALIDATION = list(range(108000, 108016))
FINAL_TEST = list(range(209900, 209932))
STOP = False


def policy_identity(policy):
    digest = hashlib.sha256()
    for name, value in sorted(policy.state_dict().items()):
        digest.update(name.encode()); digest.update(value.detach().numpy().tobytes())
    return digest.hexdigest()


def collision(case):
    return case['reason'] in ('tunnel_wall', 'tunnel_roof') or case['reason'].startswith('obstacle')


def full_score(cases):
    successes = [c for c in cases if c['full_success'] and c['reason'] == 'success' and c['delivered_kg'] >= 2000]
    return [len(successes), -sum(collision(c) for c in cases),
            -statistics.mean(c['cycle_s'] for c in successes) if successes else 0.]


def probe(policy, stage, seed, *, records=False):
    env = FiveStageEnv(1, seed=seed, scene=family('standard')[0], stage=stage, shaping=False)
    initial = pack(env)[0].copy()
    trace, steps, residual = [], 0, 0.
    while True:
        with torch.no_grad():
            action = policy.sample(policy.encode(env.observe()), deterministic=True)['action'].numpy()
        before = pack(env)[0].tolist() if records else None
        _, reward, term, trunc, info = env.step(action)
        steps += 1
        residual = max(residual, float(np.abs(env.pile.mass()+env.payload+env.delivered+
                                             env.spilled-env.pile.initial_mass).max()))
        if records:
            trace.append({'state': before, 'action': action[0].tolist(),
                          'next_state': pack(env)[0].tolist(), 'raw_reward': float(reward[0])})
        if (term | trunc).any():
            break
    if residual > 1e-7:
        raise AssertionError('evaluation material ledger differs')
    case = {'stage': stage, 'seed': seed, 'steps': steps, 'reason': str(env.reason[0]),
            'cycle_s': float(env.elapsed[0]), 'initial_payload_kg': float(initial[7]),
            'initial_state_sha256': hashlib.sha256(initial.astype('<f8').tobytes()).hexdigest(),
            'stage_success': bool(info['metrics']['stage_success'][0]),
            'full_success': bool(info['metrics']['full_success'][0]),
            'peak_load_kg': float(env.peak_load[0]), 'delivered_kg': float(env.delivered[0]),
            'spilled_kg': float(env.spilled[0]), 'max_mass_residual_kg': residual}
    return (case, trace) if records else case


@dataclass(frozen=True)
class Config:
    seed: int = 7
    method: str = 'plain'
    max_rollouts: int = 640
    stage_rollouts: int = 128
    max_wall_s: float = 1200
    test_reserve_s: float = 240

    def __post_init__(self):
        if self.method not in ('plain', 'curriculum') or type(self.seed) is not int or self.seed not in (7, 19, 41):
            raise ValueError('invalid study method/seed')
        if any(type(v) is not int or not 1 <= v <= limit for v, limit in
               ((self.max_rollouts, 640), (self.stage_rollouts, 128))):
            raise ValueError('training budget exceeds protocol')
        if not 0 < self.max_wall_s <= 1200 or not 0 < self.test_reserve_s < self.max_wall_s:
            raise ValueError('invalid study wall allowance')


class CycleRun(PilotRun):
    def __init__(self, directory, configuration, reservation_sha, validation_seeds=VALIDATION):
        self.wall_before, self.started = 0., time.perf_counter()
        self.directory = Path(directory); self.directory.mkdir(parents=True, exist_ok=True)
        self.config, self.reservation_sha = configuration, reservation_sha
        self.validation_seeds = list(validation_seeds)
        self.source = source_identity()
        self.generator = configure_cpu(configuration.seed)
        self.policy = ActorCritic(64, initial_log_std=[-.5]*4)
        self.algorithm = PPO(self.policy, PPOConfig())
        self.env = FiveStageEnv(4, seed=configuration.seed, scene=family('standard')[0],
            stage='fill' if configuration.method == 'curriculum' else 'complete',
            shaping=configuration.method == 'curriculum')
        self.counters = dict(rollouts=0, training_decisions=0, optimiser_minibatches=0,
            training_episodes=0, training_resets=4, stage_rollouts=0,
            validation_decisions=0, gate_decisions=0, test_decisions=0)
        self.candidates, self.gates, self.transitions = [], [], []
        self.phase, self.status, self.pending = 'initial', 'running', None
        self.stop_reason, self.selected, self.test_cases = None, None, []
        self.log = None

    def state(self):
        return {'kind': 'full-cycle-v1', 'configuration': asdict(self.config),
            'reservation_sha256': self.reservation_sha, 'validation_seeds': self.validation_seeds,
            'source': self.source, 'software': {'torch': str(torch.__version__), 'numpy': np.__version__},
            'actor_critic': self.policy.state_dict(), 'optimiser': self.algorithm.optimiser.state_dict(),
            'environment': checkpoints.environment_state(self.env), 'rng': checkpoints.random_state(self.generator),
            'counters': dict(self.counters), 'candidates': self.candidates, 'gates': self.gates,
            'transitions': self.transitions, 'phase': self.phase, 'status': self.status,
            'pending': self.pending, 'stop_reason': self.stop_reason, 'selected': self.selected,
            'test_cases': self.test_cases, 'wall_s': self.wall()}

    @classmethod
    def resume(cls, directory):
        started = time.perf_counter(); directory = Path(directory)
        pointer = json.loads((directory/'latest.json').read_text())
        path = directory/pointer['path']
        if checkpoints.sha256(path) != pointer['sha256']:
            raise ValueError('latest study pointer hash differs')
        state = checkpoints.load(path)
        if state.get('kind') != 'full-cycle-v1':
            raise ValueError('wrong checkpoint kind')
        run = cls(directory, Config(**state['configuration']), state['reservation_sha256'], state['validation_seeds'])
        if run.source['package_sha256'] != state['source']['package_sha256'] or run.source['training_dirty']:
            raise ValueError('resume requires exact clean source')
        if state['software'] != {'torch': str(torch.__version__), 'numpy': np.__version__}:
            raise ValueError('numerical library versions changed')
        run.policy.load_state_dict(state['actor_critic'])
        run.algorithm.optimiser.load_state_dict(state['optimiser'])
        checkpoints.restore_environment(run.env, state['environment'])
        checkpoints.restore_random_state(run.generator, state['rng'])
        for name in ('counters', 'candidates', 'gates', 'transitions', 'phase', 'status', 'pending',
                     'stop_reason', 'selected', 'test_cases', 'source'):
            setattr(run, name, state[name])
        run.wall_before = state['wall_s']+time.perf_counter()-started
        run.started = time.perf_counter(); run.open_log()
        return run

    def commit(self, kind, payload=None, label=None):
        self.log.append(kind, {'counters': dict(self.counters), 'wall_s': self.wall(),
            'phase': self.phase, 'stage': self.env.stage, 'status': self.status, **(payload or {})})
        return self.save(label or f'transaction-{self.log.sequence:06}')

    def training_time_available(self):
        return self.wall() < self.config.max_wall_s-self.config.test_reserve_s

    def request_full(self, after):
        decisions = self.counters['training_decisions']
        if any(c['training_decisions'] == decisions for c in self.candidates):
            self.phase = after
            return
        self.pending = {'purpose': 'full', 'policy_sha256': policy_identity(self.policy),
                        'training_decisions': decisions, 'cases': [], 'after': after}
        self.phase = 'evaluate'

    def iterate(self):
        batch = collect(self.env, self.policy, 64, self.generator)
        update = self.algorithm.update(batch, self.generator)
        c = self.counters
        c['rollouts'] += 1; c['stage_rollouts'] += 1; c['training_decisions'] += 256
        c['optimiser_minibatches'] += update['minibatch_updates']
        c['training_episodes'] += len(batch.episodes); c['training_resets'] += len(batch.episodes)
        self.env.history = (self.env.history+[bool(e['stage_success']) for e in batch.episodes])[-32:]
        self.phase = 'schedule'
        self.commit('rollout', {'reward_components': batch.reward_components,
            'mean_step_reward': float(batch.rewards.mean()), 'update': update,
            'episodes': batch.episodes, 'latent_std': self.policy.log_std.detach().exp().tolist()})

    def schedule(self):
        c = self.counters
        if (self.config.method == 'curriculum' and self.env.stage != 'complete'
                and c['stage_rollouts'] % 16 == 0 and len(self.env.history) == 32
                and sum(self.env.history) >= 23):
            self.pending = {'purpose': 'gate', 'policy_sha256': policy_identity(self.policy),
                'training_decisions': c['training_decisions'], 'cases': [],
                'stages': list(STAGES[:STAGES.index(self.env.stage)+1])}
            self.phase = 'evaluate'
        else:
            self.finish_schedule(False)

    def finish_schedule(self, transitioned):
        c = self.counters
        if self.config.method == 'curriculum' and c['stage_rollouts'] >= self.config.stage_rollouts:
            self.stop_reason = 'stage_budget_complete' if self.env.stage == 'complete' else 'stage_gate_failed'
        if c['rollouts'] >= self.config.max_rollouts:
            self.stop_reason = self.stop_reason or 'training_budget_complete'
        if self.stop_reason:
            self.phase = 'finalise'
        elif c['rollouts'] % 32 == 0 or transitioned:
            self.request_full('train')
        else:
            self.phase = 'train'

    def evaluate_case(self):
        p = self.pending
        if p['policy_sha256'] != policy_identity(self.policy) or p['training_decisions'] != self.counters['training_decisions']:
            raise ValueError('validation policy provenance changed')
        if not self.training_time_available():
            self.stop_reason = 'training_wall_cap'
            self.commit('partial_validation', {'batch': p})
            self.pending = None; self.phase = 'freeze'
            return
        stages = ['complete'] if p['purpose'] == 'full' else p['stages']
        if len(p['cases']) == len(stages)*len(self.validation_seeds):
            self.complete_evaluation(p)
            return
        index = len(p['cases'])
        stage = stages[index//len(self.validation_seeds)]
        seed = self.validation_seeds[index % len(self.validation_seeds)]
        case = probe(self.policy, stage, seed)
        case['split'] = 'validation'; p['cases'].append(case)
        counter = 'validation_decisions' if p['purpose'] == 'full' else 'gate_decisions'
        self.counters[counter] += case['steps']
        self.commit('validation_case', {'purpose': p['purpose'], 'case': case,
                                      'policy_sha256': p['policy_sha256']})
        if len(p['cases']) < len(stages)*len(self.validation_seeds):
            return
        self.complete_evaluation(p)

    def complete_evaluation(self, p):
        if p['purpose'] == 'full':
            candidate = {'training_decisions': p['training_decisions'], 'rollout': self.counters['rollouts'],
                'policy_sha256': p['policy_sha256'], 'score': full_score(p['cases']),
                'validation': p['cases'], 'path': f'candidate-{self.counters["rollouts"]:06}.pt'}
            self.candidates.append(candidate); self.phase = p['after']; self.pending = None
            self.commit('full_validation', {'candidate': candidate}, label=candidate['path'][:-3])
            print(self.config.method, self.config.seed, 'decisions', self.counters['training_decisions'],
                  'stage', self.env.stage, 'full', candidate['score'], 'wall', round(self.wall(), 1), flush=True)
        else:
            self.apply_gate(p)

    def apply_gate(self, batch):
        if batch['policy_sha256'] != policy_identity(self.policy):
            raise ValueError('gate evaluated a different policy')
        required = STAGES[:STAGES.index(self.env.stage)+1]
        expected = [(s, n) for s in required for n in self.validation_seeds]
        if [(c['stage'], c['seed']) for c in batch['cases']] != expected or len(self.validation_seeds) != 16:
            raise ValueError('gate case provenance differs')
        validation = {s: [bool(c['stage_success']) for c in batch['cases'] if c['stage'] == s] for s in required}
        gate = advancement_gate(self.env.stage, self.env.history, validation,
                                self.counters['stage_rollouts']*256)
        gate.update(policy_sha256=batch['policy_sha256'], cases=batch['cases'],
                    training_decisions=self.counters['training_decisions'])
        self.gates.append(gate)
        transitioned = gate['advance']
        if transitioned:
            old = self.env.stage
            discarded = int((~(self.env.terminated | self.env.truncated)).sum())
            self.env.set_stage(STAGES[STAGES.index(old)+1])
            self.counters['stage_rollouts'] = 0; self.counters['training_resets'] += 4
            self.transitions.append({'from': old, 'to': self.env.stage,
                'training_decisions': self.counters['training_decisions'],
                'policy_sha256': batch['policy_sha256'], 'discarded_partial_slots': discarded})
        self.pending = None
        self.finish_schedule(transitioned)
        self.commit('gate', {'gate': gate, 'transitioned': transitioned})

    def tick(self):
        if self.phase == 'initial':
            self.request_full('train')
        elif self.phase == 'train':
            if not self.training_time_available():
                self.stop_reason = 'training_wall_cap'; self.phase = 'finalise'
            else:
                self.iterate()
        elif self.phase == 'schedule':
            self.schedule()
        elif self.phase == 'evaluate':
            self.evaluate_case()
        elif self.phase == 'finalise':
            self.request_full('freeze')
        elif self.phase == 'freeze':
            if not self.candidates:
                raise RuntimeError('no complete initial validation candidate; abort study')
            chosen = max(self.candidates, key=lambda c: tuple(c['score']))
            self.selected = chosen | {'sha256': checkpoints.sha256(self.directory/chosen['path'])}
            self.status = self.stop_reason
            self.phase = 'frozen'
            self.commit('freeze', {'selected': self.selected})
        else:
            raise RuntimeError('not a training phase')

    def train(self):
        if self.log is None:
            self.open_log()
        while self.phase not in ('frozen', 'done') and not STOP:
            self.tick()
        if STOP:
            self.commit('interrupted')
        self.pause_clock()

    def test(self, frozen):
        if frozen != self.selected:
            raise ValueError('test selection differs from frozen checkpoint')
        if self.phase == 'done':
            return
        self.start_clock()
        weights = checkpoints.load(self.directory/self.selected['path'])
        actor = ActorCritic(64); actor.load_state_dict(weights['actor_critic'])
        if policy_identity(actor) != self.selected['policy_sha256']:
            raise ValueError('selected weights differ')
        while len(self.test_cases) < 32 and not STOP:
            if self.wall() >= self.config.max_wall_s:
                break
            seed = FINAL_TEST[len(self.test_cases)]
            case, records = probe(actor, 'complete', seed, records=True)
            case['split'] = 'final_test'
            name = f'test-{seed}.json.gz'
            path = self.directory/name
            if path.exists():
                raise ValueError('uncommitted test trace exists; refusing ambiguous recovery')
            path.write_bytes(gzip.compress(canonical_json({'case': case, 'records': records}).encode(), mtime=0))
            self.counters['test_decisions'] += case['steps']
            self.test_cases.append(case | {'trace': name, 'trace_sha256': checkpoints.sha256(path)})
            self.commit('test_case', {'case': self.test_cases[-1], 'checkpoint_sha256': frozen['sha256']})
        if len(self.test_cases) == 32:
            self.phase = 'done'
        self.commit('test_stop', {'complete': len(self.test_cases) == 32,
                    'wall_overrun_s': max(0., self.wall()-self.config.max_wall_s)})
        self.pause_clock()

    def report(self):
        rows = scan(self.directory/'events.jsonl')
        return {'configuration': asdict(self.config), 'counters': self.counters, 'status': self.status,
            'phase': self.phase, 'wall_s': self.wall(), 'stage': self.env.stage,
            'history': self.env.history, 'gates': self.gates, 'transitions': self.transitions,
            'candidates': [c | {'sha256': checkpoints.sha256(self.directory/c['path'])} for c in self.candidates],
            'selected': self.selected, 'tests': self.test_cases, 'test_complete': len(self.test_cases) == 32,
            'capability_gate_passed': len(self.test_cases) == 32 and full_score(self.test_cases)[0] >= 28
                                      and sum(collision(c) for c in self.test_cases) <= 1,
            'curve': [r['payload'] for r in rows if r['kind'] == 'rollout'], 'log': self.log.summary()}


def study(output, reservation, resume=False):
    output, reservation = Path(output), Path(reservation)
    source = source_identity()
    if source['training_dirty']:
        raise ValueError('commit source before executing study')
    audit = json.loads(reservation.read_text())
    if not audit['final_test_verified_unused']:
        raise ValueError('final test audit failed')
    if output.exists() and not resume:
        raise FileExistsError('study exists; use explicit resume')
    output.mkdir(parents=True, exist_ok=True)
    plan = {'kind': 'full-cycle-v1', 'source': source, 'reservation_sha256': checkpoints.sha256(reservation),
        'configurations': [asdict(Config(seed, method)) for method in ('plain', 'curriculum') for seed in (7, 19, 41)],
        'validation_seeds': VALIDATION, 'final_test_seeds': FINAL_TEST,
        'selection': 'each run independently: complete validation successes, fewer collisions, shorter successful duration, earlier tie',
        'test_rule': 'freeze all six selections before any final policy test; report both arms without test-based reselection'}
    path = output/'plan.json'
    if path.exists():
        original = json.loads(path.read_text()); plan['source'] = original['source']
        if original != plan or original['source']['package_sha256'] != source['package_sha256']:
            raise ValueError('study plan changed')
    else:
        path.write_text(json.dumps(plan, indent=2)+'\n')
    runs = []
    for cfg in plan['configurations']:
        directory = output/f'{cfg["method"]}-{cfg["seed"]}'
        run = CycleRun.resume(directory) if (directory/'latest.json').exists() else CycleRun(directory, Config(**cfg), plan['reservation_sha256'])
        if run.reservation_sha != plan['reservation_sha256']:
            raise ValueError('run reservation differs')
        if run.log is None:
            run.source = plan['source']
        run.train(); runs.append(run)
        (output/'report.partial.json').write_text(json.dumps({'plan': plan, 'runs': [r.report() for r in runs]}, indent=2)+'\n')
        if STOP:
            return
    selection = {f'{r.config.method}-{r.config.seed}': r.selected for r in runs}
    path = output/'selection.json'
    if path.exists() and json.loads(path.read_text()) != selection:
        raise ValueError('frozen selection changed')
    if not path.exists():
        path.write_text(json.dumps(selection, indent=2)+'\n')
    for run in runs:
        run.test(selection[f'{run.config.method}-{run.config.seed}'])
        if STOP:
            break
    report = {'plan': plan, 'selection': selection, 'runs': [r.report() for r in runs],
        'admission_by_method': {method: all(r.report()['capability_gate_passed'] for r in runs if r.config.method == method)
                                for method in ('plain', 'curriculum')},
        'limits': 'nominal synthetic reference simulator; unequal realised training budgets; not field readiness or learned-world-model training'}
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print('Study finished', report['admission_by_method'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reservation', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    def stop(*_):
        global STOP
        STOP = True
    signal.signal(signal.SIGINT, stop); signal.signal(signal.SIGTERM, stop)
    study(args.output, args.reservation, args.resume)
