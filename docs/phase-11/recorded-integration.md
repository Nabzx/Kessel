# Recorded experiment integration

Implements #243–#252 under ADRs [0043](../adr/0043-recorded-experiment-viewer.md)
and [0044](../adr/0044-offline-policy-compression-protocol.md).

## What changed

**Explore the world model** now opens a validated recorded-synthetic replay.
The source selector retains the explicitly labelled authored concept replay.
The main Earth/Rwanda/mine journey and illustrative operating figures keep
their existing source and labels. No backend, training process, browser model
inference or model weights are required to present the page.

The recorded example is model-free PPO run `rl-study-v1-full-7`, with separate
raw dynamics forecasts. It does not imply that its policy was trained inside
the learned model. That auxiliary-critic comparison remains a separate measured
experiment. None of these policies has demonstrated a complete learned cycle.

## Real decisions, outcomes and predictions

The exporter executes retained initial/intermediate/final checkpoint weights
on the same seed-100000 reference scenario and independently replays every
recorded action. It never infers learned provenance from a file's existence.
There are 755 decisions and 916 actual saved-model predictions in the bundle.
Native action replay reproduced every exported reference state exactly.
Cross-platform regression tests re-execute policy inference, reference stepping,
member endpoints and multi-step neural forecasts within documented tolerances.

| Checkpoint | Completed training episodes | Recorded decisions | Complete-task outcome |
| --- | ---: | ---: | --- |
| Initial | 0 | 116 | Wall collision; no delivery |
| Intermediate | 897 | 600 | Time limit; no delivery |
| Final | 1,479 | 39 | Wall collision; no delivery |

The selected training run executed 309,248 real simulator decisions and 9,606
optimiser minibatch updates in 120.05 seconds. Its recorded training curve
includes curriculum and shaping; the separate replay step reward uses the
versioned delivery objective. Those values have distinct labels. Counts are
actual checkpoint counters, not invented intermediate episodes.

The browser shows the current local height crop/validity, outgoing normalised
actuator commands, actual weighted reward contributions and checkpoint hash.
Physical positions use metres, angles radians and material kilograms.
Three.js maps x-forward/y-left/z-up to `(x,z,-y)`. Reversing preserves chassis
heading. Wheel angles, articulation, pile heights and material counters come
from records. The visual bucket centre follows the reference contact point;
its native checked error was below 1e-7 m. The original mesh remains a visual
proxy, not a manufacturer twin.

Forecast inspection offers 1/2/4/8 decision offsets at retained anchors. The
independent reference future and raw neural future share the same target
reference decision/timestamp. Predicted clock error remains in the residual
rather than redefining the target. Position error is metres; disagreement is a
dimensionless ensemble score. The spatial envelope derives from actual final-
step conditional member endpoints. It is neither calibrated confidence nor
cumulative horizon covariance. Raw impossible states stay flagged; model stops
and unsupported horizons remain missing. No synthetic error offsets are drawn.

## Bundle, clocks and source handling

`data/experiments/index.json` contains the run id, byte count and SHA-256.
Only world-model entry fetches the needed bundle. Python and browser validators
check version, units, finite values, state/action shapes, monotone times,
checkpoint/model identities, counter consistency and prediction residuals.
Corruption or a missing bundle produces a visible error. An authored replay
requires an explicit source choice and its own caption.

The bundle is 4,984,632 bytes, or 1,089,332 bytes with gzip in the acquisition
check. The local static server transfers the ordinary JSON; hosting compression
is a separate serving concern. Every decision, contact, transfer and terminal
boundary remains. Decimation error is zero at retained decision boundaries;
interpolated display poses are not extra simulator samples. Piles, observations,
actions, rewards and events stay at actual recorded boundaries.

One animation-frame clock owns a twelve-second default sequence, configurable
pacing, pause, replay, inspection and scrubbing. Each checkpoint retains a short
terminal hold. The UI shows simulated time and actual configured playback
acceleration; training wall time and nominal aggregate training simulation time
remain separate in run details. Reduced motion starts paused. No duplicate
intervals or independent animation timers drive the replay.

Return restores the original mine comparison, camera, product scroll and
keyboard focus. Source switching preserves that entry context. The permanent
concept caption stays; authored costs, throughput and savings never acquire a
measured-experiment label.

## Actual append-only telemetry

New training transactions append a hash-chained `events.jsonl` stream linking
source, configuration, real counters, actual optimiser/reward statistics, wall
time and checkpoint hashes. Resume verifies the existing chain and refuses to
append to a log ahead of its resumed checkpoint. The audit command reconciles
transaction sizes, optimiser updates, final counters and saved checkpoint state.

The retained native proof executes two rollouts, 1,024 environment decisions,
32 optimiser updates and five completed curriculum subtask episodes. Full-task
successes remain zero. See [the audit](recorded-telemetry.json) and
[unaltered event stream](recorded-telemetry-events.jsonl). Earlier studies retain
their genuine full curves/outcomes; no append-only stream is fabricated after
the fact. Raw world-model validation/error evidence remains in the linked
[world-model study](world-model-experiments.md).

## Offline CPU export and compression

The frozen final seed-7 teacher exports an actor-only ONNX graph with embedded
physical scaling, feature clipping and tanh-bounded actuator outputs. The
standalone runtime uses NumPy and ONNX Runtime CPU, one thread, with telemetry
disabled before runtime initialisation. It needs no PyTorch or network service.
The package includes hashes, input layout, action units and synthetic request
rate mapping. It does not contain a real-machine control interface.

