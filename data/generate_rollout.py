#!/usr/bin/env python3
"""Generate rollout.json: a scripted placeholder episode for the Kessel demo.

This file is the ONLY thing standing between the front end and a real
trained agent (ADR-0001). Every number the renderer draws (loader pose, rock
positions, world-model prediction, prediction error, HUD values) comes from
data/rollout.json. Swap this script's output for a logged rollout from the
real RL policy + world model and the front end does not change.

Schema (ADR-0001, docs/adr/0001-rollout-data-schema.md):

{
  "meta": {...},
  "rocks_init": [[x, y, z], ...],          # N rocks, initial pile positions
  "boulder_event_frame": int,               # frame at which "Drop boulder" fires
  "frames": [
    {
      "t": float,                           # seconds
      "loader": {"pos": [x,y,z], "heading": rad, "boom": rad, "bucket": rad},
      "rocks": [[x,y,z], ...],              # simulation ground truth, this frame
      "predicted_horizon": [               # world-model prediction, same length every frame
        {"dt": float, "rocks": [[x,y,z], ...]},
        ...
      ],
      "actual_horizon": [                   # ground truth at those same future times, for error calc
        {"dt": float, "rocks": [[x,y,z], ...]},
        ...
      ],
      "hud": {
        "decision_ms": float,
        "prediction_error": float,          # mean position error across horizon, metres
        "episode": int,
        "state": "nominal" | "replanning" | "halted"
      }
    },
    ...
  ]
}
"""

import json
import math
import random

random.seed(7)

FPS = 30
DURATION_S = 14.0
N_FRAMES = int(DURATION_S * FPS)
N_ROCKS = 90
HORIZON_STEPS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]  # seconds ahead
BOULDER_EVENT_T = 8.0  # seconds into the episode

PILE_CENTER = (2.2, 0.0, -0.6)
PILE_RADIUS = 1.9
TUNNEL_HALF_LENGTH = 6.0


def rand_rock_init():
    r = PILE_RADIUS * math.sqrt(random.random())
    theta = random.uniform(0, 2 * math.pi)
    x = PILE_CENTER[0] + r * math.cos(theta)
    z = PILE_CENTER[2] + r * math.sin(theta) * 0.6
    height_bias = max(0.0, 1.0 - r / PILE_RADIUS)
    y = height_bias * random.uniform(0.0, 1.4) + random.uniform(0.0, 0.08)
    return [x, y, z]


rocks_init = [rand_rock_init() for _ in range(N_ROCKS)]
rock_scale = [round(random.uniform(0.55, 1.35), 3) for _ in range(N_ROCKS)]


def loader_pose(t):
    """Scripted approach -> scoop -> reverse -> swing cycle, looping."""
    cycle = 11.0
    phase = t % cycle

    approach_end = 3.2
    scoop_end = 5.6
    reverse_end = 8.4
    swing_end = cycle

    start_x = -4.6
    scoop_x = -0.6

    if phase < approach_end:
        u = phase / approach_end
        x = start_x + (scoop_x - start_x) * ease_in_out(u)
        heading = 0.0
        boom = -0.08
        bucket = 0.05
    elif phase < scoop_end:
        u = (phase - approach_end) / (scoop_end - approach_end)
        x = scoop_x + 0.35 * ease_in_out(u)
        heading = 0.0
        boom = -0.08 + 0.55 * ease_in_out(u)
        bucket = 0.05 + 0.9 * ease_in_out(u)
    elif phase < reverse_end:
        u = (phase - scoop_end) / (reverse_end - scoop_end)
        x = (scoop_x + 0.35) + (start_x - (scoop_x + 0.35)) * ease_in_out(u)
        heading = 0.25 * math.sin(u * math.pi)
        boom = 0.47 - 0.1 * u
        bucket = 0.95
    else:
        u = (phase - reverse_end) / (swing_end - reverse_end)
        x = start_x
        heading = 0.25 * (1 - u) * math.cos(u * math.pi)
        boom = 0.37 + 0.2 * u
        bucket = 0.95 - 0.9 * ease_in_out(u)

    z = PILE_CENTER[2] + 0.4 * math.sin(phase * 0.15)
    return {
        "pos": [round(x, 4), 0.0, round(z, 4)],
        "heading": round(heading, 4),
        "boom": round(boom, 4),
        "bucket": round(bucket, 4),
    }, phase, scoop_end, reverse_end


def ease_in_out(u):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, u)))


def scoop_influence(phase, scoop_end, reverse_end):
    """How much a rock near the bucket gets displaced this instant."""
    if scoop_end <= phase < reverse_end + 0.6:
        u = (phase - scoop_end) / 0.8
        return max(0.0, 1.0 - u) if u < 1.0 else 0.0
    return 0.0


