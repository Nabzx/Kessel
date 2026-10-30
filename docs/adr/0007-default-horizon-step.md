# ADR-0007: Default horizon step shown before scrubbing

Status: Accepted

## Context

The world-model panel has to show something before the viewer ever touches
the scrubber. The shortest horizon step is closest to ground truth and
least visually interesting; a mid-range step shows more divergence but
risks looking wrong on first impression, before the viewer understands
what they're looking at.

## Decision

Default to the shortest horizon step (`horizonIdx = 0`, `+0.6s` in the
current rollout). A first-time viewer's first impression of the
world-model panel should be "this closely tracks the simulation panel," not
"this looks wrong" -- the scrubber is the mechanism for deliberately
showing more divergence once the viewer understands the two panels are
meant to differ, and the Drop boulder control reliably produces visible
divergence even at the shortest step during the replanning window.

## Consequences

The world-model panel reads as trustworthy by default and the scrubber
reads as an invitation to explore divergence, not as a bug the viewer
stumbles into by accident. `scrubber`'s HTML `value="0"` and
`state.horizonIdx = 0`'s initial value in `js/app.js` both encode this;
changing the default requires updating both.
