# ADR-0032: Selene reuse and loader prototype

Status: Accepted

## Context

Selene 3.1 contains real compact PyTorch training and a vectorised NumPy
environment. Its lunar actions are discrete mission decisions, not continuous
loader actuation. A fast lunar benchmark does not determine loading fidelity
or execution time on this machine.

## Decision

Use its separation of environment, policy, learned dynamics, logs and playback
as the reference architecture. Pin the audit to commit
`647ce1e8acf665435815576db30d38ca522240e1`. Use explicit CPU execution and
benchmark small networks and batches before choosing presets. The initial
loader has four bounded continuous controls; do not copy the categorical actor
or lunar reward/action logic. Implement the new domain kernel and contracts
independently. Preserve the MIT notice if code is later copied or adapted.

Start with a mass-tracked pile height field and bounded machine articulation.
Compare short control steps with coarse loading actions in a disposable spike.
Use a small action-conditioned ensemble only after collecting and splitting
transitions. Short imagined rollouts require measured horizon error and a
validated uncertainty gate. A separate prototype must justify how imagined
experience enters PPO or another policy update.

## Consequences

Reject authored progression actions labelled learned based on checkpoint-file
presence, fabricated prediction offsets, and monotonic best-so-far error used
as a current-error series. Export actual weights-driven trajectories and raw
prediction/reference pairs. This audit does not reproduce Selene's documented
51,200-step, 7.04-second quick run.

The [file-level audit](../research/2026-11-05-selene-reuse.md) records which
components are reusable and which are replaced. Refs: #199, #200.
