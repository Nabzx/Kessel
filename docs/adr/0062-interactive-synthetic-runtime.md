# ADR-0062: Shift evaluation and local interactive simulation

Status: Accepted for the maintainer's 22 November continuation request.
Refs #408–#412, #417–#422, #428–#431 and #271–#276.

## Decision

Freeze the ADR-0061 selected phase-memory checkpoints. Evaluate all three and
an explicitly conventional reference on eight new base scenarios in thirteen
named families: nominal, low/ridge/rubble/steep piles, receiver farther back,
receiver lateral offset, shifted initial pose, low grip, high resistance,
range dropout, impaired range and a blocked corridor. These are synthetic
stress probes, not measured operating distributions. Keep all failures.

Audit available history and raw/ZIP archives before execution. Reserve test
206200–206207 and calibration 108400–108407 only if the audit passes. Base
scenes and all derived families belong to the same split. Do not tune actors,
change selection, train or reselect against these results. Run all 416 cases,
at most 249,600 decisions. Complete delivery means empty start, at least
2,000 kg delivered, no collision. Report each family and training seed, reference
feasibility separately, and durations for all cases and successful cases.
A shifted-family admission needs at least 7/8 successes and no collision for
each learned seed. Expected blocked failures are not successful deliveries.

Extend the ADR-0031 boundary only for an isolated localhost technical route.
A Python service runs the actual reference simulator and frozen neural actor
one decision at a time. The browser renders returned states and never trains.
Start/reset, pause, step and scenario selection execute new episodes. Label
live synthetic execution separately from historical recorded playback. There
is no reference fallback for a learned source, no arbitrary weight loading,
no vehicle interface, and no public deployment or production-entry change.
Validate bounded inputs, loopback host/origin, request size and run identity.
Serialise mutations; stale clients cannot advance a replacement run.

Implement a proposed numeric observation adapter and bounded durable local
recorder separately from the original training EventLog. Identify capture/use
clocks, frame/calibration, validity, sequence gaps and observation/proposal
streams. Applied machine commands are absent. Refuse quota exhaustion, preserve
unexported records, detect corruption and explicitly recover an incomplete tail.
Demonstrate synthetic timing/degradation only, not hardware qualification.

Evaluate retained privileged/observable learned dynamics against persistence
and kinematic baselines on common new episodes. Use calibration-only residual
thresholds and horizons 1/2/4/8, never crossing reset. Preserve raw errors,
violations, event coverage and failure-class shortfalls. Assistance remains
unqualified if its forecast gate fails; do not run an ostensible assisted
learning treatment with no eligible forecasts or claim training efficiency.

Keep independent simulator accounting/actuation/reward probes and complete-site
functional/performance review distinct from policy generalisation. Retain human
visual acceptance and publication as open decisions. No unattended review can
supply human comprehension evidence or field validation.
