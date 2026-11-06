# World-model experiments

Tickets #231–#242. Native Apple M1, 16 GiB, CPU, one PyTorch thread.
Python 3.12, NumPy 2.5.4 and PyTorch 2.15.0 from the locked experiment environment.
These are learned **synthetic state dynamics**, separate from the reference
simulator, control policy and authored investor presentation. They do not model
camera perception, real rock fracture or a surveyed mine.

## Result and decision

The ensemble predicts position better than persistence and the single network,
but the documented kinematic predictor remains substantially more accurate.
Raw neural material and reward errors also lose to persistence on the first
held-out corpus. Every raw imagined branch fails the physical checks.

A separately declared hybrid adds explicit local-contact and conservation
constraints to the frozen ensemble. This allows real auxiliary critic updates
without passing imagined rows into PPO's likelihood ratios. Those constraints
are imposed by code; the network has not learned conservation.

Keep this as research tooling. Neither experiment establishes complete learned
scoop-to-delivery proficiency, a sample-efficiency gain or a deployment-ready
world model. See ADRs [0040](../adr/0040-world-model-prototype-and-evaluation.md),
[0041](../adr/0041-explicit-bounded-world-model-filter.md) and the measured
recommendation in [ADR-0042](../adr/0042-world-model-assistance-outcome.md).

## Data and independent reference

The first study collects 18,432 transitions: 8,192 training, 2,048 validation,
2,048 nominal test and six 1,024-row OOD partitions. Each mixes 50% conventional
controller, 25% bounded random actions and 25% actual saved RL-policy actions.
The training partition includes 1,414 material-transfer, eight contact-without-
transfer and 19 collision/stuck transitions. The small failure/contact samples
limit the conclusions; empty motion dominates the corpus.

An episode stays in one partition. Seeds, initial pile hashes, source/checkpoint
identities and deterministic archive/logical hashes are retained. No adjacent
row split or train/test pile reuse is permitted. Collection-budget boundaries
are distinguished from real terminal events. Input and target normalisers fit
training only; constant features have scale one, and non-finite rows fail.

The 102-element privileged state includes 15 loader/material/counter variables,
64 pile heights, and fixed scene/control context. Four continuous actuator
commands condition 79 dynamic-state residuals, a scalar reward and four event
logits: terminal, truncation, contact and collision. Static context is preserved;
the known decision index advances explicitly. Yaw differences wrap circularly.

The independent simulator records all reference outcomes before prediction.
Nothing in the learned model advances the reference simulator. Idealised local
height observations reconstructed during imagination are explicit privileged-
state projections, not learned sensor reconstruction.

## Models and losses

Single network: two 128-unit SiLU hidden layers, 41,044 parameters, seed 101.
Ensemble: three such networks, 123,132 parameters, seeds 101/211/307, with
independent whole-episode bootstrap samples. Adam uses learning rate 0.001,
batch 256 and at most 30 epochs. Each saved artefact contains all members,
normalisers, bootstrap identities, configuration and selection history.

The objective is normalised state MSE + 0.2 reward MSE + 0.1 event BCE, with
bounded positive class weights and gradient clipping. Raw current validation
error and best-so-far error are separate fields. The single network selected
epoch 4 after 900 optimiser updates (1.20 s); the ensemble selected epoch 30
after 2,640 updates (3.24 s). Checkpoint selection uses validation only.

First held-out one-step results, all 2,048 rows:

| Predictor | Position MAE, m | Carried mass MAE, kg | Pile height MAE, m | Reward MAE |
| --- | ---: | ---: | ---: | ---: |
| Persistence | 0.03757 | 5.656 | 0.0001170 | 0.005650 |
| Kinematic | 0.00114 | 5.656 | 0.0001170 | 0.005454 |
| Single network | 0.02673 | 9.174 | 0.0003162 | 0.024382 |
| Raw ensemble | 0.01389 | 7.863 | 0.0003630 | 0.039996 |

The kinematic predictor integrates known constant acceleration and bounded joint
rates. It does not predict material transfer, gravity, contact or turning yaw.
Persistence keeps physical state constant while advancing known time/index.
Per-variable, event, regime and physical-violation results remain in
[the complete metrics](world-model-evidence/prediction-metrics.json).

## Horizon and uncertainty

