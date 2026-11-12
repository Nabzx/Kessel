# Learning readiness and failure diagnosis

Refs #409, #420, #421 and #422. Recommendation:
[ADR-0056](../adr/0056-working-capability-demo-research.md), proposed.

## Result

Keep the reference simulator and isolate retraction/transport learning before
another model-assisted experiment. This investigation reproduces existing
failures; it does not train a better policy or validate mine physics.

The [new report](../phase-11/readiness-evidence/report.json) executes all four
methods from the first declared training seed, 7, on both retained test scenes,
200000 and 200001. Saved checkpoint actions, pre-action states and terminal
states exactly reproduce the retained traces: maximum state and action errors
are zero. Original checkpoint and trace hashes are verified before execution.
These are reused diagnostic cases, not fresh held-out performance evidence.

The command also executes eight conventional-controller cases, two zero-command
baselines, three controller-speed variants and the existing reference audit.
It performs zero training updates. The measured run took 85.61 seconds on
arm64 with Python 3.12.14, NumPy 2.5.4, PyTorch 2.15.0 and one Torch thread.
This is an observed diagnostic duration, not a training-time forecast.

## What failed

| Policy, training seed 7 | Scene 200000 | Scene 200001 | Interpretation |
| --- | --- | --- | --- |
| PPO | Timeout, zero pickup or delivery | Timeout, zero pickup or delivery | No complete-task behaviour in deterministic evaluation |
| Two-frame history PPO | Timeout, zero pickup or delivery | Timeout, zero pickup or delivery | Extra history alone did not fix the failure within the retained budget |
| Gated curriculum | Wall at 6.04 s, peak pickup 188.20 kg | Wall at 15.10 s, peak pickup 176.83 kg | Some material interaction, no successful transport |
| Supervised warm-start plus PPO | Timeout, zero pickup or delivery | Timeout, zero pickup or delivery | Its final selected checkpoint has not established imitation-based task proficiency |

All twelve retained follow-up runs are inspected for their training counters
and stage history. All three curriculum seeds reached `retract`; none reached
`carry` or `complete`. Their final retraction windows contained 8, 0 and 9
episodes respectively, with no retraction successes. In this experiment,
complete-task curriculum evaluation therefore tests skills that the curriculum
never reached in training. This is a concrete missing prerequisite, not proof
that larger budgets alone will solve it.

## Reference feasibility and physical limits

The conventional controller delivers over 2,000 kg in both standard, low-grip
and occluded cases, 6/6 successes. Both fully blocked cases terminate on
`obstacle_0`. Those collisions are expected infeasibility outcomes, not proof
of safe obstacle detection or avoidance. Nominal success demonstrates that
this synthetic task can be executed with the existing observation fields and
controller logic; it does not establish policy learnability or field fidelity.

The opt-in pile audit retains 6/10 successes. Legacy, ridge and rubble succeed
on both validation seeds. The low pile yields a wall collision and a timeout
with 1,154.51 kg delivered. Both steep-pile cases are stuck. Keep these failures
visible rather than expanding the demo's supported scenario set to all piles.

Every audited reference action is independently replayed in a second simulator.
Per-step mass residuals remain below 1e-7 kg. Across the policy, reference and
zero-command diagnostic cases, the maximum residual is 5.46e-12 kg. This checks
conservation of the implemented ledger, not granular mechanics.

Material extraction uses an 8 × 8 height field, cell-centre bucket contact,
bounded removal and a 1,200 kg/s transfer cap. Curl can contribute to extraction;
release depends on curl and an axis-aligned receiver footprint. There is no
particle settling, cohesion, fracture or calibrated hydraulic response. Rendered
machine geometry is not the simulator's collision geometry. Conservative swept
component AABBs can reject some clear manoeuvres.

Control intervals 0.05, 0.1 and 0.2 seconds all complete the same reference
contact task in approximately 35.9 simulated seconds, with physics increments
at most 20 ms. All 15 existing free-motion integration comparisons pass their
declared position/joint/speed bounds. One validation scene also succeeds with
approach targets 0.7, 0.9 and 1.1 m/s. This small sweep does not establish
parameter robustness outside those conditions.

