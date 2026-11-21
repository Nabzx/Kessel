# ADR-0057: Model-free skill proficiency protocol

Status: Proposed

Refs #410 and #423–#426. Extends proposed ADR-0056. If accepted, this protocol
supersedes ADR-0049's budget, gate and stage settings only for new named experiments.
The original study, weights and unsuccessful outcomes remain unchanged.

## Evidence and hypothesis

The [prerequisite investigation](../research/2026-11-12-learning-prerequisites.md)
finds two complete demonstration episodes, failed closed-loop imitation skills,
worse action fit after PPO and insufficient training of later curriculum stages.
The conventional controller completes all prepared reference skills checked.
Existing observations omit obstacle and corridor geometry, and the reference
controller has internal phase memory that the feed-forward learner does not.

Test whether the retraction skill can be learned with an explicit stage budget
and whether reducing steering exploration improves that result. These are
hypotheses, not a claim that either change will produce full-task proficiency.

## Bounded pilot

Use the current four-environment, 64-step rollout, two-layer 64-unit policy,
PPO configuration, standard randomised scene and prepared retraction task.
Keep current potential shaping and stage bonus unchanged. Log raw delivery
reward separately. Prepared payload is 1,500 kg, never full-task success.

Compare two configurations across training seeds 7, 19 and 41:

- Baseline: current initial latent `log_std = [-0.5, -0.5, -0.5, -0.5]`.
- Steering ablation: `log_std = [-0.5, -2.5, -0.5, -0.5]` initially. All
  components remain trainable with the same clamps. Architecture, reward,
  action interpretation and all other optimiser settings stay the same.

Allow 128 rollouts, 32,768 reference decisions, per configuration and seed.
The six pilot runs therefore cap at 196,608 on-policy decisions. Record all
optimiser minibatches, resets, completed episodes and wall time. This changes
the stage budget compared with the historical study; it does not isolate a
budget effect against its old 4,096-decision runs.

Evaluate deterministic retraction at rollout 0 and every 16 rollouts on 16
fixed validation starts. Select maximum stage successes, then fewer collisions,
then shorter mean successful duration; exact ties prefer the earlier checkpoint.
Do not select by training reward, pickup mass or test performance. Choose the
configuration by the median validation success across the three training seeds,
with the baseline winning an exact tie. Require at least 14/16 validation
successes in at least two seeds before proposing the full curriculum study.

Use a 600-second cumulative cap per pilot run, including its evaluation time.
If exhausted, retain the last complete transaction and report the smaller actual
budget. Do not silently increase it or compare censored runs as equal-budget
evidence. Evaluate the frozen selected checkpoint once on a separate 16-start
pilot test set; this test cannot change checkpoint or configuration selection.

## Conditional full-cycle comparison

This is a subsequent experiment, not an automatic continuation after a good
training return. It requires the pilot gate and a recorded recommendation.

Compare full-task PPO and held-out-gated curriculum with the selected initial
exploration setting, seeds 7/19/41, capped at 163,840 on-policy decisions per
run. The six-run upper bound is 983,040 decisions. The combined pilot and
conditional study cap is 1,179,648 decisions, excluding explicitly counted
evaluation. No demonstration data or learned-model assistance is included.

Use a new five-stage contract. Preserve the four-stage legacy experiments.

| Stage | Initial payload | Gate |
| --- | ---: | --- |
| Fill | 0 kg | At least 2,200 kg carried |
| Retract | 2,200 kg | Reverse at least 1 m, boom at least 0.2 rad, curl at least 0.4 rad, retain at least 2,100 kg |
| Carry | 2,200 kg | Existing receiver approach bounds and speed under 0.2 m/s, retain at least 2,100 kg |
| Tip | 2,200 kg | At least 2,000 kg delivered from a prepared receiver-aligned start |
| Complete | 0 kg | At least 2,000 kg delivered through the actual complete task |

Prepared payload must come from the pile ledger. Tip starts hold the bucket
at boom 0.35 rad and curl 0.9 rad, with the mouth aligned over the receiver;
they do not start already dumping. Validate clearance before any action.
Retain existing stage potentials except normalise fill by 2,200 kg and use
zero potential for tip, where incremental delivery reward already supplies
credit. Record the resulting shaping contract under a new version. Full-task
raw reward, physical dynamics, capacity and success threshold remain unchanged.

This gives every prepared hand-off the same 2,200 kg target, with 200 kg
above the full delivery threshold. It avoids the legacy 1,000/1,500/2,200 kg
stage discontinuity and introduces tipping explicitly.
It still needs reference feasibility checks and prepared-start ledger tests
before training. Prepared skill gates are not evidence of successful chaining.

Allocate each stage up to 32,768 decisions. Stop and retain failure
if a stage cannot pass its gate; do not force advancement. Preserve model and
optimiser state when advancing and reset the environment/history explicitly.
Do not substitute independently trained stage actors for a learned full-cycle
policy. The plain PPO arm receives the full-task budget under unchanged raw
reward; curriculum uses the declared shaping contract above. This compares practical training
recipes, not a pure curriculum-only or shaping-only ablation.

Advancement requires the existing 32-episode training window at 70% success,
at least 14/16 current-stage validation successes and at least 12/16 successes
on each prior stage. Evaluate gates at 4,096-decision stage boundaries when the
training window qualifies; charge every validation action separately. Prepared
stage performance remains separate from empty-start complete-task evaluation.

Select the full-task checkpoint by empty-start validation successes, fewer
collisions, then successful duration, with earlier checkpoint winning ties.
Evaluate full starts at initialisation, each 8,192-decision boundary, stage
transition and final/capped stop; deduplicate coincident boundaries. A 1,200-
second cumulative cap per full-study run includes evaluation. Retain all source,
counter, stopping and selection evidence. Early-stopped curriculum runs use
less data; this design does not establish equal-sample efficiency.

## Seed isolation and capability admission

Before any collection, audit previous manifests, raw retained runs and generator
seed schedules and freeze the exact realised scene identities. Candidate ranges
are validation 108000–108015, pilot test 208900–208915 and final full-cycle test
209900–209931, within the existing split contract. These are proposals, not a
claim that untouched scenes have already been verified. If a candidate range
was used, reserve a different non-overlapping range before training and record
that change without looking at outcomes. Exclude final tests from all gates,
tuning, teacher queries and pilot work.

For admission to the capability demonstration, require each of three selected
seed policies to deliver at least 2,000 kg from an empty start on at least
28/32 frozen nominal full-task tests, with at most one collision in each set.
Report all 96 cases and seed variation. This is a nominal synthetic gate; it
does not qualify obstacle avoidance, all pile families or physical deployment.
Generalisation scope remains #411/#427/#428.

## Non-goals and follow-on work

Do not alter observations, action semantics, dynamics, raw task reward or model
sizes within these comparisons. Curriculum shaping and its staged starts are
the declared differences above. A recurrent actor, observable occupancy input,
imitation retention loss and expanded teacher coverage remain separate
experiments if the pilot fails. Do not lower collision penalties merely to
improve training return. Do not add more teacher data before the controller-to-
policy coverage gap is measured and its acquisition budget is declared.

Implementation must add configurable initial per-action exploration without
changing legacy defaults; a bounded stage runner with checkpoint/resume and
evaluation counters; validated stage gates; and evidence export with independent
replay. This proposed ADR and its research are not authorisation to describe an
unexecuted protocol as a successful learner or to change the default walkthrough.
