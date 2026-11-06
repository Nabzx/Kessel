# CPU loading feasibility

Measured 5 November 2026 on Apple M1, 8 physical CPU cores and 16 GiB RAM.
Python 3.12.14, NumPy 2.5.4, PyTorch 2.15.0; CPU only, one PyTorch compute
thread. Source: `5bb41b6f7249ab0281a537673b4e939acee7b7ae`, with clean training
sources. [Raw report](cpu-spike-m1-2026-11-05.json). Issue: #200.

## What ran

The disposable workload models bounded one-dimensional travel, boom/bucket
rates and conservative material bookkeeping. It is not the final loader
environment, PPO, a trained policy or a validated world model. It omits
realistic contact, traction, collision geometry and sensing.

Control decisions advance 0.1 simulated seconds through five substeps.
Authored approach/scoop/retract primitives advance one second through 50
substeps. Their environment steps are not equivalent amounts of physical work.
Each configuration ran 200 decision calls with seeds 42, 43 and 44.

| Environments | Control steps/s, median | Primitive steps/s, median | Control physical substeps/s, median |
| --- | ---: | ---: | ---: |
| 1 | 4,606 | 472 | 23,029 |
| 16 | 73,151 | 8,104 | 365,756 |
| 32 | 151,697 | 15,887 | 758,483 |
| 64 | 271,024 | 31,028 | 1,355,121 |

Across all 24 cases, 135,600 environment steps completed 6,780 time-limited
benchmark episodes. This is not 6,780 successful loading cycles.

The separate 5,512-parameter MLP performed 40 actual Adam gradient updates per
batch setting, 160 updates total. At 32/64 environments, batches of 256 took
about 0.022 seconds for 40 updates. This is a small regression workload on
collected spike transitions, not a complete PPO update or held-out dynamics
result. The single-environment case used batches of 32 and included first-use
optimiser overhead, so it is not a like-for-like optimisation speed comparison.

Workloads took 10.10 seconds in total. Cold PyTorch import took another 13.09
seconds and is reported separately. Peak process RSS reached 321.41 MiB; RSS
is a process-wide high-water mark, not memory allocated by each case.

## Decision

Use the short-control interface for the initial task, because it exposes
physical actuation and failed loading attempts. Preserve the primitive mode
only as a benchmark comparison. Both small batched stepping and compact CPU
gradient work are feasible on the target hardware. The full environment and
policy still need their own throughput, correctness and learning measurements.

Provisional profiling presets for the later trainer:

| Preset | Parallel environments | Rollout steps | Maximum updates | Training-loop wall limit |
| --- | ---: | ---: | ---: | ---: |
| Quick | 32 | 20 | 40 | 30 seconds |
| Full | 64 | 64 | 200 | 120 seconds |

These are bounded starting configurations, not a promise of convergence or
end-to-end runtime. The trainer must stop at the wall limit, log actual updates
and count cold startup separately. Rendering remains outside the training
loop. Reassess after contact, observations and PPO have been implemented.

## Reproduce

From `training/`, with the committed lock file:

```sh
uv run --locked pytest
uv run --locked python -m kessel_training.benchmark --output runs/cpu-spike.json
```

Use a new output path for each report. Keep the raw result when changing
dependencies, thread settings or workload parameters. CI uses `--smoke` to
check execution and counters, never a machine-specific speed threshold.
