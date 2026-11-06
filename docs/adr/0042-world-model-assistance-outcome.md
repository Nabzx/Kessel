# ADR-0042: World-model assistance outcome

Status: Accepted

This records the measured recommendation for the #239 prototype. Its research
implementation is available for maintainer judgement; no visual or real-machine
acceptance is implied. ADRs 0040/0041 remain the experimental method.

## Evidence

The predeclared raw study at `68acc70` trained a single network and a three-member
ensemble, collected 18,432 transitions and executed six equal-budget policy runs.
Raw forecasts improve motion over persistence, lose to simple kinematics and
fail all imagined-branch physical checks. No auxiliary update executes.

The separately predeclared filter follow-up at `e6188d4` retains these failures,
reuses frozen training/validation/model/control artefacts, collects 8,192 fresh
held-out transitions and trains three filtered-assisted seeds. Explicit bounded
constraints permit 4,719 imagined transitions and 45 critic updates. Fresh
comparison executes all nine learned policies and the conventional controller
on identical scenes. All learned policies deliver zero material and complete
zero cycles. Equal-budget validation curves also show zero complete successes.

## Decision

Retain the independent dynamics model, raw physical-violation reporting,
short-branch gates and resumable auxiliary-critic implementation as experimental
tools. Do not enable assistance by default or describe it as more sample
efficient. Keep the explicit filter separately named and auditable; its material
conservation comes from known constraints, not learned neural accuracy.

Imagined targets affect only the critic. Real on-policy PPO remains the actor
objective. Preserve maximum two-decision branches, 25% anchor proposals every
four rollouts, coefficient 0.1, independent sampling RNGs and zero online refits.
A retained negative experiment is a completed comparison, not a successful
controller or approval for larger unbounded training.

Further algorithm changes require a new declared protocol, new held-out data
and a comparison that measures complete-task progress, failures and full compute
cost. Current uncertainty is unreliable under shift. Real-machine deployment,
learned perception and operational safety remain outside this result.

See [the report](../phase-11/world-model-experiments.md) and both linked evidence
directories for source hashes, physical-unit errors, curves, outcomes and actual
saved-model prediction/reference pairs. Recorded viewer integration remains
separate work under #243–#252.

Refs: #239, #240, #241.
