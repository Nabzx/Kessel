# Missing-range stopping and recovery pilot

24 November 2026. [ADR-0065](../adr/0065-missing-range-supervisor-pilot.md),
[frozen plan](range-supervisor-evidence/plan.json),
[complete report](range-supervisor-evidence/report.json).

## Result and decision

The conventional supervisor meets all fifteen sustained-loss stopping/holding
criteria on the declared practice scene. Healthy, one-frame loss and recovered
carry cases complete delivery for all three neural seeds. However, all three
partial-occlusion cases fail, including one collision. **The complete pilot gate
fails. Do not advance this version to qualification or the runtime.**

Every case and negative outcome is retained. No threshold, gain, checkpoint or
criterion was changed after the pilot opened. The existing runtime, receiver-
frame method, phase rules, simulator and static walkthrough remain unchanged.

| Case | Seed 7 | Seed 19 | Seed 41 |
| --- | --- | --- | --- |
| Healthy delivery | Success | Success | Success |
| Loss from reset | Stop + hold | Stop + hold | Stop + hold |
| Loss during approach | Stop + hold | Stop + hold | Stop + hold |
| Loss on fill entry | Stop + hold | Stop + hold | Stop + hold |
| Loss on lift entry | Stop + hold | Stop + hold | Stop + hold |
| Loss on carry entry | Stop + hold | Stop + hold | Stop + hold |
| One missing frame | Success | Success | Success |
| Two-second loss on carry entry, then recovery | Success | Success | Success |
| 40% cell-validity mask throughout | Wall collision | Timeout | Timeout |
| Original neural controller, healthy | Success | Success | Success |
| Original neural controller, loss from reset | Wall collision | Wall collision | Wall collision |

Success means the original empty-start 2,000 kg delivery criterion. Stop + hold
means a nonterminal three-second physical observation window meeting the frozen
criteria. It is neither delivery nor a certified emergency stop. The fifteen
stop observations are five fault timings across three weights on one shared
practice base, not fifteen independent environments.

## What was built

`training/kessel_lab/range_supervisor.py` wraps the original frozen phase-memory
neural actor. It reads the existing local observation only. A healthy sample
requires freshness, age at most 0.2 seconds and at least 20% valid range cells.
It stops immediately if range has never been healthy, or after 0.2 seconds of
continuous unhealthy samples once initial health was established.

During an override, the drive command uses conventional proportional/integral
speed feedback with saturation and bounded integration. Other joint rates are
zero. It never reads true grade, payload, obstacles or a reference action. Those
physical quantities are used only by the evaluator to describe the outcomes.
This control interface has no independently modelled parking brake.

The wrapper freezes conventional phase updates while overriding and pauses the
actor's task clock for the overridden intervals. Recovery needs three consecutive
healthy samples and three consecutive low-speed samples. It resumes the existing
task phase rather than restarting a loaded actor in approach. Unit tests exercise
fill-timeout preservation through a long synthetic input pause; physical pilot
recovery is tested at carry entry only.

Traces keep the original simulator observation, the fault-injected observation,
the unexecuted neural proposal and the applied synthetic command separately.
During overrides, the proposal uses the frozen phase and paused task-clock input.
It is not an independently running unsupervised controller. Both real and task
clocks, override reason, mode, integral state and phase are retained.

Healthy actions, phases and physical traces exactly match the separate original
neural comparator for all three seeds. Weights remain unchanged throughout.
No reference controller, teacher, learned planner or new learning is involved.

## Stopping observations and their limits

All fifteen sustained-loss cases detect within 0.2 seconds and settle within
1.0 second of loss, using three consecutive physical speed samples within
0.08 m/s. Maximum path travelled before settling is 0.472 m, below the declared
2 m limit. During each following three-second hold, maximum path length is
0.048 m and maximum physical speed is 0.028 m/s. No stop case collides or ends
the simulator during the window.

