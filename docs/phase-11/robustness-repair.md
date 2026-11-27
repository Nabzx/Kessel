# Bounded robustness repair

The new neural candidates regress and are rejected. Across all thirteen families
on practice base 19013, the original checkpoints complete 17/39 deliveries with
eight collisions; the candidates complete 5/39 with 27 collisions. None is enabled
in an existing runtime. Successful isolated steep/farther-receiver cases do not
override the worse overall result or qualify a shifted family.

Protocols: [ADR-0074](../adr/0074-bounded-robustness-repair.md) and the separate
[forward-steering correction](../adr/0076-forward-steering-stability-correction.md).
The [complete report](robustness-repair-evidence/report.json) retains 208 complete
rehearsal, validation and evaluation episodes, all three trained checkpoints and
every raw observation, phase, neural proposal, applied override and physical state.
All final candidate actions replay exactly in a separate simulator.

## What was tested

A separately named conventional comparison adds retry memory after an underfilled
tip, a shorter fill timeout and a proposed articulated-yaw steering law. Its
six-second fill variant completes 0/26 rehearsals; the twelve-second variant
completes 8/26 and is selected by the predeclared rule. Training uses only the
selected variant's 7,242 labelled decisions on bases 19010/19011, including its
failures. Each retained neural checkpoint receives exactly 1,000 minibatch
updates, balanced by observed phase, without changing original weights.

Filtered and unfiltered input are compared on base 19012 before evaluation.
All three choose unfiltered input. Missing-cell masks are preserved; smoothing
does not manufacture observations. The conventional prototype missing-range
supervisor, retry memory and trained neural commands are disclosed separately.
This experimental composition inherits no bootstrap/receiver qualification.
Complete loss avoids the three original collisions in this one practice setting,
but still produces three timeouts, not successful deliveries or qualified holds.

| Family | Original deliveries / 3 | Candidate deliveries / 3 | Original collisions | Candidate collisions |
| --- | ---: | ---: | ---: | ---: |
| Nominal | 3 | 1 | 0 | 1 |
| Low pile | 0 | 0 | 0 | 3 |
| Ridge | 2 | 1 | 0 | 1 |
| Rubble | 3 | 0 | 0 | 3 |
| Steep | 0 | 1 | 0 | 2 |
| Farther receiver | 0 | 1 | 0 | 2 |
| Left receiver | 3 | 0 | 0 | 3 |
| Shifted start | 0 | 0 | 2 | 3 |
| Low grip | 3 | 0 | 0 | 2 |
| High resistance | 3 | 1 | 0 | 1 |
| Complete range loss | 0 | 0 | 3 | 0 |
| Impaired range | 0 | 0 | 0 | 3 |
| Blocked corridor | 0 | 0 | 3 | 3 |

These are three policies on one shared consumed practice base per family, not
independent scenario replication, reliability estimates or new qualification.
The earlier separately qualified receiver/stopping methods remain unchanged.

## Diagnosed correction and remaining failures

The proposed forward yaw-rate inversion lacks articulation damping and has the
wrong feedback stability for forward motion. A separate `DampedTaskReference`
restores the original damped forward target and retains the reverse law. An
independent 120-step offset kinematic test confirms convergence without steering
saturation, while the rejected controller saturates articulation.

Its [fixed 13-case retest](damped-reference-evidence/report.json) uses base 19014
and the already selected twelve-second fill time. It completes no full deliveries:
twelve timeouts and one blocked-path collision. Partial delivered material remains
below target. The conventional steering defect is corrected, but the retry/fill
task design does not meet the unchanged 2,000 kg / 600-decision contract. No new
teacher labels are used for another neural refit after observing evaluation.
The blocked case deliberately has no clearance wrapper; it is not mislabelled
as evidence against the separate ADR-0073 stopping method.

Low/steep-pile extraction, retry efficiency, noisy-input delivery and shifted-start
behaviour therefore remain unresolved. This comparison rules out deploying the
tested repair. It does not establish that further imitation or changed physics
would solve those problems.

## Costs and verification

Combined original study and steering correction: 79,571 environment decisions,
27,590 teacher calls, 3,000 optimiser updates and 20,624 independent replay steps,
in 475.98 seconds on one CPU thread. This stays within the original
100,000 / 30,000 / 3,000 / 25,000 / 600-second caps. Both source capsules, all
221 complete episodes and their failures are retained. No budget expansion,
fresh scenario reservation, browser, service, release or runtime change occurs.

```sh
python3 scripts/verify-robustness-repair.py
PYTHONPATH=training training/.venv/bin/python -m unittest discover -s training/tests_lab -p test_robust_task.py -v
PYTHONPATH=training training/.venv/bin/python -m unittest discover -s training/tests_lab -p test_damped_reference.py -v
```