def simulate_rocks(t, halted_from=None):
    """Ground-truth rock positions at time t (deterministic scripted physics)."""
    _, phase, scoop_end, reverse_end = loader_pose(t if halted_from is None else halted_from)
    influence = scoop_influence(phase, scoop_end, reverse_end)
    positions = []
    for i, (bx, by, bz) in enumerate(rocks_init):
        dx = bx - (-0.6)
        dz = bz - PILE_CENTER[2]
        dist = math.hypot(dx, dz)
        near_bucket = max(0.0, 1.0 - dist / 1.1)
        settle = influence * near_bucket
        jitter = 0.015 * math.sin(t * 2.0 + i)
        x = bx + settle * (0.9 + 0.3 * math.sin(i)) + jitter
        y = by - settle * by * 0.7
        z = bz + settle * 0.25 * math.cos(i * 1.7)
        positions.append([round(x, 4), round(max(0.0, y), 4), round(z, 4)])
    return positions


def predicted_rocks(t, dt, noise_scale):
    """World-model's predicted future state: the real simulation plus
    structured, growing uncertainty so the right-hand panel visibly
    diverges further out on the horizon -- exactly what a real learned
    world model looks like before it has converged."""
    base = simulate_rocks(t + dt)
    out = []
    for i, (x, y, z) in enumerate(base):
        n = noise_scale * (0.3 + 0.7 * (dt / HORIZON_STEPS[-1]))
        ox = n * math.sin(i * 1.3 + t * 0.7)
        oy = n * 0.4 * math.cos(i * 0.9 + t)
        oz = n * math.sin(i * 0.6 + t * 0.5 + 1.0)
        out.append([round(x + ox, 4), round(max(0.0, y + oy), 4), round(z + oz, 4)])
    return out


def hud_for(t, episode, boulder_active_until):
    decision_ms = 38 + 14 * (0.5 + 0.5 * math.sin(t * 1.3)) + random.uniform(-2, 2)
    base_err = 0.04 + 0.03 * math.sin(t * 0.4)
    if boulder_active_until is not None and t < boulder_active_until:
        state = "replanning" if t < boulder_active_until - 1.2 else "halted" if t < boulder_active_until - 0.2 else "replanning"
        decision_ms += 55
        base_err += 0.05
    else:
        state = "nominal"
    return {
        "decision_ms": round(max(4.0, decision_ms), 1),
        "prediction_error": round(max(0.01, base_err), 3),
        "episode": episode,
        "state": state,
    }


def build():
    frames = []
    boulder_active_until = None
    episode = 1142

    for i in range(N_FRAMES):
        t = i / FPS
        halted = boulder_active_until is not None and t < boulder_active_until
        halted_from = BOULDER_EVENT_T if halted else None

        loader, phase, scoop_end, reverse_end = loader_pose(t if not halted else BOULDER_EVENT_T)
        rocks = simulate_rocks(t if not halted else BOULDER_EVENT_T)

        if abs(t - BOULDER_EVENT_T) < (0.5 / FPS) and boulder_active_until is None:
            boulder_active_until = BOULDER_EVENT_T + 3.4

        horizon = []
        actual = []
        noise_scale = 0.22 if (boulder_active_until and t < boulder_active_until) else 0.07
        for dt in HORIZON_STEPS:
            horizon.append({"dt": dt, "rocks": predicted_rocks(t if not halted else BOULDER_EVENT_T, dt, noise_scale)})
            actual.append({"dt": dt, "rocks": simulate_rocks((t if not halted else BOULDER_EVENT_T) + dt)})

        frames.append({
            "t": round(t, 3),
            "loader": loader,
            "rocks": rocks,
            "predicted_horizon": horizon,
            "actual_horizon": actual,
            "hud": hud_for(t, episode, boulder_active_until),
        })

        if boulder_active_until is not None and abs(t - boulder_active_until) < (0.5 / FPS):
            episode += 1

    return {
        "meta": {
            "name": "kessel-concept-rollout",
            "description": "Scripted placeholder rollout. Not real model output. "
                            "Generated by data/generate_rollout.py for the Kessel concept demo.",
            "fps": FPS,
            "duration_s": DURATION_S,
            "horizon_steps_s": HORIZON_STEPS,
            "rock_count": N_ROCKS,
            "source": "scripted",
        },
        "rocks_init": rocks_init,
        "rock_scale": rock_scale,
        "boulder_event_frame": int(BOULDER_EVENT_T * FPS),
        "frames": frames,
    }


if __name__ == "__main__":
    rollout = build()
    with open("data/rollout.json", "w") as f:
        json.dump(rollout, f, separators=(",", ":"))
    size_kb = len(json.dumps(rollout)) / 1024
    print(f"Wrote data/rollout.json: {len(rollout['frames'])} frames, "
          f"{N_ROCKS} rocks, {size_kb:.0f} KB")
