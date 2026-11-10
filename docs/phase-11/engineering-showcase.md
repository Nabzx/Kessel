# Directed surface haul and retrofit engineering

Implements #402, #403 and #404 under [ADR-0055](../adr/0055-directed-surface-haul-and-retrofit-engineering.md).
Presentation revision: `2026-11-10.01`. No release or publication is included.

The four product pipeline cards use independent, consistent rows for the index,
icon, title, description and equation. This removes inherited minimum heights and
formatting that displaced the earlier content. The accepted technical chapters
remain beside the four stages.

## Truck motion

The imported Blender truck used quaternion rotation mode. Its older animation
wrote Euler rotation keys, so position could change while the rendered body kept
its original orientation. The correction explicitly selects XYZ mode on the
rigid root and tyre pivots.

One finite 27 m work order replaces the circular loop: wait, accelerate, make a
smooth ninety-degree yard bend, brake and hold. Maximum speed is 2.5 m/s and
longitudinal acceleration is bounded at 0.8 m/s². Steering follows the route's
curvature and each tyre retains its own travel. Ground contact uses the actual
rendered ground height. There is no automatic restart; Replay haul is explicit.

`data/surface-haul.json` owns the trajectory. The same retained trace feeds the
16-second local film and live fallback, translating the ground datum to the yard
mesh in the fallback. Its tyre proxies also use explicit horizontal axles.
`assets/film/scene-audit.json` records the evaluated Blender forward vector and
tyre contact at all 385 source frames. This checks the actual rig transforms,
rather than assuming that writing a requested Euler angle changed the model.
The portable validator also checks the encoded movie clock and source hashes.

## Retrofit inspection

The final chapter is an engineering workspace with assembled, exploded and
signal-path views. Seven selectable components have a short role, a technical
description and proposed interface/packaging details. Spatial leaders follow the
actual component anchors. Focus part smoothly frames and isolates a component;
Full assembly restores its context. Dragging rotates the view and Reset view
restores the authored composition.

The original geometry gains local studio lighting, board markings and power-stage
detail. Each moving articulated assembly is framed against its current visible
geometry, not an interpolated approximation of the final exploded bounds. A
scissored viewport prevents close inspection from drawing over the interface.
Keyboard selection, selected-part state, view mode, assembly and paused signal
clock persist across chapter navigation.

The signal view separates sensing, state estimation, compact policy inference and
bounded vehicle-interface commands. It illustrates a local loop continuing without
an external connection. Its signal stream is explicitly illustrative. The optional
CPU export link opens retained measured research evidence; it does not turn CPU
results into Jetson measurements. The housing footprint comes from the existing
340 × 260 mm study. Hardware selection, qualification, thermal ratings and machine
integration remain proposed.

See [the primary engineering references](../research/retrofit-engineering-0055.md).
The globe, environment selector, mine comparison and training demonstration remain.

## Verification

[Native Chrome evidence](engineering-evidence/report.json) covers Retina
1440 × 900 / DPR 2, compact 1365 × 768 and reduced-motion 1280 × 800 on Apple M1
Metal. Complete routes have no page, console or HTTP errors. Settled assembly,
exploded and signal views satisfy the 55 fps / p95 20 ms acceptance thresholds.
The report retains the measured figures, source identities and framing/layout
checks. A focused reduced-motion rerun verifies that closing the CPU-evidence
dialog preserves a newer component keyboard focus.

Checks cover card alignment and content bounds, all hardware views, moving bounds,
seven technical inspectors, focused framing and drag rotation, paused signal
steps, retained CPU evidence, resumed state and controls clearing the chapter rail.
The movie turns and holds, returns at its endpoint and replays only when asked.
A missing-film fixture verifies matching route heading and tyre contact in the
fallback. Independent dense tests check rear-axle tangency, bounded acceleration,
forward tyre travel and the stable finite endpoint.

The static asset/evidence checks, 15 JavaScript contract tests and three reference
preparation tests pass. Existing learned failures and recorded model evidence are
unchanged. Visual judgement remains with the maintainer; no photorealistic mine
reconstruction or hardware deployment is claimed.
