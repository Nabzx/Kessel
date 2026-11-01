# ADR-0025: Phase 9 illustrative underground network

Status: Accepted

## Context

The Phase 9 mission needs a multi-level network for a compact haul-truck
scenario. Public sources reviewed for Rutongo do not provide current mine
plans, surveyed level spacing, an extraction method, or vehicle routes. The
network must not be presented as a reconstruction of the operating mine.

## Decision

Generate deterministic, explicitly illustrative geometry with
`data/generate_tunnel_network.py`. The checked-in output is
`data/tunnel-network.json`; the mission manifest references it. Rendering code
consumes the generated path and section values rather than defining the mine
layout itself. Seed 2026 is the committed example.

Use a 3 m wide by 3 m high flat-floor, arched-back heading. Sandvik's TH315
specification says this 15 t truck fits a 3 x 3 m heading. Its 2023 sheet
lists a maximum envelope of 7.71 m long, 2.274 m wide, and 2.395 m high. That
leaves 0.363 m nominal clearance on either side and 0.605 m above. This is a
manufacturer application reference, not a geotechnical or Rutongo-specific
design approval.

Use a 2.75% drainage grade on trackless haulage and draw crosscuts. The Hard
Rock Miner's Handbook gives 2.5-3% as a generic rule of thumb for trackless
headings. The Rwanda Mining Safety Standards separately recommend a positive
0.5 degree grade for adits where practical. Neither source gives a Rutongo
haulage design value.

Use an 8% decline grade as a scenario parameter. The TH315 specification
publishes loaded performance points at 10% and 14.3% under 3% rolling
resistance. The 8% value is an illustrative choice below those published
points, not a mine standard or certified truck operating limit.

Use three 20 m spaced levels and six draw points. Level count, spacing,
draw-point arrangement, and the mechanised extraction scenario are explicit
illustrative inputs because Rutongo's current underground design is not
public. Use 15.24 m as the minimum curve radius for ramp turns, based on the
Handbook's generic 50 ft guideline for most ramp headings. This does not
replace a TH315 swept-path check.

The geometry generator emits named nodes and segments with ordered metre
coordinates, grades, section dimensions, curve constraints, source links,
and the seed. A parallel illustrative decline between the portal and Level 1
provides a genuine alternate route for the scripted optimiser and live A*
override. It is a scenario feature, not a surveyed Rutongo working. The
machine-readable mission graph and its schema are handled separately under
#153.

## Consequences

The demo can render an authored multi-level truck route without implying
access to Rutongo survey data. Every value that is not directly tied to the
manufacturer or generic handbook guidance is labelled as an illustrative
scenario input. Replacing this network with a licensed surveyed plan remains
a data update, not a renderer rewrite.

## Sources

- [Sandvik TH315 technical specification sheet](https://www.mining.sandvik/globalassets/products/underground-loaders-and-trucks/pdf/th315-specification-sheet-english.pdf)
- [Rwanda Mining Safety Standards](https://www.rmb.gov.rw/fileadmin/user_upload/RMB/Publications/Guidelines/Mining_Safety_Standards.pdf)
- [Stantec Hard Rock Miner's Handbook](https://www.stantec.com/content/dam/stantec/files/PDFAssets/2020/stantecs-hard-rock-miners-handbook.pdf)
- [Trinity Metals, Rutongo Mines](https://trinity-metals.com/en/projects/rutongo-mine)
