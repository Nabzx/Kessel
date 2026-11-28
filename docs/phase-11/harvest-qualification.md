# Fresh harvest and forecast qualification

The repaired controller passes every fresh task/stop/recovery criterion inside
its declared synthetic qualification envelope: 288/288 checks across conventional
and saved learned-actuator sources, with no policy collisions. The separate
start guard passes 16/16 prepared stationary-hold challenges. The frozen hybrid
forecast also passes its unchanged gate on 26,325 fresh transitions.

This is conditional synthetic qualification. It does not qualify every random
pile/traction request, implement field perception, demonstrate model-assisted
learning benefit or accept the walkthrough visuals. No new runtime is admitted.

## Scope declared before queries

[ADR-0084](../adr/0084-frozen-harvest-and-forecast-qualification.md) requires at
least 3,200 kg above the blade floor and 200 N empty forward traction margin.
This conservative privileged initial-state certificate is an admission/test
condition, never an input to the observation-only task controller. It does not
claim to identify every physically solvable task. The known thin-pile repair
succeeds outside this envelope and remains a separate verified regression.

A fixed cohort of 32 unused bases, 207400–207431, was screened before any policy
query. The first eight eligible initial states per family were selected using
only those fixed physical conditions. All 440 initial identities and rejection
reasons are retained in the [reservation](harvest-qualification-evidence/reservation.json),
including prepared fixtures. No success labels, final errors or replacement
seeds influence selection. This conditions the test distribution on the stated
envelope; it is not evidence for the full unconditioned generator.

The audit covers available local Git versions and raw/container/member evidence
under data/docs/training/.local. It cannot exclude unretained external runs. It
inspected 8,899 unique blobs with no seed or fingerprint matches. The original
[rejected audit](harvest-qualification-evidence/reservation-attempt-1.json) is
preserved. Its sole error was a packaging-test `.json` file containing the literal
`data/example.json`. [ADR-0085](../adr/0085-literal-qa-fixture-audit-erratum.md)
disposes only of those exact hash-pinned non-numerical bytes, preserving the
original error and zero-query status. Corrected audit cost is 219.47 seconds.

## Results

| Source | Completed deliveries | Controlled stops | Prepared start holds | Policy collisions |
| --- | ---: | ---: | ---: | ---: |
| Conventional planner/feedback | 96/96 | 48/48 | 8/8 | 0 |
| Conventional planner, saved learned feedback | 96/96 | 48/48 | 8/8 | 0 |

Each source runs eight cases in all thirteen primary families and eight nominal
cases for each of five recovery/input patterns. The sixteen additional guard
challenges use prepared empty starts at friction 0.085 and grade 0.1 rad. They
vary seed/pile identity at that fixed parameter point; they do not establish
independent broad terrain coverage. Holding is a conventional reference-specific
prior, supported by a separate check of the declared empty grade/friction bound.

All 65,304 physical transitions and controller/sensor commands independently
replay exactly. The sixteen extra collision/stuck fixtures terminate as designed;
their intentional collisions are separate from policy collision counts. Total
retained cases are 320. The one-thread run uses 640.48 of its 900-second budget
and 33,884,923 bytes of its 96 MiB artifact cap. No policy weights, forecast weights
or calibration thresholds change. The legacy budget key `teacher` counts 64,422
planner/control decisions here; there are no teacher labels or optimiser updates.

## The hard start remains a refusal, not delivered material

The known 19024 negative-margin start is detected at 3.1 seconds and held for ten
seconds with zero drift or speed. Its original delivery outcome remains failed.
The same distinction applies to all sixteen fresh guard challenges. Their hold
windows are not environment terminals and are never counted as successful hauls.
The original full-delivery gate therefore remains false even though the separate
supported-task and guard-stability gates pass. On 28 November the maintainer explicitly accepted a detected stop and stable
hold as the outcome for this start. The [acceptance record](harvest-qualification-evidence/start-refusal-acceptance.json)
pins this exact qualification and guard source. It does not alter any recorded
delivery result, qualification threshold, controller or weight. The frozen study
plan retains its historical pending status from before that decision.

The known recoverable cases are fixed: [the repair report](harvest-repair.md)
retains 2,000.04 kg delivered in 59.08 seconds on low-pile 19023 and 2,000.98 kg in
56.60 seconds on low-grip 19021, with both sources independently repeating them.
The impossible 19025 request with only 1,471 kg accessible remains failed too.
Neither this qualification nor a controller can create the missing material.

## Frozen forecasts

The hybrid's raw high-error fraction is 0.703%, position MAE 0.000549 m and carried
mass MAE 3.01 kg on 26,325 fresh transitions. Every required non-blocked family has
accepted physically valid predictions with at most 10% high-error rows. The worst
accepted-family fraction is 3.51% for steep piles. There are no raw capacity,
joint, speed, negative-material or non-finite violations. Maximum material-ledger
error is 7.28e-12 kg, enforced by the model's explicit accounting prior.

The forecast still combines learned local acceleration/extraction heads with
known kinematics, geometric collision, event and conservation rules. It is not
learned perception or learned conservation. Contact classification retains 1,157
false negatives and 474 false positives. The frozen validation threshold and
two-decision, nominally 0.2-second support remain unchanged. Fixed-action drift
at 1/2/4/8 decisions is retained without fitting a new horizon to these labels.
No forecast is used to choose a policy action in this comparison.

## Verify

    python3 scripts/verify-harvest-development.py
    python3 scripts/verify-harvest-qualification.py
    PYTHONPATH=training training/.venv/bin/python -m pytest training/tests_lab/test_harvest_task.py training/tests_lab/test_start_progress.py training/tests_lab/test_harvest_qualification.py -q

The standard-library verifier independently reconstructs initial scope, all task
and refusal gates, actual learned commands, resource counts, raw forecast errors
and per-family acceptance. Numerical tests reconstruct the selected initial
identities, replay saved weights without a simulator oracle and protect the
non-terminal/non-delivery meaning of refusal windows. Sources, complete traces,
weights' hashes, dataset, predictions and the execution environment are retained
in [the fresh evidence](harvest-qualification-evidence/fresh/report.json).

Visual reviews #351/#385, manual browser review and release/publication remain
open. No browser automation or listening service was used in this work.
