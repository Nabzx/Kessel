"""Separate conservative coverage contract; historical supervisors stay frozen."""
import numpy as np
import torch
from kessel_training.phase_memory import features
from .range_supervisor import RangeSupervisor

METHOD = "complete_range_supervisor"


def canonicalize(observation):
    obs = RangeSupervisor.validate(observation)
    if (obs["local_height_m"] < 0).any():
        raise ValueError("range heights must be nonnegative")
    p = obs["proprio"][0]
    fresh = bool(p[12])
    if not fresh: obs["range_valid"][:] = 0
    obs["local_height_m"] *= obs["range_valid"]
    fraction = float(obs["range_valid"].mean())
    kind = "stale" if not fresh else "fresh_complete" if fraction == 1 else "fresh_partial"
    return obs, {"kind":kind,"valid_fraction":fraction,
                 "usable":kind == "fresh_complete" and p[11] <= .2+1e-9}


class CompleteRangeSupervisor(RangeSupervisor):
    """Immediate stop on incomplete input; unchanged speed-only PI and weights."""
    @torch.no_grad()
    def act(self, observation):
        obs, health = canonicalize(observation)
        p = obs["proprio"][0]; now = float(p[13]); speed = float(p[4])
        dt = 0. if self.previous_t is None else now-self.previous_t
        if self.previous_t is not None and not .09 <= dt <= .11:
            raise ValueError("the pilot requires consecutive 0.1-second observations")
        if self.was_overridden: self.paused_s += dt
        self.previous_t = now
        healthy = health["usable"]
        if not healthy and not self.latched:
            self.latched = True; self.good_samples = self.slow_samples = 0; self.integral = 0.
        if self.latched:
            self.good_samples = self.good_samples+1 if healthy else 0
            self.slow_samples = self.slow_samples+1 if abs(speed) <= .08 else 0
            if self.good_samples >= 3 and self.slow_samples >= 3:
                self.latched = False; self.integral = 0.
        prepared = {k:v.copy() for k,v in obs.items()}
        prepared["proprio"][0,13] = now-self.paused_s
        if self.latched:
            proposal = self.actor(features(prepared),torch.as_tensor(self.memory.phase)).numpy()
            candidate = float(np.clip(self.integral+speed*dt,-.45,.45))
            requested = -2.*speed-candidate
            if abs(requested) <= 1 or requested*speed >= 0: self.integral = candidate
            applied = np.array([[float(np.clip(-2.*speed-self.integral,-1,1)),0.,0.,0.]])
            mode = "holding" if self.slow_samples >= 3 else "stopping"
        else:
            proposal = self.actor.act(prepared); applied = proposal.copy(); mode = "running"
        self.was_overridden = self.latched
        self.last = {"method":METHOD,"mode":mode,"override":self.latched,
                     "reason":health["kind"] if self.latched else None,"health":health,
                     "good_samples":self.good_samples,"slow_samples":self.slow_samples,
                     "real_elapsed_s":now,"task_elapsed_s":float(prepared["proprio"][0,13]),
                     "paused_s":self.paused_s,"integral":self.integral,"phase":int(self.memory.phase[0]),
                     "canonical_observation":{k:v[0].tolist() for k,v in prepared.items()},
                     "neural_proposal":proposal[0].tolist(),"applied_action":applied[0].tolist()}
        return applied
