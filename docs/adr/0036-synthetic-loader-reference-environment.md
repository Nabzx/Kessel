# ADR-0036: Synthetic loader reference environment

Status: Accepted

## Decision

Implement a CPU NumPy reference environment independently of the disposable
benchmark. Follow ADR-0033's physical frame and four rate/acceleration controls.
The pose reference is the rear axle; its chassis heading is not reversed when
velocity is negative. The articulation joint is 1.8 m ahead of that axle and
the front axle 1.6 m beyond the joint. These and all force/material parameters
are explicit synthetic scenario choices, not a calibrated manufacturer model.

For rear speed v, articulation d and articulation rate dd, use the no-lateral-
slip constraint `yaw_rate = (v*sin(d)-1.6*dd)/(1.8*cos(d)+1.6)`.
Derive front heading, wheel contact positions and signed wheel rotation from
this same state. Export front-facing light direction independently of signed
travel. Boom and curl are rate-limited joints, with a geometric bucket mouth.

Represent the pile as an 8 x 8 height field with 0.5 m cells and explicit bulk
density. Bucket extraction is a cell-centre footprint approximation, bounded
by local available height, cavity depth, fill rate and remaining capacity.
It is not a granular/contact solver. Material moves only through a ledger:
pile, bucket, spilled and delivered kg. Delivery requires the bucket mouth in
the receiver; spilling elsewhere cannot count as delivered ore.

Use bounded engine force/power, traction, rolling/grade resistance and a
documented pile-resistance approximation. A blocked chassis cannot pass through
the pile. These are uncalibrated reference dynamics. Effort is an estimated
force-distance/joint-work proxy, not measured fuel use.

Check the rear body, articulated front and bucket against tunnel bounds and
obstacles. Swept boxes conservatively include motion between substeps, with
angular padding and smaller physical steps for large configured intervals.
This may stop some geometrically clear manoeuvres; it is not a certified
collision/safety system. Record the stop reason and impact-speed proxy.

Seed each environment by master seed, stream id and episode index. Scenario
and observation-noise streams are independent. `reset` explicitly selects
finished slots and `step` never silently resets. Success/collision/stuck are
terminations; the external step limit is truncation. Observations contain local
synthetic odometry/load estimates and a local range crop, with separate cached
noise/dropout state. Privileged geometry and future state remain in diagnostics.

Reserve scenario seed ranges before optimisation: training 0-99,999,
validation 100,000-109,999 and test 200,000-209,999. A conventional controller
and policy use the same observation/action contract and evaluation metrics.
Record failed episodes and measure the finished kernel separately from the
earlier benchmark. No browser behaviour or real-machine claim changes here.

Refs: #207-#218. Research:
[underground loader control](https://arxiv.org/abs/2103.01283),
[pile/world-model representation](https://arxiv.org/abs/2309.12016),
[vector environment semantics](https://gymnasium.farama.org/api/vector/).
