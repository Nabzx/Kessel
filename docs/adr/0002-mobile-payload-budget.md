# ADR-0002: Mobile payload budget for rollout.json

Status: Superseded by [ADR-0023](0023-phase-9-progressive-payload.md)

## Context

A first, naive encoding of the schema in ADR-0001 — 30fps, 14 seconds, 90
rocks, a 6-step prediction horizon, and a full ground-truth position array
stored alongside every predicted one for error calculation — produced a
~13MB `rollout.json`. That is a bad first load on a mobile link for a demo
whose entire point is to be opened from an application link in under a
minute.

## Decision

Four changes bring this down to ~2.3MB raw (smaller again once GitHub Pages
serves it gzipped):

1. **Lower sampling, not visual quality.** 20fps / 12s (240 frames) instead
   of 30fps / 14s. The renderer interpolates between sampled frames
   (Phase 2, #22), so display-refresh-rate smoothness is unaffected.
2. **Fewer rocks.** 64 instead of 90. Still reads as a substantial pile at
   the demo's camera distance.
3. **Shorter, coarser horizon.** 4 steps (`[0.6, 1.2, 1.8, 2.4]` seconds)
   instead of 6. Still shows the "prediction gets less confident further
   out" effect the world-model panel exists to demonstrate.
4. **Error scalar instead of a duplicate position array.** The naive
   encoding stored a full ground-truth `[x,y,z]` per rock per horizon step
   purely to let the front end compute an error magnitude. Precomputing that
   magnitude in the generator and storing one float per rock removes the
   single largest contributor to file size with no visible loss — the
   heatmap only ever needed the magnitude, never the raw ground-truth
   position.
5. **3 decimal places**, down from 4, on all coordinates.

## Consequences

The scripted rollout now loads fast on a mobile connection. The trade-off
lives entirely in the generator, not the renderer: if a future logged
rollout needs a longer horizon or finer sampling, these five knobs
(`FPS`, `DURATION_S`, `N_ROCKS`, `HORIZON_STEPS`, coordinate rounding) are
where that budget gets spent, and the real pipeline should be held to a
similar ceiling for the same reason this one is.

## Addendum: revised for Phase 6b's pacing correction

Direct maintainer feedback (#101) asked for a significantly longer,
slower episode (one 30s cycle, not several rushed 12s ones). Holding
`FPS` at 20 would have grown the file to ~5MB for the same sampling
density. Dropping `FPS` to 10 instead -- halving sampling density, not
quality, per this ADR's original "lower sampling, not visual quality"
principle -- lands the regenerated file at ~2.9MB (300 frames). The
renderer's frame interpolation (unchanged) covers the lower sample rate
just as it did at 20fps; if anything a 10fps sample of genuinely slower
motion is a smaller per-frame step than a 20fps sample of the old faster
cycle was. 2.9MB is accepted as the revised ceiling for this build,
~25% over the original ~2.3MB target but still a fast mobile load, and
still well under the original 13MB naive encoding this ADR exists to
avoid.
