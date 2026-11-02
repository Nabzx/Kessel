# ADR-0028: Continuous geographic journey

Status: Accepted

Supersedes the embedded-map presentation in ADR-0027 for Phase 10.

## Decision

Keep the pinned local Three.js renderer. Use NASA day/night/cloud imagery for
Earth and the existing Sentinel-2 and Copernicus terrain crop for geographic
context. Construct the mine foreground as an explicitly authored site with
PBR terrain, vegetation, roads, structures and the entrance. Fly the camera
into the terrain and then expose the underground cutaway in the same canvas.
The global and local coordinate scales are interpolated during the approach;
no separate map window appears. This is a cinematic scale transition, not a
claim of surveyed global-to-portal accuracy.

CesiumJS supports streamed geospatial terrain and 3D Tiles and is a valid
future integration. Its imagery/service credentials and Rutongo coverage are
not assumed. Migrating the renderer alone would not create surveyed mine
workings or higher-resolution imagery. The existing public 10 m surface
imagery remains regional context; foreground detail is original geometry and
materials, not fabricated high-resolution satellite data.

First globe target: under 3 MiB of original mission assets before interaction.
Surface and mine are progressive loads, with a 10 MiB mission-asset target;
third-party local libraries/fonts are reported separately. Reuse the licensed
excavator and CC0 mine materials. Preserve source attribution.

## Sources

- https://cesium.com/platform/cesiumjs/
- https://www.blackshark.ai/
- Existing source and redistribution notes in assets/README.md
