# Bounded model-free retraction pilot

Refs #410 and #423–#427. Protocol: [ADR-0057](../adr/0057-model-free-skill-proficiency-protocol.md).
[Measured report](retraction-pilot-evidence/report.json),
[learning curves](retraction-pilot-evidence/learning-curves.svg),
[independent replay](retraction-pilot-evidence/independent-replay.json).

## Result

The isolated retraction skill is learnable in this synthetic environment. Two
baseline seed checkpoints complete all 16 new pilot test cases; the third fails
all 16. The predeclared pilot gate passes. This does not establish reliable
learning across restarts or an empty-start full delivery cycle.

| Exploration setting | Training seed | Selected rollout | Validation successes | Pilot test successes |
| --- | ---: | ---: | ---: | ---: |
| Default | 7 | 64 | 16/16 | 16/16 |
| Default | 19 | 80 | 0/16 | 0/16 |
| Default | 41 | 128 | 16/16 | 16/16 |
| Reduced steering | 7 | 112 | 0/16 | Not tested |
| Reduced steering | 19 | 128 | 16/16 | Not tested |
| Reduced steering | 41 | 112 | 16/16 | Not tested |

Both settings have median validation success 16/16. The predeclared exact tie
favours default exploration, which is frozen before any policy pilot-test
evaluation. Reduced steering changes which seed fails; it does not consistently
improve this small comparison. No test result changes configuration or checkpoint
selection, and all six training runs are retained.

## Task and what the result means

Every episode starts near the pile with **1,500 kg prepared payload**. The
material is removed from the pile ledger, preserving mass. Success requires
reversing at least 1 m, lifting the boom to at least 0.2 rad, curling to at least
0.4 rad and retaining at least 1,200 kg. The horizon is 200 decisions, at most
20 simulated seconds. The episode terminates at the stage goal.

The successful selected checkpoints finish new test cases in about 2.0 seconds
(seed 7) and 1.6 seconds (seed 41). Seed 19 times out at 20 seconds. These are
simulated durations, not compute latency. Termination does not demonstrate an
autonomous braking/stop response after the goal.

This tests a policy learning actions with model-free PPO in the reference
simulator. It does not train inside a learned world model, learn perception
from images, perform pickup from empty, haul to the receiver or deliver material.
Prepared retraction cannot be labelled a complete learned loading cycle.

## Controlled experiment and execution

Two-layer 64-unit actor/critic, four environments, 64 decisions per rollout,
current PPO defaults and legacy retraction shaping are held fixed. All initial
network weights match for each seed. Only the initial steering latent standard
deviation changes: log standard deviation -0.5 versus -2.5 for that dimension.
All four exploration parameters remain trainable with the same clamps.

Each run completes 128 rollouts and 32,768 on-policy decisions. Initial and every
16th-rollout candidates are evaluated deterministically on the same 16 validation
starts. Select successes, fewer collisions, shorter successful duration and then
the earlier exact tie. A prepared base delivery cannot substitute for the explicit
retraction reason. No reward/pickup/test-based checkpoint selection is used.

The runner saves immutable transaction checkpoints with actor, critic, optimiser,
simulator/observations, RNGs, counters and source/library identity. Event logs are
hash-chained. Resume requires the same source package and libraries and matching
log/checkpoint counters. Unit tests reproduce uninterrupted updates exactly.
An actual completed-study resume adds no training/validation/test decisions and
changes neither selected hashes nor outcomes; its separate check is retained.

All runs stay below the 600-second active wall allowance, including their
evaluation. Active clocks pause while other runs execute. Sixty seconds is
reserved for post-selection tests. Caps are checked between complete transactions,
and incomplete validation cannot select a checkpoint. No run hits its cap.

## Scenario audit and reservation

The preflight scans **601 unique available blobs**: 281 JSON, 78 compressed JSON,
218 checkpoints, 23 NPZ archives and one JSONL stream, deduplicated across refreshed
local refs/history and local data/docs/training files. Checkpoints use safe
weights-only decoding; NPZ uses no pickle. It checks explicit seeds and initial
state/pile fingerprints at float64 and float32 precision, including geometry
reuse across differing task horizons. There are no matches or unreadable archives.

Freeze actual initial identities for validation 108000–108015, pilot test
208900–208915 and future final test 209900–209931. Starts are clearance-valid and
non-duplicated. The reference controller completes all 16 validation retraction
cases before policy training, at a separately counted cost of 773 decisions.

This certifies the available artefact scope, not unrecorded external experiments
or unreachable/deleted history outside available refs. The reservation is a
pre-collection certificate, not a declaration that the cases remain unused.
Validation and pilot-test cases are now consumed; future final-test states were
initialised for identity checks but never evaluated with a policy.

## Costs and retained evidence

| Work | Reference decisions |
| --- | ---: |
| Six on-policy training runs | 196,608 |
| Candidate validation | 94,169 |
| Three selected checkpoints on pilot test | 3,776 |
| Shared reference validation | 773 |
| Post-study independent verification | 11,405 |

There are 6,051 actual optimiser minibatches. Training active wall times including
per-run evaluation range from about 95 to 197 seconds. Failed validation episodes
run longer, so validation cost varies across runs. This is not a matched-total-
sample or end-to-end wall-speed efficiency claim. Audit, archive/export and
post-study verification are separate research overheads; no unmeasured total
wall duration is presented as a benchmark.

All 54 candidate checkpoints, their hashes, six event logs and 48 pilot-test
traces are in `artifacts.zip`. The full source package and locked dependency files
are in `source.zip`. Raw per-rollout snapshots remain in ignored `training/runs/`.
The compact report retains every validation case and learning curve. No main
presentation, public release or hardware integration is changed.

Independent execution reproduces all 96 selected validation cases. It then
re-executes each held-out action from a fresh simulator while checking the loaded
checkpoint's proposed action. All 48 traces match with zero maximum state and
action error. Verification repeats do not fit models or change selection.

## Recommendation

The pilot clears the predeclared gate for further staged research. Proceed to
implement and reference-check the coherent five-stage contract, including
ledger-consistent 2,200 kg starts, explicit tipping and retention checks. Preserve
legacy tasks and the failed seed. Do not assume the 1,500 kg pilot weights transfer
to that contract or cherry-pick a successful restart as evidence of stable learning.

Keep the conditional full-cycle trial proposed until the stage factory, reference
feasibility, interruption/resume and gate tests pass and its implementation is
frozen. Then use the existing bounded comparison and untouched final-test role.
No full-cycle training was executed in this pilot.
