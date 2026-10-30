# ADR-0003: Boulder event representation

Status: Accepted

## Context

The "Drop boulder" control needs to make the loader visibly replan and halt
safely, on demand, not just at a fixed point in a passive loop. The data
schema (ADR-0001) needs to represent that in a way that is simple to
generate and simple for the front end to trigger.

## Decision

The rollout bakes exactly **one** hazard window, anchored at a fixed elapsed
time (`BOULDER_EVENT_T` in the generator). It is always present in the
rollout's natural loop — playing the demo passively will eventually reach it
on its own. The "Drop boulder" button does not inject a new event into the
data; it jumps the playback clock's virtual time directly to
`boulder_event_frame`, so the viewer sees the same baked
replanning-then-halted-then-recovering window on demand instead of waiting
for the loop to reach it.

This repo does not build a general hazard-injection system (arbitrary
events, multiple hazard types, random placement). One scripted window,
one button that fast-forwards to it, is sufficient to demonstrate the
behaviour honestly.

## Consequences

Simple to generate (`hud_for()` just checks whether the current time falls
inside `[BOULDER_EVENT_T, BOULDER_EVENT_T + window)`) and simple to trigger
from the UI (set `virtualT`, nothing else). The natural loop also passing
through the event unprompted is a feature, not a bug, for an illustrative
demo that may run unattended.

If a later need arises to show multiple distinct hazard types, or a hazard
the viewer can place anywhere in the timeline, that is new scope and needs
its own ADR — this one should not be stretched to cover it.