## Reward and control findings

The base delivery reward pays incremental delivered mass divided by 3,500 kg.
It charges elapsed time, effort, slip, spillage and a 5-point collision penalty.
It gives no positive pickup or carried-load credit. Weighted components
independently reconstruct each diagnostic step's reward within 1e-12.

Successful standard reference returns are +0.4987 and +0.5079. PPO and history
returns are approximately -0.1201, with no delivery reward. Curriculum wall
failures return -5.0136 and -5.0318. Successful delivery is rewarded over these
failures, but positive reward is delayed across approach, pickup, reversal,
transport and tipping. A single collision costs more than the maximum
one-bucket delivery credit. This supports investigation of exploration and
skill sequencing; it does not identify reward weights as a proven cause.

`idle` in the raw report means **all four commands are zero**, not a parking
brake. Under the randomised grade, scene 200000 rolls, picks up 1,044.53 kg and
eventually hits a wall. Scene 200001 times out without pickup. The force model
allows grade-driven motion. Do not use this baseline to claim a stationary
machine or label zero controls as a safe stop.

The action named `acceleration` is a bounded drive request processed through
force, grip and resistance limits, not a direct commanded physical acceleration.
The other actions command joint rates. This distinction needs an explicit
contract before interpreting learned actions or comparing hardware interfaces.

## Prioritised hypotheses and next probes

1. **Missing retraction and carry skill.** Under #424, evaluate retraction
   independently from full starts and measure gate/retention progress per stage.
   Declare the stage budget before training. A prepared carry start is not a
   completed pickup-and-delivery task.
2. **Insufficient useful exploration across delayed reward.** Under #422/#426,
   compare the fraction of episodes reaching pickup, retraction, receiver arrival
   and tipping. Diagnose bottlenecks before increasing budgets or rewards.
3. **Teacher-to-policy coverage gap.** Under #425, inspect the existing
   phase-balanced teacher pairs and warm-start checkpoint separately from the
   final PPO checkpoint. Final failure cannot identify where imitation failed.
4. **Observation and action ambiguity.** Under #417/#423, map the 65 features
   to measured quantities. The local height crop represents pile height, not
   obstacle or wall range. Scene width and obstacle boxes are not policy inputs.
   Nominal controller feasibility does not imply observability of arbitrary
   obstacle layouts. Account for this before promising obstacle controls.
5. **Task-specific physics limitations.** Under #420/#421, isolate low/steep
   pile and clearance failures. Replace dynamics only when a measured failure
   affects the intended learning task, rather than because the visuals are
   more detailed than the reference approximation.

## Follow-on implementation proposals

- Add an independently runnable per-stage diagnostic with training-only starts,
  explicit prepared payload and held-out retention scores. Acceptance: exact
  resets and separate empty-start/full-cycle results.
- Add phase-coverage reports for existing teacher pairs and warm-start/final
  policy trajectories. Acceptance: all teacher data charged and no test data
  queried during imitation or checkpoint selection.
- Specify a bounded model-free skill-proficiency experiment under #410 before
  running further optimisation. Acceptance: protocol committed before collection,
  fixed validation selection, untouched final tests, all failures exported.

These are recommendations for the parent tickets, not implementation-ready
specifications. Changing default dynamics, rewards or presentation requires
the appropriate accepted ADR. The first batch establishes feasibility and
failure boundaries; it does not settle the remaining focused investigations.

## Reproduction and verification

From `training/`, use the locked Python 3.12 environment:

```sh
uv sync --locked
uv run --locked python -m kessel_training.diagnose_readiness --output runs/readiness-new
```

The diagnostic refuses an existing output or uncommitted training sources.
It preserves original experiment identity alongside the current source hash.
The retained [file manifest](../phase-11/readiness-evidence/files.json)
covers compact reports, geometry fixtures and compressed per-case reference
actions/states. Raw uncompressed outputs remain in ignored `training/runs/`.
Run `python3 scripts/verify-readiness-evidence.py` to check the retained bundle.
