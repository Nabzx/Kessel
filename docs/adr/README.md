# Architecture decision records

Phase 9 decisions: [mission data contract](0022-phase-9-mission-data-contract.md),
[progressive payload](0023-phase-9-progressive-payload.md), and
[scene/state architecture](0024-phase-9-scene-state-architecture.md).

An ADR is written before code for anything touching the rollout data schema,
the sim/world-model panel split, the renderer's public shape, or the
hosting/publish mechanism (see `AGENTS.md`). Most ADRs here resolve a
`wayfinder:research` or `wayfinder:grilling` ticket.

## Format

One file per decision: `NNNN-short-title.md`, numbered sequentially,
never reused. Each ADR is:

```markdown
# ADR-NNNN: Title

Status: Proposed | Accepted | Superseded by ADR-MMMM

## Context

What problem this answers, and the constraint that makes it non-obvious.

## Decision

The decision, stated plainly, in one or two paragraphs.

## Consequences

What this makes easier, what it makes harder, and what it rules out.
```

## Rules

- An Accepted ADR is changed only by a new ADR that supersedes it, linked both
  ways.
- Keep it short. An ADR is a decision record, not a design document — link out
  to a map issue or a prototype for the exploration that led here.
- British English, plain sentences, no marketing tone, per `AGENTS.md`.
