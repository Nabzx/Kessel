# Phase 11 source selection

Issue #202. Research date: 6 November 2026. Decision:
[ADR-0035](../adr/0035-public-geometry-and-look-development.md).
The executable source record is [the manifest](../phase-11/lookdev/manifest.json).

## Cleared for the comparison

Rock Face 03 and Dark Rock 02 were retrieved from Poly Haven's documented
public API/download URLs with an identifying research user agent. Both source
pages and the asset licence establish CC0. The four maps per material are
official, unmodified 1K JPEGs: base colour, OpenGL normal, roughness and AO.
Each provider MD5 was checked; acquisition date, creator, source URL, byte size,
processing and SHA-256 are recorded per file. No generated image substitutes
for a real source texture.

The eight maps total 6,146,865 transfer bytes. A conservative RGBA8-plus-mips
estimate is about 21.3 MiB per four-map material set; the actual browser texture
count is measured separately. Future packaging should compare packed channels,
WebP/KTX2 and LODs under #253 before main-scene adoption. This audit does not
claim those formats or a complete mesh pipeline are implemented.

Rock Face 03's source repeat is 2.7 m. Dark Rock 02's is approximately 2 m.
The controlled comparison displays both at 2.7 m per repeat and 1K resolution,
on identical geometry under identical lighting. That is a comparison setting,
not a remeasurement of the Dark Rock source. The old wall is shown as a
512 px baseline, so comparison against it also includes a resolution change.

The existing excavator remains credited under CC BY 4.0. Its documented boom
and bucket joints, 1 and 5, are retained. No new branded vehicle is adopted.
The floor and ore retain their existing Poly Haven maps and notices. Their
unchanged files and the original Kessel rig descriptors have audit hashes in
the manifest. The studio reflection map is the existing original Kessel asset.

## Deferred candidates and viable fallbacks

| Candidate | Actual result | Decision |
| --- | --- | --- |
| ambientCG Rock 030 | Metadata API readable; official archive download returned 403 | Do not import an unverified archive. Use the available Dark Rock 02 comparison. |
| Modular Industrial Pipes 01 | Source metadata reports 12,340 triangles, Jorge Camacho, CC0 | Eligible for selective preparation, but no pieces are adopted before topology/scale/material cost is checked. Existing simple service props remain viable. |
| Coast Rocks 01 | High-poly coastal source is poorly matched to a small underground heading | Keep the original synthetic rock shell; avoid introducing vegetation/coastal detail into the mine. |
| NASA ISS/orbital models | Library is public but asset-specific notices and LODs still require preparation | Retain the original tiny satellite geometry until #265's specific checks. No NASA model has been downloaded or added here. |
| Public surface dump truck | Surface envelope is not an underground-machine fit; exact download/rig not adopted | Retain the original compact underground hauler. |
| Bedretto scan | Publisher record returned 403; file units/CRS not inspected | No adoption. Keep the synthetic layout and separately credited Slovenian reference. |

The [tunnel inspection](2026-11-06-public-tunnel-geometry.md) documents the
successful bounded archive extraction and the unresolved physical frame.
Do not infer an operating mine's fleet, geometry or telemetry from public
preview pages. All public-data attribution remains available through Sources.

## Reproduce and validate

```sh
python3 scripts/fetch-lookdev-materials.py --output /tmp/kessel-material-source-check
python3 scripts/verify-lookdev-assets.py --retained
python3 -m unittest discover -s scripts/tests -v
```

The restore command uses the recorded static URLs and refuses changed content
by hash. It does not scrape the website or call an API at presentation time.
The retained-file option verifies the dated audit snapshot, rather than making
those old hashes an implicit constraint on every future scene-code change.

## Recommendation

Carry Rock Face 03 forward as the primary geological surface. It has irregular
fractures with good readability near the retained excavator. Use Dark Rock 02
sparingly as secondary strata; its stronger horizontal pattern becomes obvious
over a large repeated surface. Retain dark/off-white/amber UI tokens and keep
the machine readable under work lighting. Complete cutaway reconstruction,
surface variation and scene integration through the existing visual tickets.
