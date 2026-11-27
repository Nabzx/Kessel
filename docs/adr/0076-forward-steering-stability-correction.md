# ADR-0076: Forward-steering stability correction within the remaining budget

Status: Accepted as a correction to the rejected ADR-0074 feasibility prototype.

The completed 208-case study consumes 72,358 environment decisions, 20,377
teacher calls, all 3,000 optimiser updates and 13,411 replay steps in 411.91
seconds. The candidates regress overall and are rejected, with all cases retained.
Do not retune or retrain them against the final outcomes.

The proposed articulated-yaw rate inversion lacks forward articulation damping.
Its positive heading feedback is unstable for forward speed. Restore the
original reference's damped forward articulation target and retain the explicitly
separate reverse law. Keep the original source in place and introduce a distinct
`DampedTaskReference`; this is conventional control, not improved neural weights.
Verify an offset forward trajectory using the frozen kinematics before running.

Use one additional consumed practice base, 19014, across all thirteen families,
with the previously selected 12-second fill timeout. No new fitting or selection.
Retain physical failures, retries, input loss and partial deliveries. Replay all
applied actions independently. Cap this correction at 7,800 physical/teacher
calls and 7,800 replay decisions, one CPU thread and 180 seconds. It spends only
the unconsumed ADR-0074 budget: combined physical <100,000, teacher <30,000,
replay <25,000, updates exactly 3,000 and wall <600 seconds.

No fresh qualification, runtime integration or broad robustness claim follows.
This resolves a diagnosed conventional-controller defect while preserving the
negative neural comparison. Further fitting requires another separately budgeted
decision. No browser, service, new release or publication is involved.
