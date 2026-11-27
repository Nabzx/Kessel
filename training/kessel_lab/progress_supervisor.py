"""Explicit conventional task/stop composition. No neural proposal or vehicle I/O."""
import copy

import numpy as np
import torch

from kessel_training.phase_memory import PhaseMemory
from .bootstrap_hold import BootstrapHoldSupervisor
from .clearance_stop import health
from .progress_task import ProgressTask
from .range_supervisor import RangeSupervisor


class ClearanceMonitor:
    def __init__(self): self.release_m = None; self.accepted_capture_s = None
    def update(self,packet,now,speed):
        raw = health(packet,now,speed)
        if raw["reason"] in ("clear","blocked_envelope"):
            capture = float(packet["capture_s"])
            if capture < 0 or self.accepted_capture_s is not None and capture <= self.accepted_capture_s:
                return {**raw,"usable":False,"reason":"nonmonotonic_clearance_capture","release_margin_m":self.release_m}
            self.accepted_capture_s = capture
        if raw["reason"] == "blocked_envelope": self.release_m = max(self.release_m or 0.,raw["threshold_m"]+.5,1.5)
        if self.release_m is not None and raw["usable"]:
            d = packet["distance_m"]
            if min(d[:2]) <= self.release_m or min(d[2:]) <= .8: raw = {**raw,"usable":False,"reason":"blocked_latched"}
            else: self.release_m = None
        return {**raw,"release_margin_m":self.release_m}


class _NeutralProposal:
    """Conventional zero placeholder required by the frozen braking-law interface.

    It is never applied as a task command or described as neural inference.
    """
    conditioned = True
    def __init__(self): self.memory = PhaseMemory()
    def __call__(self,local,phase): return torch.zeros((1,4))


class ProgressSupervisor:
    def __init__(self,actuator=None):
        self.task = ProgressTask(actuator=actuator); self.monitor = ClearanceMonitor(); self.brake = None
        self.previous_t = None; self.paused_s = 0.; self.overridden = False
        self.seen_range = False; self.good_samples = self.slow_samples = 0; self.last = None
        self.bad_range_since = None
    @property
    def memory(self): return self.task.memory
    def act(self,observation,packet):
        obs = RangeSupervisor.validate(observation); p = obs["proprio"][0]; now = float(p[13]); speed = float(p[4])
        dt = 0. if self.previous_t is None else now-self.previous_t
        if self.previous_t is not None and not .09 <= dt <= .11: raise ValueError("consecutive real-clock observations required")
        if self.overridden: self.paused_s += dt
        self.previous_t = now; clearance = self.monitor.update(packet,now,speed)
        fresh = bool(p[12] and p[11] <= .2+1e-9 and obs["range_valid"].sum() >= 5)
        if fresh: self.seen_range = True; self.bad_range_since = None
        elif self.bad_range_since is None: self.bad_range_since = now-min(.1,float(p[11]))
        grace = bool(self.seen_range and not fresh and p[11] <= .2+1e-9 and now-self.bad_range_since <= .2+1e-9)
        healthy = clearance["usable"] and (fresh or grace)
        if not healthy and not self.overridden:
            self.overridden = True; self.good_samples = self.slow_samples = 0
            self.brake = BootstrapHoldSupervisor(_NeutralProposal())
        if self.overridden:
            self.good_samples = self.good_samples+1 if healthy else 0
            self.slow_samples = self.slow_samples+1 if abs(speed) <= .08 else 0
            if self.good_samples >= 3 and self.slow_samples >= 3:
                self.overridden = False; self.brake = None
        if self.overridden:
            stopping_input = {k:v.copy() for k,v in obs.items()}
            stopping_input["range_valid"][:] = 0; stopping_input["local_height_m"][:] = 0; stopping_input["proprio"][0,12] = 0
            action = self.brake.act(stopping_input)
            observer = copy.deepcopy(self.brake.last["observer"]); mode = self.brake.last["mode"]
            proposal = None
        else:
            task_input = {k:v.copy() for k,v in obs.items()}; task_input["proprio"][0,13] = now-self.paused_s
            action = self.task.act(task_input); proposal = action[0].tolist(); observer = None; mode = self.task.mode
        self.last = {"method":"progress_task_with_ordered_clearance","mode":mode,"override":self.overridden,
                     "proposal_source":"conventional_task" if self.task.actuator is None else "learned_linear_feedback",
                     "task_proposal":proposal,"conventional_proposal":proposal if self.task.actuator is None else None,"applied_action":action[0].tolist(),
                     "task":copy.deepcopy(self.task.last),"task_time_s":now-self.paused_s,"paused_s":self.paused_s,
                     "clearance":clearance,"range_fresh":fresh,"range_grace":grace,"valid_cells":int(obs["range_valid"].sum()),
                     "stop_observer":observer,"accepted_capture_s":self.monitor.accepted_capture_s}
        return action