One 16-unit student imitates the unchanged 32-unit teacher on 8,192 training
observations, with 2,048 validation observations and no test feedback. The fixed
60-epoch, 1,920-update study selects epoch 60, validation action MSE 0.0001501,
in 1.14 seconds. This is distillation, separate from numerical quantisation.
Three actor matrices are genuinely quantised in each dynamic-int8 variant.

Native Apple M1, Python 3.12.14, NumPy 2.5.4, PyTorch 2.15.0, ONNX 1.23.2 and
ONNX Runtime 1.31.1, CPUExecutionProvider, one thread. Warm latency uses 50
warm-ups and 500 batch-one calls with raw observations/preprocessing included.

| Variant | Bytes | Warm median, µs | Warm p95, µs | Max nominal action error | Max boundary action error |
| --- | ---: | ---: | ---: | ---: | ---: |
| PyTorch teacher actor | 16,781 | 88.58 | 93.04 | 0 | 0 |
| ONNX teacher float32 | 14,306 | 25.29 | 26.29 | 0.000000435 | 0.000000119 |
| ONNX teacher int8 | 6,825 | 28.79 | 30.13 | 0.03934 | 0.00710 |
| ONNX student float32 | 6,686 | 24.58 | 25.63 | 0.11258 | 0.21349 |
| ONNX student int8 | 4,819 | 28.79 | 30.04 | 0.10778 | 0.20552 |

Sizes compare actor-only artefacts; the original actor-plus-critic research
checkpoint is separately retained. Maximum errors use normalised action units.
The float32 teacher's median new-session creation is 0.778 ms and first
inference 0.056 ms, over five fresh sessions. Libraries are already imported
and OS caches are not flushed. These are local inference measurements, not
cold process startup, sensor-to-actuator latency or hard real-time guarantees.

All five variants execute identical fresh standard/low-grip/occluded/blocked
scenes, four cases per family, test seeds 206600–206603. All achieve 0/16 full
cycles and deliver zero material. Every case's timing, payload, failure and
effort metrics are retained. Matching zero successes cannot validate useful
loading preservation. No unsupported operators occurred in this measured set.

**Recommendation:** retain float32 teacher ONNX as the fidelity reference.
Int8 is smaller but slower here and less accurate; the student introduces
larger action errors. Neither establishes a deployment format or useful task
performance. The whole final comparison took 6.98 seconds. A preliminary
runtime acquisition was repeated after disabling all runtime telemetry; it
remains in ignored local runs and did not tune the fixed student protocol.
There is no Jetson or TensorRT measurement.

[Standalone package and full evidence](offline-policy-evidence/README.md).
The prototype and measured recommendation are available for maintainer judgement;
this report does not assume human acceptance.

## Verification and reproduction

Native browser evidence: [machine-readable report](recorded-browser.json),
[inspection image](recorded-inspection.jpg) and
[terminal image](recorded-terminal.jpg). It covers integrity/progressive loading,
actual readouts, four horizons, single-clock playback, explicit source changes,
return context/focus, reduced motion, corrupted data and local-only requests.
The isolated static package contains 65 files, 18,539,218 bytes, with no Python
tooling or research weights. Recorded-view samples were approximately 60 fps
on native M1 Chrome/ANGLE Metal; p95 frame times were about 16.8 ms. This
qualifies these sampled viewer states, not the remaining Phase 11 presentation.
Parsed-bundle heap growth was about 7.6 MB in a minimal same-origin Chrome page
with explicit GC; it is one retained-heap sample, not peak process memory.
The measured complete default replay took approximately 12.01 seconds.

122 Python tests, four pure-adapter tests, all evidence checks and the existing
cinematic/network/asset/reference-preparation checks pass. GitHub repeats the
static and locked CPU checks. Native browser QA uses:

```sh
PLAYWRIGHT_MODULE=/path/to/playwright node scripts/verify-recorded.cjs
```

Use `KESSEL_URL` and `KESSEL_RECORDED_QA` to choose a static-package server and
new evidence directory. The JSON report records source hashes and native GPU
identity. Browser screenshots/video remain optional local QA artefacts;
maintainer visual acceptance and full Phase 11 release remain separate.

From `training/`, regenerate from retained executable evidence with new paths:

```sh
uv run --locked python -m kessel_training.export_viewer --output ../data/experiments/loader-new.json --report ../docs/phase-11/viewer-export-new.json
uv run --locked python -m kessel_training.audit_run runs/quick-example
uv run --locked --all-groups python -m kessel_training.offline_experiment --datasets runs/world-model-study-new/datasets --output runs/offline-policy-new
```

The compression corpus comes from the declared world-model data collector.
Only training/validation observations supervise the student. Both exporter and
compression study require committed training sources. SHA-256 catalogue and
artefact files make edits detectable. Packaging/verifier commands live under
`scripts/`; the browser has no dependency on those tools.

Primary references: [pinned Three.js r160](https://github.com/mrdoob/three.js/tree/r160),
[ONNX operators/helpers](https://onnx.ai/onnx/api/helper.html),
[ONNX Runtime quantisation](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html),
[CPU sessions](https://onnxruntime.ai/docs/api/python/api_summary.html) and
[telemetry controls](https://github.com/microsoft/onnxruntime/blob/main/docs/Privacy.md).
