# ADR-0050: Recorded cycle inspection

Status: Accepted

## Context

Refs #323–#330 and #261. ADR-0043 introduced a twelve-second comparison of
three failed policy checkpoints. This cannot explain a complete material cycle.
The repaired reference can, but its actions are conventional control, not RL.
The ore columns also exaggerate the separation between neighbouring cells.

## Decision

Extend the recorded contract to 1.1 alongside legacy 1.0. Add an explicitly
labelled reference-cycle source, separately selectable from recorded policy
checkpoints and the concept replay. Reference identity is its controller/config
hash, never an invented policy checkpoint. Default entry remains the recorded
policy source until the viewer chooses a different source. Selection uses the
first declared held-out reference seed and all reference actions, not a visually
successful test search. The viewer exposes true terminal outcomes and sources.

One clock owns playback, with per-episode presentation duration and a finite
terminal hold. Event navigation pauses at post-action boundaries. Material and
observations update only on recorded decisions; pose interpolation is visual.
Height-field surfaces preserve each cell's integrated volume, zero-height holes
and footprint. Shared boundary heights use adjacent minima; inset plateaux are
solved from the triangle integral. Peak relief is bounded by the declared inset
coefficient, rather than falsely claiming unchanged cell maxima. Source, carried,
delivered and spilled kilograms remain a separate exact ledger. Cargo and transfer
fragments are bounded visual proxies, not additional accounted material.

Forecasts appear only in the World model tab. Observed samples, reference-future
outline and raw predicted envelope use distinct shapes as well as colour. Raw
violations, missing branches and conditional member spread stay visible. Ensemble
spread is not a confidence interval or a safety probability.

The reference export independently replays every action and compares state and
material checksums. Browser checks exercise clock controls, events, source
switching, missing assets, reduced motion and native frame tails. No release
qualification or publication is implied.

## Consequences

This supersedes the fixed three-checkpoint schedule restriction of ADR-0043 for
1.1 bundles. Legacy policy bundles retain their original identities and evidence.
A full conventional cycle illustrates the task without claiming learned autonomy.
