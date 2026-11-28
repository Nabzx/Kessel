"""Proposed empty-start no-progress hold, separate from delivery success."""
import numpy as np

from .harvest_task import HarvestTask
from .progress_supervisor import ProgressSupervisor
from .range_supervisor import RangeSupervisor


class StartProgressTask(HarvestTask):
    def __init__(self,actuator=None,lateral_gain=.15):
        super().__init__(actuator,lateral_gain)
        self.start_stall_s = None; self.start_anchor = None; self.hold_started_s = None

    def act(self,observation):
        obs = RangeSupervisor.validate(observation); p = obs["proprio"][0]; now = float(p[13])
        previous_drive = 0. if self.last is None else self.last["applied_action"][0]
        near = (obs["local_height_m"][:,:2]*obs["range_valid"][:,:2]).max()
        candidate = self.mode == "approach" and self.collection_pass == 0 and p[8] < 1 and near <= .08 and abs(p[4]) <= .01 and p[14] > .45 and previous_drive >= .98
        if candidate:
            if self.start_stall_s is None: self.start_stall_s = now; self.start_anchor = p[:2].copy()
            elif np.linalg.norm(p[:2]-self.start_anchor) > .02: self.start_stall_s = now; self.start_anchor = p[:2].copy()
            if now-self.start_stall_s >= 3.-1e-8 and self.hold_started_s is None: self.hold_started_s = now
        else: self.start_stall_s = None; self.start_anchor = None
        if self.hold_started_s is None: return super().act(obs)
        if self.previous_t is not None and not .09 <= now-self.previous_t <= .11: raise ValueError("consecutive hold observations required")
        self.previous_t = now; self.mode = "no_progress_hold"; self.phase[0] = 0
        action = np.array([[np.clip(.39-1.8*p[4],-1,1),0.,0.,0.]])
        self.last = {"method":"conventional_empty_start_hold","mode":self.mode,"phase":0,"task_time_s":now,
                     "hold_started_task_s":self.hold_started_s,"proposal_source":"conventional_initial_no_progress_hold",
                     "control_features":None,"applied_action":action[0].tolist(),
                     "guard":"three seconds of high slip, full drive and <0.02 m progress; empty bucket and no nearby crop"}
        return action


class StartProgressSupervisor(ProgressSupervisor):
    def __init__(self,actuator=None,lateral_gain=.15):
        super().__init__(actuator,lateral_gain); self.task = StartProgressTask(actuator,lateral_gain)

    def act(self,observation,packet):
        action = super().act(observation,packet)
        if not self.last["override"] and self.task.mode == "no_progress_hold":
            self.last.update(override=True,override_reason="initial_no_progress",proposal_source="conventional_initial_no_progress_hold",conventional_proposal=action[0].tolist())
        return action
