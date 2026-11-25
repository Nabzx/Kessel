"""Reference-specific disturbance estimate from observed motion; never true grade."""
import numpy as np
from .range_contract import CompleteRangeSupervisor

METHOD = "observed_motion_hold"


def response(speed, observed_load):
    return min(22000.,28000./max(abs(speed),.5))/(10500.+float(np.clip(observed_load,0,3500)))


class MotionHoldSupervisor(CompleteRangeSupervisor):
    def __init__(self, actor):
        super().__init__(actor)
        self.previous_motion = None
        self.disturbance = 0.

    def act(self, observation):
        raw = self.validate(observation); p = raw["proprio"][0]
        elapsed,speed,load = float(p[13]),float(p[4]),float(p[8])
        applied = super().act(observation)
        overriding = bool(self.last["override"]); previous = self.previous_motion
        accepted = False; acceleration = None; reason = "not_overriding"
        if overriding:
            if previous is None or not previous["override"]:
                self.disturbance = 0.; reason = "new_override"
            else:
                acceleration = (speed-previous["speed"])/(elapsed-previous["elapsed"])
                if abs(previous["speed"]) <= .1: reason = "low_speed"
                elif abs(acceleration) >= 1.4: reason = "acceleration_limit"
                else:
                    residual = response(previous["speed"],previous["load"])*previous["command"]-acceleration
                    residual -= .1962*float(np.sign(previous["speed"]))
                    self.disturbance = float(np.clip(residual,-.8,.8)); accepted = True; reason = "accepted"
            coefficient = response(speed,load)
            feedforward = self.disturbance/coefficient
            applied = np.array([[float(np.clip(feedforward-2.*speed-self.integral,-1,1)),0.,0.,0.]])
        else:
            coefficient = response(speed,load); feedforward = 0.
        self.last["method"] = METHOD
        self.last["applied_action"] = applied[0].tolist()
        self.last["observer"] = {"accepted":accepted,"reason":reason,"observed_acceleration_m_s2":acceleration,
                                 "disturbance_m_s2":self.disturbance,"response_m_s2_per_command":coefficient,
                                 "feedforward_command":feedforward}
        self.previous_motion = {"elapsed":elapsed,"speed":speed,"load":load,
                                "command":float(applied[0,0]),"override":overriding}
        return applied
