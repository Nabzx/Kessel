# Learning prerequisite diagnostic protocol

Refs #410, #423, #424, #425 and #426. This bounded investigation is committed
before collection. It does not change the task, rewards or trained weights.

## Inputs and selection

Use `docs/phase-11/policy-followup-evidence/report.json`, its teacher archive,
saved warm-start and final candidates. Verify checkpoint/archive hashes first.
Use all three declared training seeds for teacher-fit metrics. Use the first
declared training seed, 7, for new stage evaluations. This is a declared subset,
not selection by an attractive outcome.

The two validation scenes, 100000 and 100001, are reused diagnostic scenes.
Do not call them a fresh test or use diagnostic teacher queries to create
training data. Existing held-out failure results remain unchanged.

## Measurements

1. Regenerate all 1,024 teacher pairs with the unchanged reference controller.
   Require exact observation, action, phase and episode-accounting equality.
   Record phase counts and observed action/observation ranges. Charge these
   1,024 re-executed decisions as diagnostic reconstruction, not extra training.
2. Measure deterministic action MSE against the existing teacher pairs for
   warm-start and final candidates across seeds 7, 19 and 41. Retain per-action
   and per-phase errors and saved latent exploration standard deviations.
   Training-pair fit is not generalisation or proficiency. Latent standard
   deviation is not the standard deviation of the bounded action after tanh.
3. Evaluate the warm-start and final candidates from seed 7 on all four task
   stages in both validation scenes: 16 rollouts. Preserve prepared payload,
   actual state/action sequences, material transfers and terminal outcomes.
4. Evaluate eight matching stage-initialised conventional-controller rollouts.
   Prepared fill/retraction/carry starts use controller phases 1/2/3; complete
   starts use phase 0. A controller reset to approach is not a valid prepared
   carry baseline. Count prepared-stage success separately from full delivery.
5. Compare the initial 65-feature observations of the same seed under ordinary,
   narrower-corridor and blocked-route geometry. Record differences rather than
   adding privileged geometry to the policy.
6. Execute the existing PPO smoke workload three times: four environments,
   64 decisions per rollout, four rollouts, seeds 7, 19 and 41. These perform
   3,072 reference decisions in total and discard their weights. Record
   collection, optimisation and total timing, actual minibatch updates and RSS.
   This checks CPU execution, not learning or a sufficient training budget.

## Boundaries

Run after focused tests, without a concurrent benchmark or test process, using
the locked CPU environment and one Torch thread. The tool refuses existing
output and uncommitted training code. Keep the original source identities and
new diagnostic source identity separate. Never overwrite retained experiments.

Use the measurements to recommend the next bounded model-free experiment.
Changing curriculum gates, task rewards, dynamics, observations or action
representations requires an accepted protocol before task training. Do not
silently promote a prepared skill into a full-cycle capability demonstration.

Reproduce from `training/`:

```sh
uv run --locked python -m kessel_training.inspect_prerequisites --output runs/prerequisites-new
```