The single practice scene has grade +0.013423 rad. Its slope is below the kernel's
nominal 0.02 rolling-resistance coefficient; this is not a demanding downhill
holding test. Reset faults start at rest. Lift-entry faults carry about
2.47 tonnes at roughly 0.30–0.32 m/s. Carry-entry faults begin at rest, before
the neural carry command accelerates the machine during the grace period.
They do not establish stopping from sustained loaded reverse travel. Steeper
grades, lower grip, longer holds and greater approach/reverse speeds remain
untested. The unit test of command sign in both directions is not physical
reverse-stop qualification.

All task-phase names refer to an observation-derived trigger memory. A fault
starts when the original phase rule would enter the named phase. The supervised
actor's phase can therefore still be the preceding phase when loss begins.
No privileged simulator event chooses the injection point.

## Why partial occlusion blocks advancement

The pattern named `partial_occlusion` masks the first two rows of validity in
the 5x5 crop, leaving 60% of cells valid and fresh. Height values remain present,
including those labelled invalid. That passes the pilot's 20% valid-cell health
threshold, so all three actors continue without a single supervisor override.

This limits the match to the intended occlusion test. Native simulator occlusion
also zeros hidden height values; this injection does not. Interpret it as a
partial-validity-mask fault, rather than as a reproduction of native occlusion.
Both height and validity are neural inputs, so the retained comparison cannot
isolate their effects. The implementation and raw values are preserved; it is
not corrected by rerunning the same frozen pilot or changing the adverse scores.

Seed 7 collides while filling, with a peak load of about 1,263 kg. Seed 19
times out in carry with about 849 kg. Seed 41 times out in lift with about
2,477 kg. These are three different task failures under a coverage condition
the supervisor calls healthy. The remaining valid fraction alone does not
establish that the actor has the spatial input coverage it needs.

This isolates a concrete shortfall in the proposed health rule. It does not
prove which masked cells or neural features caused each action, nor show that
one higher threshold will solve the problem. Reclassifying these runs as
acceptable fault stops would change the frozen delivery gate after observing
failure; this study does not do that.

The next design should declare required spatial coverage and distinguish
unusable range from usable partial observations. First inspect coverage and
phase-specific input dependence on practice data, using these cases only as
consumed diagnostics. Explicitly distinguish stale-but-invalid heights from
native zero-height occlusion in the next input contract and test both. Any
revised threshold or partial-observation treatment
needs a separately named method and frozen pilot. Its criteria must distinguish
controlled stops from retained delivery capability before execution. Include
moving loaded reverse stops, larger positive/negative grades and longer holds
in that next bounded design. Fresh qualification stays blocked until the full
declared pilot gate passes.

## Resource use and verification

All 33 declared cases complete within 73.80 seconds of active execution, under
the frozen 180-second cap, with one CPU thread and no GPU. Evaluation uses
8,446 environment decisions and 8,446 neural queries. Independent replay uses
6,534 additional physical decisions across all 27 supervised traces and 8,446
additional actor queries across all 33 traces. The latter verifies proposal,
applied action, phase, health state and task clock exactly. Physical replay also
reconstructs both original and fault-injected observations exactly.

Maximum state, action and observation replay error is zero. Teacher/reference
queries, optimiser updates and held-out cases are all zero. The trace archive
is 2,755,299 bytes, below the 16 MiB cap. Source, dependency lock, protocol and
checkpoint selection are bound before the first pilot query; outcomes are
sealed before replay. Exact sources and all raw traces are retained locally.

```sh
python3 scripts/verify-range-supervisor.py
PYTHONPATH=training OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 training/.venv/bin/python -m unittest discover -s training/tests_lab -p 'test_range*.py' -v
```

The evidence verifier reads retained files and requires no PyTorch, browser,
server or new simulation. The focused tests cover health/grace/recovery,
phase-clock preservation, input immutability, missing proprioception and physical
hold accounting. All results remain training-partition synthetic evidence.
Human visual acceptance, publication and field qualification are unaffected.
