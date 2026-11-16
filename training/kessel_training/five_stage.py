"""ADR-0057 task factory and held-out retention gates, separate from legacy tasks."""

import hashlib

import numpy as np

from .curriculum import TrainingEnv
from .dynamics import clearance
from .environment import LoaderEnv
from .kinematics import components

STAGES = ('fill', 'retract', 'carry', 'tip', 'complete')
CONTRACT = 'five-stage-potential-v2'
HORIZONS = (200, 200, 400, 200, 600)


class FiveStageEnv(TrainingEnv):
    checkpoint_wrapper = 'five-stage-v2'

    def __init__(self, num_envs, *, seed, scene, stage='fill', shaping=True, gamma=0.995):
        if stage not in STAGES:
            raise ValueError('unknown five-stage task')
        if scene.success_kg != 2000:
            raise ValueError('five-stage contract requires 2000 kg delivery threshold')
        if not np.isfinite(gamma) or not 0 < gamma <= 1:
            raise ValueError('invalid shaping discount')
        self.curriculum, self.shaping, self.gamma = True, shaping, gamma
        self.original_scene = scene
        self.stage_index = STAGES.index(stage)
        self.history, self.transitions = [], []
        self.base = LoaderEnv(num_envs, seed=seed, scene=self._scene())
        self.initial_rear_x = np.zeros(num_envs)
        self._prepare(np.ones(num_envs, dtype=bool))

    @property
    def stage(self):
        return STAGES[self.stage_index]

    def _scene(self):
        from dataclasses import replace
        return replace(self.original_scene,
                       max_steps=min(self.original_scene.max_steps, HORIZONS[self.stage_index]))

    def set_stage(self, stage, *, seed=None):
        if stage not in STAGES:
            raise ValueError('unknown five-stage task')
        self.stage_index = STAGES.index(stage)
        self.history = []
        self.base.scene = self._scene()
        return self.reset(seed=seed)

    def _prepare(self, mask):
        b = self.base
        for i in np.flatnonzero(mask):
            if self.stage in ('fill', 'retract'):
                b.pose[i, 0] = b.pile.origin[i, 0]-3.8
                b.joints[i] = (0, -0.1, -0.3)
            elif self.stage in ('carry', 'tip'):
                b.pose[i, 0] = 2.0
                b.joints[i] = (0, 0.35, 0.9)
                if self.stage == 'tip':
                    # Translate the whole chassis so its mouth is over the receiver.
                    b.pose[i, :2] += b.receiver[i]-components(b.pose, b.joints)['mouth'][i]
            if self.stage in ('retract', 'carry', 'tip'):
                mass = b.pile.mass()[i]
                if mass < 2200:
                    raise ValueError('prepared load exceeds available pile mass')
                b.pile.height[i] *= (mass-2200)/mass
                b.payload[i] = b.peak_load[i] = 2200
            b.initial_pose[i] = b.pose[i]
            b.initial_pile_hashes[i] = hashlib.sha256(b.pile.height[i].astype('<f8').tobytes()).hexdigest()
        invalid = clearance(b.pose, b.joints, b.pose, b.joints,
                            b.half_width, b.scene.ceiling_m, b.scene.obstacles)
        if (invalid[mask] != '').any():
            raise ValueError('prepared start fails clearance: '+str(invalid[mask].tolist()))
        b._assert_finite()
        b._update_observations(mask, reset=True)
        self.initial_rear_x[mask] = b.pose[mask, 0]

    def potential(self):
        if self.stage == 'fill':
            return np.clip(self.base.payload/2200, 0, 1.5)
        if self.stage == 'tip':
            return np.zeros(self.num_envs)
        return super().potential()

    def achieved(self):
        b = self.base
        if self.stage == 'fill':
            return b.payload >= 2200
        if self.stage == 'retract':
            return ((b.pose[:, 0] <= self.initial_rear_x-1) & (b.joints[:, 1] >= .2)
                    & (b.joints[:, 2] >= .4) & (b.payload >= 2100))
        if self.stage == 'carry':
            mouth = components(b.pose, b.joints)['mouth']
            return ((np.abs(mouth-b.receiver) <= [1.4, 1.8]).all(axis=1)
                    & (np.abs(b.speed) < .2) & (b.payload >= 2100))
        return b.delivered >= 2000

    def step(self, actions):
        before = self.potential()
        active = ~(self.base.terminated | self.base.truncated)
        observation, raw, _, _, info = self.base.step(actions)
        b = self.base
        # Tip uses the base delivery terminal. Other prepared skills cannot count
        # an accidental delivery as their gate. Collisions always take precedence.
        achieved = self.achieved()
        stage_success = active & achieved & ~b.terminated & (self.stage in STAGES[:3])
        b.terminated[stage_success] = True
        b.truncated[stage_success] = False
        b.reason[stage_success] = 'stage_success'
        terminal = b.terminated.copy()
        shaping = (self.gamma*np.where(terminal, 0, self.potential())-before
                   if self.shaping else np.zeros(self.num_envs))
        shaping = np.where(active, shaping, 0)
        bonus = stage_success.astype(float)
        delivered_success = active & (b.reason == 'success') & (self.stage in ('tip', 'complete'))
        info['metrics'].update(reason=b.reason.copy(), stage=np.full(self.num_envs, self.stage),
            stage_success=stage_success | delivered_success,
            full_success=delivered_success & (self.stage == 'complete'))
        info['training_reward'] = {'version': CONTRACT, 'stage': self.stage,
            'raw_delivery_reward': raw.copy(), 'potential_difference': shaping,
            'subtask_bonus': bonus, 'gamma': self.gamma}
        return observation, raw+shaping+bonus, terminal, b.truncated.copy(), info

    def consider_advancement(self, episodes, rollout):
        raise RuntimeError('five-stage advancement requires explicit validation and retention gates')

    def checkpoint_state(self):
        return {**super().checkpoint_state(), 'task_contract': CONTRACT}

    def restore_checkpoint_state(self, state):
        if state.get('task_contract') != CONTRACT:
            raise ValueError('checkpoint task contract differs')
        super().restore_checkpoint_state(state)


