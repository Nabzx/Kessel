# ADR-0065: Missing-range supervisor pilot

Status: Accepted for the maintainer's repo-local continuation on 24 November 2026.
Extends ADR-0062 for a separately named training-partition experiment only.
The retained failure ranking remains diagnostic evidence, with no admission.

## Observation health and control boundary

Wrap each original frozen phase-memory actor in `missing_range_supervisor`.
Do not combine this pilot with the receiver-frame adapter. Use only the existing
local observation: finite proprioception, binary range validity, finite local
height, freshness and age. Require the single-slot shapes (1,15)/(1,5,5).
Invalid proprioception or malformed inputs raise an error; no stopping claim
is made when speed/time cannot be observed. Do not use grade, hidden geometry,
true payload or the reference controller in the supervisor.

A healthy range sample has freshness 1, age at most 0.2 seconds and at least
20% valid cells. With no previously healthy sample, stop immediately. After
initial health, tolerate up to 0.2 seconds of consecutive unhealthy inputs;
then latch a stop. This grace is an engineered pilot choice, not a hardware
requirement or a calibrated detection time. Healthy empty pile crops remain
healthy; height zero does not mean sensor failure.

During an override, freeze articulation, boom and bucket rate commands at zero.
Drive uses observed speed feedback: proportional gain 2.0, integral gain 1.0,
integral limited to +/-0.45 and conditional integration against saturation.
Clip the command to [-1,1]. Do not change simulator physics or pretend that
this interface has a parking brake. The controller must demonstrate holding
despite the grade in the declared scene; zero command alone is insufficient.

Freeze conventional phase updates while overridden. Pause the actor's task clock
for intervals with an applied override, using a copied proprio input; retain
the real input and both clocks in traces. Recovery requires three consecutive
healthy samples and three consecutive observed speeds within 0.08 m/s. Resume
the existing phase and remaining fill time rather than resetting a loaded actor
to approach. Keep the integral until recovery, then reset it. No observer, planner
or component here is newly learned.

Record the neural proposal on the paused-clock input/frozen phase separately
from applied synthetic controls, including override reason and mode. No fallback
controller or teacher call is allowed. Healthy operation with no fault must
reproduce original actions and phases exactly. This pilot changes no existing
source label, runtime, weights, checkpoint selection or observation schema.

## Frozen bounded pilot

Use practice base 19000 with the existing nominal scene, all three original
neural seeds 7/19/41. Keep the empty start and 2,000 kg delivery criterion.
Inject faults into a copied policy observation, not physical scene state:

- healthy, with no injected faults;
- permanent loss from reset;
- permanent loss in approach, after 1 second;
- permanent loss on first entry to fill, lift and carry respectively;
- one missing frame after 1 second (transient);
- permanent loss for 2 seconds on carry entry, followed by healthy recovery;
- deterministic 40% cell occlusion throughout, with fresh remaining cells.

Phase-triggered faults begin when the unmodified observed phase rule would
enter the named phase, using a separate observation-derived trigger memory.
Do not peek at simulator state to choose when a fault happens. Loss sets
validity/freshness to zero, retains the last range crop and increases range age.
Retain the underlying healthy observation separately. The transient and recovery
cases restore actual simulator observations, not invented healthy data.

This is 27 supervised cases. Include six unsupervised comparators: healthy and
reset loss for each seed. Fixed order, 33 cases, at most 600 decisions each and
19,800 evaluation decisions total. Continue permanent-loss cases through a
three-second hold window after settling, rather than terminating the physics
at the first small velocity. A diagnostic observation-window ending is not an
environment terminal, successful delivery or validated emergency stop.

Use one CPU thread, no GPU, a 180-second total active-run cap including replay,
and a 16 MiB trace-archive cap. Independently replay all 27 supervised physical
traces, at most 16,200 additional decisions; recompute proposals, applied actions,
phase, health state and clock from the logged input, at most 19,800 additional
actor queries for all 33 cases. Preserve every outcome and incomplete case.
Do not expand limits, retune or replace weights after observing results.

Advance the hypothesis only if every supervised permanent-loss case detects the
fault within 0.3 seconds, reaches three consecutive physical speed samples within
0.08 m/s within 2.5 seconds of loss, travels at most 2 m after loss before settling,
then holds for three seconds with physical speed at most 0.10 m/s and path length
at most 0.25 m. Require zero collisions and no simulator termination during the
hold. Report each phase and seed; no pooled override of a failure.

Healthy, transient, partial-occlusion and recovery cases must each complete the
original delivery with zero collisions for every seed. Healthy actions/phases
must match the separate original trace exactly. Recovery must actually override,
resume, and retain phase/task-clock continuity. Check unchanged weights, all
material ledgers and exact independent replay. Count neural queries, overridden
decisions, environment/replay costs and zero teacher/training costs separately.

Freeze protocol, code, checkpoint/source hashes and case plan before the first
pilot query. Retain exact sources and raw observations, neural proposals and
applied actions. This pilot is training-partition evidence only: no held-out
claim, controller admission, runtime promotion, RL gain or field safety claim.
Fresh qualification requires a separate frozen protocol, unused-case audit and
per-seed stopping/recovery/delivery gates. Keep all work in the repo, with local
commits, no browser/service interaction, remote publication or machine connection.
