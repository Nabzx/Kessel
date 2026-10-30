# ADR-0002: Mobile payload budget for rollout.json

Status: Accepted

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
