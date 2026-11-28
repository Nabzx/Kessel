"""Observed-load harvesting on the return stroke, with unchanged frozen physics."""
import numpy as np

from .progress_task import ProgressTask
from .progress_supervisor import ProgressSupervisor
from .range_supervisor import RangeSupervisor


class HarvestTask(ProgressTask):
    def __init__(self,actuator=None,lateral_gain=.15):
        super().__init__(actuator=actuator,lateral_gain=lateral_gain)
        self.lanes = [1.35,-1.35]

    def act(self,observation):
        obs = RangeSupervisor.validate(observation); p = obs["proprio"][0]
        if self.mode in ("collect","sweep","back_out","shift") and p[8] >= 2100: self.mode = "lift"
        if self.mode == "shift" and p[0] <= self.cut_start-3.:
            self.mode = "approach"; self.cut_start = None; self.contact_at = None
        actuator = self.actuator; self.actuator = None
        try: action = super().act(obs)
        finally: self.actuator = actuator
        features = np.asarray([self.last["control_features"]])
        if self.mode == "back_out" and p[0] >= self.cut_start-.3:
            curl_target = .95 if int(p[13]/1.2)%2 == 0 else .25
            features[0,4] = -.1-p[6]; features[0,5] = curl_target-p[7]
            action[0,2:] = np.clip(features[0,4:]*4,-1,1)
        if actuator is not None: action = actuator(features)
        self.last.update(method="harvest_task_reference" if actuator is None else "harvest_task_learned_linear",
                         proposal_source="conventional_task" if actuator is None else "learned_linear_feedback",
                         control_features=features[0].tolist(),applied_action=action[0].tolist())
        return action


class HarvestSupervisor(ProgressSupervisor):
    def __init__(self,actuator=None,lateral_gain=.15):
        super().__init__(actuator=actuator,lateral_gain=lateral_gain)
        self.task = HarvestTask(actuator,lateral_gain)
