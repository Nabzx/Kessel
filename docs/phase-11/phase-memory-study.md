# Phase memory and rehearsal study

21 November 2026. Refs #410, #423–#427, #413–#414 and #434.
Protocol: [ADR-0061](../adr/0061-phase-memory-and-rehearsal-study.md).
[Measured report](phase-memory-evidence/report.json),
[learning curves](phase-memory-evidence/learning-curves.svg),
[recorded demo](phase-memory-demo/index.html).

## Result

Imitation-trained continuous controls with conventional phase memory complete
**96/96 final policy/scenario cases with zero collisions**, 32/32 for each training
seed. The memoryless comparator completes **54/96**, with zero collisions and
42 time limits. Only the phase-memory method passes the predeclared admission
requirement of at least 28/32 complete deliveries and at most one collision for
every seed.

The same 32 nominal held-out scenarios are evaluated for each of six policies,
192 policy/scenario outcomes total. These are not 192 distinct mines or distinct
scenario geometries. Every successful case starts empty and delivers at least
2,000 kg through actual simulator dynamics. No prepared load is used.

| Method | Training seed | Selected round | Validation | Final deliveries | Final collisions |
| --- | ---: | ---: | ---: | ---: | ---: |
| Memoryless | 7 | 2 | 6/16 | 15/32 | 0 |
| Memoryless | 19 | 3 | 14/16 | 20/32 | 0 |
| Memoryless | 41 | 3 | 12/16 | 19/32 | 0 |
| Phase memory | 7 | 3 | 16/16 | 32/32 | 0 |
| Phase memory | 19 | 2 | 16/16 | 32/32 | 0 |
| Phase memory | 41 | 1 | 16/16 | 32/32 | 0 |

The result qualifies a finite recorded technical demo for this synthetic task.
The network produces every continuous drive, steer, boom and bucket command.
A conventional observation-derived state machine supplies the phase input for
the admitted method. This is imitation learning with rule-based phase memory;
it does not establish PPO proficiency, learned high-level planning, training
inside a learned world model or readiness for a real machine.

## Diagnosis and intervention

The [earlier comparison](full-cycle-study.md) completes no final deliveries.
The retained diagnostic confirms three failed retraction curricula. Seed 41
regresses from 16/16 fill to 0/16 after retraction training, while retraction
validation reaches only 12/16. Actor weights change by L2 norm about 1.347 between
those gates. The weight change alone does not identify the cause of regression.

The reference controller has persistent phase/timer state; the old feed-forward
actor has no explicit counterpart. A counterfactual same-observation probe yields
different reference actions for different assigned phases. That probe does not
prove reachable observation aliasing or impossibility of a memoryless learner.
The prior imitation dataset also covers only two complete teacher episodes.

The new study collects 32 complete teacher episodes, then three rounds of learner
rollouts labelled by the teacher at each visited training state. It retains all
failures and replays all observed phases rather than successively replacing a
single-stage dataset. Both arms see the same shared aggregate corpus. They start
from matched seed-specific weights, use identical 70-input, two-layer 128-unit
networks and identical optimisation budgets. The memoryless arm masks the five
phase inputs to zero. The explicit-memory arm uses observation-derived contact,
load, boom/curl, receiver displacement, speed and a fill timer. Its memory
computes no continuous control action.

This controlled comparison supports the utility of explicit phase information
within this shared imitation recipe. It does not separately isolate rehearsal,
teacher coverage, architecture or imitation from the earlier PPO recipe. The
new models start fresh; old failed weights and outcomes remain retained.

## Acquisition, fitting and selection

Initial teacher collection supplies 12,077 labelled decisions across 32 training
episodes, including every phase. Initial phase counts are 519 approach, 4,337
fill, 996 lift, 5,170 carry and 1,055 tip. Final shared coverage is 82,917 labels:
2,882 approach, 23,456 fill, 12,333 lift, 40,815 carry and 3,431 tip. There are 176
collection episodes over 56 distinct training scenario seeds. Repeated teacher
queries on shared states are charged each time.

All six actors use uniform sampling across observed phases, batches of 512,
Adam learning rate 0.001 and gradient-norm clipping at 1.0. Each actor receives
1,500 initial updates and 750 per corrective round. Optimiser, sampler RNG,
data identity and exact source are checkpointed every 250 updates. Cached
collection cases carry seed, actor and collection-mode identity; cached cases
cannot silently switch weights or source roles.

The four fixed validation checks select complete deliveries, fewer collisions,
shorter successful duration and the earlier exact tie. All six choices freeze
before either method opens final scenarios. Selected rounds differ across seeds;
no later checkpoint replaces one because its final score looks better. The
predeclared demo preference uses memoryless control if both methods admit,
otherwise the sole admitted method. Here only phase memory admits.

