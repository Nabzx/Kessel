# ADR-0014: Detail budget vs. the Phase 5 frame budget

Status: Accepted

## Context

Phase 6 adds a long list of visual detail (support beams, rail track,
contact shadows, a volumetric light shaft, mineral glint, falling debris,
camera parallax, two new post-process effects). Phase 5 (ADR-0009)
measured ~21fps under a 4x CPU throttle on a Pixel 5 profile -- not much
headroom to spend before regressing it.

## Decision

Split the Phase 6 detail list by cost profile, not by feature name:

- **Static or additive-mesh items** (support beams, rail track, contact
  shadow decals, the volumetric light cone, mineral glint, the retrofit
  sensor pod) are cheap after initial setup (instanced where repeated) and
  stay on for every device tier.
- **Per-frame-cost items** (falling debris particles, camera parallax
  recompute, animated HUD number tweening) are small but real per-frame
  work and stay on everywhere too, since none of them individually
  approaches the cost of a full render pass.
- **New full-screen shader passes** (the world-model panel's
  scanline/chromatic-aberration treatment, the vignette) are the actual
  risk. These are implemented as cheaply as possible (ADR-0013's
  restrained version, a vignette via a single cheap shader) and then
  **measured** against the Phase 5 throttled profile before being
  accepted, rather than assumed safe. If the regression pass (#95) shows a
  meaningful frame-rate drop, the fallback is gating the heavier
  post-process additions off under `IS_MOBILE` -- the mesh-based detail
  stays everywhere, the shader passes become desktop-only.

## Consequences

This is a policy, not a final number: the actual pass/fail call happens in
#95's measurement, against this ADR's stated fallback (gate shader passes
under `IS_MOBILE` first, before cutting mesh detail) rather than an
undocumented ad hoc choice under deadline pressure.

## Addendum: what #95 actually found

The "mesh-based detail is cheap" assumption above was wrong. #95's
throttled measurement (Pixel 5 profile, 4x CPU throttle -- the same
profile ADR-0009 used) showed ~21fps before Phase 6, ~8fps after all of
it landed. Gating the two shader passes under `IS_MOBILE` alone (the
fallback this ADR specified) only recovered to ~13fps -- the mesh and
material additions were real cost too, not negligible "after initial
setup" as assumed.

Bisected by gating categories one at a time and re-measuring: the bump
map (#74, per-fragment sampling across 64 lit instances) and the
`DoubleSide` additive light-shaft cone (#72) each moved the number only
slightly. The two biggest contributors turned out to be (a) the combined
weight of support beams, rail track, contact shadows, mineral glint and
debris particles together -- no single one dominated, but cutting all of
them under `IS_MOBILE` mattered -- and (b) the dust system's switch to a
textured, additively-blended sprite (#83): dropping the texture on mobile
specifically (keeping the plain coloured dot) recovered more than
shrinking the sprite size alone did.

Final policy, corrected from the original: on mobile, every Phase 6
addition gates off except camera parallax and HUD-number easing (genuinely
cheap, confirmed negligible individually) -- support beams, rail track,
contact shadows, the light shaft, mineral glint, debris, the rock bump
map, and both shader passes are desktop-only. Re-measured after the full
set of gates: readings ranged 12-20fps across repeated identical runs
(this environment's CPU-throttle emulation is itself noisy under
concurrent load), averaging close to the pre-Phase-6 baseline. Treat any
single throttled-fps reading in this repo with that noise band in mind --
prefer several runs over one.
