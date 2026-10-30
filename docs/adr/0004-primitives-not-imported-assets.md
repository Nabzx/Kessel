# ADR-0004: Primitives, not an imported CC0 asset, for the tunnel and loader

Status: Accepted

## Context

"No build step" (AGENTS.md) does not strictly rule out a CC0 GLTF mesh
fetched at runtime via Three.js's `GLTFLoader` -- that is still plain
JavaScript, no bundler required. The open question was whether a
procedurally built, perturbed primitive tunnel and a primitive-built loader
rig would read as a convincing underground scene, or whether the demo needed
an imported mesh to avoid looking like a programmer-art box with a crate in
it.

## Decision

Primitives only. A perturbed partial-cylinder tunnel shell, a displaced
floor plane, and a loader rig built from boxes and cylinders in a `Group`
hierarchy, lit and composed well, reads clearly as a moody underground
tunnel -- confirmed visually once the lighting rig (ADR-0005) and the
camera framing were corrected. No GLTF import, no external asset fetch, no
licence attribution burden, no load-time cost beyond the rollout data
itself.

## Consequences

Keeps the site genuinely dependency-free beyond the Three.js CDN import map
and `rollout.json`. The cost is real: getting primitives to read well took
real iteration -- material albedo, camera distance from the tunnel wall,
and the partial-cylinder's open-wedge orientation all had to be tuned
correctly before the scene looked like a tunnel rather than an empty box
(see #17's resolution for the specific framing bug this surfaced). A future
phase that wants more organic rock or machine detail can still import a CC0
asset later without this ADR blocking it -- this decision is "primitives
are sufficient for the concept demo," not "primitives forever."
