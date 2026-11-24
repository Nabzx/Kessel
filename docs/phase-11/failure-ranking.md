# Remaining robustness failures

24 November 2026. [Frozen analysis plan](failure-ranking-plan.md),
[complete per-case evidence](failure-ranking-evidence/report.json).

## Recommendation

Define and test missing-range stopping behaviour next. The existing controllers
receive validity, freshness and age but continue executing the task when range
is entirely absent. Both controller types can pick up material without ever
leaving approach. This is a concrete observation/phase-contract gap, and the
available inputs permit a separately named conventional supervisor to be tested.
No such supervisor or successful stopping result is implemented by this ranking.

Blocked-path handling is equally necessary before an autonomy claim, but needs
an obstacle-observation contract first. It cannot be treated as another failure
of the learned policy to use the current pile-height input.

## Work order

Each neural count is out of eight, in training-seed order 7 / 19 / 41. Reference
delivery counts are out of eight; neural collisions are out of 24. All counts
describe the original frozen controllers, not the newer receiver-frame adapter.

| Rank | Family | Neural deliveries 7 / 19 / 41 | Reference deliveries | Neural collisions | Reference collisions |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | Complete range dropout | 0 / 0 / 0 | 0 | 20 | 8 |
| 2 | Blocked corridor | 0 / 0 / 0 | 0 | 24 | 8 |
| 3 | Shifted starting pose | 2 / 0 / 0 | 0 | 8 | 8 |
| 4 | Low pile | 0 / 0 / 0 | 0 | 8 | 1 |
| 5 | Impaired sensing | 5 / 2 / 5 | 8 | 0 | 0 |
| 6 | Steep pile | 1 / 1 / 1 | 1 | 0 | 0 |
| 7 | Ridge pile | 6 / 3 / 5 | 6 | 0 | 0 |
| 8 | Low grip | 5 / 5 / 5 | 5 | 0 | 0 |
| 9 | High resistance | 6 / 5 / 6 | 6 | 0 | 0 |
| 10 | Rubble pile | 7 / 6 / 7 | 7 | 0 | 0 |

This is an engineering work order combining observed collisions and the inputs
available for a bounded fix. It is not a ranking of real-mine risk or frequency.
The plan fixes the order explicitly; no weighted score conceals that judgement.
Nominal and left-receiver cases already pass the original gate. Farther-receiver
cases remain historical negative evidence, with separate nominal/farther
[receiver-frame qualification](receiver-robustness.md). No other family has
been qualified for that adapter.

## What the retained traces show

### 1. Complete range dropout: missing phase cue and no validated stop

All 24 neural and eight reference cases have zero valid range cells throughout
execution, no observed height cue above 0.1 m, and terminate in approach. Yet
every case physically extracts material, as recorded by its transfer ledger.
The conventional phase logic enters fill only on the masked height cue. Load
by itself does not move a phase-0 controller into fill.

Neural traces contain 6,440 completely invalid decisions; 5,337 have a drive
command magnitude above 0.05. They travel 286.76 m in total while invalid.
Reference traces contain 1,242 invalid decisions, with 1,037 non-neutral drive
commands and 102.35 m of travel. These are catalogue totals across different
runs, not stopping distances. Physical movement is measured separately from
command values. The four neural timeouts without a collision are not validated
safe stops. No range-fault recovery or holding behaviour was qualified.

The code and traces support a missing-observation/phase-contract explanation;
they do not prove the cause of every continuous neural command. The next target
is explicit fault handling, rather than training more deliveries on these cases.

### 2. Blocked corridor: the obstacle is absent from the observation contract

All 32 cases collide with `obstacle_0`, without collecting material. The archived
environment samples `self.pile.sample(points)` for the local height input; it
does not project obstacle boxes or tunnel geometry into that input. Proprioception
contains pose, joints, load, receiver displacement and sensor status. It contains
no obstacle occupancy or obstacle-distance channel. Both controller types also
lack a separate path-clearance guard.

A pile-height cue appears in four cases but does not describe the blocking box.
That cue cannot be presented as obstacle detection. Add a declared, observable
hazard representation before studying avoidance or blocked-route stopping.
Reading the privileged obstacle box directly in a learned-policy wrapper would
change the observation boundary and needs a separate, explicit baseline.

### 3. Shifted start: shared geometry/control problem, with multiple failures

The reference collides in carry in all eight cases with at least 2,000 kg still
onboard. Neural failures occur in fill (6), carry (5) and tip (11); eight collide.
Eighteen of the 22 neural failures never reach a 2,000 kg peak payload, while
eleven make partial deliveries. This is not one uniform carry failure.

Audit clearance and steering during reverse travel on the reference first,
alongside the neural pickup shortfall. Exact replay establishes reproducibility,
not valid real-machine geometry or a uniquely identified steering defect.
Do not use a receiver-frame result to imply shifted-pose qualification.

### 4. Low pile: underfilled single cycles, plus collisions

Every neural and reference case peaks below 2,000 kg, with no spillage. Fifteen
neural and seven reference cases reach tip and make partial deliveries. The
minimum initial available pile mass is 6,425.60 kg, so insufficient total scene
mass does not explain the failed delivery target. Reachable extraction volume
and physical feasibility are still unproven.

