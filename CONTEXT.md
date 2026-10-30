# Context

The glossary for this repo. Use these terms as defined here, in issue titles,
ADRs, commits and code. See [`docs/agents/domain.md`](docs/agents/domain.md)
for how an agent should use this file.

## What this repo is

Kessel builds physical AI for extreme environments, starting with underground
mining: loaders trained inside a learned world model, running fully offline on
a retrofit computer once deployed. This repo is not the training stack or the
onboard runtime. It is the **concept visualisation**: a static, data-driven web
demo that shows how the approach works, for people (initially, YC and EWOR
partners) who cannot visit a mine or read a policy's weights.

## Glossary

**World model** — a learned simulation of the environment that the policy is
trained and evaluated inside, instead of the real mine. The reason training can
happen at all: real underground data collection is too slow, too dangerous and
too disconnected to generate at scale.

**Rollout** — one played episode: a timestamped sequence of loader pose, rock
state, world-model predictions and HUD values. On disk this is
`data/rollout.json`, consumed by the renderer as the single source of truth for
everything drawn on screen. Schema: [ADR-0001](docs/adr/0001-rollout-data-schema.md);
mobile payload budget: [ADR-0002](docs/adr/0002-mobile-payload-budget.md).

**Scripted rollout** — the rollout this repo ships today, produced
deterministically by `data/generate_rollout.py`. It is placeholder data built
to be visually honest about the shape of the real pipeline, not a measurement
of anything. _Avoid: "real data", "live rollout", "model output" for this._

**Logged rollout** — a rollout recorded from the real trained policy and world
model, in the same schema as the scripted one. Dropping a logged rollout in
place of the scripted one should require no change to the renderer
(`js/app.js`). This is the architectural point of the schema boundary.

**Prediction horizon** — the fixed set of future offsets (`dt`, in seconds)
the world model predicts ahead of the current simulation frame. The time
scrubber moves across this horizon. Each step carries a predicted rock
position plus a per-rock `error` scalar (distance from ground truth), not a
duplicate ground-truth position array — see ADR-0002.

**Decision time** — the latency, in milliseconds, the onboard policy takes to
choose its next action. Shown in the HUD. In the scripted rollout this is an
illustrative value, not a measurement.

**Prediction error** — the mean per-rock positional divergence, in metres,
between the world model's predicted state and the ground-truth simulation state
at a given horizon step. Drives the heatmap colouring in the world-model panel.

**Boulder event** — the scripted hazard in the rollout: an obstacle that forces
the loader to replan and halt safely. Reachable either by letting the rollout
loop play to it, or on demand via the "Drop boulder" control, which jumps
playback to `boulder_event_frame` rather than injecting a new event — see
[ADR-0003](docs/adr/0003-boulder-event-representation.md).

**Simulation panel** — the left canvas. Ground truth: the loader and rock pile
as the (scripted) simulation has them right now. _Avoid: calling this panel
"the real one" — both panels are illustrative in this repo._

**World-model panel** — the right canvas. The world model's predicted state at
the selected horizon step, rendered as a glowing wireframe pile with a
per-rock heatmap showing divergence from ground truth. Never "the prediction
panel" or "the AI panel" — use the defined term.

**Concept visualisation** — what this whole repo produces. A scripted,
honestly-labelled illustration of how Kessel's approach works. Never presented,
in copy or in the UI, as real model output. The permanent on-screen caption and
the "illustrative" labelling on HUD values exist to keep that true.

**Retrofit kit** — the physical sensor, compute and controls package fitted to
an existing machine in the field. Product context only; out of scope for this
repo's code.
