# Context

The glossary for this repo. Use these terms as defined here, in issue titles,
ADRs, commits and code. See [`docs/agents/domain.md`](docs/agents/domain.md)
for how an agent should use this file.

## What this repo is

Kessel builds physical AI for extreme environments, starting with underground
mining: loaders trained inside a learned world model, running fully offline on
a retrofit computer once deployed. This repo is not the training stack or the
onboard runtime. Phase 11 adds isolated CPU-first synthetic experiment tooling
under `training/`; it is not a production control stack. The shipped site is
the **concept visualisation**: a static, data-driven web
demo that shows how the approach works, for people (initially, YC and EWOR
partners) who cannot visit a mine or read a policy's weights.

## Current experience

Phase 10 replaces the Phase 9 presentation with a centred Earth opener,
themed environment carousel, continuous Rwanda descent and substantial
roof-off mine cutaway. Four trucks and a licensed excavator illustrate the
baseline/trained comparison. The optional technical viewer defaults to
recorded-synthetic policy checkpoints and raw dynamics forecasts. Actual failed
outcomes remain visible; the authored demonstration is an explicit alternate
source. Ordinary scrolling explains the proposed pipeline and exploded kit.

`data/experience.json` is the active authored contract. ADR-0031 separates the
Phase 11 experimental tools and validated recorded-synthetic bundles from the
authored mission. Learned dynamics, policy training and model-assisted
updates need their own implementation and evaluation evidence; none is implied
by the current cinematic replay. The onboard runtime remains proposed.
See ADRs 0028–0032.

The Phase 11 reference simulator, resumable PPO tools and model-free comparison
study are implemented under ADRs 0033-0039. The bounded study completed curriculum
subtasks but no learned complete delivery cycle. Retained weights, failed
replays and measured comparisons live in `docs/phase-11/rl-evidence/`; the report
is `docs/phase-11/rl-experiments.md`. Learned state-dynamics ensembles and bounded
auxiliary-critic experiments are implemented under ADRs 0040-0042. Their report
is `docs/phase-11/world-model-experiments.md`; raw and explicitly filtered
forecasts are separately identified in retained evidence. The filter permits
imagined updates but the equal-budget studies demonstrate no complete learned
cycle or sample-efficiency gain. Recorded integration and CPU ONNX/compression
comparisons are implemented under ADRs 0043/0044, with the report in
`docs/phase-11/recorded-integration.md`. The static adapter validates curated
records before switching source labels. Mine business metrics remain
illustrative. Do not describe these policies as having demonstrated full
autonomous haulage.

## Glossary

**Recorded synthetic experiment** — a reproducible simulator run with source
version, configuration, seed, controller or checkpoint identity and measured
outputs. It is neither real-mine telemetry nor evidence of deployment savings.

**Reference simulator** — the explicit synthetic environment used to generate
transitions and independently evaluate predictions. Its deterministic dynamics
are distinct from the learned world model.

**Mission dataset** — the historical Phase 9 authored data contract in
`data/mission.json`. It describes the location, staged scene references,
tunnel graph, fleet, haul cycles, routes, and compact optimiser trace. See
[ADR-0022](docs/adr/0022-phase-9-mission-data-contract.md). It replaces the
single-loader rollout contract for the mission demo.

**Scripted mission** — the illustrative dataset shipped with the concept
visualisation. Its optimiser trace is pre-baked; it does not represent a live
run of 100,000 simulations or output from a trained policy.

**Logged mission** — mission data recorded from a real deployment or model
run, using the same contract as the scripted mission. The renderer should
consume either without code changes.

**Directed tunnel edge** — an ordered path between two tunnel graph nodes.
Its order defines vehicle travel direction and is the source for heading,
forward-facing lights, and loading approach.

**Illustrative underground scene** — the Phase 9 underground network and
fleet, authored as a research-informed mechanised scenario located at
Rutongo. It is not a survey or reconstruction of Rutongo's current workings.

**World model** — a learned simulation of the environment that the policy is
trained and evaluated inside, instead of the real mine. The reason training can
happen at all: real underground data collection is too slow, too dangerous and
too disconnected to generate at scale.

**Earlier-demo rollout** — one played episode: a timestamped sequence of loader pose, rock
state, world-model predictions and HUD values. On disk this is
`data/rollout.json`, consumed by the renderer as the single source of truth for
everything drawn on screen. Schema: [ADR-0001](docs/adr/0001-rollout-data-schema.md);
mobile payload budget: [ADR-0002](docs/adr/0002-mobile-payload-budget.md).

**Scripted rollout** — the earlier-demo rollout this repo ships today, produced
deterministically by `data/generate_rollout.py`. It is placeholder data built
to be visually honest about the shape of the real pipeline, not a measurement
of anything. _Avoid: "real data", "live rollout", "model output" for this._

**Logged rollout** — an earlier-demo rollout recorded from the real trained policy and world
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
an existing machine in the field. The exploded Phase 10 view illustrates a proposed assembly; it does not
select or validate production hardware.
