# Synthetic loader reference

This implements #207-#218 under ADR-0036. It is separate from the default
cinematic page. No learned controller, granular solver, manufacturer twin or
physical deployment is claimed. The reference controller uses feedback rules;
its trajectories must not be labelled policy inference.

## Geometry and dynamics

Use metres, radians, seconds and kilograms. The rear axle pose is `(x, y, yaw)`
in the physical right-handed frame: x forwards, y left, z up. Negative speed
does not turn the chassis around. The same state derives the articulation,
boom, bucket mouth, wheel centres, signed wheel rotations and front-facing
light direction. The straight envelope is 7.1 x 1.5 x 1.9 m. This implementation
rejects other envelopes and speeds beyond its documented reference range.

The control period defaults to 0.1 s with five physical steps. A larger decision
period increases the substep count to keep physical increments at most 20 ms.
The four bounded controls command acceleration, articulation rate, boom rate
and bucket curl rate. All actuator limits are explicit in `LoaderConfig`.

The synthetic force model uses 10,500 kg dry mass plus payload, 22 kN engine
force, a 28 kW drive-power cap, friction-limited traction, rolling resistance
and an x-axis grade. A local pile-height resistance and front-axle clearance
stop the chassis passing through uncollected material. Static resistance stops
low-speed creep. Slip is the requested force fraction beyond available grip;
integrated slip has seconds as its unit. Effort is a force-distance and joint-
work proxy in joules, including a low-speed hydraulic/drive allowance. These
parameters are uncalibrated choices, not measured machine efficiency or fuel.

The pile is 8 x 8 cells, each 0.5 m square. Its seeded 9-14 tonne initial mass
and 1,600-2,100 kg/m3 density determine non-negative cell heights. Cell `(i,j)`
has centre `origin + ((i+0.5)*0.5, (j+0.5)*0.5)` in physical xy coordinates.
Bucket contact selects cell centres inside a 1.2 x 1.5 m footprint. Available
height above the mouth, a 0.7 m cavity-depth approximation, forward travel/curl,
a 1,200 kg/s fill cap and remaining payload capacity bound extraction.
There is no grain interlocking, fragment dynamics or deformable terrain solver.

Material is tracked as pile, carried, spilled and delivered kg. Their sum must
equal initial mass within absolute 1e-7 kg after every decision. Spillage is
accounted ground material, not a second collectible height field. Tipping
credits delivery only when the mouth lies inside the receiver. Empty or
out-of-zone tipping cannot create delivered ore. Each step exposes transferred
mass, mouth position and per-cell removed kg for later recorded playback.

Swept conservative boxes cover rear body, articulated front and bucket.
Rotational padding includes lever-arm motion. Tunnel bounds, ceiling and
vertical obstacle boxes stop motion and record identity, time and impact speed.
The approximation can stop a geometrically clear path. It does not model
overhangs, bucket teeth or certify continuous collision detection.

## Batch and observation contract

`LoaderEnv(N).step(actions)` accepts finite `(N,4)` controls within [-1,1]. It
returns observation, `(N,)` reward, `(N,)` terminated, `(N,)` truncated and a
diagnostic dictionary. It never autoresets. Reset finished slots with a boolean
mask before stepping again. A seeded reset reproduces the trace; masked reset
leaves other scenario and sensor streams unchanged. Explicit stream ids allow
the same scene to be compared in scalar and batched execution.

| Policy input | Shape | Meaning |
| --- | --- | --- |
| `proprio` | N x 15 | Local synthetic odometry, heading sin/cos, signed speed, three joints, estimated load, receiver displacement in chassis coordinates, crop age/freshness, elapsed time and slip estimate. |
| `local_height_m` | N x 5 x 5 | Mouth-relative local height crop at 0.75 m spacing, in the front-chassis frame. No global pile array. |
| `range_valid` | N x 5 x 5 | Current visible cells. A dropped frame retains the last crop but invalidates its mask and increments age. |

Inputs are cached and returned as copies. Reading twice consumes no random
draws. Noise, occlusion and frame dropout use independent per-slot sensor RNGs;
they do not change scenario generation. Odometry is a synthetic local estimate,
not underground GPS. True geometry, material ledger, realised dynamics and
outcomes are diagnostics rather than policy inputs. No future state is supplied.

Success is at least 2,000 kg delivered in one cycle. Collision and sustained
immobility under a drive demand terminate with their own reasons. The 600-step
external limit truncates; it is not a terminal failure transition for value
bootstrapping. Success/collision/stuck take precedence over simultaneous limits.
Rewards currently combine delivery, spillage, elapsed time, effort and collision
with explicit raw units. #221 will implement and audit the learning reward.

