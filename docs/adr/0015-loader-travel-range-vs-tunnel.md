# ADR-0015: Compress the loader's travel range to fit the tunnel

Status: Accepted

## Context

The loader travels along world X (`loader_pose()`'s `start_x` to
`scoop_x` range, currently -4.6 to -0.6). The tunnel's long axis is world
Z, with a 3.1-unit radius cross-section centred near x=1.2 (ADR-0004,
ADR-0005). A static side-on camera mostly hid the mismatch; the Phase 6b
three-quarter chase camera (#105) would expose it directly -- the loader
drives outside the tunnel shell's cross-section at the extremes of its
existing path.

Three options were on the table (#102): compress the loader's travel
range, widen the tunnel radius, or reorient the tunnel to run along X.

## Decision

Compress the loader's travel range to fit inside the existing tunnel
cross-section, rather than changing the tunnel's geometry. Concretely,
`start_x` moves from -4.6 to roughly -1.8 (distance 3.0 from the tunnel's
x=1.2 centre, inside the 3.1 radius with a small margin), `scoop_x` stays
near the pile. No change to `tunnel`'s radius, rotation, or arc.

Rejected: widening the tunnel radius would also work with no data change,
but a materially larger cross-section reads as less enclosed, working
against the Phase 6b brightness correction's "still underground, not
daylight" requirement -- a bigger tunnel needs *more* light to read as
clearly as a smaller one does with the same fixtures. Reorienting the
tunnel to run along X was rejected as the highest-risk option under time
pressure: getting the partial cylinder's open wedge to face the floor
rather than the camera took several iterations the first time (ADR-0004,
ADR-0005), and there was no reason to redo that work when a data-only fix
is available.

## Consequences

This is a `data/generate_rollout.py` change only -- no renderer geometry
touched. It also suits the Phase 6b pacing correction (#104) well: a
shorter travel distance stretched over a longer, slower cycle reads as
more deliberate heavy-machine work, not less, which is exactly what was
asked for. The trade-off is a smaller stage for the loader to work across
than the original script had -- acceptable, since the camera follows it
regardless of how far it travels.
