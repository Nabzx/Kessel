# Retrofit, observations and offline recording

Refs #408, #417, #418 and #419. Recommendation: proposed ADR-0059.
Evidence: [bounded audit](../phase-11/demo-frontier-evidence/report.json),
`environment.py`, `followup_data.py`, `telemetry.py` and
`data/retrofit-showcase.json`. No hardware was purchased, installed or tested.

## Hardware story and first integration boundary: #408

Keep the implemented assembled/exploded/signal views. Explain each component
through its contribution to the same loader task rather than adding another
manufactured-looking assembly. The current model already has seven inspectors.

| Existing inspector | Explain its role | Current evidence or gap |
| --- | --- | --- |
| Range sensing | Supply nearby geometry before a bucket action | Simulated height crop exists; raw range processing is absent |
| Stereo vision | Proposed additional visual context | Images are not inputs to the existing 65-feature policy |
| Compute | Estimate observations and evaluate the policy locally | CPU policy exports exist; depicted edge hardware is proposed |
| Vehicle I/O | Separate observations, proposed actions and applied commands | Policy actions are normalised simulator commands, not validated machine I/O |
| Power | Supply sensors and compute | Electrical layout is illustrative; no qualified power design |
| Chassis | Mount and service the assembly | Authored geometry; no machine mounting validation |
| Thermal path | Remove heat from the compute package | Geometry and intended path, no measured thermal performance |

Recommend observation-only ingestion/recording as the first hardware interface
boundary. Shadow inference can follow without applying commands. Active vehicle
control is a later integration with its own command, supervision and stopping
contracts. This is an engineering sequence, not a decision that the first
commercial product is a sensor logger or a claim of a ready retrofit kit.

## Minimum observation contract: #417

The existing actor consumes exactly 65 features. Keep their identities and
units explicit before proposing real sensor feeds.

| Fields | Units | Intended source and unresolved assumption |
| --- | --- | --- |
| Odometry x/y, heading sine/cosine | m, dimensionless | Local state estimator; no drift/calibration evidence |
| Speed, articulation, boom, bucket | m/s, rad | Vehicle estimates/encoders; machine interfaces not selected |
| Load | kg | Payload estimate; current simulator supplies it directly |
| Receiver forward/left displacement | m | Preloaded target map transformed into the chassis frame |
| Range age, fresh flag | s, boolean | Capture-to-use timing; do not infer freshness from connectivity |
| Elapsed time, slip ratio | s, dimensionless | Local episode clock and estimate; episode reset must be explicit |
| 5 × 5 local heights and validity mask | m, boolean | Bucket-frame sample grid, not raw images or a complete occupancy map |

Physical coordinates use the existing planar frame and metre/radian contract.
Grid locations follow the front-frame heading: longitudinal offsets -0.75 to
2.25 m and lateral offsets -1.5 to 1.5 m from the bucket mouth, at 0.75 m spacing.
Heights use the reference ground datum. A real feed needs time-aligned pose,
joint angles and calibrated sensor-to-machine transforms to construct that grid.

Specify per-channel capture and delivery times, local clock identity, sequence
number, sensor identity, units, coordinate frame, calibration version and mask.
Missing values must not masquerade as measured zero heights. No full-pile mass,
future state, hidden friction or simulator obstacle box enters the onboard actor.
The audit retains the existing observable/privileged inventory separately.

## Sensor impairment diagnostic: #418

The committed tool executes nine fixed-action rollouts, two slots × 32 steps,
576 reference decisions total. It compares clean, two-step delay, impaired and
complete-dropout profiles with communications both available and unavailable.

| Profile | Valid samples / 1,600 | Maximum age |
| --- | ---: | ---: |
| Clean | 1,600 | 0 s |
| Two-decision delay | 1,550 | 0.2 s |
| Delay + 25% dropout + 15% occlusion + 0.01 m noise | 993 | 0.4 s |
| Complete dropout | 0 | 3.2 s |

All physical states match the clean fixed-action rollout exactly. Changing only
communications changes neither states nor observations. This verifies wrapper
separation, not closed-loop policy robustness: a policy reacting to degraded
observations could choose different actions. The perturbations are declared
synthetic probes, not measured mine sensor distributions or calibrated bounds.

Next compare per-channel latency, clock-offset error, transform error and joint
timing independently, then selected combinations. Derive each case from a stated
input/transform hypothesis; freeze scenarios and report missing-data recovery.
Do not add random noise to unrelated state fields and call it perception.

## Offline log proposal: #419

The current EventLog is an append-only training transaction chain. It checks
counter/source continuity and rejects incompatible resume. It is not a bounded,
durable multi-sensor machine recorder: it lacks per-channel capture clocks,
calibration epochs, storage quotas and a power-loss persistence contract.

Propose separate observation, policy-proposal and applied-command streams with
run/clock/sequence identities, timestamps, configuration/calibration hashes,
validity and append-chain checks. Observation-only mode has no applied-command
stream. A replay may verify a proposal against its checkpoint, but cannot invent
evidence that a machine applied it. Record dropped sequences and storage loss.

At the current 10 Hz decision interval, 65 observations plus four actions as
float64 are 552 bytes per decision, about 19.9 MB/hour before metadata, checksums
or encoding. This excludes raw images/range returns, which need separate bounded
storage measurement. Benchmark actual framing, persistence and export costs
before selecting quotas. Do not silently delete unexported data.

Required prototype checks: mixed-rate timestamp alignment, masked missing
samples, calibration change, restart after an incomplete final record, quota
exhaustion, duplicate/gapped sequences and replay with the wrong checkpoint.
Keep local recording independent of network synchronisation. Zero policy
commands are not a parking brake in the simulator; do not invent a stopping
guarantee from a missing-data convention.

## Follow-on specifications

1. Versioned numeric observation adapter and calibration/frame validation.
2. Bounded local log writer and replay reader with explicit loss/restart tests.
3. Shadow-policy proposal stream and comparison with actual recorded actions.
4. Hardware-specific integration only after concrete interfaces are selected.

The [draft contract](demo-contracts/observation-record.json) describes the
required fields. It is a research proposal, not implemented acquisition software.