The conventional phase machine has no transition from tip back to collection.
Investigate extraction coverage, the fill timeout and an explicit retry/multiple-
load task contract. Merely waiting longer after an exhausted partial tip cannot
establish the missing pickup. Treat the eight neural and one reference collision
as separate failures within that work.

### 5. Impaired sensing: the clearest remaining policy-specific delivery gap

The reference completes all eight settings. Neural actors fail twelve matched
policy/scenario cases, all by timeout and all after reaching a peak payload above
2,000 kg. Eight end in lift, three in carry and one in tip. Most failures
therefore precede receiver arrival, unlike the diagnosed farther-receiver stall.

This family combines 25% frame dropout, 20% cell occlusion and sensor noise.
Noise affects odometry, heading, speed, joint angles and measured load as well
as local height. The retained comparison does not isolate which component
causes the gap. A follow-up should separate these perturbations and inspect
lift commands/phase thresholds on practice cases before any fresh test.
The safe treatment of transient loss must also be distinguished from permanent
loss; an unconditional abort on every missing frame could damage useful behaviour.

### 6–10. Shared pile and traction limits

Steep piles have 19 neural fill-stage `stuck` failures and two underfilled tip
timeouts; the reference has six fill-stage stuck failures and one partial tip.
All failed runs peak below target. All three neural seeds fail on the same seven
base settings as the reference. Inspect extraction geometry, resistance and
the fill/stuck timing interaction before changing the actor or simulator.

Ridge piles have seven neural fill-stage stuck failures, two partial tips and
one loaded carry failure. Nine of ten failed neural runs peak below target.
Four neural failures occur where the matched reference succeeds; six pair with
reference failure. Separate that policy gap from the shared collection limit.

Low grip has the same three failed bases for every neural seed and the reference.
Six neural runs end stuck, including three still in approach; others make
underfilled tips or remain in carry. All nine failed neural runs peak below
target. Inspect traction, grade and initial motion rather than assuming that
more imitation data can overcome a physical/controller limit.

High resistance has seven failed neural cases, all below target: five partial
tips and two fill-stage stuck runs. Six pair with reference failure, and one
with reference success. Investigate extraction and retry logic first.

Rubble's four neural failures all reach tip, deliver less than 2,000 kg and
finish with negligible payload, without spillage. Three pair with reference
failure; one is policy-specific. Investigate underfilling/retry handling before
calling these receiver-arrival or dumping failures. The prior simulator audit
also exposes contact-discretisation sensitivity on a separate consumed rubble
case; this ranking changes neither physics nor the historical scores.

## Concrete next work: missing-range behaviour

1. Declare an observation-health contract using the existing validity mask,
   freshness and age. Distinguish permanent loss, brief missing frames, partial
   occlusion and recovery. Select thresholds on practice data before fresh tests.
2. Design a separately named conventional supervisor around the frozen actor.
   Disclose every override and keep raw neural proposals separate from applied
   synthetic actions. Do not substitute the reference controller or privileged
   scene state. Decide how phase memory is held or reset during recovery.
3. Verify controlled deceleration and holding under declared speeds, loads and
   grades. The current action interface has drive and joint commands, not an
   independently modelled parking brake. A zero command is not itself proof of
   a stable stop, and a simulation termination is not a stopping controller.
4. Freeze a small training-partition pilot and cost limits before execution.
   Cover loss from reset and during approach, fill, lift and carry, plus transient
   dropout and healthy nominal controls. Retain unsuccessful stops and recovery.
5. If the pilot supports the design, reserve unused cases and predeclare separate
   stopping/recovery and delivery gates per neural seed. Specify physical stopping
   distance, residual speed, hold duration and collision criteria before testing.
   An expected fault stop is neither a successful delivery nor broad autonomy.

These are proposed follow-ups. This diagnostic task runs no pilot, changes no
controller and admits no new method. The existing world-model accuracy gate,
human visual reviews and publication remain separate and open.

## Provenance, checks and limits

The analysis reads all 416 retained cases and 154,244 recorded decisions in
16.26 seconds, using one serial standard-library Python process under a
60-second cap. No controller is imported or queried; there are no environment
steps, teacher queries, training updates or new scenarios. The output is below
the 2 MiB cap. Per-case trace hashes, identities, continuity and material
ledgers are checked, including failed runs. Original evidence remains unchanged.

The report binds its analysis source, plan, original archive/report and the
archived controller, phase, observation and state-schema sources. It retains
true terminal state separately from the last policy input, and physical pickup
separately from the observed height cue. Kernel peak payload can occur between
recorded decision frames; it is not replaced by a smaller sampled peak.

All cases were consumed previously. Eight paired base settings per family are
diagnostic evidence, not independent mines, reliability estimates or fresh
qualification. Stage labels narrow investigation; they do not prove a unique
cause. No broader success is inferred for the receiver-frame adapter.

Verify the retained result without executing policies or a browser:

```sh
python3 scripts/verify-failure-ranking.py
python3 -m unittest discover -s scripts/tests -p test_failure_ranking.py -v
```
