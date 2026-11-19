# Bounded full-cycle policy comparison

19 November 2026. Refs #410 and #423–#427.
Protocol: [ADR-0057](../adr/0057-model-free-skill-proficiency-protocol.md).
[Measured report](full-cycle-evidence/report.json),
[learning curves](full-cycle-evidence/learning-curves.svg),
[frozen selections](full-cycle-evidence/selection.json).

## Result

Neither method demonstrates a complete delivery. Plain PPO scores **0/96** and
curriculum scores **0/96** on the nominal final tests. All 192 cases deliver
0 kg. Neither passes the three-seed capability gate. The runner, bounded six-run
experiment and final evaluation are complete; learned full-cycle proficiency is
not achieved.

| Method | Seed | Actual training decisions | Selected checkpoint decisions | Validation | Final tests | Final collisions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Plain | 7 | 147,456 | 40,960 | 0/16 | 0/32 | 0 |
| Plain | 19 | 139,264 | 24,576 | 0/16 | 0/32 | 0 |
| Plain | 41 | 139,264 | 40,960 | 0/16 | 0/32 | 0 |
| Curriculum | 7 | 36,864 | 24,576 | 0/16 | 0/32 | 0 |
| Curriculum | 19 | 40,960 | 40,960 | 0/16 | 0/32 | 3 |
| Curriculum | 41 | 40,960 | 0 | 0/16 | 0/32 | 19 |

The selected curriculum seed 41 checkpoint is the **untrained initialisation**.
Its later candidates have more full-task validation collisions. Initialisation
was a predeclared candidate; this choice is retained rather than replaced by a
more attractive prepared-stage actor. All selected checkpoints have zero
complete validation successes. None is labelled a successful full-cycle learner.

The three plain-PPO final sets and curriculum seed 7 all time out. Curriculum
seed 19 has 29 timeouts and three wall collisions. The initial curriculum seed
41 checkpoint has 13 timeouts and 19 wall collisions. Zero collisions in a failed
set do not establish useful autonomous operation.

## Prepared-stage performance and regression

All three seeds pass prepared fill with 16/16 validation successes. Seed 7
advances at 4,096 training decisions; seeds 19 and 41 advance at 8,192. This establishes
prepared near-pile pickup performance from zero load. It does not establish a
learning gain over initialisation or a complete empty-start scoop-to-delivery cycle.

Every curriculum run stops at retraction after that stage's 32,768-decision
budget. Seeds 7 and 19 end with 0/32 successes in their latest training windows,
so they do not qualify for a retraction validation gate. Do not infer measured
prior-skill retention for them after the stage change.

Seed 41 qualifies with 23/32 training successes, but its retraction validation
is only 12/16, below 14. Its previously successful fill validation drops to 0/16,
below the 12/16 retention threshold. Both conditions block advancement. The gate
exposes regression that a training-window-only curriculum would conceal.
No run advances to carry, tip or complete-stage training.

This does not identify a unique cause or prove that the task cannot be learned.
The 1,500 kg cold-start retraction pilot is a different start/load from the
2,200 kg hand-off here. Its successes do not establish transfer from a fill actor.
The present evidence supports investigating skill transfer, forgetting and phase
observability before admitting a learned capability demonstration.

## Predeclared comparison

Both methods start fresh from matching seed-specific initial actor/critic weights,
with two 64-unit layers, four environments, 64 decisions per rollout and unchanged
PPO defaults. Initial latent log standard deviation is -0.5 for every action,
the configuration selected by the earlier pilot. No teacher demonstrations,
learned-model assistance, observation changes or action-semantic changes are used.

Plain PPO trains on empty-start complete tasks using unchanged raw task reward.
Curriculum uses the accepted five-stage prepared starts and versioned shaping.
This compares practical recipes, not a pure curriculum-only or shaping-only
ablation. Prepared material comes from the pile ledger. Only complete empty-start
successes count for full-task checkpoint selection and final admission.

Each run allows up to 163,840 training decisions and 1,200 cumulative active
seconds including evaluation. A 240-second final-test allowance is reserved;
training/selection stop at the remaining 960-second boundary. Each curriculum
stage allows at most 32,768 decisions and stops on a failed prerequisite.
Advancement retains policy and optimiser state while resetting environment and
history, and requires the 32-episode window, 14/16 current validation and 12/16
on each prior stage. Every gate decision is counted separately.

Full-task validation runs at initialisation, every 8,192 training decisions,
stage transitions and final/capped stopping. Coincident evaluations are
deduplicated. Complete validation selects successes, fewer collisions, shorter
successful duration and the earlier exact tie. Partial batches cannot select.
All six selections freeze before either method opens the final cases. No final
outcome changes checkpoint, method, hyperparameter or stopping selection.

