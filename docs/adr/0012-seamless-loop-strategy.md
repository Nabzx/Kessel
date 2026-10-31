# ADR-0012: Seamless loop strategy

Status: Accepted

## Context

`state.virtualT` wraps from `duration` back to `0` every 12 seconds. The
loader's end-of-cycle pose does not match its start-of-cycle pose, so the
wrap is a visible snap -- fine for development screenshots, not fine for
an unattended demo loop a YC partner might watch for more than one cycle.

## Decision

A short crossfade at the wrap point, not a regenerated `rollout.json`. A
full matching-start-and-end rollout would require reworking the scripted
physics in `data/generate_rollout.py` to close the loop exactly, which is
a bigger change to a file ADR-0001/0002 already locked down, for a problem
a simple crossfade solves just as well visually.

**Implementation note, revised from the original plan:** this was first
built as a DOM overlay (a `div` positioned over the canvases, faded via a
CSS class toggle). That broke rendering outright in this environment --
toggling the class even once left both WebGL canvases permanently black
for the rest of the session. Isolated by bisecting the change: removing
only that `classList.toggle` call restored correct rendering; a hardcoded
`false` (so the call never fires) also rendered correctly; the call firing
even a single time reproduced the failure consistently across five runs.
Rather than chase the exact compositing mechanism further, the crossfade
was rebuilt as a `ShaderPass` (`FADE_SHADER`) added to both composer
chains, driven by a smoothstep of `distToSeam` against
`LOOP_VEIL_WINDOW_S` -- entirely inside the WebGL pipeline, no DOM
mutation on every tick, and strictly safer regardless of root cause. The
HTML `div` and its CSS were removed.

## Consequences

No change to the data schema or the generator. The fix is entirely
additive in `js/app.js`. The trade-off: a viewer who is watching closely
will see a brief dip rather than a perfectly continuous loop -- judged an
acceptable, honest way to hide a seam rather than pretending the loop is
seamless when it isn't. More generally: this repo's renderer should avoid
toggling CSS classes on elements layered over the WebGL canvases inside
the render loop -- prefer driving visual state through uniforms/shader
passes instead, now that this failure mode is known.
