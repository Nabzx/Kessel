# ADR-0006: Prediction-error colour scale

Status: Accepted

## Context

The world-model panel's heatmap needs to look like genuine, evolving
uncertainty, not an arbitrary rainbow, and it needs to stay legible both
when the rollout is near-perfect (nominal operation) and when it is
visibly wrong (the boulder event).

## Decision

A two-segment scale, implemented as `errorColor()` in `js/app.js`: cyan
through amber for the lower half of the observed error range, amber through
red for the upper half. The range itself is **adaptive**, not fixed: a
running `maxErrorSeen` value decays slowly (`*0.998` per rock, per frame)
towards the largest error actually observed, with a floor of 0.25m so a
near-perfect stretch of rollout doesn't make ordinary noise look alarming.
Each rock's colour is normalised against that running maximum, not a
hardcoded constant.

## Consequences

The heatmap stays legible across the whole rollout: calm cyan during
nominal operation, a visible shift toward red during the boulder event,
without needing a manually tuned constant that would only suit one episode
length or noise profile. The cost is that the scale's meaning is relative,
not absolute -- "red" means "the worst this episode has shown so far," not
"worse than N metres." That is acceptable for an illustrative demo; a real
deployment's dashboard would need an absolute, calibrated scale, which is
out of scope here.
