# ADR-0022: Phase 9 mission data contract

Status: Accepted; interactive waypoint decision superseded by [ADR-0026](0026-phase-9-autonomous-operation.md).

Supersedes [ADR-0001](0001-rollout-data-schema.md) for the Phase 9 mission demo.

## Context

ADR-0001 describes one loader moving through one rollout. Phase 9 needs a
globe and mine location, staged scene assets, a tunnel graph, a fleet, haul
cycles, candidate routes, an optimiser trace, and an interactive route
override. Extending the frame-by-frame schema would make the renderer depend
on one scripted scene and would not leave a useful boundary for later logged
mission data.

## Decision

`data/mission.json` is the authored data contract for the mission. It contains
metadata and source labels; location and surface references; tunnel graph
nodes and ordered directed edges with grade, width, and geometry; vehicle
definitions and fleet state; haul-cycle and route data; and a compact
optimiser trace with the claimed run count and per-step route scores. Large
textures and models remain external assets referenced by URL. The manifest
labels the scene and each result as `scripted` or `logged`; it must not imply
that the demo's optimiser trace is a live run of 100,000 simulations.

The renderer consumes this contract without hardcoding mine geometry, vehicle
poses, routes, or HUD values. A logged dataset can replace the scripted
dataset without renderer changes if it conforms to the same contract.
The mission does not accept interactive waypoint input. The selected truck
view may show a clearly labelled scripted prediction preview. See ADR-0026 for
the decision to keep this demonstration focused on autonomous operation.

Mission route records carry an ID, vehicle ID, source label, route status,
ordered `node_ids`, and matching `edge_ids`. The renderer resolves these IDs
against the tunnel graph and geometric segments. Route direction follows the
ordered nodes; it may traverse a segment in reverse only when the graph edge is
not one-way. Scripted route statuses such as `unoptimised` must remain clearly
separate from logged or live policy output.

The tunnel network asset carries both geometric `segments` and a pathfinding
`graph`. Each graph edge refers to one segment and copies its ordered endpoints,
kind, grade, and width, while adding centreline length and a `one_way` flag.
Graph node records match geometry node records exactly. `from` to `to` defines
the stored grade orientation; reverse traversal negates the grade. The
committed network marks its segments bidirectional as a scenario input because
no Rutongo traffic plan is public. The Draft 2020-12 JSON Schema is at
[`data/schemas/tunnel-network.schema.json`](../../data/schemas/tunnel-network.schema.json);
the standard-library validator checks cross-references that the schema cannot
express on its own.

## Consequences

The old `data/rollout.json` remains available for the earlier demo until the
Phase 9 build replaces it. It is not the Phase 9 data contract. The mission
manifest can describe many vehicles and routes without duplicating static
scene data per animation frame. The new contract needs a validator and a
documented example before the renderer switches to it.
