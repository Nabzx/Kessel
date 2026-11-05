# Selene 3.1 reuse audit

Issue: #199. Decision: [ADR-0032](../adr/0032-selene-reuse-and-loader-prototype.md).
Inspected commit: `647ce1e8acf665435815576db30d38ca522240e1`.
This is a source audit, not an independently executed Selene benchmark.

## File-level recommendation

| Source file | Useful pattern | Kessel decision |
| --- | --- | --- |
| `apps/sim/selene_sim/env.py` | NumPy batch dimensions, seeded independent environments, recorded transitions | Write a loader kernel with its own state/action contract. Replace ballistic hops, craters, relay windows and mission rewards. |
| `apps/sim/selene_sim/mappo.py`, `MAPPOConfig` | Bounded quick/full runs and small CPU networks | Benchmark the available machine. Do not inherit the quick run's timing or categorical action space. |
| `mappo.py`, `Actor` and `Critic` | Separate actor/value modules and centralised training | Begin with one loader and bounded continuous actions. No multi-agent critic is needed initially. |
| `mappo.py`, `train_mappo` | Rollouts, advantage estimation, PPO clipping, checkpointing and logging | Reuse the structure after checking termination, truncation and continuous-action likelihoods in focused tests. |
| `apps/sim/selene_sim/world_model.py` | Normalised action-conditioned dynamics ensemble, bootstrapping and disagreement | Adapt the approach to loader state and pile change after the model-free baseline. Fit normalisers on training splits only. |
| `mappo.py`, `imagine_rollout` | Short branches stopped on uncertainty and invalid values | Evaluate calibration and drift in the new environment before using imagined samples. |
| `mappo.py`, `export_episodes_json` | Executes the actor before serialising a trajectory | Keep actual policy execution. Replace its visual prediction-offset generation with measured model inference. |
| `apps/sim/scripts/export_demo_bundle.py` | Static bundle organisation and interpolation-friendly records | Do not reuse its canonical authored action sequences as learned progression. |
| `scripts/run_demo_pipeline.sh` | Repeatable command sequence | Do not import LLM orchestration, lunar verification claims or hardcoded success summaries. |

## Evidence corrections

The demo-bundle exporter calls `_resolve_policy_source`, which treats a
non-empty loaded checkpoint dictionary as sufficient for a learned source
label. `_rollout_progression_episodes` then calls `env.step` with fixed action
arrays. That label does not establish that the supplied actor chose the actions.

The actor exporter does execute `actor.act`, but constructs displayed ground
positions using offsets derived from validation loss. Those coordinates are
illustrative, not action-conditioned future predictions in metres.

The training loop logs `current_wm_error` through a running `min`. Kessel must
keep raw current error and best-so-far error as separate named series. Model
normalisation loss must not be converted into metres by an arbitrary factor.

The documented quick configuration is 64 environments, 20 rollout steps and
40 updates: 51,200 environment steps. Its reported 7.04 seconds includes
training work, but does not mean 51,200 complete episodes. These are Selene's
reported results and are not a Kessel performance target or reproduction.

## Licence and dependencies

The pinned [LICENSE](https://github.com/Nabzx/selene3.1/blob/647ce1e8acf665435815576db30d38ca522240e1/LICENSE)
is MIT, copyright 2026 Nabil Shah. Preserve its copyright and permission notice
in any copied or substantially adapted source. The independent loader kernel
does not require copying Selene geometry, data or third-party assets.

Use Python 3.12, NumPy and PyTorch as the initial numerical/training tools,
with pytest for focused checks. Keep versions in the training project's lock
file. A Gymnasium-compatible tuple/batch contract does not require installing
Gymnasium until an adapter needs it. ONNX, CUDA, TensorRT, video models, ROS
and rendering packages are not initial runtime requirements.

## Source links

- [Environment](https://github.com/Nabzx/selene3.1/blob/647ce1e8acf665435815576db30d38ca522240e1/apps/sim/selene_sim/env.py)
- [Trainer and actor exporter](https://github.com/Nabzx/selene3.1/blob/647ce1e8acf665435815576db30d38ca522240e1/apps/sim/selene_sim/mappo.py)
- [Dynamics ensemble](https://github.com/Nabzx/selene3.1/blob/647ce1e8acf665435815576db30d38ca522240e1/apps/sim/selene_sim/world_model.py)
- [Demo exporter](https://github.com/Nabzx/selene3.1/blob/647ce1e8acf665435815576db30d38ca522240e1/apps/sim/scripts/export_demo_bundle.py)
- [Reported quick run](https://github.com/Nabzx/selene3.1/blob/647ce1e8acf665435815576db30d38ca522240e1/docs/runs/run-01-mappo-quick.md)
