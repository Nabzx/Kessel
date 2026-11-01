# ADR-0001: Rollout data schema

Status: Superseded by [ADR-0022](0022-phase-9-mission-data-contract.md)

## Context

AGENTS.md's "front end is data-only" invariant means `index.html`/`js/app.js`
must never hardcode scene content. Every value the renderer draws — loader
pose, rock positions, the world model's predicted future state, HUD numbers
— has to come from one file, in a shape generic enough that a logged rollout
from the real trained policy and world model can replace the scripted
placeholder (`data/generate_rollout.py`) without a front-end change.

## Decision

`data/rollout.json` has this shape:

```
{
  "meta": {
    "name", "description", "fps", "duration_s",
    "horizon_steps_s": [float, ...],
    "rock_count", "source": "scripted" | "logged"
  },
  "rocks_init": [[x, y, z], ...],   // generation-time only; not read by the renderer
  "rock_scale": [float, ...],        // per-rock instance scale, constant across the rollout
  "boulder_event_frame": int,
  "frames": [
    {
      "t": float,
      "loader": {"pos": [x,y,z], "heading": rad, "boom": rad, "bucket": rad},
      "rocks": [[x,y,z], ...],                      // ground truth, this frame
      "predicted_horizon": [
        {"dt": float, "rocks": [[x,y,z], ...], "error": [float, ...]},
        ...
      ],
      "hud": {"decision_ms", "prediction_error", "episode", "state"}
    },
    ...
  ]
}
```

`rocks_init` is carried for transparency and debugging (it is how
`generate_rollout.py` seeds the pile) but the renderer never reads it — every
frame already carries absolute rock positions. `rock_scale` is read once per
rock, not per frame, since a rock's size does not change over an episode.

`predicted_horizon[i].error` is a per-rock scalar distance between the
predicted and ground-truth position at that horizon step, not a duplicate
full position array — see ADR-0002 for why.

## Consequences

The renderer (`js/app.js`) only ever asks "what frame is it, what horizon
step is selected" and reads arrays off this structure; it has no notion of
tunnels, loaders, or rocks as anything other than numbers to place meshes at.
A logged rollout from the real stack is a drop-in replacement as long as it
matches this shape and `meta.source` is set to `"logged"`.

The cost: the schema has no per-rock identity beyond array index, so a rock
cannot be tracked by a stable ID across a schema change that reorders the
array. Acceptable for an illustrative pile; would need revisiting if a future
feature needs to reference one specific rock across frames by name.
