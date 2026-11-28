# ADR-0083: Harvest recovery and traction feasibility

Status: Accepted for the maintainer's 28 November request to finish low-pile,
low-grip and fresh qualification. Preserves all earlier failed gates and frozen
source. No browser, service, hardware command or visual acceptance is involved.

The low-pile failure leaves recoverable material during reversing manoeuvres
with a raised bucket. Test low-bucket return harvesting, stronger non-spilling
curl cycles, shorter reversing clearance and an observed-load lift threshold.
Retain the original 2,000 kg delivered goal, 600-decision limit, initial state,
material conservation and frozen reference physics. Tactical control receives
existing observations only, not privileged friction, grade or future states.

The low-grip 19024 start has negative straight-ahead traction margin. Investigate
bounded physical recovery before declaring its delivery infeasible. Retain any
failed attempts and separate a controlled refusal from actual delivery. Never
relabel a failed delivery as a passed stop after seeing its outcome. A new
feasibility envelope must be declared and qualified separately if required.

Development uses consumed bases 19020–19024. Allow at most eight adaptive source
revisions, 40,000 physical/planning decisions, 40,000 independent replay steps and
600 seconds combined. Each revision has an immutable source capsule, complete
trace archive, consumed-case list and cumulative cost ledger. Separate diagnostic
probes may use at most 4,800 physical decisions and 60 seconds within those same
limits. No optimiser or policy-weight updates. Reuse the fitted linear actuator
only with explicit conventional planner context and actual saved-weight commands.

Select a candidate only after it passes the known failing low-pile and low-grip
cases plus regressions. Freeze it before an eighteen-case-per-source practice
comparison on 19025, bounded by 12,000 physical/planning/replay decisions and
180 seconds. Preserve any practice failure. Fresh qualification needs a separate
predeclared protocol, a frozen source/weight identity and a no-policy-query audit
of genuinely unused bases and initial-state/pile fingerprints across available
Git history, repository archives and ignored local experiment artifacts.

Qualification must retain delivery, stopping, input-fault/recovery and forecast
criteria separately. No final-driven threshold fitting, fresh-seed replacement,
physics change, hidden-state task inputs or runtime admission is inferred from a
partial result. Do not describe a conventional recovery as learned planning.

## Separate proposed start refusal

The maintainer has been asked whether controlled refusal is an acceptable outcome
for the negative-traction start. Until an answer, keep the delivery gate unchanged.
A proposed guard may be built and measured without treating it as accepted task
success. It latches only after three seconds of saturated drive/high slip,
<0.02 m observed movement, speed <=0.01 m/s, empty load and no nearby crop. Hold
uses explicit conventional 0.39 - 1.8*speed drive and stationary joints. Within
the empty synthetic low-grip scene's grade <=0.1 rad envelope, 0.39*22,000 N is
above maximum slope minus rolling resistance. This is a reference-specific
holding prior, not estimated friction or field certification. Keep the independent
clearance/range brake precedence. Log actual hold source and all unused/delivered
queries correctly. Measure ten-second stability separately from failed delivery.
