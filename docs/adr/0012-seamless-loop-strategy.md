# ADR-0012: Seamless loop strategy

Status: Accepted

## Context

`state.virtualT` wraps from `duration` back to `0` every 12 seconds. The
loader's end-of-cycle pose does not match its start-of-cycle pose, so the
wrap is a visible snap -- fine for development screenshots, not fine for
an unattended demo loop a YC partner might watch for more than one cycle.

## Decision

A short crossfade at the wrap point, implemented entirely in the renderer
(CSS/canvas opacity), not by regenerating `rollout.json`. A full
matching-start-and-end rollout would require reworking the scripted
physics in `data/generate_rollout.py` to close the loop exactly, which is
a bigger change to a file ADR-0001/0002 already locked down, for a problem
a simple crossfade solves just as well visually.

Concretely: a full-viewport overlay fades to the page background colour
over roughly 300ms as `state.virtualT` approaches `duration`, and fades
back out over the same window just after it wraps to `0`. The HUD and
caption stay visible throughout (only the canvases dim) so the demo never
reads as having frozen or broken.

## Consequences

No change to the data schema or the generator. The fix is entirely
additive in `js/app.js` and `css/style.css`. The trade-off: a viewer who
is watching closely will see a brief dip rather than a perfectly
continuous loop -- judged an acceptable, honest way to hide a seam rather
than pretending the loop is seamless when it isn't.