## Scenario and controller protocol

Seed ranges are immutable: training 0-99,999; validation 100,000-109,999; test
200,000-209,999. Standard scenes vary pile position, density, mass, friction,
grade, resistance and tunnel width within documented bounds. `low_grip` and
`occluded` are difficult families; `blocked` is explicitly an expected failure,
not an allegedly solvable scene. Realised settings, initial pile hash and pose
are included in scenario identity.

The reference controller only reads the policy observation dictionary. It
approaches, fills, curls/lifts, reverses to the receiver and tips. The sole
initial tuning change increased its fill timeout from 14 to 22 seconds on
training seeds 0/1; the local range crop sees the pile before physical contact.
The frozen configuration is evaluated unchanged on validation and test seeds.
Every case is reported, including partial deliveries, stuck states and collisions.
Representative traces are the first success and first failure in traversal
order, not the most attractive runs.

## Reproduction

From `training`, using the isolated locked environment:

```sh
uv run --locked pytest -q
uv run --locked python -m kessel_training.evaluate --split validation --count 4 --output runs/reference-validation.json
uv run --locked python -m kessel_training.evaluate --split test --count 4 --output runs/reference-test.json
uv run --locked python -m kessel_training.profile --steps 400 --repeats 3 --output runs/kernel-profile.json
```

Choose new output paths; commands refuse accidental overwrite. Evaluation
includes source package SHA-256, Git identity, configuration hash, scene hashes,
per-case outcomes, step counts, wall time and success/failure traces. Full local
runs remain ignored; compact reviewed evidence is retained beside this report.

The profiling control trace is prepared before timing. Kernel time includes
physical stepping, sensor creation, accounting assertions and diagnostic copies.
Reset and trace-generation time are reported separately. No policy network or
optimiser runs in that benchmark. Counts are control decisions per environment,
not physical substeps or training episodes. Profile outcomes are workload
diagnostics, not a separate controller-efficacy study.

## Recorded M1 results

The frozen package `30c68ed07c648ec7654952d052966d40f9c1b448877e0772ac7cb42ce202c994`
was evaluated from commit `e266c44`, with no training-source changes pending.
The Mac is the available Apple M1 with 16 GiB RAM. These small synthetic sets
establish a reference for later experiments, not real-machine reliability.

| Family | Validation successes | Test successes |
| --- | --- | --- |
| Standard | 4/4 | 4/4 |
| Low grip | 2/4 | 3/4 |
| Occluded | 4/4 | 4/4 |
| Deliberately blocked | 0/4 | 0/4 |
| All cases | 10/16 | 11/16 |

Validation used 4,623 decisions in 18.70 s. Test used 4,321 in 17.73 s.
There were zero policy updates. Low-grip failures include stuck and wall-stop
outcomes; blocked scenes stopped at the obstacle. Per-case operating metrics,
configuration/source hashes and representative traces are in
[`simulator-evidence`](simulator-evidence/manifest.json). The development probes
retain the initial 14-second and 22-second fill-timeout results, explicitly
from their earlier source revisions. They are not held-out evidence.

| Environments | Median decisions per second |
| --- | --- |
| 1 | 250 |
| 16 | 3,518 |
| 32 | 6,486 |
| 64 | 10,976 |

The final profile ran 400 batched calls per trial, three trials per size.
Peak cumulative process RSS was 39.92 MiB; PyTorch was not imported. See the
[raw profile](simulator-evidence/kernel-profile.json). This is substantially
more work per decision than the disposable one-dimensional CPU spike. It is
not valid to reuse that spike's roughly 271,000 control steps/s for this kernel.

The 32-environment quick preset's 25,600 decisions imply about 3.95 seconds of
kernel work; the 64-environment full preset's 819,200 imply about 74.64 seconds.
Retain provisional 30/120-second training-loop caps, but remeasure once PPO is
implemented. Inference, optimisation, resets, checkpointing and export add cost;
these estimates do not promise a completed learning run in those times.

All 48 tests pass on the locked native environment. Scalar versus batched
traces agree within absolute 1e-12, including randomised scenarios and sensors.
The sensor-vectorisation change also matched the saved pre-change trace within
1e-12. Tests cover finite inputs, masked resets, reverse direction, joint limits,
local extraction/capacity, scene accounting, grade/grip, thin obstacle and
articulating bucket sweeps, roof/reverse wall limits, complete success, explicit
failure, truncation, stale sensors and withheld far-away geometry.
