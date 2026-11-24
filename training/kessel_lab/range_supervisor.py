"""Experimental conventional range-health supervisor around frozen neural controls."""
import numpy as np
import torch

from kessel_training.phase_memory import features

METHOD = "missing_range_supervisor"


class RangeSupervisor:
    """Single-slot pilot controller; needs usable speed/time proprioception."""
    def __init__(self, actor):
        if not actor.conditioned:
            raise ValueError("the pilot requires the original phase-conditioned actor")
        self.actor = actor
        self.last = None
        self.previous_t = None
        self.was_overridden = False
        self.paused_s = 0.
        self.seen_healthy = False
        self.bad_since = None
        self.latched = False
        self.good_samples = self.slow_samples = 0
        self.integral = 0.

    @property
    def memory(self):
        return self.actor.memory

    @staticmethod
    def validate(observation):
        if set(observation) != {"proprio", "local_height_m", "range_valid"}:
            raise ValueError("only the existing local observation is supported")
        obs = {k:np.asarray(v,dtype=np.float64).copy() for k,v in observation.items()}
        if obs["proprio"].shape != (1,15) or any(obs[k].shape != (1,5,5) for k in ("local_height_m","range_valid")):
            raise ValueError("the pilot supports one observation slot")
        if not all(np.isfinite(v).all() for v in obs.values()):
            raise ValueError("the pilot requires finite local inputs, including usable speed/time")
        if not np.isin(obs["range_valid"], (0,1)).all():
            raise ValueError("range validity must be binary")
        p = obs["proprio"][0]
        if p[11] < 0 or p[12] not in (0,1) or p[13] < 0:
            raise ValueError("invalid range status or clock")
        return obs

    @torch.no_grad()
    def act(self, observation):
        obs = self.validate(observation)
        p = obs["proprio"][0]; now = float(p[13]); speed = float(p[4])
        dt = 0. if self.previous_t is None else now-self.previous_t
        if self.previous_t is not None and not .09 <= dt <= .11:
            raise ValueError("the pilot requires consecutive 0.1-second observations")
        if self.was_overridden: self.paused_s += dt
        self.previous_t = now
        healthy = bool(p[12] == 1 and p[11] <= .2+1e-9 and obs["range_valid"].mean() >= .2)
        if healthy:
            self.seen_healthy = True; self.bad_since = None
        elif self.bad_since is None:
            self.bad_since = now
        if not self.latched and not healthy and (not self.seen_healthy or now-self.bad_since >= .2-1e-9):
            self.latched = True
            self.good_samples = self.slow_samples = 0
            self.integral = 0.
        if self.latched:
            self.good_samples = self.good_samples+1 if healthy else 0
            self.slow_samples = self.slow_samples+1 if abs(speed) <= .08 else 0
            if self.good_samples >= 3 and self.slow_samples >= 3:
                self.latched = False; self.integral = 0.
        prepared = {k:v.copy() for k,v in obs.items()}
        prepared["proprio"][0,13] = now-self.paused_s
        if not self.latched:
            proposal = self.actor.act(prepared)
            applied = proposal.copy()
            mode = "running"; reason = None
        else:
            # Proposals remain neural; phase does not advance while overridden.
            proposal = self.actor(features(prepared),torch.as_tensor(self.memory.phase)).numpy()
            candidate = float(np.clip(self.integral+speed*dt,-.45,.45))
            requested = -2.*speed-candidate
            # Integrate unless saturation would grow further in the same direction.
            if abs(requested) <= 1 or requested*speed >= 0:
                self.integral = candidate
            drive = float(np.clip(-2.*speed-self.integral,-1,1))
            applied = np.array([[drive,0.,0.,0.]])
            mode = "holding" if self.slow_samples >= 3 else "stopping"
            reason = "range_uninitialised" if not self.seen_healthy else "range_timeout"
        self.was_overridden = self.latched
        self.last = {"method":METHOD, "mode":mode, "override":self.latched,
                     "reason":reason, "range_healthy":healthy,
                     "valid_fraction":float(obs["range_valid"].mean()),
                     "good_samples":self.good_samples,"slow_samples":self.slow_samples,
                     "real_elapsed_s":now, "task_elapsed_s":float(prepared["proprio"][0,13]),
                     "paused_s":self.paused_s,"integral":self.integral,
                     "phase":int(self.memory.phase[0]), "neural_proposal":proposal[0].tolist(),
                     "applied_action":applied[0].tolist()}
        return applied
