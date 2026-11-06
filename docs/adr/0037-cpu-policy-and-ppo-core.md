# ADR-0037: CPU policy and PPO core

Status: Accepted

## Decision

Implement a model-free PPO reference on ADR-0036's observation and action
contract before model-assisted training. Both actor and critic read the same
65 local features: 15 proprioceptive values, 25 height samples and 25 validity
flags. Use fixed physical-unit scales and bounded feature clipping, stored as
model buffers. Do not fit normalisation on validation or test data.

Use independent two-layer 64-unit tanh actor and critic networks, a four-value
state-independent log standard deviation, float32 CPU tensors and one PyTorch
intra-operation thread by default. Sample a diagonal normal latent and apply
tanh exactly once to produce the four bounded controls. Store the pre-tanh
latent and calculate its transformed log density with the stable tanh Jacobian.
Never clamp a Gaussian action while evaluating its unclamped density. Use the
actor mean through tanh for deterministic evaluation.

Collect transitions before masked reset. Evaluate the final observation for
time-limit bootstrapping. GAE's value bootstrap is masked only by termination;
its recursive advantage trace is masked by both termination and truncation.
No return or advantage may cross an episode reset. Use clipped policy loss,
value regression, a Monte Carlo transformed-entropy estimate, gradient clipping
and a declared KL stop. Reject non-finite data, losses, gradients and weights;
restore the update's model/optimiser/RNG snapshot on an invalid update.

Version the base delivery reward as `delivery-v1`. Credit only incremental
delivered kg, never pickup or carrying. Retain raw units and weighted components
for delivery, spillage, time, effort, collisions and slip. This adds an explicit
slip penalty to ADR-0036's provisional scalar reward without changing physical
dynamics. Any later curriculum reward must be named and logged separately.

This core does not establish learning improvement or replace the authored
presentation. Resumable experiment commands, curriculum, checkpoint evaluation
and comparative evidence remain subsequent tickets.

Refs: #219, #220, #221.

## Sources

- [PPO paper](https://arxiv.org/abs/1707.06347).
- [PyTorch distributions and tanh transforms](https://docs.pytorch.org/docs/2.9/distributions.html).
  The stable Jacobian was also checked against the locally locked PyTorch source.
- [Gymnasium time-limit handling](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/).
