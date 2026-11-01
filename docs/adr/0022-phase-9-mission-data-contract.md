# ADR-0022: Phase 9 mission data contract

Status: Accepted

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
Interactive waypoint input and its A* result are transient user-session state,
computed by generic code over the directed graph rather than written back to
the authored manifest. Prediction data is scoped to the selected truck view.

## Consequences

The old `data/rollout.json` remains available for the earlier demo until the
Phase 9 build replaces it. It is not the Phase 9 data contract. The mission
manifest can describe many vehicles and routes without duplicating static
scene data per animation frame. The new contract needs a validator and a
documented example before the renderer switches to it.
