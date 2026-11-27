"""Idealised clearance packets and an explicit conventional stop handoff."""
import copy

import numpy as np

from kessel_training.kinematics import footprints
from .bootstrap_hold import BootstrapHoldSupervisor
from .range_contract import canonicalize

VERSION = "synthetic-envelope-clearance-1"
FRAME = "world-aligned-body-envelope"
METHOD = "clearance_bootstrap_stop"


def synthetic_clearance(env):
    """Privileged synthetic sensor producer. Controller never receives the env."""
    if env.num_envs != 1: raise ValueError("single-slot clearance sensor required")
    corners = footprints(env.pose,env.joints)[0]
    low = corners.min(axis=(0,1)); high = corners.max(axis=(0,1))
    distance = np.array([18.-high[0],low[0]+11.,env.half_width[0]-high[1],low[1]+env.half_width[0]])
    for xmin,xmax,ymin,ymax in env.scene.obstacles:
        if low[1] <= ymax and high[1] >= ymin:
            if xmin >= high[0]: distance[0] = min(distance[0],xmin-high[0])
            elif xmax <= low[0]: distance[1] = min(distance[1],low[0]-xmax)
            else: distance[:2] = 0
        if low[0] <= xmax and high[0] >= xmin:
            if ymin >= high[1]: distance[2] = min(distance[2],ymin-high[1])
            elif ymax <= low[1]: distance[3] = min(distance[3],low[1]-ymax)
            else: distance[2:] = 0
    return {"version":VERSION,"frame":FRAME,"capture_s":float(env.elapsed[0]),"valid":True,
            "max_range_m":12.,"distance_m":np.clip(distance,0,12).tolist(),
            "producer":"idealised privileged geometric sensor; no implemented perception"}


def health(packet,now,speed):
    threshold = .6+.2*abs(speed)+speed**2/1.2
    if packet is None: return {"usable":False,"reason":"missing_clearance","threshold_m":threshold}
    try:
        distances = np.asarray(packet["distance_m"],dtype=float)
        captured = packet["capture_s"]; limit = packet["max_range_m"]
        if packet["version"] != VERSION or packet["frame"] != FRAME or type(packet["valid"]) is not bool:
            raise ValueError("clearance schema differs")
        if isinstance(captured,bool) or isinstance(limit,bool) or not np.isfinite([captured,limit]).all(): raise ValueError("invalid channel time/range")
        if distances.shape != (4,) or not np.isfinite(distances).all() or limit != 12 or (distances < 0).any() or (distances > limit).any():
            raise ValueError("invalid clearance distances")
        if not packet["valid"]: reason = "invalid_clearance"
        elif not 0 <= now-captured <= .2+1e-9: reason = "stale_or_future_clearance"
        elif min(distances[:2]) <= threshold or min(distances[2:]) <= .3: reason = "blocked_envelope"
        else: reason = "clear"
    except (KeyError,TypeError,ValueError): reason = "malformed_clearance"
    return {"usable":reason == "clear","reason":reason,"threshold_m":threshold}


class ClearanceStop:
    def __init__(self,actor): self.supervisor = BootstrapHoldSupervisor(actor); self.last = None
    @property
    def memory(self): return self.supervisor.memory
    def act(self,observation,packet):
        obs,range_health = canonicalize(observation)
        p = obs["proprio"][0]; channel = health(packet,float(p[13]),float(p[4]))
        handoff = {k:v.copy() for k,v in obs.items()}
        if not channel["usable"]:
            handoff["range_valid"][:] = 0; handoff["local_height_m"][:] = 0
            handoff["proprio"][0,12] = 0
        action = self.supervisor.act(handoff)
        self.last = {"method":METHOD,"clearance":channel,"range_health":range_health,
                     "proposal_input":"clearance_handoff_mask" if not channel["usable"] else "canonical_range",
                     "packet":copy.deepcopy(packet),"supervision":copy.deepcopy(self.supervisor.last)}
        return action
