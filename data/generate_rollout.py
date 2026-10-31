#!/usr/bin/env python3
"""Generate rollout.json: a scripted placeholder episode for the Kessel demo.

This file is the ONLY thing standing between the front end and a real
trained agent. Every number the renderer draws (loader pose, rock
positions, world-model prediction, prediction error, HUD values) comes
from data/rollout.json. Swap this script's output for a logged rollout
from the real RL policy + world model and the front end does not change.

Schema (ADR-0001; attempt_cards added Phase 6c, #113):

{
  "meta": {
    ...,
    "attempt_cards": [{"t": float, "duration": float, "text": str}, ...]
  },
  "rocks_init": [[x, y, z], ...],          # N rocks, initial pile positions
  "boulder_event_frame": int,               # frame at which "Drop boulder" fires
  "frames": [
    {
      "t": float,                           # seconds
      "loader": {"pos": [x,y,z], "heading": rad, "boom": rad, "bucket": rad},
      "rocks": [[x,y,z], ...],              # simulation ground truth, this frame
      "predicted_horizon": [               # world-model prediction, same length every frame
        {"dt": float, "rocks": [[x,y,z], ...], "error": [float, ...]},  # error: per-rock
        ...                                                              # distance vs ground truth at t+dt
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

Phase 6c (#113, #114, #116): the episode is two named attempts, each a
full approach-scoop-carry-drop-return cycle, separated by full-screen
text cards (meta.attempt_cards). Attempt 1 fumbles the carry -- a subset
of rocks spill partway to the dump point instead of arriving -- and runs
a noisier, less accurate world-model prediction. Attempt 2 completes the
same cycle cleanly with a tight, accurate prediction. The boulder/hazard
event (ADR-0003) is unrelated to this narrative and still fires once per
loop, inside attempt 2, plus on demand via the Drop boulder button.
"""

import json
import math
import random

random.seed(7)

FPS = 10
CARD_DURATION = 1.8
ATTEMPT_DURATION = 13.2  # Phase 6c (#112): shorter sub-phases than Phase 6b, snappier motion
DURATION_S = 2 * (CARD_DURATION + ATTEMPT_DURATION)  # 30.0, one full two-attempt episode
N_FRAMES = int(DURATION_S * FPS)
N_ROCKS = 64
HORIZON_STEPS = [0.6, 1.2, 1.8, 2.4]  # seconds ahead
CARRIED_COUNT = 10

ATTEMPT2_START = CARD_DURATION + ATTEMPT_DURATION  # 15.0
BOULDER_EVENT_T = ATTEMPT2_START + CARD_DURATION + 4.0  # 4s into attempt 2's carry phase

PILE_CENTER = (2.2, 0.0, -0.6)
PILE_RADIUS = 1.9
START_X = -1.6
SCOOP_X = -0.6
# The loader's own X travel stays inside ADR-0015's tunnel-radius
# constraint throughout -- the dump point is reached by swinging the
# bucket via heading, not by driving further, since the boom arm's ~2.3
# unit fixed offset already dwarfs any further small X travel the tunnel
# radius could safely allow. See loader_pose_for_attempt's carry phase.
DUMP_HEADING = 1.25


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

# Fixed once: the rocks nearest the scoop point are the ones the loader
# picks up each attempt (#114). A deterministic choice against rocks_init,
# not a function of time, so both attempts carry the same rocks.
_carried_indices = sorted(
    range(N_ROCKS),
    key=lambda i: math.dist(rocks_init[i], (SCOOP_X, 0, PILE_CENTER[2])),
)[:CARRIED_COUNT]
_carried_set = set(_carried_indices)


def ease_in_out(u):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, u)))


def attempt_and_local_t(t):
    """Which attempt is active at time t, local time within it, and
    whether t falls inside that attempt's lead-in text card."""
    t = t % DURATION_S
    segments = [
        (1, CARD_DURATION, True),
        (1, ATTEMPT_DURATION, False),
        (2, CARD_DURATION, True),
        (2, ATTEMPT_DURATION, False),
    ]
    acc = 0.0
    for attempt, dur, in_card in segments:
        if t < acc + dur:
            local = 0.0 if in_card else (t - acc)
            return attempt, local, in_card
        acc += dur
    return 2, ATTEMPT_DURATION, False  # float rounding fallback


