# ADR-0051: Visual direction and asset sources for the redesigned walkthrough

Status: Accepted

## Context

The maintainer rejected the walkthrough's visual result (#349) despite
passing automated checks. Phase 11's earlier work established that frame
rate and geometry validation say nothing about whether a shot looks
real or communicates the product. #350 required a reference-led
direction, verified asset sourcing and measurable budgets before any
rebuilding starts.

Baseline frames were captured first, on the target hardware — Google
Chrome 156 with the native Apple M1 Metal renderer, retina and
compact-reduced profiles, all nine scenes, 60 fps throughout, no
errors. Those captures are the comparison baseline, not an endorsement.

What the baseline shows, scene by scene:

- **Hero.** A small, low-contrast Earth on near-black. The star field
  exists in `globe-stage.js` but is effectively invisible. Satellites
  read as grey specks. The wordmark is unstyled. It is flat, not
  photographic.
- **Selector.** The chosen environment is a small card; the globe
  dominates. Underground is the **fourth** of five options (`04 / 05`),
  reached by three carousel steps.
- **Surface.** Flat yellow-green terrain closer to a golf course than
  Rwandan hill country; box buildings; vegetation as dark blobs.
- **Underground.** A brown tray with salmon route loops and grey
  blocks. It reads as a diagram, not a mine.
- **Retrofit kit.** Flat grey slabs with green rectangles standing in
  for boards. No connectors, fixings, materials or manufacturing cues.
- **Learning.** Addressed separately under #364; framing fixed.

The source imagery is not the limiting factor. The shipped Blue Marble
texture is already 5400×2700, Black Marble 3600×1800. The deficiency is
shading, exposure, composition and geometric detail.

## Decision

### Photorealistic map tiles are rejected

Google Photorealistic 3D Tiles — directly or through Cesium ion — are
**not** adopted, for three independent reasons, each sufficient alone:

1. **Licence conflict with the delivery model.** The Map Tiles API
   policies prohibit pre-fetching, indexing, storing, caching,
   re-sharing or re-hosting content outside the service, prohibit bulk
   tile download, and prohibit offline use. This repository serves every
   font, texture and model locally under ADR-0034's static package
   allowlist. The two models are incompatible.
2. **Account and key requirement.** The tiles need an API key and a
   billing account. README promises the site runs with "no installation,
   API key or build step".
3. **Coverage is almost certainly absent.** Coverage is city-oriented —
   roughly 2,500 cities across 49 countries. Rutongo is rural, about
   26 km north of Kigali. Coverage must not be assumed; it was not
   demonstrable.

Blackshark and Cesium remain **visual references** for what a credible
geospatial scene looks like. No asset is copied from either.

The local-file fallback is therefore not a fallback at all — it is the
delivery model, and the surface scene is built from openly licensed
public data under ADR-0035.

### Approved sources

