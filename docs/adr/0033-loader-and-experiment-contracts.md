# ADR-0033: Loader and experiment contracts

Status: Accepted

## Decision

Use SI units and a right-handed physical frame: x forward at zero yaw, y left,
z up. Positive yaw turns towards positive y. Three.js coordinates are
`(x, z, -y)`; convert directions and orientations through the same basis.
Velocity is signed: reversing does not turn the chassis around.

The initial loader uses the reference 7.1 x 1.5 x 1.9 m envelope and 3,500 kg
payload capacity. These are scenario inputs, not a validated manufacturer twin.
Four normalised actions in [-1, 1] command longitudinal acceleration,
articulation rate, boom rate and bucket-curl rate. Commands outside the range,
wrong shapes and non-finite values are rejected, not silently clipped.

Default decisions are 0.1 simulated seconds with five 0.02-second physical
substeps. Clamp resulting actuator states to the configured physical limits.
Separate true simulator state from noisy/local policy observations. Reward
components retain physical units before configured weights turn them into a
dimensionless sum: delivered kg, elapsed s, effort proxy J, spilled kg,
collision count and slip duration s. Effort remains an uncalibrated proxy until
the traction/force model exists. A success/failure is termination; a time limit
is truncation. Never reset a finished environment silently inside `step`.

## Experiment export

Use schema version `1.0` and source mode `authored` or `recorded_synthetic`.
The run manifest contains run id, UTC start, source commit, dirty-source flag,
configuration hash and complete configuration, simulator id/version, seed,
dataset split identity, controller type, checkpoint hash where applicable,
software versions, hardware identity and actual counters. An untrained/random
or reference controller is not labelled a learned policy. A learned controller
requires the hash of executed weights. A model prediction requires its own
weights hash, horizon and actual reference target.

Episodes contain an id, seed, outcome, terminated/truncated flags, summary
metrics and strictly increasing timestamped records. Each record separates
privileged state, observed state, the action applied next, reward components
and optional prediction/reference pairs. Terminal records have no next action.
Represent absent predictions as null or omit the optional field. Use finite
JSON numbers, explicit units and an asset/bundle hash. Do not fill gaps with
synthetic predictions under a recorded label.

Counters distinguish completed episodes, environment steps, agent decisions,
optimiser updates and imagined transitions. Record simulated seconds and
training wall seconds separately. Playback rate is viewer metadata and does
not change either counter. The current `data/experience.json` is untouched;
an adapter and bundle validation must land before the viewer consumes exports.

## Consequences

The contract and its examples live in `training/contracts/`. Initial executable
assertions cover units, frame conversion and action bounds; later bundle
validation owns episode/prediction consistency. Changing schema semantics
requires another ADR and version change. The first CPU spike may use a smaller
state, explicitly labelled as a disposable benchmark rather than an episode
bundle or learned policy.

Refs: #204, #205. Sources:
[time-limit handling](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/),
[underground loader control](https://arxiv.org/abs/2103.01283).
