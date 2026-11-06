# ADR-0040: World-model prototype and evaluation

Status: Accepted

## Decision

Implement an action-conditioned CPU dynamics ensemble independently of the
reference simulator and policy. Audit Selene's pinned five-MLP example, but
replace its lunar features, categorical actions and row-level splitting with
the loader's continuous controls, explicit physical state and episode splits.
Use three independently initialised, episode-bootstrapped 128-unit MLPs and a
single-model comparison. Learn residual state/pile changes, raw reward and
separate terminal/truncation/contact/collision logits. Save weights, train-only
normalisers, bootstrap identities, raw epoch losses and configuration hashes.
Do not add an aleatoric-distribution or calibrated-probability claim.

Collect complete state/action/next-state tuples under reference, random and
executed learned policies. Keep per-episode source, seed, initial-pile identity,
observations, reward terms, physical timestep and outcomes. Training, validation
and test use disjoint episode/seed/pile sets. Named OOD families are separate.
Prepared contact fixtures are labelled reset conditions, not learned loading.
Raw buffers remain outside the static package.

Fit normalisation only on training data, with explicit constant-feature handling
and physical floors for target scales. Compare persistence, a simple documented
kinematic predictor, a single model and the ensemble. Report component errors in
physical units, material/contact regimes, mass-balance/joint violations and
event errors. Diagnostic open-loop drift uses fixed recorded actions at 1/2/4/8
decisions and never crosses reference episode boundaries. Best-so-far curves
cannot replace raw current error.

Calibrate disagreement thresholds only on validation data and publish coverage,
missed high-error cases and OOD behaviour. Ensemble disagreement is a dimensionless
normalised score, not distance error or a calibrated confidence probability.
Imagination proposes at most two steps from training-only reference states and
stops on uncertainty, terminal events, invalid state or unsupported inputs.
Publish raw physical violations; do not silently clip impossible outputs into
valid predictions. Validation may support no usable imagination horizon.

Prototype model assistance as an auxiliary critic target, not PPO likelihood
updates on arbitrary imagined replay. Sample current-policy actions inside short
frozen-model rollouts and regress V(real anchor observation) towards discounted
predicted rewards plus final predicted-observation value. Actor gradients still
come only from real on-policy PPO batches. Bound anchors to at most 25% of real
rollout size, horizon to two, auxiliary coefficient to 0.1 and cadence to every
four rollouts. Keep auxiliary RNG independent and record accepted/rejected
branches, imaginary transitions and actual critic updates. Synthetic future
observations are idealised local projections, not a learned perception model.

For a controlled comparison, use complete-task delivery-v1 rewards without
curriculum/shaping, since the dynamics model does not predict subtask bonuses.
Re-run a fixed model-free control with identical network, scenes and seeds.
Charge model-assisted training for its train/validation corpus collection:
10,240 offline reference transitions plus 30,720 policy transitions versus
40,960 on-policy transitions for model-free. Report policy interaction and
pretraining collection separately, and include dataset/model/gate training cost
in compute totals. This is a complete-method sample-budget comparison, not an
isolated estimate of the auxiliary loss. The earlier curriculum study remains
a separate result and is not an equal-budget comparator.

Freeze the machine-readable budget before collecting/training: train/validation/
test datasets of 8,192/2,048/2,048 transitions; reference/random/policy proportions
one-half/one-quarter/one-quarter; six 1,024-transition OOD datasets. Train single
and three-member models for at most 30 epochs. Compare policy seeds 7/19/43 under
equal 40,960-total-reference-sample targets, with a 120-second per-policy cap.
Report all model, data and evaluation costs, capped runs and negative results.
No default concept-viewer switch or operational recommendation follows merely
from the existence of model weights.

Export real model predictions from identified saved weights alongside reference
targets, horizons, residuals, units and uncertainty method. Recompute residuals
in verification. Missing/terminated horizons are explicitly absent. Keep
recorded prediction examples available for later viewer integration, not a
fabricated curve or copied future reference state.

Refs: #231-#242.

## Sources

- [Selene ensemble, pinned source](https://github.com/Nabzx/selene3.1/blob/647ce1e8acf665435815576db30d38ca522240e1/apps/sim/selene_sim/world_model.py).
- [World Modeling for Autonomous Wheel Loaders](https://arxiv.org/abs/2309.12016).
- [PETS](https://arxiv.org/abs/1805.12114).
- [When to Trust Your Model](https://arxiv.org/abs/1906.08253).

The published algorithms motivate a bounded prototype. Their accuracy, speed
and sample-efficiency figures are not results for this loader environment.
