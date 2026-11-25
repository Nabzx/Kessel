"""Reference-specific probing and bumpless holding; consumes local inputs only."""
import numpy as np
from .range_contract import CompleteRangeSupervisor
from .motion_hold import response

METHOD = "bootstrapped_motion_hold"


class BootstrapHoldSupervisor(CompleteRangeSupervisor):
    def __init__(self, actor):
        super().__init__(actor)
        self.previous_motion = None; self.disturbance = 0.; self.estimate_valid = False

    def act(self, observation):
        raw = self.validate(observation); p = raw["proprio"][0]
        elapsed,speed,load = float(p[13]),float(p[4]),float(p[8])
        applied = super().act(observation)
        overriding = bool(self.last["override"]); previous = self.previous_motion
        accepted = probe = cleared = False; acceleration = None; reason = "not_overriding"
        if overriding:
            new_override = previous is None or not previous["override"]
            if new_override:
                self.disturbance = 0.; self.estimate_valid = False; reason = "new_override"
            else:
                acceleration = (speed-previous["speed"])/(elapsed-previous["elapsed"])
                if abs(previous["speed"]) <= .03 or abs(speed) <= .03 or previous["speed"]*speed <= 0:
                    reason = "speed_transition"
                elif abs(acceleration) >= 1.4: reason = "acceleration_limit"
                else:
                    residual = response(previous["speed"],previous["load"])*previous["command"]-acceleration
                    residual -= .1962*float(np.sign(previous["speed"]))
                    self.disturbance = float(np.clip(residual,-.8,.8))
                    accepted = self.estimate_valid = True; reason = "accepted"
            coefficient = response(speed,load); feedforward = self.disturbance/coefficient if self.estimate_valid else 0.
            if self.estimate_valid and abs(speed) <= .08:
                self.integral = 0.; self.last["integral"] = 0.; cleared = True
            drive = float(np.clip(feedforward-2.*speed-self.integral,-1,1))
            if new_override and abs(speed) > .03:
                drive = -.25*float(np.sign(speed)); probe = True
            applied = np.array([[drive,0.,0.,0.]])
        else:
            coefficient = response(speed,load); feedforward = 0.
        self.last["method"] = METHOD; self.last["applied_action"] = applied[0].tolist()
        self.last["observer"] = {"accepted":accepted,"reason":reason,"observed_acceleration_m_s2":acceleration,
            "disturbance_m_s2":self.disturbance,"estimate_valid":self.estimate_valid,
            "response_m_s2_per_command":coefficient,"feedforward_command":feedforward,
            "probe_applied":probe,"integral_cleared":cleared}
        self.previous_motion = {"elapsed":elapsed,"speed":speed,"load":load,
                                "command":float(applied[0,0]),"override":overriding}
        return applied
