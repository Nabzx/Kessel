# Model-free loader experiments

This report covers #222-#230. The implementation uses ADRs 0038/0039 and the
fixed [study plan](../../training/experiments/rl-study-v1.json). Experiments use
the available M1 CPU, one PyTorch intra-operation thread and synthetic data.
They do not validate a manufacturer model, real mine or physical deployment.
The cinematic site continues to use its existing authored experience.

**Result:** the bounded PPO study did not learn a complete scoop-to-delivery
cycle. The implementation and evaluation are complete; the retained policies
are research artefacts, not a successful autonomous hauling demonstration.

## Measured outcome

The 18 runs executed 1,520,640 environment decisions, 47,394 minibatch optimiser
steps and 7,655 terminated/truncated training episodes in 565.51 seconds of
training-loop time. There were 1,090 curriculum-subtask completions and zero
full-task training successes. Many episodes use prepared starts; neither the
episode count nor subtask count means completed full haul cycles.

| Held-out family | Reference | Untrained, each of 3 seeds | Final PPO, each of 3 seeds |
| --- | --- | --- | --- |
| Standard | 4/4 | 0/4 | 0/4 |
| Low grip | 4/4 | 0/4 | 0/4 |
| Occluded | 4/4 | 0/4 | 0/4 |
| Deliberately blocked | 0/4 | 0/4 | 0/4 |

No learned policy delivered any mass in these tests. Some untrained policies
picked up more material than the trained policies before failing. Curriculum
subtask completions therefore do not establish improvement on the complete
task. The conventional controller outperformed PPO on the declared delivery
objective. It was re-evaluated on the corrected simulator and the same scenes.
This study uses explicit stream ids; its scene set differs from the earlier
scalar reference report, so the earlier counts are not a before/after ablation.

The 108 additional OOD policy episodes also had zero successes. Reported
outcomes include wall/obstacle stops, stuck states and time limits; all actions
were finite and bounded. Stops are enforced simulator outcomes, not evidence
that the policy learned hazard avoidance. Full per-case operating metrics and
failure reasons are retained rather than reduced to favourable examples.

## Checkpoints and reproducibility

Initial, periodic and final checkpoints preserve actor/critic weights, fixed
normalisation buffers, Adam state, all random generators, full physical/pile
state, sensor caches, curriculum state, configuration and measured counters.
They are atomically written with SHA-256 sidecars. Resume checks source,
configuration, numerical library versions and runtime layout. Native regression
tests compare interrupted and uninterrupted weights, physical state, sensor
observations and RNG exactly. Cross-platform bitwise equality is not claimed.

The wall budget is cumulative and checked at rollout/update boundaries.
SIGINT/SIGTERM request a checkpointed stop at the next boundary. One final
transaction and checkpoint I/O can extend the cap; the report records actual
wall time and counts. `nominal_simulated_s` counts configured decision periods,
including partially terminated decisions, and is labelled accordingly.

## Objective curriculum

| Stage | Reset condition | Objective |
| --- | --- | --- |
| Fill | Empty bucket near the pile | Carry at least 1,000 kg without a competing failure. |
| Retract | 1,500 kg prepared load near the pile | Reverse at least 1 m, raise boom to 0.2 rad, curl to 0.4 rad and retain 1,200 kg. |
| Carry | 2,200 kg prepared load, boom raised | Reach the receiver below 0.2 m/s and retain 1,800 kg. |
| Complete | Empty machine at the original approach start | Scoop, retract, haul and deliver at least 2,000 kg. |

Prepared loads are removed from the pile at reset. They conserve material and
are never counted as learned scoops. Advancement requires at least 32 current-
stage episodes and 70% success in the latest 32. Stage changes, discarded partial
slots and reward configuration are logged. Elapsed time cannot advance a stage.

Optional `potential-v1` shaping adds `gamma*Phi(next)-Phi(current)` and sets
terminal potential to zero. Subtask completion has a separately named bonus.
Truncations retain the final-state bootstrap and potential. Raw delivery-v1
terms remain logged independently. All final evaluation runs complete original
tasks with raw rewards, without shaping or prepared loads.

## Randomisation and evaluation

Training records the seeded ranges for pile mass, density and position,
friction, grade, resistance, tunnel width and sensors. Sensor faults include
noise scale 1, 10% frame dropout, 10% local-cell occlusion and a fixed per-episode
load-estimate bias in [-5%,5%] of capacity. Observed load is bounded to capacity;
estimated mass never changes the physical ledger. Scenario and sensor RNGs
remain independent and are checkpointed.

Three independent training seeds are 7, 19 and 43. Validation and test use their
reserved seed ranges with explicit independent stream ids. Every controller
faces identical scene identities, initial conditions and complete 600-decision
budgets. An episode that finishes early is counted once; dummy reset slots do
not add evaluation samples. Every case retains mass, fill, time, spillage,
effort, slip, collision and failure reason, with realised parameter values.

Per-policy success intervals use the Wilson method on four scene streams.
Metrics include sample standard deviation and range. Spread across training
seeds is descriptive: repeated scenes are not additional independent evidence
of machine reliability. The case count is deliberately small and exploratory.

## Search and ablations

The plan was committed before execution. It declares nine search runs, three
longer runs and six ablation runs, with at most 810 seconds of training-loop
caps in total, plus transaction/I/O/evaluation overhead. Each search/ablation
targets 40,960 decisions within 30 seconds. Longer runs target 327,680 within
120 seconds. Cap-limited runs retain their actual smaller sample counts.

| Candidate | Hidden width | Environments | Rollout length | Learning rate |
| --- | --- | --- | --- | --- |
| Compact | 32 | 16 | 32 | 0.0003 |
| Balanced | 64 | 32 | 32 | 0.0003 |
| Longer | 64 | 32 | 64 | 0.0001 |

