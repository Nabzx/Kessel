"""Separate retry/steering feasibility baseline and neural rehearsal candidates."""
import numpy as np
import torch

from kessel_training.phase_memory import PhaseMemory, features
from .range_supervisor import RangeSupervisor


class RetryMemory(PhaseMemory):
    def __init__(self,fill_timeout=12.):
        super().__init__(); self.fill_timeout = fill_timeout; self.empty_samples = 0; self.cycles = 0
    def update(self,observation):
        p = observation["proprio"]; phase = self.phase
        contact = (observation["local_height_m"]*observation["range_valid"]).max() > .1
        if phase[0] == 0 and contact: phase[0] = 1; self.fill_start[0] = p[0,13]
        if phase[0] == 1 and (p[0,8] >= 2450 or p[0,13]-self.fill_start[0] >= self.fill_timeout): phase[0] = 2
        if phase[0] == 2 and p[0,6] >= .33 and p[0,7] >= .6: phase[0] = 3
        reach = 1.8+(1.6+1.2*np.cos(p[0,6]))*np.cos(p[0,5])
        if phase[0] == 3 and abs(p[0,9]-reach) < .5 and abs(p[0,4]) < .08: phase[0] = 4
        self.empty_samples = self.empty_samples+1 if phase[0] == 4 and p[0,8] <= 20 else 0
        if self.empty_samples >= 3:
            phase[0] = 0; self.empty_samples = 0; self.cycles += 1
        return phase.copy()


class TaskReference:
    """Observation-only conventional feasibility comparison; never a neural fallback."""
    def __init__(self,fill_timeout):
        self.memory = RetryMemory(fill_timeout); self.last = None; self.integral = 0.
    def act(self,observation):
        obs = RangeSupervisor.validate(observation); p = obs["proprio"][0]
        if p[12] == 0 or not obs["range_valid"].any():
            self.integral = float(np.clip(self.integral+p[4]*.1,-.45,.45))
            action = np.array([[np.clip(-2*p[4]-self.integral,-1,1),0,0,0]])
            self.last = {"owner":"conventional_stop","phase":int(self.memory.phase[0]),"cycles":self.memory.cycles}
            return action
        self.integral = 0.; phase = int(self.memory.update(obs)[0]); speed,art,boom,curl = p[4:8]
        reach = 1.8+(1.6+1.2*np.cos(boom))*np.cos(art); error = p[9]-reach
        target = 1. if phase == 0 else .45 if phase == 1 else float(np.clip(error*.65,-1.,.3)) if phase == 3 else 0.
        drive = np.clip(1.8*(target-speed)+np.sign(target)*.12,-1,1)
        heading = np.arctan2(p[2],p[3]); direction = -1. if phase == 3 and target < 0 else 1.
        target_yaw = -direction*np.arctan(.25*p[1])
        # Solve the small-angle articulated yaw equation for articulation rate.
        steer = np.clip((speed*np.sin(art)+3.4*(heading-target_yaw))/1.6/.35,-1,1)
        target_boom = -.1 if phase < 2 else .35
        target_curl = -.1 if phase == 0 else -.7 if phase == 4 else .95
        action = np.array([[drive,steer,np.clip((target_boom-boom)*4,-1,1),np.clip((target_curl-curl)*4,-1,1)]])
        self.last = {"owner":"conventional_task","phase":phase,"cycles":self.memory.cycles}
        return action


class InputSmoother:
    def __init__(self): self.previous = None
    def __call__(self,observation):
        obs = RangeSupervisor.validate(observation)
        obs["local_height_m"] *= obs["range_valid"]
        if self.previous is not None:
            obs["proprio"][:,:11] = .5*obs["proprio"][:,:11]+.5*self.previous["proprio"][:,:11]
            norm = np.linalg.norm(obs["proprio"][0,2:4])
            if norm > 0: obs["proprio"][0,2:4] /= norm
            valid = obs["range_valid"]*self.previous["range_valid"]
            obs["local_height_m"] = np.where(valid,.5*obs["local_height_m"]+.5*self.previous["local_height_m"],obs["local_height_m"])
        self.previous = {k:v.copy() for k,v in obs.items()}
        return obs


class RetryActor:
    conditioned = True
    def __init__(self,actor,fill_timeout,smooth=False):
        self.actor = actor; self.memory = RetryMemory(fill_timeout); self.smoother = InputSmoother() if smooth else None
        self.last_features = None
    def __call__(self,*args):
        self.last_features = args[0].detach().numpy()[0].tolist()
        return self.actor(*args)
    @torch.no_grad()
    def act(self,observation):
        obs = self.smoother(observation) if self.smoother else observation
        phase = self.memory.update(obs)
        return self(features(obs),torch.as_tensor(phase)).numpy()


class NeuralCandidate(RangeSupervisor):
    """Old partial-input stopping prototype, retrained commands and retry memory.

    Experimental composition. It carries none of the bootstrap qualification.
    """
    def act(self,observation):
        action = super().act(observation)
        self.last["model_input_features"] = self.actor.last_features
        self.last["task_cycles"] = self.memory.cycles
        return action