No teacher is called during validation or final evaluation. The evaluator requires
an actor and has no reference fallback. Labels are restricted to the immutable
training split. Corrective collection executes learner actions, not teacher
corrections. The shared corpus depends on all arms' training rollouts and is not
an independently acquired dataset for each method.

## Actual costs

| Work | Count |
| --- | ---: |
| Collection reference decisions | 82,917 |
| Teacher action queries | 82,917 |
| Supervised optimiser minibatches, six runs | 22,500 |
| Reused pair presentations, batch 512 | 11,520,000 |
| Validation reference decisions | 180,884 |
| Final evaluation reference decisions | 89,412 |

Teacher queries label the collection decisions; they are not another set of
executed environment transitions. Costs are distinct from the historical PPO
and world-model studies. No sample-efficiency claim against reward-only PPO is
made. Total original active study duration is about 1,693 seconds, inside its
5,400-second global cap and reserved final-evaluation allowance. Audit, export,
QA and post-study independent replay are separate research overheads.

The original numerical source is commit `5cee52a`, with Python 3.12.14, PyTorch
2.15.0 and NumPy 2.5.4 on Darwin/arm64. All student training uses one Torch thread.
Numerical source and budgets remain unchanged throughout collection. Regular
subsequent commits add the separate viewer, evidence tools and review results.

## Fresh-case audit and verification

The audit covers 5,348 unique available archive/history blobs and 385 ZIP members.
It rejects the proposed 209800 and 209600 ranges because older world-model
contact/high-resistance data reused those scenes. Validation 108100 is excluded
because a unit fixture touched it before collection. The accepted validation
range is 108200–108215 and the accepted final range is 207600–207631. No matches
or unreadable archives remain for those replacement cases. The audit covers
available local artefacts and refs, not unrecorded external experiments.

Both ranges are now consumed. A future tuned study needs newly reserved final
cases. All 192 final traces, all 24 round candidates, all 176 acquisition episodes,
all validation records, weights/optimisers/RNGs and exact source are retained.
The original failed PPO studies remain unchanged.

Independent replay re-executes the 96 selected validation cases and every final
trace, checking proposed neural actions, conventional phase state, physical
pre/post states, reward and final outcomes. The verifier makes teacher calls
fatal. Its counted executions are verification of these same cases rather than
a new held-out generalisation set. All cases reproduce with zero maximum state, action and raw-reward error.
Verification adds 42,984 selected-validation decisions and
89,412 final-trace decisions, with zero teacher queries.

Completed-study resume is checked with new episode execution, teacher action
queries and optimiser steps blocked. It adds zero decisions or updates and
preserves selections and all final outcomes. The training suite passes 182 tests
with one optional ONNX dependency skip. Two additional export tests reject
failed methods and forged admission flags that contradict per-seed scores.

## Recorded viewer and narrative review

The [technical viewer](phase-memory-demo/index.html) supports three finite
recordings: the first successful final case for each admitted training seed.
All three use scenario 207600 with different frozen policies. Its aggregate
result covers all 96 admitted-method cases. It verifies record bytes against
SHA-256, keeps clock/source/metrics coherent when switching, starts paused,
retains terminal outcomes, offers a readout of the four actual recorded commands,
and fails closed on corrupt data. Commands are normalised to -1 through 1. Actual poses,
joints, pile heights and kilogram values drive the view. Cargo/receiver shapes
and fixed wheels are disclosed visual proxies. There is no browser inference
or arbitrary physics rerun.

Native Chrome 157 checks pass at 1440×900, 1365×768 retina/reduced motion and a
narrow functional profile. They inspect 2,222 recorded machine poses across
the desktop profiles, play/pause, keyboard control, rapid record selection,
no horizontal overflow and corrupt-record retry. A five-second recorded-playback
rendering check on the Apple M1 Metal renderer averages about 60.06 fps, with
p95 16.8 ms and p99 16.8 ms. This measurement covers rendering recorded playback.
The narrow profile is functional coverage, not phone presentation qualification.

The [separate narrative review](narrative-review-2026-11-21/README.md) retains native
captures and agent visual findings. Mine-first is preferred for the isolated
technical explanation; source transitions and failed historical learned runs
remain explicit. This does not constitute a human comprehension study or adopt
a new production opening. The primary authored concept walkthrough is unchanged.
Seven prior research/training PRs (#435–#441) are reviewed and merged into main.

The standalone preview is about 1.2 MB as a ZIP. Its root entry, asset/module
dependencies, three record identities, action readout, playback and recovery
pass the same native Chrome checks from an independently served package folder.
The package includes no training tools or weights.
