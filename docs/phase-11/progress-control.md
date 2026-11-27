# Progress-driven task and clearance compatibility

The new conventional controller passes all eighteen frozen practice validation
checks on base 19022: eleven deliveries across the thirteen primary families,
two expected stops, one recovered delivery and four additional stop/input cases.
Every action, observation, sensor packet and physical state replays exactly.
The original healthy scenario on base 19001 now delivers with the guard active
in a separate bounded regression test. Existing neural weights and runtimes are
unchanged. This is conventional planning/control, not learned task success or
fresh qualification.

Protocols: [ADR-0078](../adr/0078-progress-driven-task-and-clearance-compatibility.md)
and [lateral stability correction](../adr/0079-lateral-feedback-stability-correction.md).
The [frozen validation report](progress-validation-evidence/report.json) and all
eight append-only [development revisions](progress-development-evidence/) retain
their source capsules, actual outcomes and cost ledgers.

## Concrete repairs

The earlier fixed fill deadline left underfilled buckets. The original neural
wall-guard case kept driving in fill with about 2,311 kg onboard. The new method
uses measured load progress and cut travel. It lifts at 2,250 kg, retains material
while retracting to another collection lane and never resets physics to retry.
The empty-start delivery target remains 2,000 kg within 600 decisions.

Retained payload is no longer mistaken for new contact on a return approach.
Direction-aware damped steering replaces the unstable lateral feedback. Stalled
cuts can sweep the bucket before a more expensive retreat, and measured slip may
select an entry lane. None of these decisions receives hidden pile geometry.
A separate privileged geometric producer supplies the explicitly synthetic
clearance packet; this is not implemented lidar or camera perception.

The ordered clearance latch remains active. Missing, stale, malformed or old
packets stop the task. A fresh partial range crop needs at least five valid cells.
After initialisation a bounded 0.2-second range grace tolerates short gaps while
independent clearance remains usable; it does not invent valid cells. Persistent
loss stops within the declared grace plus one decision. Initial absence and
blocked clearance stop immediately. Three usable/slow samples are required to
resume. Task time and tactical memory pause during overrides.

Stopping uses the retained bootstrap numerical law with an explicit zero
conventional interface placeholder. It executes no neural network and records
no supposed neural proposal. All task commands and stopped/held outcomes are
labelled conventional. Stop windows are not deliveries or environment terminals.

## Complete results and limits

Development uses bases 19020/19021 and retains 128 complete tuning episodes over
eight revisions. The selected gain 0.15 passes 25/26 final rehearsal criteria:
21/22 deliveries and four stops. Low-grip base 19021 still times out. It is not
removed, relabelled as a stop or claimed solved by validation on another base.
Both predeclared damping corrections share the original cumulative resource caps.

Frozen validation uses only base 19022, after source/parameter selection. Its
thirteen primary families all meet their declared delivery/stop criteria. A
two-second moving-range outage recovers and delivers; permanent moving loss,
stale/old/missing clearance all stop and hold for ten seconds. No collision occurs.
The actual physical terminal state remains separate from a completed hold window.

Development costs 34,066 physical/conventional decisions in 178.21 seconds, under
40,000/300 seconds. Validation costs 3,947 physical and 3,947 independent replay
steps in 39.67 seconds, under 12,000/12,000/180 seconds. One CPU thread is used.
The original-scenario regression has its own 600-step/600-replay/20-second test
bound. No browser, tab automation, service, new runtime admission or release is
performed. Fresh qualification still requires separately reserved cases.

```sh
python3 scripts/verify-progress-control.py
PYTHONPATH=training training/.venv/bin/python -m unittest discover -s training/tests_lab -p 'test_progress_*.py' -v
```
