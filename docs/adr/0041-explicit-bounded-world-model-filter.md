# ADR-0041: Explicit bounded world-model filter

Status: Accepted

Supersedes ADR-0040's prohibition on correcting learned forecasts only for a
separately identified experimental hybrid predictor. Raw neural predictions,
their violations and the completed first study remain unchanged and visible.

## Evidence

The frozen first study trained the ensemble and selected a one-step horizon.
All 128 validation branch probes failed physical guards, including remote pile
changes and material creation. The actual policy comparison consequently used
zero imagined transitions and zero auxiliary critic updates. Global position-
error/disagreement correlation on validation was approximately -0.0094.
This does not justify enabling the raw predictor for model-assisted learning.

## Decision

Test one separately predeclared variant: a bounded, explicit physical filter
after the frozen network. It uses current state and raw prediction only, never
reference future outcomes. Constrain local extraction, payload/release budgets,
receiver credit, monotone material counters, actuator bounds and non-positive
operating costs. Recompute carried mass from the same ledger. Do not repair
machine position or bypass uncertainty, clearance and input-envelope gates.
Reject corrections beyond recorded physical-unit limits. Every filtered result
retains raw forecasts, correction magnitudes and filter identity. Conservation
is imposed by known constraints, not claimed as something learned by the MLP.

Reuse the first study's immutable training/validation corpus and model weights.
Select the filtered gate on validation only. Do not reuse the inspected first
test set as fresh evidence: collect new nominal and OOD test seeds and evaluate
all retained baseline/raw-assisted policies on the same fresh policy scenes.
Train three filtered-assisted policies with the same 30,720 on-policy plus
10,240 charged offline samples and 120-second caps. Existing control weights
remain fixed. Record this extra budget before running it; retain negative
outcomes and the raw study regardless of the result.

This is not an orthogonal/KKT projection, a learned perception model or a
deployment safety system. Report the hybrid predictor separately from neural
accuracy. A successful auxiliary update would demonstrate pipeline execution,
not useful policy learning or a real-machine guarantee.

Refs: #234, #238, #239, #240, #241.

Primary methodological references:
[physics-informed constraints](https://arxiv.org/abs/2109.06407) and
[explicit projection layers](https://arxiv.org/abs/2402.07251).
Their guarantees do not apply automatically to this bounded prototype.
