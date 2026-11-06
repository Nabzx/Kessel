# Public tunnel geometry inspection

Research date: 6 November 2026. Issue #201. Decision:
[ADR-0035](../adr/0035-public-geometry-and-look-development.md).

## Slovenian mine reference

[Zenodo record 18835599](https://zenodo.org/records/18835599), v1.0, supplies
mine LiDAR, meshes and radio-propagation measurements under CC BY 4.0. The
record metadata and archive README agree on the licence. Creators: Andrej
Hrovat, Aleš Simončič, Grega Morano, Teodora Kocevska and Tomaž Javornik.
This is not a Rutongo dataset and contains no heavy-machine control telemetry.

The 645,482,816-byte ZIP supports HTTP range reads. A bounded inspection read
1,196,639 HTTP bytes, including the directory, documentation and selected mesh.
It did not download the full point cloud or propagation records. The archive's
provider MD5 is `96ba95bf8cf62e83ab20202f738cf734`; this audit did not recompute
that whole-archive digest. ZIP entry CRC was checked for the extracted STL.

Selected entry:
`Environment_Data/PolygonMesh/Quadric_Edge_Collapse_Decimation/Cave_Segment1_simplified[30-10].stl`.
It is 1,970,234 bytes, 39,403 triangles, from the provider's two-stage
MeshLab decimation. SHA-256:
`1b7edcf4c7656474d6d30c42396f163069bccc0c02bac312f27bb4ce29abaf06`.

Measured source extents are approximately 71.40 x 90.80 x 13.78 source units.
The STL has no unit/CRS declaration. Descriptive radio notes refer to a roughly
58 m segment, which does not independently calibrate those mesh bounds. Do not
infer metres, absolute elevation or a Rwanda placement from these values.

## Browser reference derivative

`scripts/prepare-tunnel-reference.py` validates finite binary STL geometry,
finds a horizontal principal direction and keeps whole triangles whose
centroids fall in a 12-source-unit longitudinal crop. It centres the result
and maps assumed source +Z to view +Y. That up-axis is a viewing assumption,
not survey certification. No metric rescaling is applied.

The crop has 7,416 triangles and 266,976 bytes of float32 positions. Its
metadata retains the source/derivative hashes, credit, viewing transform,
bounds and null physical units/CRS. Boundaries are uncapped. This reference is
unsuitable as a watertight collision mesh and must not define training physics.
The isolated look-development page can inspect it with explicit source labels.

Reproduce from the verified local source STL:

```sh
python3 scripts/prepare-tunnel-reference.py --source /path/to/source.stl --output /tmp/tunnel-reference
python3 -m unittest discover -s scripts/tests -v
```

The three checks cover deterministic cropping/provenance, malformed/non-finite
geometry and invalid crop spans. Raw archives stay outside the repository.

## Bedretto alternative and fallback

The [ETH Bedretto dataset record](https://www.research-collection.ethz.ch/items/65adf5ab-b96b-4d46-afa1-6bf96417e568)
was rechecked and returned HTTP 403. Publisher search metadata advertises open
TLS/mesh data and CC BY 4.0, but this audit could not inspect the source files,
units or coordinate frame. No Bedretto data is adopted.

Use an original synthetic geological cutaway with documented metre dimensions
for the main scene and the future simulator. The public crop informs surface
irregularity and is displayed separately. A verified source scan can replace
it later through its own licence, scale and integration checks.
