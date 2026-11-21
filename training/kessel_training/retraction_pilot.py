"""Bounded ADR-0057 pilot. Retraction success is not full-cycle delivery."""

import argparse
from dataclasses import asdict, dataclass
import gzip
import json
from pathlib import Path
import signal
import statistics
import time

import numpy as np
import torch

from . import checkpoints
from .contracts import canonical_json
from .curriculum import TrainingEnv
from .evaluate import source_identity
from .inspect_prerequisites import stage_probe
from .policy import ActorCritic, configure_cpu
from .ppo import PPO, PPOConfig, collect
from .reserve_scenarios import identities, RANGES
from .scenarios import family
from .telemetry import EventLog

SETTINGS = {'baseline': [-.5, -.5, -.5, -.5], 'steering': [-.5, -2.5, -.5, -.5]}
STOP = False


def stage_env(seed, num_envs=4):
    env = TrainingEnv(num_envs, seed=seed, scene=family('standard')[0], curriculum=True, shaping=True)
    env.stage_index = 1
    env.base.scene = env._scene()
    env.reset(seed=seed)
    return env


def score(cases):
    successes = [c for c in cases if c['stage_success'] and c['reason'] == 'stage_success']
    collisions = sum(c['reason'] in ('tunnel_wall', 'tunnel_roof') or c['reason'].startswith('obstacle') for c in cases)
    return [len(successes), -collisions, -statistics.mean(c['cycle_s'] for c in successes) if successes else 0.0]


def best_candidate(candidates):
    # Python max returns the first exact tie, as predeclared.
    return max(candidates, key=lambda c: tuple(c['score']))


@dataclass(frozen=True)
class Config:
    seed: int = 7
    setting: str = 'baseline'
    rollouts: int = 128
    validation_every: int = 16
    max_wall_s: float = 600
    test_reserve_s: float = 60

    def __post_init__(self):
        if self.setting not in SETTINGS or isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed not in (7, 19, 41):
            raise ValueError('unknown pilot setting or seed')
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (self.rollouts, self.validation_every)) or not 1 <= self.rollouts <= 128 or not 1 <= self.validation_every <= 16:
            raise ValueError('pilot rollout budget exceeds protocol')
        if not 0 < self.max_wall_s <= 600 or not 0 <= self.test_reserve_s < self.max_wall_s:
            raise ValueError('invalid cumulative pilot wall cap')


