"""Experimental receiver-x input frame; weights and phase transitions stay frozen."""
import numpy as np
import torch

from kessel_training.phase_memory import features

METHOD = "receiver_x_frame"
NOMINAL_RECEIVER_X_M = -1.5


def encode(observation, phase):
    p = np.asarray(observation["proprio"])
    phase = np.asarray(phase)
    if p.ndim != 2 or p.shape[1] != 15 or phase.shape != (len(p),):
        raise ValueError("observation and phase batch shapes differ")
    if not np.isin(phase, np.arange(5)).all():
        raise ValueError("invalid phase")
    result = {k: np.asarray(v).copy() for k, v in observation.items()}
    carrying = phase >= 3
    result["proprio"][carrying, 0] = (
        NOMINAL_RECEIVER_X_M - p[carrying, 9] * p[carrying, 3]
        + p[carrying, 10] * p[carrying, 2])
    return result


class ReceiverFrameActor:
    def __init__(self, actor):
        if not actor.conditioned:
            raise ValueError("this pilot requires the original phase-conditioned actor")
        self.actor = actor

    @property
    def memory(self):
        return self.actor.memory

    def reset(self):
        self.actor.reset()

    @torch.no_grad()
    def act(self, observation):
        phase = self.memory.update(observation)
        prepared = encode(observation, phase)
        return self.actor(features(prepared), torch.as_tensor(phase)).numpy()