Open-loop evaluation uses fixed recorded actions on common episode windows at
1/2/4/8 decisions, without crossing reference resets. These are diagnostics:
predicted events do not end the diagnostic rollout, and rejected hybrid
corrections remain visible rather than being discarded from aggregate error.
Operational imagined branches apply all gates and stop independently.

The raw validation gate supports one decision (nominally 0.1 s). At two decisions,
cumulative reward MAE is 0.1063, above the declared 0.1 limit. Validation chooses
disagreement threshold 0.291254: 75% score coverage, 98 high-error cases missed
among 1,536 accepted rows. A score pass alone does not authorise imagination.

Disagreement is the RMS ensemble standard deviation of train-normalised outputs,
not a probability, metre error or cumulative covariance. Validation Pearson
correlation with position error is -0.0094. The raw gate passes 611 high-error
low-grip rows and 450 high-error blocked rows in the first OOD audit. Uncertainty
alone is unreliable, especially under shift. High-resistance and unusual-pile
branch probes are rejected; sensing changes can be hidden by privileged input.

[Disagreement/error and coverage figure](world-model-evidence/figures/uncertainty.svg).
[Measured open-loop drift](world-model-evidence/figures/drift.svg).
Both figures are generated from retained measured values, not authored curves.

## Physical guards and auxiliary learning

The raw study proposes 5,760 training branches and accepts zero. Validation and
test diagnostic probes each reject all 128 anchors. Failures include remote
pile edits, negative material, non-monotone counters, mass imbalance, actuator
bounds and unearned reward. This negative result is retained unchanged.

ADR-0041 predeclares a separate bounded filter before collecting fresh held-out
data. It preserves machine position and original uncertainty scores. It applies
local bucket contact, payload/release-rate and receiver budgets, non-negative
pile removal, monotone delivered/spilled mass, actuator bounds and conservative
reward credit. Carried mass comes from the same material ledger. Per-row raw
forecasts, corrections and rejection flags remain available.

Corrections exceeding 2 mm per cell, 25 kg material/pile change, 0.01 rad joint
change, 0.02 s clock/slip change, 100 J effort, 0.01 m/s speed, 0.02 slip ratio
or 0.05 reward are rejected. The original geometry, mass, movement, uncertainty,
input-envelope and terminal gates still apply. This is an explicit hybrid
approximation, not a safety guarantee or a claim of learned physics.

Actor updates remain real on-policy PPO. Every fourth rollout, at most 25% of
training anchors propose at most two imagined decisions. Accepted branches
supply an auxiliary critic target with coefficient 0.1; no imagined action or
likelihood enters PPO's actor loss. The frozen model has zero online refits.
Actor-gradient isolation, rejection handling and exact resumption are tested.

## Equal-budget comparison

The original model-free arm receives 40,960 on-policy reference decisions per
seed. Each assisted arm receives 30,720 on-policy decisions plus a charged
10,240-row offline training/validation corpus. Seeds are 7, 19 and 43, with the
same 16 environments, 32-step rollouts, 32-unit actor/critic, raw delivery reward,
complete tasks and no curriculum/shaping. This tests equal total real-sample
cost, not an isolated auxiliary-loss ablation.

The raw study executes 215,040 policy decisions. Raw assistance makes zero
critic updates; model-free and raw-assisted policies both complete zero held-out
full cycles and deliver zero material. The conventional controller completes
4/4 standard, low-grip and occluded cases, and correctly fails all four blocked
cases. Its success is independent of learned proficiency.

Original policy-training totals are 48.27 s model-free and 36.31 s raw-assisted.
Each standalone assisted run also incurs 47.57 s training/validation collection,
3.24 s ensemble fitting and 0.06 s gate calibration. The shorter assisted policy
run uses fewer on-policy samples; it is not a demonstrated wall-time gain.
The original complete study takes 326.64 s including data, fitting, diagnostics,
policy training and evaluations. One-time shared and per-run charged costs are
both retained, with current and matched-budget validation outcomes.

The follow-up adds three assisted runs (at most 92,160 on-policy decisions),
reuses immutable training/validation and frozen raw-model/control weights, and
collects 8,192 genuinely fresh test/OOD transitions. Fresh data seeds do not
overlap any first-study episode/pile. All nine final policies and the reference
controller execute identical fresh policy scenes. Test results never tune the
filter, model or validation gate.

Fresh held-out one-step results, all 2,048 rows:

