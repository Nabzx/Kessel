# Architecture decision records

Phase 11: [synthetic learning boundary](0031-synthetic-learning-and-presentation-boundary.md)
and [Selene reuse](0032-selene-reuse-and-loader-prototype.md).
The [loader and export contracts](0033-loader-and-experiment-contracts.md)
define the first experiment interface.
The [static package allowlist](0034-static-package-allowlist.md) separates
presentation assets from experiment artefacts.

Phase 10 decisions: [continuous geography](0028-phase-10-geographic-journey.md),
[learning presentation](0029-world-model-learning-presentation.md) and
[cinematic architecture](0030-cinematic-experience-architecture.md).

Historical Phase 9 decisions: [mission data contract](0022-phase-9-mission-data-contract.md),
[progressive payload](0023-phase-9-progressive-payload.md), and
[scene/state architecture](0024-phase-9-scene-state-architecture.md),
[autonomous operation](0026-phase-9-autonomous-operation.md), and
[demo completion](0027-phase-9-demo-completion.md).

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

## Public visual references

The [public geometry and look-development boundary](0035-public-geometry-and-look-development.md)
keeps scan references distinct from calibrated mine or training geometry.
