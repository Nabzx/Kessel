# ADR-0019: Explicit `loader.phase` field, and a phase-aware camera

Status: Accepted

## Context

Camera work was flagged as part of the direction reset alongside
lighting (ADR-0018). The chase camera (Phase 6b, #105) follows the
loader's world position and heading uniformly throughout the cycle.
But the loader's actual motion is very lopsided: it drives a short
distance during approach and return (the only phases where its X
position changes at all, per ADR-0015's tunnel-radius travel
constraint), then sits at a fixed position for the scoop, carry and
drop phases, where only its heading sweeps -- up to ~72 degrees
(`DUMP_HEADING`) -- while the boom and bucket animate.

A camera that rotates `CHASE_OFFSET` by heading throughout reads fine
while the loader is actually driving (the rotation matches real
motion), but during scoop/carry/drop it swings the camera through the
same ~72-degree arc around an otherwise-stationary subject, which
reads as the camera spinning for no reason the viewer can see, rather
than a clean view of the work happening. This was very likely part of
what read as a confused/unclear camera even before ADR-0018's render
fixes.

## Decision

The renderer needs to know which phase is active to treat these two
situations differently, and deriving that purely from pose numbers in
`js/app.js` (there is no single reliable threshold on heading/boom/
bucket alone) would duplicate `generate_rollout.py`'s own phase logic
and drift from it. Per the "front end is data-only" invariant
(AGENTS.md, ADR-0001), the generator already knows the phase it's
computing a pose for -- it should just say so.

`frames[i].loader` gains a `phase` field: one of `"approach"`,
`"scoop"`, `"carry"`, `"drop"`, `"return"`. A real logged rollout
would carry whatever the actual policy's phase/subtask label is
(or a placeholder constant, if it doesn't have one) -- the renderer's
contract is just "a phase string exists," not anything about how it
was computed.

The renderer uses it to pick a camera mode, not to change anything
about the data a real rollout would need to reproduce:
- **approach / return** ("drive" mode): unchanged -- the existing
  smooth chase-follow, offset rotated by heading, since the rotation
  tracks real motion here.
- **scoop / carry / drop** ("work" mode): the camera target is a
  fixed offset in world space from wherever the loader was standing
  when the work phase began, not rotated by heading. The loader turns
  in view rather than the camera orbiting with it -- a static,
  legible shot of the action instead of a spin.

Both modes still feed the same exponential position/lookAt smoothing
already in place, so the transition between them at a phase boundary
is gradual, not a hard cut.

## Consequences

`data/generate_rollout.py` and `js/app.js` both change. Payload cost
is negligible -- one short string per frame. This is exactly the kind
of schema addition ADR-0001 anticipated handling via a documented
field, not a renderer-side guess.
