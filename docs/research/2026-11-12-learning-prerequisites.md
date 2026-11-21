# Loader learning prerequisites

Refs #410, #423, #424, #425 and #426. Findings from the
[committed diagnostic protocol](2026-11-12-prerequisite-protocol.md).
Next experiment recommendation: [proposed ADR-0057](../adr/0057-model-free-skill-proficiency-protocol.md).

## Result

Do not scale the previous imitation-plus-PPO recipe unchanged. It fits a narrow
teacher archive, fails closed-loop skills and loses teacher-action fit after
PPO. The curriculum also has inconsistent payload boundaries and never reaches
later training stages in the retained budget. Recommend a bounded retraction
pilot, then a conditional curriculum with aligned payloads and explicit tipping.
No improved task policy is produced by this investigation.

The [report](../phase-11/prerequisite-evidence/report.json) and its
[manifest](../phase-11/prerequisite-evidence/files.json) retain six candidate
comparisons, 16 learned stage probes, eight reference stage probes and three
execution timing checks. Stage rollouts execute 5,088 reference decisions;
teacher reconstruction executes 1,024; discarded-weight execution smokes execute
3,072. The diagnostic therefore accounts for 9,184 executed decisions. Model
inference on archived teacher rows adds no environment transitions. All new
stage evaluations reuse validation scenes, not an untouched test set.

## Observations and actions: #423

The policy receives 15 proprioceptive estimates, 25 local pile heights and 25
validity flags. Receiver displacement assumes a preloaded local target map.
There is no obstacle occupancy or corridor-width measurement. For seed 7,
ordinary, narrower and fully blocked-route scenes produce exactly identical
initial observations despite different scenario identities and valid starts.
This is an explicit alias, not proof that all later observations remain equal.

Do not promise arbitrary obstacle avoidance from the existing height crop.
Retain the 65-feature contract for the nominal skill pilot. An observable
occupancy input would need a separate sensor contract and evaluation. A
privileged obstacle box cannot be renamed a sensor measurement.

The conventional controller also holds `phase` and `fill_start` memory.
Its feasibility with local observations and controller memory does not prove
that a memoryless actor can implement the same decisions. The previous two-frame
history comparison failed within its budget; that neither establishes memory
sufficiency nor rules out a useful recurrent policy. Keep recurrence as a
separate follow-up rather than changing it alongside exploration and budgets.

The four actions are drive request and articulation/boom/bucket rates.
The drive request is named acceleration in the schema, but physical acceleration
depends on load, friction, grade and resistance. Articulation commands are
clipped to ±0.35 rad/s and ±0.6 rad; boom/bucket have separate rate and position
limits. There is no parking-brake action. Keep rate controls for the first pilot;
position-target controls would be a different learning/control contract.

## Teacher coverage and PPO regression: #425

The teacher archive exactly regenerates, including episode accounting. It
contains 1,024 rows from training seeds 0, 1 and 2: two complete episodes
(352 and 474 rows), followed by 198 rows of an incomplete episode.

| Controller phase | Unique rows |
| --- | ---: |
| Approach | 39 |
| Fill | 388 |
| Lift/retract preparation | 96 |
| Carry | 433 |
| Tip | 68 |

The existing trainer already samples inverse phase frequency. Rebalancing the
same rows again would not expand the number of demonstrated situations. The
teacher's steering action spans only -0.06431 to +0.00748. This is a narrow
straight-task dataset, not demonstrated obstacle handling or recovery coverage.

| Training seed | Warm-start action MSE | Final PPO action MSE | Increase |
| --- | ---: | ---: | ---: |
| 7 | 0.01131 | 0.03790 | 3.35× |
| 19 | 0.00927 | 0.08789 | 9.48× |
| 41 | 0.01082 | 0.06093 | 5.63× |

These are deterministic action errors on the same full training archive,
not the trainer's final sampled minibatch loss or a generalisation score.
All three candidates' lift/retract phase errors worsen. In retained complete
validation, the warm-start candidates pick up approximately 3,052–3,230 kg
in the first scene but deliver zero; all six final candidate validation cases
have zero pickup and delivery. Improved teacher fit did not establish stable
closed-loop behaviour before PPO, and PPO did not preserve that fit.

Supervision trains actor weights, leaving initial latent action standard
deviations at approximately 0.60653 in every control dimension. Final values
remain roughly 0.604–0.614. These are Gaussian latent deviations before tanh,
not bounded action deviations or direct physical-rate noise. The narrow teacher
steering range motivates a controlled steering-exploration ablation, but no
experiment here isolates exploration as the cause of the regression.