| Use | Source | Licence | Notes |
|---|---|---|---|
| Earth day | NASA Blue Marble Next Generation | Public domain | Already shipped at 5400×2700 |
| Earth night | NASA Black Marble | Public domain | Already shipped at 3600×1800 |
| Cloud layer | NASA | Public domain | Already shipped at 2048×1024 |
| Spacecraft | [nasa/NASA-3D-Resources](https://github.com/nasa/NASA-3D-Resources) | Public domain | GLB available; no attribution burden |
| Surface imagery | Copernicus Sentinel-2 | Open, attribution | Regional context, not a surveyed reconstruction |
| Elevation | Copernicus DEM / SRTM | Open, attribution | Terrain around 01°49′03″S 30°03′33″E |
| Scanned PBR | Poly Haven | CC0 | Established pattern from #122/#123 |
| Authored geometry | Blender 5.2.3 LTS via the pinned connector | Repo-owned | ADR-0048 |

Every candidate must record source, licence, modification rights,
resolution, scale and delivered byte cost in the asset manifest before
it ships.

### Art direction

**Palette.** Black, off-white, restrained mineral amber. Red and green
are reserved for operating state and must not appear decoratively.

**Lighting and exposure.** One motivated key per scene with physically
plausible falloff; fill only where it keeps a silhouette legible. Tune
exposure against both large surfaces *and* small objects — Phase 11
already produced a case where lighting tuned on floors and walls blew
small instanced rock to white. Material tint multiplies its texture, so
dark tints cap reflected light however bright the key becomes. Reject
saturated bloom used to imply detail that the geometry does not have.

**Camera grammar.** Each scene states its subject, frames it to a
measured extent, and holds. Motion is motivated: the camera moves when
the subject moves, and holds when the subject works in place. Framing is
derived from scene geometry rather than hard-coded, following the
recorded-stage fix under #364. Where a continuous move cannot be made
convincing, a clean cut or fade is preferred to an unconvincing flight.

**Scale.** Real metres throughout. A machine must read at its true size
against drift dimensions, and the drift against the published
engineering envelope.

**Typography and graphics.** The existing JetBrains Mono / Space Grotesk
pairing is retained. Technical overlays are restrained and earn their
place; no generic floating dashboard furniture, no glow used as
decoration.

**Rejected outright.** Toy geometry. Saturated glow. Flat untextured
slabs standing in for manufactured hardware. Vegetation as dark blobs.
Diagram-coloured routes presented as a physical scene.

### Superseded requirements

- **ADR-0030** — the continuous-journey requirement is relaxed. A clean
  cinematic cut or fade is permitted for the Earth-to-Rwanda arrival and
  the surface-to-underground reveal where a continuous camera move does
  not read convincingly (#382, #383).
- **ADR-0030** — the selector requirement changes: the chosen
  environment fills the background and the globe moves to a side panel
  (#356); Underground becomes the first and default option (#357).
- **ADR-0043 / ADR-0050** — the permanent global "Concept demonstration"
  footer is withdrawn, as explicitly authorised by the maintainer
  (#375). Source distinction is **not** withdrawn: short source labels
  stay beside simulated results and proposed hardware, asset credits
  stay reachable through Sources, and the honesty invariants in
  AGENTS.md otherwise stand unchanged. Nothing scripted may read as
  live inference.
- **ADR-0050** — default learning entry may change as part of #369's
  guided task view, provided every source stays reachable and no failed
  outcome is hidden.

### Budgets

Measured on the target laptop, Chrome with the Metal renderer:

| | Budget |
|---|---|
| Sustained frame rate, any scene | ≥ 55 fps, p95 frame ≤ 20 ms |
| Total transferred bytes, main route | ≤ 28 MB |
| Any single texture | ≤ 2.5 MB delivered |
| Any single model | ≤ 3 MB delivered |
| Draw calls, any scene | ≤ 400 |
| Cold first meaningful frame | ≤ 4 s |
| Main investor route | ~60 s; new chapters are optional and separate |

### Review criteria

Automated checks are necessary and not sufficient. A scene is accepted
only when, on a real captured frame at retina and compact sizes:

1. The subject is identifiable within two seconds without reading copy.
2. The subject occupies a deliberate share of frame — for a working
   machine, not less than a quarter of usable width.
3. Materials read as their real substance.
4. Nothing is blown out or crushed; detail survives in both highlight
   and shadow, verified on large *and* small objects.
5. Technical overlay earns its place.
6. The maintainer records visual judgement explicitly. It is never
   inferred from passing tests or from approval of an earlier direction.

## Consequences

Surface realism must come from geometry, materials and lighting rather
than purchased photogrammetry, which is the more durable result and
keeps the site dependency-free, key-free and offline-capable.

The rejection of map tiles is recorded here so it is not re-proposed:
the blocker is licensing and delivery model, not cost or effort.

Dependent work — #351's prototype, #359's surface strategy and #375's
footer removal — proceeds against this document. #351 must still show a
materially different composition in real frames before dependent asset
and layout work is accepted.
