# ADR-0026: Phase 9 autonomous operation

Status: Accepted

Supersedes the interactive waypoint decision in [ADR-0022](0022-phase-9-mission-data-contract.md).

## Context

The Phase 9 story demonstrates physical AI working in places without a
reliable connection. A manual route override shifts the demonstration towards
remote operation and weakens that point. The product trains and runs machine
policies autonomously on the vehicle, with no cloud dependency.

## Decision

The mission demo has no manual waypoint, operator route, or live A* control.
The viewer may inspect a truck and its clearly labelled scripted prediction
preview, then return to the fleet. The fleet optimiser remains a pre-computed
illustrative result. A future trained policy must be identified as logged or
live model output before the interface presents it as such.

## Consequences

The mission keeps its focus on offline autonomy and removes the waypoint
controls, graph-editing code, and override feedback. The network graph remains
available as input to authored routes and future autonomous policy work.
