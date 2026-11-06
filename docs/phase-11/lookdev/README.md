# Geological material study

An isolated browser prototype for #201, #202 and #203. It does not replace the
main cinematic experience or present learned output. Source/geometry decisions
are in [ADR-0035](../../adr/0035-public-geometry-and-look-development.md).

From the repository root:

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

Open [the study](http://localhost:8080/docs/phase-11/lookdev/). Select a material
and lighting preset, inspect the surface, or switch to the separately credited
scan reference. Pause stops the authored joint motion. Reduced motion starts
paused and removes the camera animation; an explicit Resume can enable motion.

## Controlled comparison

The two new sets share a 2.7 m display repeat, geometry, camera and lighting.
The old wall is 512 px rather than 1K and is included as a baseline, not a
resolution-matched scientific ablation. Base colour uses sRGB; the OpenGL
normal, roughness and occlusion maps remain linear. Dominant-plane UVs avoid
the large side-wall stretch of a top-only projection. This remains a coarse
synthetic shell, not the full cutaway rebuild planned in #255.

The original studio CubeUV reflection asset is reused. Neutral light makes
material differences inspectable; the mine preset uses restrained ambient
light and local work lamps. No screen-space post-processing pass or runtime
asset API is added. The HUD reports actual frame p95 and rendered triangles.
The scan uses an untextured translucent surface and its actual triangle edges.
It never shows a metre repeat or fabricated calibrated dimensions.

## Reference shot sheet

Capture the old wall, both natural sets at the overhead view, both natural
sets at the inspection view, local work lighting and the scan reference.
Review silhouette, floor contact, machine readability, texture repeat, exposed
surfaces and caption contrast. Main experience pricing, manual override and
chase-camera flows remain excluded.

```sh
node scripts/verify-lookdev.cjs
```

Set `KESSEL_URL` for the server URL and `KESSEL_QA_DIR` for output. The runner
uses installed Chrome and a parent-directory Playwright installation, as the
main demo QA does. Its report records native GPU identity, samples, errors,
layout, source-view restoration and reduced-motion checks. This is laptop
evidence; it does not qualify a phone or prove a future full mine will meet the
same frame budget.

## Sources

See [the manifest](manifest.json), [asset notices](assets/README.md),
[source selection](../../research/2026-11-06-asset-selection.md) and
[tunnel inspection](../../research/2026-11-06-public-tunnel-geometry.md).
