"""Damped forward steering, separate from the rejected rehearsal source."""
import numpy as np

from .robust_task import TaskReference


class DampedTaskReference(TaskReference):
    def act(self,observation):
        action = super().act(observation)
        if self.last["owner"] == "conventional_task" and self.memory.phase[0] != 3:
            p = observation["proprio"][0]; heading = np.arctan2(p[2],p[3])
            target = np.clip(-.8*heading-.15*p[1],-.2,.2)
            action[0,1] = np.clip((target-p[5])*2,-1,1)
        self.last = {**self.last,"method":"damped_retry_reference"}
        return action
