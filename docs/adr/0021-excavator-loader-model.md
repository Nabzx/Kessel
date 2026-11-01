# ADR-0021: Excavator model replaces the primitive loader rig

Status: Accepted

## Context

#124 (ADR-0017: adopt a CC-BY model) needed a specific pick. Research
turned up wheel-loader candidates, but the maintainer separately asked
for an excavator-style hauler instead and linked two Sketchfab models
directly. Both turned out unusable as the *animated* hauler:

- "Old underground mine excavation 06" -- a paid Sketchfab Store item
  ($31.99), "Standard" licence (not Creative Commons), not
  downloadable without purchase, ~1M triangles.
- "Mining excavator, Mining machine" -- CC-BY, free, downloadable, but
  a photogrammetry scan (drone + camera, `RealityCapture`/`RealityScan`
  tags) fused into ~992k triangles. Even though its glTF export splits
  into 14 separate mesh objects, their bounding boxes are all nearly
  identical and overlapping -- they're arbitrary chunks from whatever
  decimation tool processed the raw scan, not semantically separate
  parts. No skin, no bones, nothing to animate a boom or bucket with.

## Decision

["Excavator 3d Rigging"](https://sketchfab.com/3d-models/excavator-3d-rigging-f82f787abd304dea89667e078ccf7052)
by mohamed.salaah880 -- CC-BY, free, 10,000 triangles, and a real
skinned/rigged CG model (11 bones, one skin, no baked animation clip).
Credited in `assets/models/excavator/README.md`.

The source has no bone names -- every joint is just "Bone" -- and no
animation clip, so which bone does what was found empirically: load
the model, rotate each bone individually, screenshot, read off the
effect. Bone 1 (in Three.js's `model.traverse()` bone-encounter order)
is the boom's base joint; bone 5 is the bucket's curl joint. Driven
directly by rotation, the same way the primitive rig's `boomPivot`/
`bucketPivot` Groups always were -- `applyLoaderPose` (js/app.js) now
takes an axis/scale/offset per rig so the same function drives both
the primitive Groups (Z axis) and this model's bones (X axis) without
needing two separate pose-application code paths.

The downloaded export embedded its diffuse texture as base64 PNG
inside the `.gltf` itself (2048x2048, ~7.4MB decoded) -- re-exported
as an external 1024px/quality-80 JPEG (~460KB) referenced by URI
instead, same "trim the payload" pattern as #122/#123's textures.
Total footprint ~3.7MB, desktop-only (mobile and the wireframe
prediction panel keep the primitive rig, same pattern as the rock
model in #123 -- a SkinnedMesh is real GPU cost mobile doesn't need to
pay, and the wireframe panel's own low-poly silhouette reads better
for the sci-fi "ghost" look, ADR-0013, than this model's real geometry
would in wireframe).

## Consequences

`assets/models/excavator-3d-rigging/` (the raw, unedited Sketchfab
download -- 66MB mine-excavation scan included, since that's where it
was first placed) is not committed; only the cleaned-up
`assets/models/excavator/` is. `generate_rollout.py`'s `boom`/`bucket`
values and the renderer's animation timing are completely unchanged --
only the mesh/rig driving them changed, same invariant #123 and #124
were scoped around from the start.