The three plain runs reach their training wall boundary with 147,456, 139,264
and 139,264 decisions. Partial final validation is retained in the logs and
charged, but excluded from selection. The curriculum runs stop on failed stage
gates at 36,864, 40,960 and 40,960 total decisions. Different realised budgets
and censoring prevent an equal-sample-efficiency conclusion.

## Costs and execution

| Work | Reference decisions |
| --- | ---: |
| On-policy training, six runs | 544,768 |
| Full-task selection validation, including partial capped batches | 571,806 |
| Current/prior-stage gate validation | 4,503 |
| Final policy evaluation, 192 cases | 104,903 |

There are 16,634 actual optimiser minibatches, 2,044 completed training episodes
and 2,080 training resets including initial and stage-transition resets. These
are actual collection counts, not the six-run upper limit. The previous pilot's
196,608 training decisions remain separate; combined study training is 741,376,
below the accepted combined upper bound. Existing reference-feasibility costs
are retained in the earlier report and are not counted again as new collection.
Unit-test fixtures, audit/export overhead and subsequent independent replay are
separate research work, not training data used by these policies.

The host is Darwin/arm64 with eight logical CPUs, Python 3.12.14, PyTorch 2.15.0
and NumPy 2.5.4. Execution starts sequentially, then a recorded scheduling
amendment permits at most two independent single-thread training workers. Every
worker uses the exact frozen runner and its own output directory. Queues do not
share weights or optimiser state. Final testing is centralised after all six
selections freeze. Caps include actual scheduling/contention. No wall-speed or
hardware-qualification claim is made.

Per-run active wall totals including final testing are approximately 1,055,
1,056 and 1,054 seconds for plain PPO, and 345, 301 and 211 seconds for curriculum.
Training time is checked between whole rollout/update or evaluation-case
transactions, so the actual training-boundary overrun is retained rather than
hidden. All final test sets finish inside their 1,200-second run allowances.

## Checkpoint, interruption and replay evidence

The runner stores actor, critic, optimiser, simulator/observation caches, all RNGs,
counters, curriculum/history, pending evaluation case cursor and exact source/library
identity in immutable checkpoints. Logs are hash-chained. Resume requires a clean
matching training package and numerical-library versions; unmatched log/checkpoint
counters fail closed. Evaluation never updates the training environment or sampler.

The actual study gracefully stops and resumes at 13,056 training decisions. The
saved and resumed counters match exactly. A second graceful stop at 65,536
seed-19 decisions permits the recorded worker scheduling change. Completed-study
resume adds zero decisions and changes neither the six selections nor any final
outcome. The training suite passes 176 tests with one optional ONNX dependency
skip. Tests include exact resumed optimisation, mid-validation recovery, retained
optimiser state at stage changes, provenance/retention failure and idempotent tests.

Independent execution is retained in `independent-replay.json`: it reruns all
96 selected validation cases, then replays every final trace while checking the
selected checkpoint's proposed actions, pre/post states and raw reward. These
verification executions are additional counted research work, not another set
of held-out policy cases. The verification summary supplies its actual decision
counts separately: 53,203 selected-validation decisions and 104,903 final-action
replay decisions, 158,106 verification decisions total. All selected validation
outcomes reproduce. Maximum state, action and raw-reward error across all final
traces is zero.

## Case roles and retained files

Validation seeds 108000–108015 are already consumed validation cases. Reuse is
explicitly for gates and selection, not fresh-test evidence. Before new collection,
the audit scans 1,462 unique available archive/history blobs and 111 ZIP members.
It permits only exact hashes of the prior registration and prior non-use
declaration, pinned to the committed earlier manifest. No policy trace matches
the final seeds or registered state/pile fingerprints. This covers available
local artefacts, not unrecorded external experiments.

Final seeds 209900–209931 are evaluated only after all six selections freeze.
`pre-test-freeze.json` records zero final decisions for every run before opening
tests. `consumption.json` records frozen-selection and first-trace ordering.
These final scenes are now consumed by all six policies. A future tuned study
must reserve different unused tests; do not reuse this certificate to claim
fresh final evidence.

`artifacts.zip` retains all 71 validation candidate checkpoints and hashes, four
gate checkpoints, the interruption checkpoint, six event logs and every one of
the 192 final traces. `source.zip` retains the exact training package at commit
`c30167b`, locked dependencies and the worker/archive/replay scripts. Raw
transaction snapshots remain under ignored `training/runs/`. `files.json`
hashes every retained evidence file. The standard-library verifier runs in CI.
The default concept walkthrough, hardware integration and production runtime
are unchanged. No successful learned capability is admitted by this report.