class PilotRun:
    def __init__(self, directory, configuration, reservation_sha, validation_seeds):
        self.wall_before = 0.0
        self.started = time.perf_counter()
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.config = configuration
        self.reservation_sha = reservation_sha
        self.validation_seeds = list(validation_seeds)
        self.generator = configure_cpu(configuration.seed)
        self.policy = ActorCritic(64, initial_log_std=SETTINGS[configuration.setting])
        self.algorithm = PPO(self.policy, PPOConfig())
        self.env = stage_env(configuration.seed)
        self.source = source_identity()
        self.counters = {'rollouts': 0, 'training_decisions': 0, 'optimiser_minibatches': 0,
                         'training_episodes': 0, 'training_stage_successes': 0,
                         'validation_decisions': 0, 'test_decisions': 0}
        self.candidates, self.curve, self.validation_batches = [], [], []
        self.status = 'running'
        self.log = None

    def wall(self):
        return self.wall_before + (time.perf_counter() - self.started if self.started is not None else 0.0)

    def pause_clock(self):
        self.wall_before = self.wall()
        self.started = None

    def start_clock(self):
        if self.started is None:
            self.started = time.perf_counter()

    def open_log(self):
        import hashlib
        identity = {'configuration': asdict(self.config), 'reservation_sha256': self.reservation_sha,
                    'validation_seeds': self.validation_seeds}
        self.log = EventLog(self.directory / 'events.jsonl', self.source,
                            hashlib.sha256(canonical_json(identity).encode()).hexdigest(), dict(self.counters))

    def state(self):
        return {'kind': 'retraction-pilot-v1', 'configuration': asdict(self.config),
                'reservation_sha256': self.reservation_sha, 'validation_seeds': self.validation_seeds,
                'source': self.source, 'software': {'torch': str(torch.__version__), 'numpy': np.__version__},
                'actor_critic': self.policy.state_dict(), 'optimiser': self.algorithm.optimiser.state_dict(),
                'environment': checkpoints.environment_state(self.env), 'rng': checkpoints.random_state(self.generator),
                'counters': dict(self.counters), 'candidates': list(self.candidates), 'curve': list(self.curve),
                'validation_batches': self.validation_batches,
                'wall_s': self.wall(), 'status': self.status}

    def save(self, label):
        path = self.directory / f'{label}.pt'
        digest = checkpoints.save(path, self.state())
        pointer = self.directory / 'latest.json'
        temporary = pointer.with_suffix('.tmp')
        temporary.write_text(json.dumps({'path': path.name, 'sha256': digest}) + '\n')
        temporary.replace(pointer)
        return path

    @classmethod
    def resume(cls, directory):
        loading_started = time.perf_counter()
        directory = Path(directory)
        pointer = json.loads((directory / 'latest.json').read_text())
        path = directory / pointer['path']
        if checkpoints.sha256(path) != pointer['sha256']:
            raise ValueError('latest pilot pointer hash differs')
        state = checkpoints.load(path)
        if state.get('kind') != 'retraction-pilot-v1':
            raise ValueError('wrong checkpoint kind')
        run = cls(directory, Config(**state['configuration']), state['reservation_sha256'], state['validation_seeds'])
        if run.source['package_sha256'] != state['source']['package_sha256'] or run.source['training_dirty']:
            raise ValueError('resume requires the exact clean training package')
        if state['software'] != {'torch': str(torch.__version__), 'numpy': np.__version__}:
            raise ValueError('numerical library versions changed')
        run.policy.load_state_dict(state['actor_critic'])
        run.algorithm.optimiser.load_state_dict(state['optimiser'])
        checkpoints.restore_environment(run.env, state['environment'])
        checkpoints.restore_random_state(run.generator, state['rng'])
        run.counters, run.candidates, run.curve = state['counters'], state['candidates'], state['curve']
        run.validation_batches = state['validation_batches']
        run.wall_before, run.status, run.source = state['wall_s'] + time.perf_counter() - loading_started, state['status'], state['source']
        run.started = time.perf_counter()
        run.open_log()  # Reject an interrupted transaction with unmatched log counters.
        return run

    def iterate(self):
        batch = collect(self.env, self.policy, 64, self.generator)
        update = self.algorithm.update(batch, self.generator)
        self.counters['rollouts'] += 1
        self.counters['training_decisions'] += 256
        self.counters['optimiser_minibatches'] += update['minibatch_updates']
        self.counters['training_episodes'] += len(batch.episodes)
        self.counters['training_stage_successes'] += sum(e['reason'] == 'stage_success' for e in batch.episodes)
        self.curve.append({'rollout': self.counters['rollouts'], 'mean_step_reward': float(batch.rewards.mean()),
                           'reward_components': batch.reward_components, 'update': update,
                           'training_episodes': batch.episodes, 'latent_std': self.policy.log_std.detach().exp().tolist()})

    def evaluate(self):
        cases = []
        for seed in self.validation_seeds:
            if self.wall() >= self.config.max_wall_s - self.config.test_reserve_s:
                self.validation_batches.append({'rollout': self.counters['rollouts'], 'complete': False, 'cases': cases})
                self.status = 'training_wall_cap'
                if not self.candidates:
                    raise RuntimeError('initial validation exceeded the wall allowance; no selectable candidate')
                return None
            result = stage_probe('retract', seed, self.policy)
            result['stage_success'] = result['reason'] == 'stage_success'
            cases.append({k: v for k, v in result.items() if k != 'records'})
            self.counters['validation_decisions'] += result['steps']
        candidate = {'rollout': self.counters['rollouts'], 'path': f'candidate-{self.counters["rollouts"]:06}.pt',
                     'score': score(cases), 'validation': cases}
        self.validation_batches.append({'rollout': self.counters['rollouts'], 'complete': True, 'cases': cases})
        self.candidates.append(candidate)
        return candidate

    def transaction(self, kind, label):
        self.log.append(kind, {'counters': dict(self.counters), 'wall_s': self.wall(), 'status': self.status})
        return self.save(label)

    def train(self):
        if self.log is None:
            self.open_log()
        if not self.candidates:
            self.evaluate()
            self.transaction('validation', 'candidate-000000')
        if self.status != 'running':
            self.pause_clock()
            return
        while self.counters['rollouts'] < self.config.rollouts and not STOP:
            if self.status != 'running':
                break
            if self.wall() >= self.config.max_wall_s - self.config.test_reserve_s:
                self.status = 'training_wall_cap'
                break
            self.iterate()
            candidate = None
            if self.counters['rollouts'] % self.config.validation_every == 0:
                candidate = self.evaluate()
            label = candidate['path'][:-3] if candidate else f'rollout-{self.counters["rollouts"]:06}'
            self.transaction('validation' if candidate else 'rollout', label)
            if candidate:
                print(self.config.setting, self.config.seed, 'rollout', self.counters['rollouts'],
                      'validation', candidate['score'][0], '/', len(self.validation_seeds),
                      'wall', round(self.wall(), 1), flush=True)
        if STOP:
            self.status = 'interrupted'
        elif self.status == 'running':
            self.status = 'completed'
        # Different filename from the last transaction; all checkpoints immutable.
        self.transaction('stop', f'stop-{self.counters["rollouts"]:06}-{self.status}-{self.log.sequence:06}')
        self.pause_clock()

    def report(self):
        chosen = best_candidate(self.candidates)
        return {'configuration': asdict(self.config), 'counters': dict(self.counters), 'status': self.status,
                'wall_s': self.wall(), 'candidates': [c | {'sha256': checkpoints.sha256(self.directory / c['path'])} for c in self.candidates],
                'selected': chosen | {'sha256': checkpoints.sha256(self.directory / chosen['path'])},
                'curve': self.curve, 'validation_batches': self.validation_batches, 'log': self.log.summary()}


