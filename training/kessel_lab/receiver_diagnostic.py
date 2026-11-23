"""Pure receiver-error and static-force diagnostics; no controller override."""
import math

from kessel_training.phase_memory import SCALE


def mouth_error(proprio):
    reach = 1.8 + (1.6 + 1.2 * math.cos(proprio[6])) * math.cos(proprio[5])
    return proprio[9] - reach


def receiver_x(proprio):
    return proprio[0] + proprio[9] * proprio[3] - proprio[10] * proprio[2]


def static_force(state, drive_command):
    mass = 10500 + state[7]
    requested = drive_command * min(22000, 28000 / max(abs(state[3]), .5))
    grip = state[83] * mass * 9.81 * math.cos(state[84])
    drive = max(-grip, min(grip, requested))
    slope = mass * 9.81 * math.sin(state[84]) * math.cos(state[2])
    rolling = .02 * mass * 9.81 * math.cos(state[84])
    free = drive - slope
    return {"requested_n": requested, "drive_n": drive, "slope_n": slope,
            "free_force_n": free, "rolling_n": rolling,
            "stationary": abs(state[3]) <= .01,
            "within_rolling_resistance": abs(free) <= rolling,
            "scope": "carry-state probe with bucket clear of the pile; not a general traction replacement"}


def recover_proprio(features):
    return [float(features[i]) * SCALE[i] for i in range(15)]
