"""Learned continuous actions with explicitly conventional observation-derived memory."""
import numpy as np
import torch
from torch import nn

SCALE = [12, 4.2, 1, 1, 2, .6, 1.1, 1, 3500, 20, 6, 5, 1, 60, 1]


class PhaseMemory:
    def __init__(self, count=1):
        self.phase = np.zeros(count, dtype=np.int64)
        self.fill_start = np.zeros(count)

    def update(self, observation):
        p = observation['proprio']
        speed, art, boom, curl, load = (p[:, i] for i in (4, 5, 6, 7, 8))
        contact = (observation['local_height_m']*observation['range_valid']).max(axis=(1, 2)) > .1
        entered = (self.phase == 0) & contact
        self.fill_start[entered] = p[entered, 13]; self.phase[entered] = 1
        self.phase[(self.phase == 1) & ((load >= 2450) | (p[:, 13]-self.fill_start >= 22))] = 2
        self.phase[(self.phase == 2) & (boom >= .33) & (curl >= .6)] = 3
        reach = 1.8+(1.6+1.2*np.cos(boom))*np.cos(art)
        self.phase[(self.phase == 3) & (np.abs(p[:, 9]-reach) < .5) & (np.abs(speed) < .08)] = 4
        return self.phase.copy()


def features(observation):
    p = torch.as_tensor(observation['proprio'], dtype=torch.float32)
    height = torch.as_tensor(observation['local_height_m'], dtype=torch.float32).flatten(1)
    valid = torch.as_tensor(observation['range_valid'], dtype=torch.float32).flatten(1)
    result = torch.cat((p/torch.tensor(SCALE), height/1.5, valid), dim=1).clamp(-5, 5)
    if result.shape[1] != 65 or not torch.isfinite(result).all():
        raise ValueError('invalid local observation')
    return result


class PhaseActor(nn.Module):
    def __init__(self, conditioned=True):
        super().__init__()
        self.conditioned = conditioned
        self.net = nn.Sequential(nn.Linear(70, 128), nn.ReLU(), nn.Linear(128, 128),
                                 nn.ReLU(), nn.Linear(128, 4), nn.Tanh())
        self.memory = PhaseMemory()

    def forward(self, local, phase):
        onehot = torch.nn.functional.one_hot(phase.long(), 5).float()
        if not self.conditioned:
            onehot = torch.zeros_like(onehot)
        return self.net(torch.cat((local, onehot), dim=1))

    @torch.no_grad()
    def act(self, observation):
        phase = self.memory.update(observation)
        return self(features(observation), torch.as_tensor(phase)).numpy()

    def reset(self):
        self.memory = PhaseMemory()
