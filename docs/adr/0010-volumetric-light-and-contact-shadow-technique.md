# ADR-0010: Volumetric light and contact-shadow technique

Status: Accepted

## Context

The demo needs to look more "high-tech" without a build step and without
breaking the Phase 5 frame budget (ADR-0009: ~21fps under a 4x CPU
throttle on a Pixel 5 profile, which has little headroom to spend).

## Decision

**Volumetric headlamp glow**: not a real volumetric/raymarched light. A
small additive-blended, radially-faded cone mesh (`MeshBasicMaterial`,
`AdditiveBlending`, a baked radial-gradient texture for soft falloff),
parented to the loader and oriented along the headlamp's facing direction.
One extra mesh, one extra draw call per panel -- cheap, and reads
convincingly as a light shaft once bloom picks it up.

**Contact shadows**: not real-time SSAO. A flat circular decal mesh
(`MeshBasicMaterial`, a canvas-generated radial-gradient alpha texture,
`transparent: true`), placed just above the floor under the loader and
under the rock pile's centre. No screen-space pass, no extra render
target.

Both rejected alternatives (a real volumetric light pass, real SSAO) were
ruled out specifically because they add a full-screen shader pass each --
on top of the bloom pass already in both composer chains, that's a cost
this demo's frame budget cannot absorb without regressing Phase 5's
numbers.

## Consequences

Both techniques are additive meshes, not new render passes, so they
should be close to free relative to the existing bloom cost. Validate
against the Phase 5 throttled-device measurement once implemented (#95)
rather than assuming "cheap" is actually cheap.
