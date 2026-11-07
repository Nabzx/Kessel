# Architecture decision records

Phase 11: [synthetic learning boundary](0031-synthetic-learning-and-presentation-boundary.md)
and [Selene reuse](0032-selene-reuse-and-loader-prototype.md).
The [loader and export contracts](0033-loader-and-experiment-contracts.md)
define the first experiment interface.
The [static package allowlist](0034-static-package-allowlist.md) separates
presentation assets from experiment artefacts.
The [synthetic loader environment](0036-synthetic-loader-reference-environment.md)
defines the reference dynamics and their limits.
The [CPU policy and PPO core](0037-cpu-policy-and-ppo-core.md) defines bounded
likelihoods, episode bootstrapping and versioned delivery rewards.
The [reproducible RL experiment protocol](0038-reproducible-rl-experiments.md)
defines checkpointing, curriculum gates and bounded comparisons.
[Stuck detection at actuator limits](0039-stuck-detection-at-actuator-limits.md)
closes a measured saturated-command loophole before policy comparisons.
The [world-model prototype protocol](0040-world-model-prototype-and-evaluation.md)
defines episode splits, learned dynamics, uncertainty gates and the auxiliary
critic comparison.
The [bounded-filter follow-up](0041-explicit-bounded-world-model-filter.md)
retains raw failures while testing explicitly constrained imagined samples.
The [measured assistance outcome](0042-world-model-assistance-outcome.md) keeps
the method experimental after equal-budget comparisons find no task improvement.

The [recorded experiment viewer](0043-recorded-experiment-viewer.md) defines
validated static playback and independent prediction inspection. The
[offline compression protocol](0044-offline-policy-compression-protocol.md)
separates CPU export, distillation and quantisation from task proficiency.

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

The [cinematic visual material decision](0045-cinematic-visual-materials.md)
adopts the cleared maps for the main experience while preserving the scan boundary.

The [home and environment presentation](0046-home-environment-presentation.md)
retains geographic alignment, neutral Earth lighting and credited reference photos.

The [reference repair protocol](0047-training-repair-and-replay-evidence.md)
separates audited geometry/material behaviour from new learning claims.

The [local Blender authoring decision](0048-local-blender-authoring.md)
pins the MCP connection and keeps editable source scenes outside static packaging.

[Bounded learning follow-up](0049-bounded-learning-follow-up.md) declares
policy, observation, world-model and equal-reference-budget comparisons.
