# ADR-0009: Mobile quality thresholds

Status: Accepted

## Context

Two WebGL canvases, each with its own `EffectComposer` and bloom pass,
rendering simultaneously, is a real frame-budget risk on a phone. The
renderer needed concrete numbers for device-pixel-ratio cap, dust particle
count, and antialiasing -- not just a qualitative "make it lighter on
mobile."

## Decision

Gated on a single `IS_MOBILE` check (`matchMedia("(max-width: 720px)")` or
a mobile user-agent string), set once at load:

- **DPR cap**: 1.6 on mobile, 2 on desktop (`DPR_CAP`). Uncapped device
  pixel ratio on a high-density phone screen multiplies fragment shader
  cost for no perceptible gain at this viewing distance.
- **Dust particle count**: 140 per panel on mobile, 320 on desktop. Two
  panels means this is doubled in practice (280 vs 640 total points).
- **Antialiasing**: off on mobile (`antialias: !IS_MOBILE`), on desktop.
  Bloom already softens hard edges enough that MSAA's cost is not worth it
  at mobile viewport sizes.

Verified by device emulation (Playwright's iPhone 13 profile, portrait and
landscape) rather than a physical device for this round -- see #46 for why
that is a documented limitation, not a silent gap.

## Consequences

These four numbers are the tuning surface for future device-tier work. If
a future phase needs a third tier (e.g. a genuinely low-end Android
device), it extends this same `IS_MOBILE`-gated pattern rather than adding
new ad hoc checks throughout the renderer.