def run_study(output, reservation, resume=False):
    output, reservation = Path(output), Path(reservation)
    source = source_identity()
    if source['training_dirty']:
        raise ValueError('commit training code before collection')
    reserved = json.loads(reservation.read_text())
    if not reserved['reservation_verified'] or reserved['identities'] != identities():
        raise ValueError('reservation is unverified or initial scene identities changed')
    reservation_sha = checkpoints.sha256(reservation)
    if output.exists() and not resume:
        raise FileExistsError('choose a new study directory or explicitly resume')
    output.mkdir(parents=True, exist_ok=True)
    validation = list(range(*RANGES['validation']))
    plan = {'schema': 'retraction-pilot-v1', 'source': source, 'reservation_sha256': reservation_sha,
            'settings': SETTINGS, 'seeds': [7, 19, 41], 'configuration': asdict(Config()),
            'validation_seeds': validation, 'pilot_test_seeds': list(range(*RANGES['pilot_test'])),
            'selection': 'validation successes, fewer collisions, shorter successful duration; earlier exact tie; median configuration, baseline tie',
            'task': 'prepared 1500 kg retraction only; no full-cycle proficiency'}
    plan_path = output / 'plan.json'
    if plan_path.exists():
        original = json.loads(plan_path.read_text())
        if original['source']['package_sha256'] != source['package_sha256']:
            raise ValueError('resume training package changed')
        proposed = dict(plan, source=original['source'])
        if original != proposed:
            raise ValueError('resume plan or source changed')
        plan = original
    else:
        plan_path.write_text(json.dumps(plan, indent=2) + '\n')
    reference_path = output / 'reference-validation.json'
    if reference_path.exists():
        reference_validation = json.loads(reference_path.read_text())
    else:
        reference_validation = []
        for seed in validation:
            case = stage_probe('retract', seed)
            reference_validation.append({k: v for k, v in case.items() if k != 'records'})
        reference_path.write_text(json.dumps(reference_validation, indent=2, allow_nan=False) + '\n')
    if not all(c['reason'] == 'stage_success' for c in reference_validation):
        raise ValueError('reserved validation reference cannot complete retraction; no policy training started')
    runs = []
    for setting in SETTINGS:
        for seed in (7, 19, 41):
            directory = output / f'{setting}-{seed}'
            trainer = PilotRun.resume(directory) if (directory / 'latest.json').exists() else PilotRun(directory, Config(seed, setting), reservation_sha, validation)
            if trainer.log is None:
                trainer.source = plan['source']
            if trainer.status == 'interrupted':
                trainer.status = 'running'
            if trainer.reservation_sha != reservation_sha or trainer.source['package_sha256'] != source['package_sha256']:
                raise ValueError('run identity differs from study')
            trainer.train()
            runs.append(trainer)
            partial = {'plan': plan, 'runs': [r.report() for r in runs]}
            (output / 'report.partial.json').write_text(json.dumps(partial, indent=2, allow_nan=False) + '\n')
            if STOP:
                return partial
    medians = {setting: statistics.median(best_candidate(r.candidates)['score'][0] for r in runs if r.config.setting == setting) for setting in SETTINGS}
    selected_setting = max(SETTINGS, key=lambda setting: medians[setting])
    # Freeze configuration selection before reading the pilot test outcomes.
    selection = {'setting': selected_setting, 'validation_medians': medians,
                 'gate_passed': sum(best_candidate(r.candidates)['score'][0] >= 14 for r in runs if r.config.setting == selected_setting) >= 2}
    frozen = output / 'selection.json'
    if frozen.exists() and json.loads(frozen.read_text()) != selection:
        raise ValueError('test stage cannot change selection')
    frozen.write_text(json.dumps(selection, indent=2) + '\n')
    tests = []
    for trainer in runs:
        if trainer.config.setting != selected_setting:
            continue
        selected = best_candidate(trainer.candidates)
        checkpoint = trainer.directory / selected['path']
        trainer.start_clock()
        weights = checkpoints.load(checkpoint)
        policy = ActorCritic(64, initial_log_std=SETTINGS[selected_setting])
        policy.load_state_dict(weights['actor_critic'])
        test_path = trainer.directory / 'test.json'
        cases = []
        if test_path.exists():
            prior = json.loads(test_path.read_text())
            if prior['checkpoint_sha256'] != checkpoints.sha256(checkpoint):
                raise ValueError('test checkpoint identity changed')
            if prior['test_complete']:
                tests.append(prior)
                trainer.pause_clock()
                continue
            cases = prior['cases']
        for seed in list(range(*RANGES['pilot_test']))[len(cases):]:
            if trainer.wall() >= trainer.config.max_wall_s or STOP:
                break
            case = stage_probe('retract', seed, policy)
            case['split'] = 'test'
            case['stage_success'] = case['reason'] == 'stage_success'
            filename = f'test-{seed}.json.gz'
            (trainer.directory / filename).write_bytes(gzip.compress(json.dumps(case, separators=(',', ':'), allow_nan=False).encode(), mtime=0))
            trainer.counters['test_decisions'] += case['steps']
            cases.append({k: v for k, v in case.items() if k != 'records'} | {'trace': filename,
                         'trace_sha256': checkpoints.sha256(trainer.directory / filename)})
        result = {'seed': trainer.config.seed, 'setting': selected_setting, 'checkpoint_sha256': checkpoints.sha256(checkpoint),
                  'cases': cases, 'test_complete': len(cases) == 16}
        test_path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        trainer.transaction('test', f'tested-{trainer.counters["rollouts"]:06}-{trainer.log.sequence:06}')
        trainer.pause_clock()
        tests.append(result)
    report = {'plan': plan, 'selection': selection, 'runs': [r.report() for r in runs], 'tests': tests,
              'shared_reference_validation': reference_validation,
              'shared_reference_validation_decisions': sum(c['steps'] for c in reference_validation),
              'full_cycle_training_executed': False,
              'limits': 'Prepared retraction is not empty-start full delivery. Tests cannot change the frozen configuration selection. All costs are separate.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reservation', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    def stop(*_):
        global STOP
        STOP = True
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    result = run_study(args.output, args.reservation, args.resume)
    print(json.dumps(result.get('selection', {'status': 'interrupted'})))
