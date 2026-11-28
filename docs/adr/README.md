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
[Recorded cycle inspection](0050-recorded-cycle-inspection.md) separates reference
control from learned checkpoints and preserves material volume and event clocks.
[Walkthrough visual direction](0051-walkthrough-visual-direction.md) rejects
photorealistic map tiles on licence and delivery grounds, fixes the approved
asset sources, art direction, budgets and visual review criteria, and
supersedes the continuous-journey, selector and global-caption requirements.

[Orbital home and immersive selection](0052-orbital-home-and-immersive-selection.md)
implements the photographic opening, original spacecraft, background-led selector
and controlled local fade while retaining contextual source distinctions.

[Guided task and engineering chapters](0053-guided-task-and-engineering-chapters.md)
sets the conventional reference entry, full-machine fitting, prepared fades,
progressive disclosure, detailed proposed hardware and source-aware technical chapters.

[Phase-memory imitation](0061-phase-memory-and-rehearsal-study.md) qualifies finite
nominal recorded evidence. [Shift evaluation and local runtime](0062-interactive-synthetic-runtime.md)
adds frozen-policy stress tests, fresh localhost execution and separate observation/logging prototypes.

[Receiver-frame pilot](0063-receiver-frame-pilot.md) freezes a bounded
training-partition test of an engineered input adapter.
[Narrow receiver qualification](0064-receiver-frame-qualification.md) freezes
fresh-case audit, all-seed nominal/farther gates, replay and resource limits.

[Missing-range supervisor pilot](0065-missing-range-supervisor-pilot.md) freezes
observation-health rules, conventional stopping/recovery, distinct hold/delivery
criteria and a bounded training-partition comparison with exact replay.

[Spatial range contract](0066-spatial-range-contract-and-pilot.md) separates
invalid-height semantics, input sensitivity and conservative stopping criteria.
[Serialization erratum](0067-spatial-pilot-serialization-erratum.md) retains the
aborted attempt and freezes a reduced-budget correction without control retuning.

[Observed-motion holding](0068-observed-motion-holding-pilot.md) freezes the
reference-specific force observer and unchanged practice gates.
[Bootstrap holding](0069-bootstrap-motion-holding-pilot.md) freezes the separately
named probing/integral-reset law and adds cold-start grade fixtures.

[Fresh stopping qualification](0070-bootstrap-hold-fresh-qualification.md) freezes
the unchanged controller, audited bases and moving-carry stop/recovery gates.
[Logging erratum](0071-fresh-qualification-logging-erratum.md) excludes the consumed
aborted base and binds a separately audited replacement without control retuning.

[Qualified live simulator](0072-qualified-stopping-live-simulator.md) adds an
isolated interface for the frozen controller, explicit playback and complete
exports, with bounded consumed-practice regression and human visual review open.

[Blocked-path stopping](0073-blocked-path-observation-and-stopping.md) adds an
explicit synthetic clearance boundary and a bounded latched-stop pilot.
[Robustness repair](0074-bounded-robustness-repair.md) freezes the separate task,
rehearsal and full-family practice comparison.
[Working-policy refit](0075-working-policy-world-model-refit.md) freezes new
training-only model fitting and unchanged calibration gates on practice episodes.
[Forward-steering correction](0076-forward-steering-stability-correction.md)
uses only the remaining robustness budget and retains the rejected refit.
[Clearance capture ordering](0077-clearance-capture-order-guard.md) completes the
input contract through a separate wrapper without changing the frozen pilot.
[Progress-driven collection](0078-progress-driven-task-and-clearance-compatibility.md)
and [lateral stability correction](0079-lateral-feedback-stability-correction.md)
separate feasible conventional control from fresh qualification.
[Linear feedback imitation](0080-linear-feedback-imitation.md) bounds a sparse
learned actuator with explicit conventional planner context.
[Structured local dynamics](0081-structured-local-dynamics-and-rare-events.md)
bounds local learned heads, known priors and independent rare-event acquisition.

[Collection coverage correction](0082-bounded-collection-coverage-correction.md)
retains two fixed task variants and matched final practice, including misses.

[Harvest and traction repair](0083-harvest-recovery-and-traction-feasibility.md)
preserves bounded recovery attempts and distinct proposed start refusals.
[Fresh harvest/forecast qualification](0084-frozen-harvest-and-forecast-qualification.md)
freezes initial feasibility screening, unused-case audit and separate endpoints.