def loader_pose_for_attempt(local_t):
    """One attempt's approach -> scoop -> carry -> drop -> return cycle.
    Shorter sub-phases than Phase 6b (#112): more happens per second."""
    approach_end = 3.0
    scoop_end = 5.3
    carry_end = 9.6
    drop_end = 10.8
    return_end = ATTEMPT_DURATION

    if local_t < approach_end:
        u = local_t / approach_end
        x = START_X + (SCOOP_X - START_X) * ease_in_out(u)
        heading, boom, bucket = 0.0, -0.08, 0.05
    elif local_t < scoop_end:
        u = (local_t - approach_end) / (scoop_end - approach_end)
        x = SCOOP_X
        heading = 0.0
        boom = -0.08 + 0.55 * ease_in_out(u)
        bucket = 0.05 + 0.9 * ease_in_out(u)
    elif local_t < carry_end:
        # swing the bucket to the dump point via heading, not by driving
        # further -- the boom arm's fixed offset already moves the
        # bucket's world position far more than the tunnel's radius
        # constraint (ADR-0015) could safely let the loader body travel
        u = (local_t - scoop_end) / (carry_end - scoop_end)
        x = SCOOP_X
        heading = DUMP_HEADING * ease_in_out(u)
        boom, bucket = 0.47, 0.95
    elif local_t < drop_end:
        u = (local_t - carry_end) / (drop_end - carry_end)
        x = SCOOP_X
        heading = DUMP_HEADING
        boom = 0.47 - 0.1 * ease_in_out(u)
        bucket = 0.95 - 0.9 * ease_in_out(u)
    else:
        u = (local_t - drop_end) / (return_end - drop_end)
        x = SCOOP_X + (START_X - SCOOP_X) * ease_in_out(u)
        heading = DUMP_HEADING * (1 - ease_in_out(u))
        boom = 0.37 - 0.45 * ease_in_out(u)
        bucket = 0.05

    z = PILE_CENTER[2] + 0.3 * math.sin(local_t * 0.35)
    pose = {
        "pos": [round(x, 3), 0.0, round(z, 3)],
        "heading": round(heading, 3),
        "boom": round(boom, 3),
        "bucket": round(bucket, 3),
    }
    return pose, scoop_end, carry_end, drop_end


def bucket_world_pos(pose):
    """Approximate world position of the bucket, given a loader pose --
    enough for carried rocks to visibly travel with it (#114), without
    reproducing the renderer's full scene-graph math exactly."""
    pos, heading, boom, bucket = pose["pos"], pose["heading"], pose["boom"], pose["bucket"]
    boom_tip_x = 0.95 + 1.5 * math.cos(boom)
    boom_tip_y = 0.85 + 1.5 * math.sin(boom)
    ba = -bucket * 1.4
    bucket_local_x = 0.3 * math.cos(ba) + 0.18 * math.sin(ba)
    bucket_local_y = 0.3 * math.sin(ba) - 0.18 * math.cos(ba)
    lx = boom_tip_x + bucket_local_x
    ly = boom_tip_y + bucket_local_y
    wx = pos[0] + lx * math.cos(heading)
    wz = pos[2] - lx * math.sin(heading)
    return (wx, ly, wz)


def cluster_jitter(i):
    """Small fixed per-rock offset so carried rocks read as a clump, not
    one point."""
    a = i * 2.399963  # golden-angle-ish spread, deterministic
    r = 0.06 + 0.05 * ((i * 7) % 3)
    return (r * math.cos(a), 0.04 * ((i * 3) % 2), r * math.sin(a) * 0.7)


def dump_pile_offset(i):
    a = i * 2.399963
    r = 0.12 + 0.3 * ((i * 11) % 5) / 5
    height = max(0.0, 0.5 - r) * 0.4
    return (r * math.cos(a), height, r * math.sin(a) * 0.6)


def spill_scatter_offset(i):
    a = i * 1.877
    r = 0.25 + 0.4 * ((i * 5) % 4) / 4
    return (r * math.cos(a), 0.0, r * math.sin(a))


def scoop_influence(local_t, scoop_end, carry_end):
    """How much a non-carried rock near the bucket gets cosmetically
    displaced during the scoop (unrelated to the carried subset)."""
    if scoop_end <= local_t < carry_end:
        u = (local_t - scoop_end) / max(0.5, (carry_end - scoop_end) * 0.4)
        return max(0.0, 1.0 - u) if u < 1.0 else 0.0
    return 0.0


_pose_cache = {}


def pose_at(attempt, local_t):
    key = (attempt, round(local_t, 4))
    if key not in _pose_cache:
        _pose_cache[key] = loader_pose_for_attempt(local_t)
    return _pose_cache[key]


