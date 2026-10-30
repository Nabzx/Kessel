# ADR-0008: Drop boulder drives both panels together

Status: Accepted

## Context

The boulder event is meant to show the policy replanning under a hazard.
If both panels freeze on the same frame, the viewer cannot see the
world-model panel's prediction error actually spike during the event --
arguably the more interesting moment to show, since it is the clearest
illustration of what the world-model panel is for.

## Decision

Both panels share a single playback clock (`state.virtualT`). The Drop
boulder control sets that one clock directly to `boulder_event_frame`;
there is no separate "pause" state per panel. Because the simulation
panel's `rocks` and the world-model panel's `predicted_horizon` are both
read from the same current frame, triggering the event moves both panels
together, frame for frame -- the world-model panel's prediction error
genuinely spikes in sync with the simulation panel's replanning/halted
state, because `predicted_horizon[i].error` was generated against the
same boulder-event ground truth (ADR-0003).

The world-model panel's independent axis is the horizon scrubber
(`state.horizonIdx`), not time. A viewer can still freeze the current
instant and scrub through how far ahead the world model is predicting,
independently of playback -- that is a different, deliberate degree of
freedom from "pause one panel and not the other."

## Consequences

Simpler state (one clock, not two), and the boulder event reads as a
single coherent moment across both panels rather than two panels telling
slightly different stories. The trade-off: there is no way, today, to
watch the world-model panel keep predicting forward while the simulation
panel is frozen mid-event. If a future need arises to show that
specifically, it is new scope for its own ADR, not a reinterpretation of
this one.
