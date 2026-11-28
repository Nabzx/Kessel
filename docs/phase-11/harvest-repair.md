# Harvest repair and traction boundary

The known 19023 low-pile case now delivers 2,000.04 kg in 59.08 seconds. The known
19021 positive-margin low-grip case delivers 2,000.98 kg in 56.60 seconds. Both
use the original empty start, 2,000 kg goal, 600-decision limit and frozen physics,
with no collisions or spilled material. Conventional and saved learned-actuator
versions independently repeat both repairs in the frozen practice comparison.

The task collects material during its return stroke, uses stronger curl cycles
that stay above the spill threshold and lifts after observing sufficient load.
Receiver-relative geometry permits tipping within a conservative contained target
region, avoiding a slow uphill correction after the bucket is already inside.
The planner is conventional; the saved linear network supplies continuous task
commands. No new policy training or world-model assistance is claimed.

## Retained development

[ADR-0083](../adr/0083-harvest-recovery-and-traction-feasibility.md) bounds seven
source revisions and independent replay. All 76 complete development cases,
including unsuccessful early revisions and the first guard-window logging
failure, remain in [the development evidence](harvest-development-evidence/).
The final broad rehearsal passes 27/28 original criteria. The remaining original
delivery failure is the negative-margin 19024 start; a stationary hold is reported
separately and never called delivered material.

The [42-case practice comparison](harvest-practice-evidence/report.json) preserves
all six original failed delivery criteria: both sources on low-pile 19025, low-grip
19025 and low-grip 19024. It also retains the repaired low-pile and recoverable
low-grip regressions. Every controller, sensor and physical transition replays
exactly. Practice uses 11,204 physical/planning and 11,204 replay decisions in
111.10 seconds, within 180 seconds and 12,000 decisions per category.

## Why some requests cannot use the same delivery guarantee

Low-pile 19025 contains only 1,471.34 kg above the minimum blade height. The fixed
physics can never deliver 2,000 kg from that accessible material. Low-grip 19024
has -3,207.71 N empty forward margin at its initial heading; low-grip 19025 has
-625.61 N. This establishes failure of straight uphill approach, not a proof that
every possible manoeuvre is impossible. No amount of retiming that same approach
creates the missing traction or material.

The separate proposed start guard requires three seconds of full drive/high
slip, speed <=0.01 m/s, less than 0.02 m movement, an empty bucket and no nearby
crop. In both negative-margin cases it detects at 3.1 seconds and holds for ten
seconds with zero drift, zero speed and no collision. The hold is explicitly
conventional. It is specific to empty synthetic starts with the declared grade
bound, not a general brake or onboard terrain estimator. Range/clearance braking
retains precedence. Maintainer acceptance of refusal as an outcome remains a
separate question; the original delivery gate is unchanged.

## Fresh qualification boundary

[ADR-0084](../adr/0084-frozen-harvest-and-forecast-qualification.md) freezes a
conservative executable-request envelope: initially at least 3,200 kg above the
blade floor and at least 200 N empty forward traction margin. This privileged
initial-state certificate is a synthetic qualification/admission condition. It
is never passed to the observation-only task controller and is not implemented
field perception. The repaired 19023 case demonstrates a particular success
outside this conservative envelope; that does not qualify every thin pile.

Before fresh policy queries, audit a fixed 32-base screening cohort against all
available local Git versions and repository/ignored raw archives. Select the
first eight eligible initial states per family using only those fixed physical
conditions. Retain every screened state identity and rejection; never select or
replace cases using policy outcomes. The fresh study also includes eight
prepared no-progress starts for each source and independent collision/stuck
fixtures. Original delivery, supported-envelope performance, guard stability
and frozen forecast gates remain separate.

The [completed fresh qualification](harvest-qualification.md) retains 288/288
supported task/stop/recovery checks, 16/16 prepared start holds and a passing
frozen forecast gate. Original failed-delivery outcomes stay separate. No
new service, browser capture, public release or visual acceptance follows from
these numerical results.
