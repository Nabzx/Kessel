# Bootstrap holding practice result

25 November 2026. [ADR-0069](../adr/0069-bootstrap-motion-holding-pilot.md),
[frozen plan](bootstrap-hold-evidence/plan.json),
[all outcomes](bootstrap-hold-evidence/report.json).

## Result and boundary

The new `bootstrapped_motion_hold` method meets the complete practice gate:
45/45 stopping cases and 9/9 supervised empty-start deliveries, plus three exact
original healthy comparators. All 57 cases and independent replay complete.
This advances the prototype hypothesis only. It is not held-out qualification,
a runtime controller, new learning or a field-safety result.

| Condition | Cases | Criterion met |
| --- | ---: | ---: |
| Healthy neural delivery | 3 | 3 |
| One-frame loss then delivery | 3 | 3 |
| Moving-carry loss, stop, recovery and delivery | 3 | 3 |
| Partial coverage, retained invalid heights | 12 | 12 |
| Partial coverage, zeroed hidden heights | 12 | 12 |
| Complete loss during moving loaded carry | 3 | 3 |
| Loaded grade fixtures, initial speed +/-0.8 m/s | 12 | 12 |
| Loaded grade fixtures, cold start at rest | 6 | 6 |
| Separate original healthy neural comparators | 3 | 3 |

Stopping cases satisfy the original detection, settling, distance and ten-second
nonterminal hold criteria, with no collisions. They are not deliveries. Under
persistent partial coverage the supervisor holds the machine rather than restoring
useful partial-observation operation. The old failed partial-delivery gate remains.

Each neural seed, 7/19/41, passes every declared case. The common practice base
is 19000; component fixtures share their declared geometry. The eighteen grade
records are six physical conditions repeated across three weights, not eighteen
independent machines. Conventional override actions do not depend on neural
proposals, so those fixture trajectories repeat identically across weights.

## What changed

The [first observed-motion law](motion-hold-study.md) is retained and rejected.
It estimates disturbance too late after uphill braking and preserves integral
bias that triggers `stuck` termination during opposite-direction holds.

The new law applies one gentle initial braking command when already moving,
then estimates disturbance from actual speed response and the previous applied
command. This gives a usable nonsaturated sample earlier. It rejects rest,
reversal and acceleration-limit samples. Once the estimate is valid and speed
is small, it clears residual PI integral before applying feedforward holding.
All thresholds, case additions and gates freeze before this pilot opens.

Only observed speed, load, elapsed time and prior applied command enter the
observer. The force-response coefficient and rolling term are declared assumptions
from the reference simulator, not a learned world model or measured hardware
calibration. True grade, hidden load and reference-controller actions are absent.

The complete-coverage contract, invalid-height canonical input, frozen phase,
paused task clock and stable recovery remain. Neural proposals are logged on
the canonical task-clock input and kept separate from applied conventional
commands. Healthy actions, phases and physical states exactly match the original
neural comparators, with unchanged weights.

## Grade and cold-start measurements

All fixtures carry 2,500 kg. Grade magnitude 0.06 rad is about 3.4 degrees.
Their initial material mass is conserved by transferring payload from the pile;
these nonempty fixtures are component tests, never empty-start deliveries.

| Grade rad | Initial speed m/s | Settling time s | Stop path m | Hold path m | Hold peak speed m/s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| -0.06 | -0.8 | 0.8 | 0.240 | 0 | 0 |
| -0.06 | 0 | 0.2 | 0.007 | 0.005 | 0.065 |
| -0.06 | +0.8 | 0.9 | 0.333 | 0 | 0 |
| +0.06 | -0.8 | 0.9 | 0.333 | 0 | 0 |
| +0.06 | 0 | 0.2 | 0.007 | 0.005 | 0.065 |
| +0.06 | +0.8 | 0.8 | 0.240 | 0 | 0 |

The moving fixtures acquire their first force estimate at 0.1 seconds; cold
starts acquire it at 0.2 seconds after actual motion. Static force is not
invented from a stationary sample. The zero-speed cases permit a small initial
movement but remain inside the same physical speed/path limits throughout the
following ten-second hold. The evaluator never resets a failed window to pass.

Maximum stopping path across all 45 stops is 0.333 m, below the unchanged 2 m
limit. The initial gentle probe can lengthen braking relative to a hard first
command; the declared distance gate measures that tradeoff rather than assuming
the probe is universally safe. The previously adverse uphill fixtures no longer
roll beyond the hold limit, and no fixture ends as `stuck`.

## Resource use and verification

Execution takes 113.30 seconds within the 150-second cap, using one CPU thread,
no GPU and no browser or service:

- 12,073 evaluation decisions and 12,073 neural queries;
- 10,924 additional physical replay decisions across 54 supervised cases;
- 12,073 additional actor queries across all 57 cases;
- zero state, action, observation or observer replay error;
- zero teacher queries, optimiser updates or held-out cases;
- 3,258,726-byte trace archive, below the 16 MiB cap.

These costs are additional to the retained spatial and rejected-observer studies.
No new attempt or tuning follows the results. Source/checkpoint identity, raw
observations, canonical inputs, estimates, integral resets, initial probes,
proposals and applied commands are retained. Outcomes freeze before replay.

```sh
python3 scripts/verify-bootstrap-hold.py
```

The verifier independently checks observer arithmetic, canonical inputs, every
physical stopping gate, all source hashes and the recorded replay results.
It does not run a controller, simulator, browser or server.

## Required next evidence

The prototype has only consumed, noiseless practice evidence with adequate grip
and the reference force law. Probe validity under noisy speed/load, lower grip,
digging contact, larger speeds/grades and longer or repeated faults is unproven.
Full-grid validity is deliberately restrictive, not learned perception.

A subsequent qualification must freeze the unchanged method and separate
stopping/recovery/delivery gates, audit unused base scenarios before querying,
and retain every seed's failures and costs. Do not relabel these practice cases
as fresh or combine their counts into a reliability claim. Existing runtimes,
human visual reviews and publication remain unchanged.
