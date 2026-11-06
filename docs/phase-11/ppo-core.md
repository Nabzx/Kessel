# CPU policy and PPO core

This implements #219-#221 under ADR-0037. It adds an executable learning core,
not evidence that a policy has learned to load a machine. The cinematic page
continues to use its existing authored content.

## Networks and observations

Both networks consume only the accepted local observation: 15 proprioceptive
values, 25 local heights and 25 range-validity flags. The actor is
65 -> 64 -> 64 -> 4 with tanh hidden activations and four learned log standard
deviations. It has 8,648 parameters. The independent 65 -> 64 -> 64 -> 1 critic
has 8,449, for 17,097 total float32 parameters. CPU execution defaults to one
PyTorch intra-operation thread, fixed seeds and deterministic algorithms.

The model stores fixed physical-unit scales as state-dictionary buffers.
Proprioceptive scales follow observation order:
`[12,4.2,1,1,2,0.6,1.1,1,3500,20,6,5,1,60,1]`.
Local heights use 1.5 m; validity stays binary. Concatenated features are clipped
to [-5,5]. There is no fitted running normaliser or held-out-data fitting.
Unknown observation keys, incorrect shapes, non-binary validity and non-finite
observations are rejected.

The actor samples a diagonal normal latent `z` and sends `tanh(z)` to the
environment. Log density includes the stable tanh Jacobian. PPO retains `z`,
so it does not invert rounded/saturated actions or evaluate an unclamped normal
density for a clamped control. Deterministic evaluation uses `tanh(mean)` and
consumes no sampling RNG state. Floating-point tanh can round to an endpoint;
the original latent preserves the density calculation.

## Return and update semantics

The collector evaluates the final observation before masked reset. With
`b = 1-terminated` and `c = 1-(terminated or truncated)`:

```text
delta[t] = reward[t] + gamma*b[t]*V(final_next_observation[t]) - V(observation[t])
advantage[t] = delta[t] + gamma*lambda*c[t]*advantage[t+1]
return[t] = advantage[t] + V(observation[t])
```

Truncation retains its final-state bootstrap but breaks the recursive trace.
Termination removes both. Neither crosses into a reset episode. Masks use the
reward dtype explicitly; a hand-calculated float64 case caught implicit
float32 promotion of boolean masks before this implementation was committed.

The update normalises advantages within the collected batch and uses clipped
policy loss, value regression and a fresh transformed-entropy Monte Carlo
estimate. Defaults are gamma 0.995, GAE lambda 0.95, clip 0.2, value weight 0.5,
entropy weight 0.005, Adam learning rate 0.0003, maximum gradient norm 0.5,
four epochs, 128-sample minibatches and a 0.03 approximate-KL stop.

Diagnostics retain each minibatch's loss, value error, entropy estimate, KL,
clip fraction and gradient norms before/after clipping. A KL stop records the
observed stopping value and actual completed updates. Invalid losses, ratios,
gradients or weights abort the update and restore its model, optimiser and
sampling RNG snapshot, including when an earlier optimiser step already ran.

## Reward contract

`delivery-v1` uses incremental physical quantities. Pickup and carried load
earn no material reward. Every step returns raw values, unit labels, scales,
weighted components and configuration hash.

| Raw term | Unit | Default scalar weight |
| --- | --- | --- |
| Delivered mass | kg | +1/3500 |
| Spillage | kg | -1/3500 |
| Elapsed time | s | -0.002 |
| Effort proxy | J proxy | -0.00000003 |
| Collision | count | -5 |
| Integrated slip | s | -0.02 |

The environment's payload capacity sets the default mass scale. Reward
weights can be configured and hashed without changing raw-unit definitions.
Later curriculum stages must record their own configuration/stage changes.
Effort is an uncalibrated proxy, not fuel or measured energy savings.

The [reward audit](ppo-evidence/reward-audit.json) records idle, empty driving,
carrying, collision and partial-delivery fixtures. Idle/driving/carrying cannot
earn positive task reward. The 500 kg partial delivery is credited once;
continued tipping cannot credit it again.

## Verification and measured smoke run

All 64 locked tests pass on native M1. They include transformed-density
agreement with PyTorch, fixed-seed evaluation/sampling, hand-calculated GAE,
final-state bootstrapping, reset boundaries, real gradient updates, KL stopping,
post-mutation rollback and reward accounting.

The [bounded execution report](ppo-evidence/core-smoke.json) records 2,560
environment decisions across four 32-environment, 20-step rollouts. It completed
49 minibatch updates; the KL guard stopped each epoch sequence early. Collection
took 0.473 s and updates 0.138 s. Total workload was 1.65 s excluding Python/
PyTorch import, with 283.20 MiB cumulative peak process RSS. Initial/final model
state hashes differ and source identity is recorded from a clean training tree.

It completed zero episodes and demonstrated zero task successes. This is an
execution check, not a quick-run proficiency result, saved checkpoint or
comparison against the conventional controller. No millions-of-runs figure is
derived from this check. Resumable commands and checkpoints (#222), curriculum,
held-out policy evaluation and useful-learning evidence remain outstanding.

From `training`, choose a new output path:

```sh
uv run --locked pytest -q
uv run --locked python -m kessel_training.core_smoke --output runs/ppo-core-smoke.json
```

CI executes a smaller two-rollout smoke workload alongside the tests. Source
tools and evidence remain outside the static presentation package.
