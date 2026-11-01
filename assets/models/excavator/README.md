# Loader model

CC-BY 3D model from Sketchfab: ["Excavator 3d Rigging"](https://sketchfab.com/3d-models/excavator-3d-rigging-f82f787abd304dea89667e078ccf7052)
by [mohamed.salaah880](https://sketchfab.com/mohamed.salaah880), licensed
under [CC-BY-4.0](http://creativecommons.org/licenses/by/4.0/).

> This work is based on "Excavator 3d Rigging"
> (https://sketchfab.com/3d-models/excavator-3d-rigging-f82f787abd304dea89667e078ccf7052)
> by mohamed.salaah880 (https://sketchfab.com/mohamed.salaah880)
> licensed under CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/)

Replaces the primitive box-built loader rig (#124), desktop solid-panel
only -- see ADR for the full decision history (ADR-0017 adopted a
CC-BY model in principle; this is the specific pick).

## Files

- `excavator.gltf` -- the model, re-exported from the Sketchfab
  download with its texture reference pointed at the compressed JPEG
  below instead of the original embedded PNG (geometry buffers stay
  embedded as base64; only the 2048x2048 PNG was re-encoded).
- `textures/excavator_diff.jpg` -- the diffuse texture, downscaled to
  1024px / JPEG quality 80 from the original embedded 2048x2048 PNG
  (~7.4MB decoded). ~460KB.

## Rig

The source has no bone names (every joint is just "Bone") and no
baked animation clip -- it's driven by rotating specific bones
directly, same way the primitive rig's boom/bucket Groups are. Found
by loading the model, rotating each bone individually, and screenshotting
to see which one moved the boom vs. the bucket:

- Bone index 1 (in `model.traverse()`'s bone-encounter order, *not*
  the glTF node index) = the boom's base joint.
- Bone index 5 = the bucket's curl joint.
- Bone index 7 = cab swing/turret (unused -- the existing animation
  has no cab-swing data).
- Bones 9/10 = undercarriage/track joints (unused -- tracks aren't
  animated, same as the primitive rig's wheels weren't modelled as a
  real suspension).

See `EXCAVATOR_BOOM_BONE_INDEX` / `EXCAVATOR_BUCKET_BONE_INDEX` in
`js/app.js`.
