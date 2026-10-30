# ADR-0013: How far to push sci-fi styling on the world-model panel

Status: Accepted

## Context

The world-model panel already differs from the simulation panel in
content (wireframe, glowing colours). The open question was whether to
add an explicit stylistic treatment -- scanlines, chromatic aberration, a
grid overlay -- to reinforce "this is synthetic/predicted," and how far
that could go before it reads as a gimmick (a "broken screen" effect)
rather than purposeful differentiation.

## Decision

Restrained, barely-there versions of two effects, both GPU-cheap:

- **Scanlines**: a large-scale, low-opacity (~3%) repeating horizontal
  line pattern, applied as a CSS overlay on the canvas container rather
  than a shader pass -- visible on close inspection, not at a glance.
- **Chromatic aberration**: a 1-2 pixel maximum RGB channel offset at the
  frame edges only (a small custom `ShaderPass`), not a heavy full-frame
  effect.

Explicitly rejected: visible scan-rolling, glitch/jitter effects, heavy
noise, or anything that would read as the panel malfunctioning. The
wireframe rendering and the cyan/red heatmap colouring are already doing
the real work of signalling "this is a prediction, not reality" --
these two effects are a light garnish on top of that, not the mechanism.

## Consequences

Both effects are intentionally subtle enough that a screenshot comparison
is needed to confirm they're even present -- that's by design. If a
future iteration wants a stronger sci-fi read, that's a deliberate
decision to revisit this ADR, not scope creep on these two effects.
