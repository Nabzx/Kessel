# ADR-0087: Matched one-step forecast assistance comparison

Status: Accepted bounded experiment, not admission of an assisted controller.
Preserves every earlier failed assistance study and original qualified method.

Compare the same frozen learned actuator, conventional planner and independent
stopping guards with shadow-only forecasts versus privileged hybrid candidate
refinement. Both arms predict the same five bounded alternatives at each usable
task decision, with identical per-case caps and no optimiser/teacher-label work.
Shadow-only discards the ranking. Refinement may change collect/sweep/back-out
commands only; no range/clearance/start override may be changed. No rollout is
continued after termination or padded to equalise actual costs.

Candidates are the base action plus +/-0.15 drive or +/-0.15 bucket command,
clipped to the normalised contract. Use the frozen validation uncertainty
threshold and physical-validity/collision checks. Score predicted carried gain
plus twice delivered gain minus five times spilled gain minus 0.0001 times
incremental effort. Require more than 5 kg-equivalent score improvement over the
base before applying a different action; otherwise use the qualified proposal.
The score, candidate set and gate are fixed before evaluation, with no tuning
on results. This is model-assisted action selection, not RL or sample efficiency.

Use consumed practice bases 19020/19021 across nominal, low, ridge, rubble, steep,
start_offset, low_grip, high_resistance, range_impaired and blocked, plus nominal
recovery/carry-loss. Screen both arms by the same existing initial certificate,
retaining every rejected initial case. Run all admitted pairs and preserve failures.
Cap at 30,000 physical decisions, 30,000 independent replay decisions, 300,000
model rows including replay (five candidates plus the standard applied-action shadow per usable decision), 600 s, one CPU thread and 96 MiB evidence. Stop
on an exhausted cap and retain incomplete/failed gates. No seed replacement.

Report all actual neural, forecast and physical costs, success/stop/hold/collision
counts, material, cycle time and effort by pair. Benefit requires no worse paired
criterion success, zero collisions, no degraded stopping and >=10% median cycle
reduction among paired successful deliveries. Otherwise report no demonstrated
benefit. Retain every candidate forecast, ranking, gate, chosen action and exact
independent replay. Changing applied controls creates a new method with no
inherited qualification; do not silently activate it in the live runtime.

Both arms may reuse a candidate prediction for the identical applied action/state.
Cache hits are reported separately and are not charged as new model rows. The
cache never crosses a state/action identity or run. This avoids duplicate shadow
inference without changing candidate coverage or equal per-case allocation.