| Predictor | Position MAE, m | Carried mass MAE, kg | Reward MAE | Mass-ledger MAE, kg |
| --- | ---: | ---: | ---: | ---: |
| Frozen raw ensemble | 0.01510 | 8.103 | 0.04502 | 0.899 |
| Explicit hybrid | 0.01510 | 2.305 | 0.03934 | < 1e-9 |
| Kinematic | 0.00199 | 5.702 | 0.01278 | < 1e-9 |

The hybrid's material improvement is imposed partly by known constraints.
These diagnostic averages include 362 rows exceeding the bounded-correction
limits; those rows are rejected for operational imagination. No position
correction occurs. The hybrid validation gate supports two decisions. It
accepts 64/128 validation branch probes and 74/128 fresh nominal test probes;
all high-resistance and unusual-pile probes still fail. Full rejection reasons,
per-row-unit correction aggregates and OOD errors remain in
[the follow-up metrics](world-model-filter-evidence/prediction-metrics.json).

| Filtered seed | Accepted imagined transitions | Critic updates | Policy wall time, s | Fresh complete cycles |
| --- | ---: | ---: | ---: | ---: |
| 7 | 2,009 | 15 | 12.22 | 0/16 |
| 19 | 1,396 | 15 | 12.01 | 0/16 |
| 43 | 1,314 | 15 | 11.96 | 0/16 |

The follow-up executes 92,160 additional on-policy decisions, accepts 4,719
imagined transitions and makes 45 auxiliary critic updates in total. All nine
learned policies deliver zero material on the fresh comparisons. Reference
outcomes are 4/4 standard, 2/4 low-grip, 4/4 occluded and 0/4 blocked. Every
matched-budget validation check also has zero learned complete-task successes.
There is no demonstrated task-success or sample-efficiency improvement.

The filtered policies take 36.18 s combined training time; each also carries
its recorded model/data setup costs and 0.072 s filtered-gate calibration.
The complete follow-up takes 202.10 s including fresh acquisition, diagnostics,
training and evaluation. The two studies acquire 26,624 dataset transitions,
execute 307,200 on-policy training decisions and fit 3,540 model minibatches.
Test/evaluation interactions are diagnostic costs, not hidden training samples.
Three short seeds with zero successes cannot establish equivalence between
methods. Retain the negative result and investigate task learning separately.

## Reproduction and evidence

From `training/`, using the locked isolated environment and new output paths:

```sh
uv run --locked python -m kessel_training.wm_experiment --output runs/world-model-study-new
uv run --locked python -m kessel_training.wm_filter_experiment --source runs/world-model-study-new --output runs/world-model-filter-new
```

Each command requires committed training sources and refuses an existing output.
The immutable predeclared plans live in `training/experiments/`. The raw study
ran at `68acc70`; the filter follow-up ran at `e6188d4`. Execution uses CPU with
one thread. Wall times are local observations, not hard real-time guarantees.

Compact evidence retains full curves/episode outcomes, per-variable and OOD
metrics, plot points, deterministic corpus manifests, actual prediction/reference
pairs, both learned dynamics artefacts and all nine final policy weights. Large
transition archives and resumable simulator/optimiser snapshots remain in ignored
local runs. Regeneration follows manifests and checksums. No research weights or
buffers are added to the shipped static site.

`python3 scripts/verify-world-model-evidence.py` checks hashes, frozen protocol,
partition isolation, equal-budget accounting, scene equality and residuals.
The Python test suite also executes retained neural weights and reconstructs
multi-step predictions, events, rewards and filter corrections. Missing
prediction horizons stay explicitly missing; no smooth error curve is invented.

## Research basis and limits

The implementation adapts the small ensemble/short-branch pattern from
[MBPO](https://arxiv.org/abs/1906.08253) and
[PETS](https://arxiv.org/abs/1805.12114), rather than claiming to reproduce their
algorithms or results. [Wheel-loader world modelling](https://arxiv.org/abs/2309.12016)
provides task context. The pinned Selene source informed the CPU workflow;
its lunar features, random row splitting and authored exporter were not copied.

[Physics-informed architectural constraints](https://arxiv.org/abs/2109.06407)
and [explicit projection layers](https://arxiv.org/abs/2402.07251) informed the
separate constraint experiment. Their mathematical guarantees do not carry over
to this bounded filter. Synthetic height fields, sparse contact failures,
privileged state and three short policy seeds cannot establish real-machine
performance, perception robustness or safe deployment. Recorded viewer
integration, ONNX/distillation and visual polish remain later ticket groups.
