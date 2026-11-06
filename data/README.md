# Public mineral deposit markers

`mineral-deposits.json` is generated from the U.S. Geological Survey's global
Mineral Resources Data System (MRDS) Compact Version feature service. The
generator queries the documented `CODE_LIST` field for the tin (`SN`) and
tantalum (`TA`) commodity codes, pages through the matching records, keeps
valid WGS84 coordinates, and emits a compact file for the globe.

Refresh the committed snapshot deliberately with:

```sh
python3 data/generate_deposit_markers.py
```

The service's matching-record count, generated marker count, retrieval time,
and per-commodity counts are recorded in the JSON metadata. Coordinates are
rounded to four decimal places for display. Each point retains its MRDS record
link.

MRDS is a historical mineral occurrence catalogue, not an inventory of
currently operating mines. USGS says that systematic updates ceased in 2011
and operational fields are out of date. The globe labels these as historical
deposit markers. The Rutongo marker is a separate target from the mine
location in `mission.json`; it does not show a concession boundary. No public
boundary was found in the research for #140.

Sources: [USGS MRDS](https://mrdata.usgs.gov/mrds/) and the
[MRDS Compact Version feature service](https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/Mineral_Resources_Data_System_MRDS_Compact_Version/FeatureServer/0).

## Illustrative underground network

`tunnel-network.json` contains the generated tunnel geometry and its routing
graph. Regenerate it with the same seed and check that node positions,
segment endpoints, edge references, and centreline lengths agree:

```sh
python3 data/generate_tunnel_network.py
python3 data/validate_tunnel_network.py
```

The contract is described by
[`schemas/tunnel-network.schema.json`](schemas/tunnel-network.schema.json),
using [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12).
Geometry `segments` are the source for graph `edges`. Each edge refers to its
segment by `segment_id` and carries the measured centreline length, the
segment's stored grade orientation, width, and a `one_way` flag. `from` and
`to` describe the segment's ordered geometry. A bidirectional traversal in
reverse uses the opposite grade. The current `one_way: false` values are
scenario inputs, not Rutongo traffic-plan data. Graph nodes duplicate the
geometry nodes so consumers can load the graph directly; the validator checks
that the two lists match exactly.

The mission manifest's `routes` records identify a vehicle, status, ordered
node IDs, and graph edge IDs for both the initial and pre-computed optimised
path. The validator checks both path variants, vehicle IDs, the optimiser
trace count, and the referenced data-defined truck model. Every route edge
must exist, each route must have one more node than edge, and traversals must
respect the edge's direction and `one_way` value.

The mission also references `assets/models/haul-truck.json`. It defines a
procedural placeholder, not a licensed or manufacturer-authentic truck model.
Fleet state, route variants, telemetry, motion parameters, and the illustrative
optimiser trace live in `mission.json`; the renderer reads these values rather
than defining the scene in code.

The generated network is a scripted example, not a surveyed Rutongo plan.
See [ADR-0025](../docs/adr/0025-phase-9-illustrative-underground-network.md)
for the cited engineering references and scenario assumptions.

## Recorded synthetic experiment

`experiments/index.json` identifies a curated browser bundle by SHA-256 and
byte count. `experiments/loader-v1.json` contains executed initial/intermediate/
final seed-7 policies, their real training counters/curve and actual raw-model
forecasts. It loads only after world-model entry and stays separate from
`experience.json`'s illustrative mine figures.

Records use metres, radians, kilograms and seconds in x-forward/y-left/z-up.
Each timestamp has the current privileged reference state, recorded local
observation and outgoing normalised action. Its reward terms and weighted
contributions belong to that outgoing transition. The terminal record has no
next action or reward. Keep every decision and event; visual interpolation
never creates a new policy decision or material transfer.

Forecasts identify a future reference decision/timestamp, independent model
weights, actual prediction, residuals and member endpoints. Raw impossible
forecasts remain flagged. Conditional member spread in metres is distinct from
the dimensionless disagreement score and is not calibrated confidence.
Missing predictions remain missing. See ADR-0043 and
[the measured integration report](../docs/phase-11/recorded-integration.md).

Validate with `python3 scripts/verify-recorded-demo.py`. Regeneration executes
the retained weights using the isolated exporter documented in `training/`.
No checkpoint, ONNX file or training buffer belongs in this published directory.
