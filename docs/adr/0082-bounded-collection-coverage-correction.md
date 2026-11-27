# ADR-0082: Bounded collection coverage and return timing

Status: Accepted for the remaining collection miss. Adds a separate task variant;
all frozen controllers, studies and services remain unchanged.

The base-19023 low-pile trace ends with 1,994 kg carried and no delivery. Two
long reversing manoeuvres and overlapping cuts consume the sixty-second task.
The earlier base-19021 low-grip miss remains development evidence. Do not lower
the 2,000 kg delivery criterion, reset physics or extend the 600-decision limit.

Use the observation-only progress task and unchanged clearance/brake composition.
During forward approach/collection, steer using observed bucket-mouth lateral
position, computed from existing odometry and joint observations. Reverse uses
the existing rear-frame feedback. Compare exactly two declared variants: lane
spacing 1.35 m with 3 m reverse clearance, and 1.6 m with 2.5 m reverse clearance.
Keep all other thresholds, sweep timings and feedback gains unchanged. Retain
actual commands, features, method source and all unsuccessful trajectories.

Development uses nominal, low, low_grip and start_offset on 19020/19021, plus
low on consumed base 19023: nine cases per variant. Select most passed
criteria, then least collisions, then first variant. Freeze selection before
base 19024. Compare conventional and the retained fitted linear actuator over all
thirteen families plus recovery, carry loss and stale/old/missing clearance.
Every learned command must come from the saved six-gain network; planning and
braking remain conventional. No new weight fitting or learning benefit claim.

Cap combined development and final comparison at 24,000 physical/planning steps,
18,000 independent replay steps and 300 seconds, one CPU thread. No adaptive third
variant or final-driven refit. Recheck the consumed low-pile failure explicitly.
A complete failed comparison remains a failed gate. Passing practice is not fresh
qualification, field validation or permission to replace the existing runtime.
No browser, listening service or deployment is part of this study.