def advancement_gate(stage, history, validation, stage_decisions):
    """Inspect a complete, externally evaluated batch; never query test cases here.

    validation maps current/prior stage names to exactly 16 Boolean outcomes.
    The caller owns case isolation, provenance and separately charged evaluation.
    """
    if stage not in STAGES:
        raise ValueError('unknown five-stage task')
    if isinstance(stage_decisions, bool) or not isinstance(stage_decisions, int) or stage_decisions < 0:
        raise ValueError('invalid stage decision counter')
    required = STAGES[:STAGES.index(stage)+1]
    if set(validation) != set(required):
        raise ValueError('current and all prior validation stages are required')
    for outcomes in validation.values():
        if len(outcomes) != 16 or any(type(v) is not bool for v in outcomes):
            raise ValueError('validation requires 16 explicit Boolean outcomes per stage')
    if any(type(v) is not bool for v in history):
        raise ValueError('training history must contain explicit Boolean outcomes')
    window = history[-32:]
    reasons = []
    if stage == 'complete':
        reasons.append('final_stage')
    if not 0 < stage_decisions <= 32768 or stage_decisions % 4096:
        reasons.append('not_stage_boundary')
    if len(window) < 32 or sum(window) < 23:
        reasons.append('training_window')
    if sum(validation[stage]) < 14:
        reasons.append('current_validation')
    if any(sum(validation[prior]) < 12 for prior in required[:-1]):
        reasons.append('prior_retention')
    return {'contract': CONTRACT, 'stage': stage, 'stage_decisions': stage_decisions,
            'advance': not reasons, 'reasons': reasons,
            'window_episodes': len(window), 'window_successes': sum(window),
            'validation_successes': {name: sum(values) for name, values in validation.items()}}
