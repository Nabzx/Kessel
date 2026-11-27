"""Progress-driven conventional collection, with no hidden scene inputs."""
import numpy as np

from .range_supervisor import RangeSupervisor


class ProgressTask:
    def __init__(self,lane_changes=True):
        self.mode = "approach"; self.phase = np.zeros(1,dtype=int); self.memory = self
        self.lane_changes = lane_changes; self.lane = 0.; self.lanes = [1.1,-1.1]
        self.cut_start = None; self.contact_at = None; self.last_progress = None; self.progress_load = 0.
        self.integral = 0.; self.previous_t = None; self.collection_pass = 0; self.last = None
        self.sweep_at = None

    def act(self,observation):
        obs = RangeSupervisor.validate(observation); p = obs["proprio"][0]
        now = float(p[13]); x,y = p[:2]; heading = np.arctan2(p[2],p[3]); speed,art,boom,curl,load = p[4:9]
        dt = 0. if self.previous_t is None else now-self.previous_t; self.previous_t = now
        if dt < 0 or dt > .11: raise ValueError("task clock must be consecutive")
        near = bool((obs["local_height_m"][:,:2,:]*obs["range_valid"][:,:2,:]).max() > .08)
        if self.mode == "approach" and near:
            self.mode = "collect"; self.cut_start = x; self.contact_at = now
            self.last_progress = now; self.progress_load = load
        if self.mode in ("collect","sweep"):
            if load-self.progress_load >= 25:
                self.progress_load = load; self.last_progress = now
            if load >= 2250: self.mode = "lift"
            elif self.mode == "collect" and now-self.last_progress >= 3.:
                self.mode = "sweep"; self.sweep_at = now
            elif (self.mode == "collect" and x-self.cut_start >= 3.8) or (self.mode == "sweep" and now-self.sweep_at >= 8.):
                if self.lane_changes and self.lanes:
                    self.mode = "back_out"; self.collection_pass += 1; self.lane = self.lanes.pop(0)
                else: self.mode = "lift"
        if self.mode == "back_out" and x <= self.cut_start-1.5:
            self.mode = "shift"
        if self.mode == "shift" and x <= self.cut_start-4.:
            self.mode = "approach"; self.cut_start = None; self.contact_at = None
        if self.mode == "lift" and boom >= .33 and curl >= .6: self.mode = "carry"
        reach = 1.8+(1.6+1.2*np.cos(boom))*np.cos(art); mouth_error = p[9]-reach
        if self.mode == "carry" and abs(mouth_error) < .4 and abs(speed) < .08: self.mode = "tip"
        self.phase[0] = 0 if self.mode in ("approach","shift","back_out") else 1 if self.mode in ("collect","sweep") else 2 if self.mode == "lift" else 3 if self.mode == "carry" else 4
        if self.mode == "approach": target = 1.2; target_boom = -.1; target_curl = -.1 if load < 20 else .95
        elif self.mode in ("collect","sweep"):
            target = .2 if self.mode == "sweep" else .7; target_boom = -.1
            target_curl = .95 if int((now-self.contact_at)/.8)%2 == 0 else .65
        elif self.mode in ("back_out","shift"):
            target = -1.1; target_boom = .2; target_curl = .95
        elif self.mode == "lift": target = 0.; target_boom = .35; target_curl = .95
        elif self.mode == "carry": target = float(np.clip(mouth_error*.8,-1.2,.25)); target_boom = .35; target_curl = .95
        else: target = 0.; target_boom = .35; target_curl = -.7
        lane = 0. if self.mode in ("carry","tip","lift") else self.lane
        direction = -1. if target < 0 else 1.
        desired_yaw = -direction*np.arctan(.4*(y-lane))
        desired_art = np.clip(-direction*.8*(heading-desired_yaw),-.25,.25)
        if self.mode == "sweep": desired_art = (.55 if abs(self.lane) < .2 else .25)*(1 if int((now-self.sweep_at)/4.)%2 == 0 else -1)
        steer = float(np.clip((desired_art-art)*2,-1,1))
        candidate = float(np.clip(self.integral+(target-speed)*dt,-.4,.4))
        drive = float(np.clip(1.8*(target-speed)+candidate+np.sign(target)*.12,-1,1)); self.integral = candidate
        action = np.array([[drive,steer,np.clip((target_boom-boom)*4,-1,1),np.clip((target_curl-curl)*4,-1,1)]])
        self.last = {"method":"progress_task_reference","mode":self.mode,"phase":int(self.phase[0]),
                     "lane_y_m":lane,"collection_pass":self.collection_pass,"load_progress_kg":float(self.progress_load),
                     "cut_start_x_m":None if self.cut_start is None else float(self.cut_start),"task_time_s":now,
                     "proposal_source":"conventional_task","applied_action":action[0].tolist()}
        return action
