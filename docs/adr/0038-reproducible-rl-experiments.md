# ADR-0038: Reproducible RL experiments

Status: Accepted

## Decision

Complete the model-free experiment tools before world-model-assisted learning.
Checkpoints contain actor, critic, fixed normalisation buffers, optimiser,
configuration, counters, learning curves, curriculum state, CPU/Python/NumPy RNG
state and the complete simulator/sensor state. Write them atomically, identify
them by SHA-256 and resume only compatible clean-source configurations. Compare
an interrupted and uninterrupted run numerically. Budget limits are checked
between complete rollout/update transactions; report any final transaction and
checkpoint overhead separately. Count actual completed episodes and updates.

Use objectively gated fill, retract, carry and complete-cycle curriculum stages.
Prepared loaded starts remove the same mass from the pile; they are reset
conditions, not learned scoops. Advance only after at least 32 current-stage
episodes and 70% success in the latest 32. Log changes and never equate subtask
success with complete delivery. Optional named potential shaping uses discounted
potential differences and terminal zero potential. Delivery-v1 remains the raw
task reward. Final policy comparisons always start on complete unmodified tasks.

Randomised training records physical/sensor ranges, including load-estimate
bias. Keep training, validation and test seed ranges separate. Evaluate every
controller on identical scene identities and complete episode budgets. Record
all failures, source/configuration/checkpoint hashes, operating metrics, spread
and success intervals. Select checkpoints by an explicit validation rule. Run
test/robustness only after selection; do not tune on their results.

Before running the study, freeze a machine-readable plan. Compare three small
configurations over training seeds 7, 19 and 43, with 40,960 environment decisions
and a 30-second loop cap each. Configurations vary width, batch, rollout and
learning rate. Select on four standard validation cases, ranking success,
delivered mass, fill ratio, collisions, then smaller network. Run the selected
configuration to 327,680 decisions with a 120-second cap for each seed. Compare
no-curriculum and no-shaping ablations at the same 40,960-decision/30-second
budget and seeds. Keep unsuccessful configurations and full learning curves.
Any additional search requires a separately recorded budget before execution.

Evaluate untrained, final policy and reference controller on held-out standard
and perturbed scenes. Stress grip/grade, sensing, clearances, obstacles and pile
position separately, with severity and in/out-of-distribution labels. Probe idle
reward, repeated material credit, wall pushing and reset/truncation semantics.
If an environment/reward defect is found, correct it and rerun comparisons.

Execute saved initial, halfway and final checkpoints on the same scenes for
replay evidence. Preserve the first success/failure in declared traversal order.
If training fails to learn a useful full cycle, state that result rather than
substituting authored or reference-controller actions. This work does not change
the cinematic viewer, establish a production stack or validate real machinery.

Refs: #222-#230.

## Sources

- [PyTorch checkpoint guidance](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html).
- [Time limits and bootstrapping](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/).
- [Underground-loader RL](https://arxiv.org/abs/2103.01283).
- [Policy invariance under reward transformations](https://people.eecs.berkeley.edu/~russell/papers/icml99-shaping.pdf).

These sources motivate the protocol. Their published performance is not a
measurement of this simplified environment or the current CPU experiment.
