# ADR-0005: Lighting rig that reads under bloom

Status: Accepted

## Context

A first lighting pass (a single warm point light) left the tunnel and
loader nearly invisible against pure black. The fix was not obvious: the
geometry and framing were confirmed correct by raycasting from the camera
to the tunnel mesh (hits at 3.7-8.3m in every direction tested, nothing
degenerate), and swapping the tunnel material to flat white under the same
lighting rendered a clean, well-shaded curved surface. The actual fault was
albedo: a `0x2a2620`-class "dark rock" colour is simply too dark to read as
anything but near-black once multiplied through a Lambertian response and
ACES tone mapping, regardless of how much light hits it.

## Decision

Two changes, not one:

1. **A five-light rig**: `AmbientLight` (fills shadow floor uniformly),
   `HemisphereLight` (sky/ground tint, so the ceiling reads cooler than the
   floor), a warm `headlamp` `PointLight` near the loader, a second warm
   `keyFill` point light for the loader's near side, a cool cyan `farGlow`
   point light for depth into the tunnel, and a soft `rim` `DirectionalLight`
   for silhouette. Locked intensities and colours are in `js/app.js`'s
   `buildCommonScene`.
2. **Material albedo lifted well above what "looks right" in a flat-lit
   reference image.** Tunnel wall, floor, loader cab and loader wheels all
   moved from near-black (`0x2a2620`-class) to mid-tone (`0x6b5f4d`-class)
   colours. A "dark, moody rock" material that is *actually* dark in RGB
   terms reads as nothing at all under realistic point-light falloff and
   fog; the mood has to come from the lighting and fog, not from a material
   colour that is already most of the way to black before any shading is
   applied.

## Consequences

The scene now reads clearly as an underground tunnel with a visible floor,
ceiling silhouette, and a legible loader, while staying dark and moody
overall (confirmed in `assets/` screenshots). The lesson generalises: any
future material added to this scene should be sanity-checked against a flat
white reference under the same lighting before being called "too bright" --
it is very easy to mistake "the lighting is broken" for "the albedo is
already black."
