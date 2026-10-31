# ADR-0016: Physics runs once in the generator, not live in the browser

Status: Accepted

## Context

Rapier (or any real physics engine) could run two ways: live in the
browser, simulating the rock pile and bucket interaction in real time, or
once inside `data/generate_rollout.py`'s pipeline, with the results baked
into `rollout.json` exactly like every other scripted value today.

Live-in-browser physics would be a genuine architecture change: AGENTS.md's
"front end is data-only" invariant, true since Phase 1, means the renderer
has no notion of a rock pile or a loader as anything other than numbers to
place meshes at. A real-time simulation would make the renderer itself
stateful and non-reproducible -- every page load could differ, scrubbing
to a specific moment would no longer be well-defined, and "swap
`rollout.json` for a logged rollout from the real policy, zero front-end
changes" (ADR-0001) would no longer be simply true, since there would be
two different sources of rock motion (data-driven playback vs. live
simulation) to reconcile.

## Decision

Physics runs once, server-side, as part of generating `rollout.json`. The
renderer's contract doesn't change at all: it still just plays back
per-frame positions from a JSON file. What changes is how those positions
get computed -- a real physics simulation instead of the current
hand-tuned lerp/offset heuristics (`bucket_world_pos`, the settle-near-
bucket formulas).

This has a direct, favourable consequence for ADR-0002's payload budget
and the Phase 5/6 mobile frame-budget work (ADR-0009, ADR-0014): **physics
itself costs zero runtime payload and zero runtime simulation cost**. No
WASM fetch, no `requestAnimationFrame`-driven rigid-body stepping, nothing
for a phone's CPU to do that it isn't already doing. The generator's own
runtime (a one-off `python data/generate_rollout.py` run, not something a
viewer ever waits on) is free to use whatever physics library is most
convenient -- a decision for a follow-up research ticket, not this one.

## Consequences

The real runtime cost in this phase is the *asset* payload -- Poly
Haven textures, rock geometry, a loader model -- not physics. That
re-frames what #120's "how far does load budget stretch" question is
actually deciding: not "can we afford Rapier's WASM binary" (we don't pay
that cost at all), but "how large can the downloaded textures and models
be before they hurt cold-open load time." #128's re-verification should
measure against that framing.

The generator produces richer, more physically grounded motion than
today's hand-authored curves, without touching the "data-only front end"
invariant that has held since Phase 1.
