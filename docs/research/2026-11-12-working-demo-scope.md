# From concept walkthrough to a working capability demonstration

Refs #406. Recommendation: [ADR-0056](../adr/0056-working-capability-demo-research.md),
proposed. This investigation changes no default scene or product positioning.

## What exists and what it answers

| Artefact | Audience and question | Existing evidence | Missing proof |
| --- | --- | --- | --- |
| Concept walkthrough | A viewer asks what Kessel intends to build and how its parts connect | Static mine, authored training jobs, perception and model chapters, proposed kit inspection | It does not execute a learned policy or show measured mine savings |
| Synthetic technical prototype | An engineer asks whether reference dynamics, training and evaluation can run reproducibly | Loader kernel, mass ledger, conventional controller, PPO, dynamics models, saved weights and independent replay | Physics and observations are not calibrated to a real machine |
| Learned capability demonstration | A technical viewer asks whether a saved policy completes a stated task | Retained checkpoints and failed evaluations | A repeatable empty-start scoop-to-delivery result |
| Customer MVP | An operator asks whether a workflow solves a useful operational problem | No real-site ingestion workflow or machine deployment in this repo | Defined input sources, useful output, user workflow and evaluation in the intended setting |

Sources: [context](../../CONTEXT.md), [reference report](../phase-11/simulator-reference.md),
[policy follow-up](../phase-11/policy-follow-up.md),
[world-model follow-up](../phase-11/world-model-follow-up.md),
[engineering presentation](../phase-11/engineering-showcase.md).
The [readiness investigation](2026-11-12-learning-readiness.md) adds rerun evidence.

## Smallest useful next result

One loader, one pile and one receiver. Start with an empty bucket. Execute a
saved policy using the supported observation contract and measure actual pickup,
transport and delivery. Keep full-cycle success, partial pickup, prepared-load
subtasks, collisions and timeouts separate. The existing task defines success
as at least 2,000 kg delivered, with a 3,500 kg bucket limit.

A viewer should be able to select a declared scenario, replay the actual
evaluation and inspect its initial conditions, policy identity and outcome.
An initial recorded implementation reuses the static adapter and avoids a
new server or browser-training requirement. Live inference remains an option
to investigate, not a prerequisite for proving the policy result.

The long-term explanation is collect observations, learn environment dynamics,
train and evaluate a policy, then eventually run that policy locally on a
machine. Distinguish the current reference simulator from learned dynamics.
Do not say the first successful model-free policy was trained inside a learned
world model unless that is what the experiment actually did.

## Choices and limits

Retain the polished walkthrough rather than funding further environment
expansion during this technical investigation. Explore a shorter mine entry
and a single-machine story under #407 without assuming a visual rebuild.
Keep the kit chapter tied to actual observation fields and proposed interfaces
under #408. An observation-only sensor installation and an actuation retrofit
have different engineering requirements.

A mine-data MVP is a legitimate alternative hypothesis, but this repository
cannot settle it. A map or ingestion prototype would require a specified data
contract and useful decision output. A loader simulation alone does not
demonstrate either. No outreach, customer evidence or data access is assumed.

## Ordered follow-on work

| Work item | Output needed before implementation | Acceptance gate |
| --- | --- | --- |
| #409 and #420–#422 | Reproduced failures, physics/accounting limits and reward diagnosis | Saved actions reproduce and reference feasibility is independently checked |
| #410 and #423–#426 | Bounded protocol targeting the missing skills | Predeclared budgets, seed partitions, retention and full-cycle metrics |
| #411 and #427–#428 | Scenario families and scorecard | Frozen test scenes and visible failures, no nominal-only robustness claim |
| #412 and #429–#431 | Model-assistance comparison protocol | A useful model-free baseline and charged model/data costs |
| #413 and #432–#433 | Recorded/live architecture choice and scenario contract | Source-correct, repeatable playback; unsupported combinations are explicit |
| #414 and #434 | Admission contract and integration recommendation | Independent evidence verification before changing the presentation |

Do not create another batch of broad implementation tickets until these
research recommendations establish the necessary decisions. Existing evidence,
packaging and visual acceptance issues remain in place.
