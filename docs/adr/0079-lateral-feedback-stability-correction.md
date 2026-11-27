# ADR-0079: Lateral-feedback stability correction

Status: Accepted as a specific correction within ADR-0078's unconsumed budget.

Six development revisions complete 21/22 delivery cases and all four expected
stops in the final two-base rehearsal. Low-grip base 19021 still times out.
Its traction-aware entry reaches excessive yaw and lateral displacement, taking
the bucket outside useful coverage. No validation case has been queried.

The damped articulation controller's heading gain is 0.8, but its effective
lateral gain near zero is 0.32 from `atan(0.4*error)`. Linearising the frozen
kinematics shows insufficient damping near the 1.2 m/s commanded approach speed.
Keep direction-aware steering; compare `atan(0.15*error)` and `atan(0.10*error)`
as two fixed corrections after a kinematic convergence test. Change no other
task threshold, input, material criterion, stopping rule or physics.

This supersedes only the six-revision count with eight. Both corrections share
the original 40,000-decision/teacher and 300-second cumulative development caps;
prior costs are deducted, never reset. Retain all old runs/source capsules.
Select by complete collision-free delivery plus declared stop successes on
19020/19021, then fewer collisions; ties favour 0.15. Freeze the selected source
and parameter before 19022 validation. No tuning on validation or fresh cases.
