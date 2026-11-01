# ADR-0024: Phase 9 scene and state architecture

Status: Accepted; override state superseded by [ADR-0026](0026-phase-9-autonomous-operation.md), presentation extended by [ADR-0027](0027-phase-9-demo-completion.md).

## Context

Phase 9 moves between a globe, biome selection, a Rwanda surface view, an
underground fleet, a selected truck, and a live route override. The renderer
must support animated transitions without keeping every scene's assets in
memory or creating multiple WebGL contexts.

## Decision

Use one persistent `THREE.WebGLRenderer`, canvas, `THREE.Scene`, and camera.
Give the globe, surface, and underground stages separate scene roots and
asset owners. A finite-state controller owns the states `space`,
`biome-select`, `surface-descent`, `fleet`, `truck`, and `override`; it
validates which user actions are available in each state. The transition
coordinator alone owns camera motion and stage cross-fades. State handlers
request transitions and never animate the camera directly.

During a transition, retain the current and next stage roots. On completion,
remove the old root and dispose of its stage-owned GPU resources unless that
stage is explicitly needed again. Shared materials or textures must have
shared ownership and may only be disposed when their final owner releases
them. Cancel or ignore stale asynchronous loads when the requested state has
changed. The selected truck and override states reuse the underground root.

## Consequences

The experience keeps one WebGL context and one camera contract across the
story. Stage assets can be released in line with ADR-0023. The transition
coordinator and state controller are explicit application components; ad hoc
screen flags and per-stage camera loops are not the architecture. A new
biome can be added as a stage later without changing this ownership model.