Selection uses standard validation success, delivered mass, fill ratio, fewer
collisions, smaller network and candidate id in that order. It uses no test
results. The no-curriculum and no-shaping ablations use the selected configuration
and the same short-run sample/wall budgets and training seeds. Compare them
with the selected short-run baseline, not the larger-budget runs. Multiple
dimensions change between candidates; this is a bounded configuration search,
not an isolated causal estimate of each hyperparameter.

All candidates completed their short-run sample targets. Validation full-cycle
success and delivered mass were zero for every candidate. The declared fill-
ratio tie-break chose Compact:

| Candidate | Mean validation fill ratio | Median training seconds |
| --- | --- | --- |
| Compact | 0.0444 | 16.19 |
| Balanced | 0.0295 | 10.04 |
| Longer | 0.0390 | 9.98 |

This selects an experimental configuration under the recorded rule, not a
validated operating policy. The three longer Compact runs hit their wall caps
at 309,248, 288,256 and 308,736 decisions, each ending in the carry stage.
They did not reach full-cycle proficiency. Their different actual sample
counts are reported, not treated as equal fixed-sample runs.

At the matched 40,960-decision ablation budget:

| Variant | Mean validation fill ratio | Mean training seconds | Full deliveries |
| --- | --- | --- | --- |
| Selected curriculum + shaping | 0.0444 | 16.41 | 0/12 |
| No curriculum | 0.0257 | 16.08 | 0/12 |
| No shaping | 0.0000 | 15.84 | 0/12 |

These exploratory differences do not establish reliable learning improvement.
All per-seed curves and failed configurations remain in the package. Difficulty
at the carry stage, sequential-task forgetting and sparse full-cycle feedback
are follow-up hypotheses, not isolated causes established by this experiment.

The shipped quick preset uses Compact, 80 rollouts and 40,960 decisions with a
30-second loop cap. The full preset uses the same network, 512 rollouts and a
262,144-decision target with a 120-second cap. Its target is reduced from the
study's cap-limited 327,680 target using the slowest observed throughput; it is
a conservative workload estimate, not a newly measured proficiency result.

## Exploit and robustness checks

The adversarial audit covers idle credit, empty driving, out-of-zone tipping,
repeated wall pushes, reset credit, time-limit bootstrapping and potential
cycles. It found an implementation defect: a saturated actuator request could
reset the stuck timer without physical joint movement. ADR-0039 changes the
criterion to actual joint movement. The corrected source is used for every
training run and conventional-controller comparison in this study.

Held-out standard scenes are kept separate from low-grip, occluded and blocked
families. Additional out-of-distribution tests vary grip/grade, sensing and
tunnel clearance at two severities, pile lateral/longitudinal position and an
oversized blocking obstacle. These test finite bounded actions and explicit
failure/stop behaviour. They do not certify a safe deployed controller.

## Genuine checkpoint playback

For training seed 7, selection is initial, available checkpoint nearest halfway
to the actual final rollout, then final; a tie chooses the earlier checkpoint.
All three execute on the same complete validation scenes. Replay retains the
first success and first failure in scene order when those outcomes exist.
Missing successes remain missing. Actions, joint/wheel poses, material transfer
and rewards come from actual checkpoint execution, not reference or authored
actions. Compact policy exports retain their parent checkpoint hash.

## Evidence and commands

The [evidence index](rl-evidence/files.json) covers 31 files, approximately
2.1 MB before its index. It includes every rollout curve and training episode,
28 controller-comparison reports, 27 robustness reports, three replay milestones
and nine compact policy files representing seven distinct file hashes. Repeated
initial/final exports share hashes. Curves omit per-minibatch rows but retain
all rollout aggregates; full raw logs and resumable state remain locally under
ignored `training/runs/rl-study-v1/`.

The recorded source is commit `2eb90b18d49df35bd394d8ddf7d51a3621d42e30`, package
SHA-256 `be1f16ca8c1ef3dc1e1548ecad611edd11ce96e411e22778c3b6e95b89d95e1c`.
CLI presets were updated after this study; reproduction/resume of the original
runs must use their recorded source. Retained policy exports execute with the
current unchanged physics/observation contract.

All 88 native tests pass. CI also verifies evidence hashes, source/configuration
identity, counts, complete curves and identical comparison scenes. A regression
executes retained initial/intermediate/final weights and reproduces recorded
actions and machine motion within 1e-5 across the first twelve steps of each
selected trace. All three recorded complete-task milestones failed; there is
no fabricated success trajectory to display.

From `training`:

```sh
uv run --locked pytest -q
uv run --locked python -m kessel_training.train --preset quick --output runs/quick-new
uv run --locked python -m kessel_training.train --preset full --output runs/full-new
uv run --locked python -m kessel_training.study --output runs/rl-study-new
uv run --locked python -m kessel_training.evaluation --checkpoint <policy.pt> --split test --count 4 --output runs/policy-test-new.json
```

The study refuses an existing output directory and uncommitted training
sources. Reproduction must use the recorded source revision and locked
environment. See the package's source hash and plan hash before comparing runs.

From the repository root, `python3 scripts/verify-rl-evidence.py` verifies the
committed package. `scripts/package-rl-evidence.py` reproduces a new evidence
directory from a complete raw study and refuses existing destinations.

Primary references: [loader RL](https://arxiv.org/abs/2103.01283),
[potential shaping](https://people.eecs.berkeley.edu/~russell/papers/icml99-shaping.pdf),
[checkpoint guidance](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html),
[time limits](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/)
and [Wilson intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).
