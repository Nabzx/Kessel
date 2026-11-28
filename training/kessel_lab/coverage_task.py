"""Observation-only bucket-mouth lane feedback and shorter reversing manoeuvres."""
import numpy as np

from .progress_task import ProgressTask
from .progress_supervisor import ProgressSupervisor
from .range_supervisor import RangeSupervisor


class CoverageTask(ProgressTask):
    def __init__(self,actuator=None,lateral_gain=.15,spacing=1.35,reverse_clearance=3.):
        super().__init__(actuator=actuator,lateral_gain=lateral_gain)
        self.spacing = spacing; self.reverse_clearance = reverse_clearance
        self.lanes = [spacing,-spacing]

    def act(self,observation):
        obs = RangeSupervisor.validate(observation); p = obs["proprio"][0]
        if self.mode == "approach" and self.collection_pass == 0 and not self.traction_lane_selected and p[14] > .45:
            self.lane = self.spacing; self.lanes = [-self.spacing,0.]; self.traction_lane_selected = True
        if self.mode == "shift" and p[0] <= self.cut_start-self.reverse_clearance:
            self.mode = "approach"; self.cut_start = None; self.contact_at = None
        actuator = self.actuator; self.actuator = None
        try: action = super().act(obs)
        finally: self.actuator = actuator
        features = np.asarray([self.last["control_features"]])
        if self.mode in ("approach","collect"):
            heading = np.arctan2(p[2],p[3]); art,boom = p[5:7]
            mouth_y = p[1]+1.8*np.sin(heading)+(1.6+1.2*np.cos(boom))*np.sin(heading+art)
            yaw = -np.arctan(self.lateral_gain*(mouth_y-self.lane))
            desired_art = np.clip(-.8*(heading-yaw),-.25,.25)
            features[0,3] = desired_art-art; action[0,1] = np.clip(2*features[0,3],-1,1)
        if actuator is not None: action = actuator(features)
        self.last.update(method="coverage_task_reference" if actuator is None else "coverage_task_learned_linear",
                         proposal_source="conventional_task" if actuator is None else "learned_linear_feedback",
                         control_features=features[0].tolist(),applied_action=action[0].tolist(),
                         lane_spacing_m=self.spacing,reverse_clearance_m=self.reverse_clearance)
        return action


class CoverageSupervisor(ProgressSupervisor):
    def __init__(self,actuator=None,lateral_gain=.15,spacing=1.35,reverse_clearance=3.):
        super().__init__(actuator=actuator,lateral_gain=lateral_gain)
        self.task = CoverageTask(actuator,lateral_gain,spacing,reverse_clearance)
