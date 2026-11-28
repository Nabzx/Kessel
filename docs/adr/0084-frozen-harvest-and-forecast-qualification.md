# ADR-0084: Frozen harvest and forecast qualification

Status: Accepted for the 28 November request. Preserves every failed original
full-delivery gate. No browser, service or deployment is authorised by this study.

Freeze the return-harvest task, the separately identified no-progress guard, the
saved six-gain actuator and structured hybrid forecast weights before practice.
Use the same sources for conventional and learned-actuator comparisons. Planning,
start refusal, range/clearance braking and hybrid kinematic/event/accounting
priors remain explicitly conventional. No training, final-driven refit or
calibration change. Refusal acceptance has been asked of the maintainer; until
answered, treat a stable refusal separately from failed original delivery.

## Task feasibility and endpoints

The frozen generator includes impossible or marginal requests. For example,
low-pile material above the blade's minimum height can be less than 2,000 kg;
the known 19024 low-grip start has -3,208 N forward margin. Declare a conservative
synthetic qualification envelope before fresh queries: at least 3,200 kg initially
above the fixed minimum bucket height and at least 200 N empty forward drive
margin after slope/rolling resistance at the initial heading. Compute this once
from privileged initial simulator state as a qualification/admission certificate.
It is not an implemented onboard feasibility estimator or a controller input.

Retain every screened initial identity, including those outside this envelope.
Before any policy query, select the first eight eligible bases per family from
the fixed 32-base screening cohort. This conditions the declared synthetic test
distribution on feasibility, not future success. Never screen on outcomes.
Execute and retain every selected case and every prepared challenge.
Never replace seeds or count an unsupported delivery as a passed stop. Report
original full-delivery criteria, proposed stable refusals, supported-envelope
criteria and coverage separately. Require all supported cases to pass, exactly
eight supported cases per primary family and no collisions anywhere
for supported-envelope qualification. Do not claim all generated low-grip/low-pile
requests qualify. The fixed 2,000 kg/600-decision task and physics never change.
Require the known 19023 low-pile and 19021 positive-margin low-grip deliveries
independently even though the conservative envelope may exclude the former.

Practice uses all thirteen families plus recovery, carry loss and stale/old/
missing clearance on consumed-practice base 19025, each with reference and learned
actuator. Also repeat the three known difficult cases with both sources: 42 cases.
Cap practice at 12,000 physical/planning decisions, 12,000 replay steps and 180 s.
Practice must pass every supported case and both repaired positive regressions;
unsupported practice groups retain zero coverage and their original outcomes.
Only fresh qualification requires eight supported cases per family.

## Fresh reservation and qualification

Screen bases 207400–207431 only after auditing all available Git versions and
raw/container members under data/docs/training/.local. Compare seed identities
and exact/f32 initial-state and pile hashes for every primary family. Prepared
failure fixtures use 207450–207457 collision and 207458–207465 stuck. The audit
makes no policy/physics-transition query, runs one CPU thread, has a 240 s parent
cap and a 16 MiB certificate cap. Any hit or unreadable evidence blocks execution.
No failed seed is replaced. Fewer than eight eligible initial states in any
family rejects the reservation; do not extend the fixed screening cohort. Record audit-source and history inventory hashes.

Execute eight selected cases in each primary family for both sources and the
five nominal input/recovery patterns on its eight selected bases. Also execute
eight prepared no-progress starts (207470–207477) for both sources, with fixed
friction 0.085, grade 0.1 rad and no parameter randomisation. These explicitly
prepared fixtures qualify guard stability separately from failed delivery. Add
the sixteen collision/stuck fixtures: 320 cases. Independently replay every
physical transition and controller/sensor command. Require exact replay, unchanged
weights, no teacher labels and no optimiser updates. Charge all physical/planning
and replay work, with at most 100,000 physical/planning steps, 100,000 replay steps,
900 s total, one CPU thread and a 96 MiB retained-artifact cap. This is synthetic
qualification within the declared envelope, not field qualification.

## Fresh forecasts

Evaluate the frozen hybrid on every learned-actuator primary-family episode plus
the prepared fixtures. Stop-window ends remain non-terminal. Retain training-free
predictions, raw errors, event false-safe/false-stop, physical validity, common
1/2/4/8-decision drift and per-family acceptance. Use the exact earlier validation
threshold and its two-decision horizon. Do not refit it to fresh labels. Require
nonzero physically valid accepted predictions and <=10% accepted high-error rows
for every non-blocked family, including prepared collision, stuck and no-progress
starts. Qualification
of forecasts does not demonstrate model-assisted policy benefit or perception.

A completed failed gate remains failed. Retain every counterexample and report
scope/coverage instead of describing an unfulfilled full-delivery gate as passed.
