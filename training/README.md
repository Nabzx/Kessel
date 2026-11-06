# CPU experiment tools

These tools are separate from the static investor experience. No policy or
world model is trained by the current page. See ADRs 0031-0034 and the
[interface contract](contracts/README.md).

Use Python 3.12 and uv 0.12.18 or later. The lock file supports Apple Silicon
macOS and x86-64 Linux. Linux resolves PyTorch from its official CPU index;
no CUDA environment is installed. All experiment commands use CPU explicitly.

The synthetic loader kernel and conventional controller now have a
[reference report](../docs/phase-11/simulator-reference.md). They are distinct
from the disposable benchmark and do not constitute a trained RL policy.
The [policy and PPO core](../docs/phase-11/ppo-core.md) provides bounded actions,
correct episode bootstrapping and versioned reward decomposition. Its smoke
command checks optimiser execution; it does not claim task improvement.

From this directory:

```sh
uv sync --locked
uv run --locked pytest
uv run --locked python -m kessel_training.benchmark --output runs/cpu-spike.json
uv run --locked python -m kessel_training.evaluate --split validation --count 4 --output runs/reference-validation.json
uv run --locked python -m kessel_training.profile --output runs/kernel-profile.json
uv run --locked python -m kessel_training.core_smoke --output runs/ppo-core-smoke.json
uv run --locked python -m kessel_training.train --preset quick --output runs/quick-example
```

The trainer saves initial, periodic and final checkpoints, complete simulator/
sensor state and all RNGs. To stop at a reproducible boundary, add
`--until-update 20`, then resume with
`--resume runs/quick-example/checkpoint-000020-final.pt --output runs/quick-example`.
Resume requires the same training source package, numerical library versions
and recorded configuration. `--preset full` selects the provisional larger
budget. The [completed RL study](../docs/phase-11/rl-experiments.md) selects a
32-unit Compact network with 16 environments and 32-step rollouts. Quick targets
40,960 decisions within 30 seconds; full targets 262,144 within 120 seconds.
The study achieved no complete learned delivery cycle. These are workload
presets for further research, not a proficiency guarantee.
Wall limits are cumulative and checked between complete rollout/update
transactions. SIGINT/SIGTERM request a checkpointed stop at the next boundary.
Reports count completed episodes, decisions and optimiser steps separately;
`nominal_simulated_s` is the sum of configured decision periods, including
partially terminated decisions, rather than a claim of exact integrated time.

Run the predeclared comparison with
`uv run --locked python -m kessel_training.study --output runs/rl-study-new`.
It needs a clean committed training tree and refuses an existing output. The
recorded study source, seed/configuration plan, every outcome, learning curves
and executable checkpoint exports are documented in the linked report.

The [world-model experiments](../docs/phase-11/world-model-experiments.md) add
leak-free transition collection, a saved single network/three-member ensemble,
physical-unit errors, uncertainty calibration, short imagined branches and a
resumable experimental auxiliary critic. Run both declared protocols with new
output directories:

```sh
uv run --locked python -m kessel_training.wm_experiment --output runs/world-model-study-new
uv run --locked python -m kessel_training.wm_filter_experiment --source runs/world-model-study-new --output runs/world-model-filter-new
```

The second command reuses frozen weights and training/validation data, applies
an explicitly identified bounded physical filter and acquires fresh test/OOD
scenes. Raw neural failures remain separate. The completed experiments show no
full learned cycle or sample-efficiency gain; do not enable assistance as a
proven improvement. Saved-model prediction replay and evidence accounting run
in the test suite. Compact reports and executable research weights stay under
`docs/phase-11/`, outside the static package.

Recorded playback and the isolated CPU export comparison are documented in
[the integration report](../docs/phase-11/recorded-integration.md). The browser
loads no model weights or training runtime. Recreate the static bundle from
retained executable checkpoint artefacts, then validate it from the repo root:

```sh
uv run --locked python -m kessel_training.export_viewer --output ../data/experiments/loader-new.json --report ../docs/phase-11/viewer-export-new.json
```

Use `uv sync --locked --all-groups` for optional CPU ONNX tools and their tests.
The declared compression study requires the regenerated world-model corpus:

```sh
uv run --locked --all-groups python -m kessel_training.offline_experiment --datasets runs/world-model-study-new/datasets --output runs/offline-policy-new
uv run --locked python -m kessel_training.audit_run runs/quick-example
```

New training runs append hash-chained `events.jsonl` records from actual
transactions. Resume verifies log/checkpoint counters and rejects a log ahead
of the resumed state. Older retained studies keep their genuine curves and
outcomes; no append-only stream is fabricated retrospectively. Distillation
and numerical quantisation are separate experiments. Runtime telemetry is
disabled before ONNX Runtime initialises. No NVIDIA result is implied.

The project creates its own ignored `training/.venv`. It does not touch a
repository-root `.venv` or another personal environment. To use a separate
temporary environment, set `UV_PROJECT_ENVIRONMENT` to a task-specific path.
Keep generated runs in `training/runs/`, checkpoints in `training/checkpoints/`
and source archives in `training/raw/`; all are ignored. Commit only compact
reviewed reports or validated viewer exports in their intended locations.

`uv lock --upgrade-package <name>` updates a dependency deliberately; rerun
tests and compare the numerical/benchmark effects before accepting an update.
Dependabot covers this uv manifest and GitHub Actions. Vendored Three.js files
remain governed by their explicit version/update procedure. Dependabot changes
are reviewed and re-landed under the maintainer as CONTRIBUTING.md requires.

The benchmark compares 1/16/32/64 environments and a small real PyTorch
gradient workload. It is a disposable feasibility spike, not PPO, a trained
controller or the final loader simulator. Primitive decisions advance ten
times as much physical time as control decisions, so compare physical substeps
as well as decisions/second. It reports actual episode, step and update counts,
wall time, versions, source identity and cumulative process peak RSS.

## Static presentation package

From the repository root, choose a new output directory:

```sh
python3 scripts/package-static.py --output /private/tmp/kessel-static-demo
```

Serve that directory with `python3 -m http.server 8080 --bind 127.0.0.1`.
The package contains only the static entry point, scene code/data, supported
assets and their notices. It does not include Python tools, environments,
raw scans, unexported weights or Git metadata. No deployment is performed.