Expanded demonstrations, a retained imitation objective and training-only
expert queries are alternatives if the stage pilot fails. Each would require
separately charged data, a matched comparison and frozen evaluation scenes.
Do not train on the diagnostic validation queries or call reference-supervised
behaviour pure reinforcement learning.

## Stage feasibility and compatibility: #424

With stage-appropriate controller initialisation, the reference completes both
validation cases in every stage: six prepared skill successes and two true
empty-start full-cycle successes. Initialising a prepared carry controller in
approach phase would test the wrong controller state.

For seed 7, both warm-start and final candidates fail all eight prepared/full
stage checks each. Warm-start's first complete case peaks at 3,230.23 kg but
collides. Prepared retraction starts at 1,500 kg, below all teacher phase-2
loads (approximately 2,379–2,650 kg in the archived rows). These prepared starts
are curriculum diagnostics, not an assertion that they match the imitation
training distribution. Failure there does not prove the skill is unlearnable.

The legacy curriculum contains a structural hand-off mismatch:

| Stage | Prepared payload | Success condition relevant to payload |
| --- | ---: | --- |
| Fill | 0 kg | At least 1,000 kg carried |
| Retract | 1,500 kg | Retain at least 1,200 kg while reversing/lifting |
| Carry | 2,200 kg | Retain at least 1,800 kg on receiver arrival |
| Complete | 0 kg | Deliver at least 2,000 kg |

Thus passing fill need not provide enough material for retraction's retention
condition, carry's prepared load or a complete delivery. Carry terminates before
tipping. These isolated successes cannot establish skill chaining. The proposed
five-stage protocol uses a common 2,200 kg target and an explicit tipping stage,
while retaining the complete task's 2,000 kg requirement.

Existing curriculum seeds advance from fill only at rollouts 11, 15 and 12 of
16, leaving 1,280, 256 and 1,024 decisions respectively for retraction. None
reaches carry. Larger per-stage budgets address this opportunity imbalance,
but consistent boundaries and retention tests are also required. Keep complete
starts and prepared successes separate throughout checkpoint selection.

## CPU budget and practical limits: #426

Three existing four-environment execution smokes each run 1,024 decisions,
four rollouts and 32 actual optimiser minibatches. Their wall times excluding
import are 1.379, 1.314 and 1.340 seconds. Collection takes 1.204–1.225 seconds;
optimisation takes 0.071–0.108 seconds. Collection dominates this workload.
Peak process RSS is approximately 285 MiB, a cumulative high-water mark after
the earlier diagnostics, not independently allocated policy memory.

This supports using the available CPU for a bounded stage pilot. It does not
forecast convergence or include full-study validation/export costs. Multiplying
throughput by a larger decision count gives a workload estimate only. Preserve
per-stage, per-seed counters, optimiser counts and cumulative wall caps and
report every capped or interrupted run.

The full diagnostic took 32.47 seconds. The smoke weights are discarded and
are not new trained candidates. No GPU, purchase, cloud job or task-proficiency
training was performed. These are native observations from the current machine,
not a comparison against historical runs on an otherwise controlled host.

## Recommendation and follow-on implementation

Proposed ADR-0057 declares a 196,608-decision retraction pilot and a conditional
983,040-decision full-cycle comparison. Pilot selection uses validation only.
The latter requires pilot success, aligned stage contracts and a recorded
recommendation. Untouched seed reservations must be audited before collection.

Implementation should proceed in this order after protocol acceptance:

1. Add optional per-action exploration initialisation and verify that omitted
   settings reproduce the legacy policy. Keep bounded action densities intact.
2. Add a per-stage runner with frozen validation identities, explicit counters,
   exact checkpoint/resume, cumulative wall caps and failure exports.
3. Implement the separate five-stage factory, ledger-consistent prepared
   payloads and stage-initialised reference checks before curriculum training.
4. Add retention and complete-task checkpoint selection, then admit genuine
   results only through #414's evidence contract.

The proposed protocol is reviewable research output. It does not make these
implementation tickets ready automatically, change the accepted legacy study
or claim that the conditional capability gate has been met.

## Reproduction

Use the committed diagnostic command from `training/`:

```sh
uv run --locked python -m kessel_training.inspect_prerequisites --output runs/prerequisites-new
```

The output refuses overwrite and dirty training sources. It verifies teacher
regeneration and checkpoint hashes, records actual trajectories and retains
source identities. Run `python3 scripts/verify-prerequisite-evidence.py` from
the repository root for independent bundle and trajectory-continuity checks.