def simulate_rocks(t):
    """Ground-truth rock positions at time t (deterministic scripted physics)."""
    attempt, local_t, in_card = attempt_and_local_t(t)
    local_t = min(local_t, ATTEMPT_DURATION)
    pose, scoop_end, carry_end, drop_end = pose_at(attempt, local_t)
    influence = scoop_influence(local_t, scoop_end, carry_end)

    spill_t = scoop_end + (carry_end - scoop_end) * 0.55
    fall_duration = 0.4

    positions = []
    for i, (bx, by, bz) in enumerate(rocks_init):
        if i in _carried_set and local_t >= scoop_end and not in_card:
            if attempt == 1 and local_t >= spill_t:
                # fumbled: spilled on the floor near where the carry broke
                spill_pose, _, _, _ = pose_at(attempt, spill_t)
                sx, sy, sz = bucket_world_pos(spill_pose)
                ox, _, oz = spill_scatter_offset(i)
                if local_t < spill_t + fall_duration:
                    fall_u = ease_in_out((local_t - spill_t) / fall_duration)
                    y = sy * (1 - fall_u) + 0.04 * fall_u
                else:
                    y = 0.04
                positions.append([round(sx + ox, 3), round(max(0.0, y), 3), round(sz + oz, 3)])
            elif attempt == 2 and local_t >= drop_end:
                # delivered cleanly -- anchored to the bucket's actual
                # position at drop_end, not a separately guessed point,
                # so the settled pile lines up with where it was carried
                drop_pose, _, _, _ = pose_at(attempt, drop_end)
                dx, dy, dz = bucket_world_pos(drop_pose)
                ox, oh, oz = dump_pile_offset(i)
                positions.append([
                    round(dx + ox, 3),
                    round(0.04 + oh, 3),
                    round(dz + oz, 3),
                ])
            else:
                # in transit, following the bucket
                bx2, by2, bz2 = bucket_world_pos(pose)
                jx, jy, jz = cluster_jitter(i)
                positions.append([round(bx2 + jx, 3), round(max(0.0, by2 + jy), 3), round(bz2 + jz, 3)])
            continue

        # not carried (or not picked up yet this attempt): cosmetic settle
        # near the bucket during the scoop, otherwise sits at its pile spot
        dx = bx - SCOOP_X
        dz = bz - PILE_CENTER[2]
        dist = math.hypot(dx, dz)
        near_bucket = max(0.0, 1.0 - dist / 1.1)
        settle = influence * near_bucket
        jitter = 0.015 * math.sin(t * 2.0 + i)
        x = bx + settle * (0.9 + 0.3 * math.sin(i)) + jitter
        y = by - settle * by * 0.7
        z = bz + settle * 0.25 * math.cos(i * 1.7)
        positions.append([round(x, 3), round(max(0.0, y), 3), round(z, 3)])

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
        out.append([round(x + ox, 3), round(max(0.0, y + oy), 3), round(z + oz, 3)])
    return out


def hud_for(t, boulder_active_until):
    attempt, local_t, in_card = attempt_and_local_t(t)
    episode = 1142 if attempt == 1 else 1143

    decision_ms = 38 + 14 * (0.5 + 0.5 * math.sin(t * 1.3)) + random.uniform(-2, 2)
    # Phase 6c (#116): attempt 1's fumble runs a visibly noisier, less
    # accurate world model; attempt 2 is tight and accurate -- ties the
    # heatmap to "trained on world models", not just the text card.
    base_err = (0.09 if attempt == 1 else 0.025) + 0.02 * math.sin(t * 0.4)
    state = "nominal"

    _, scoop_end, carry_end, _ = pose_at(attempt, min(local_t, ATTEMPT_DURATION))
    spill_t = scoop_end + (carry_end - scoop_end) * 0.55
    if attempt == 1 and not in_card and spill_t - 0.3 <= local_t < spill_t + 0.9:
        state = "replanning"
        decision_ms += 40
        base_err += 0.08

    if boulder_active_until is not None and t < boulder_active_until:
        state = "replanning" if t < boulder_active_until - 1.4 else "halted" if t < boulder_active_until - 0.3 else "replanning"
        decision_ms += 55
        base_err += 0.05

    return {
        "decision_ms": round(max(4.0, decision_ms), 1),
        "prediction_error": round(max(0.01, base_err), 3),
        "episode": episode,
        "state": state,
    }


def build():
    frames = []
    boulder_active_until = None

    for i in range(N_FRAMES):
        t = i / FPS
        attempt, local_t, in_card = attempt_and_local_t(t)
        pose, _, _, _ = pose_at(attempt, min(local_t, ATTEMPT_DURATION))

        rocks = simulate_rocks(t)

        if abs(t - BOULDER_EVENT_T) < (0.5 / FPS) and boulder_active_until is None:
            boulder_active_until = BOULDER_EVENT_T + 5.0

        attempt_now, local_now, _ = attempt_and_local_t(t)
        noise_scale = 0.2 if attempt_now == 1 else 0.05
        if boulder_active_until and t < boulder_active_until:
            noise_scale = max(noise_scale, 0.22)

        horizon = []
        for dt in HORIZON_STEPS:
            pred = predicted_rocks(t, dt, noise_scale)
            truth = simulate_rocks(t + dt)
            err = [round(math.dist(p, a), 3) for p, a in zip(pred, truth)]
            horizon.append({"dt": dt, "rocks": pred, "error": err})

        frames.append({
            "t": round(t, 3),
            "loader": pose,
            "rocks": rocks,
            "predicted_horizon": horizon,
            "hud": hud_for(t, boulder_active_until),
        })

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
            "attempt_cards": [
                {"t": 0.0, "duration": CARD_DURATION, "text": "First attempt"},
                {"t": ATTEMPT2_START, "duration": CARD_DURATION, "text": "Trained on world models"},
            ],
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
