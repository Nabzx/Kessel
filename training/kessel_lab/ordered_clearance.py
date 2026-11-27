"""Freshness does not imply packet ordering. Preserve the frozen pilot code."""
from .clearance_stop import LatchedClearanceStop, health

METHOD = "ordered_clearance_bootstrap_stop"


class OrderedClearanceStop(LatchedClearanceStop):
    def __init__(self,actor):
        super().__init__(actor); self.accepted_capture_s = None

    def channel_health(self,packet,now,speed):
        raw = health(packet,now,speed)
        if raw["reason"] in ("clear","blocked_envelope"):
            captured = float(packet["capture_s"])
            if captured < 0 or self.accepted_capture_s is not None and captured <= self.accepted_capture_s:
                return {**raw,"usable":False,"reason":"nonmonotonic_clearance_capture",
                        "release_margin_m":self.release_m}
            self.accepted_capture_s = captured
        return super().channel_health(packet,now,speed)

    def act(self,observation,packet):
        action = super().act(observation,packet)
        self.last.update(method=METHOD,accepted_capture_s=self.accepted_capture_s)
        return action
