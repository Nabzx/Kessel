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
themed environment carousel, prepared Rwanda arrival and substantial
roof-off mine cutaway. Four trucks and a licensed excavator illustrate the
baseline/trained comparison. ADR-0054 adopts one clearly labelled authored
training demonstration for the main walkthrough: early mistakes, partial
pickup and three complete evaluation jobs with obstacle avoidance. It is
kinematic illustration, not measured policy success. The recorded experiments
and their unsuccessful learned outcomes remain retained as research evidence.
Seven full-screen chapters replace ordinary scrolling, retain playback state
and provide a persistent navigation rail. The local Blender surface now uses one finite, evaluated haul trajectory with
a still and a matching real-time fallback. ADR-0055 replaces the original kit
presentation with assembled, exploded and signal views, component inspection,
spatial labels and a local offline architecture. The accepted observation-to-action
chapters remain. Hardware interfaces and performance targets remain proposed.

`data/experience.json` is the active authored contract. ADR-0031 separates the
Phase 11 experimental tools and validated recorded-synthetic bundles from the
authored mission. Learned dynamics, policy training and model-assisted
updates need their own implementation and evaluation evidence; none is implied
by the current cinematic replay. The onboard runtime remains proposed.
See ADRs 0028–0032. ADR-0045 adopts cleared natural-rock and near-ground maps,
a capped synthetic cutaway, detailed authored surface props, a simplified
credited NASA orbital silhouette and refined machinery/kit/HUD presentation.
Native visual evidence is in `docs/phase-11/visual-realism.md`. The maintainer
has deferred reported recorded-demo behaviour problems; visual acceptance does
not resolve them. Recorded material-transfer verification in #261 remains
partial.

ADR-0046 refines the home globe, decorative orbit and environment selector with
credited photographic references. A single sun direction serves translated
globe layers, labels follow actual marker transforms, and the reduced-motion
path settles immediately. The training/replay follow-up (#305) and offline
Blender authoring plan (#306) remain separate research backlogs; no Blender MCP
connection or new learned task success is implied by home improvements.

ADR-0047 adds independent reference-cycle, geometry, integration and reset audits
with opt-in synthetic pile families, preserving legacy replay dynamics. ADR-0048
uses a verified local Blender MCP connection to author bounded visual GLBs,
portable source scenes and original baked detail. Browser playback owns every
machine/transfer clock. The authored geometry is not automatically calibrated
collision geometry. The proposed kit uses metre-scale source geometry and a
declared tenfold presentation enlargement. No release is implied.

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

The 21 November ADR-0061 study adds a separate phase-memory imitation policy.
It supplies every continuous action through a trained neural network and task
phase through a conventional observation-derived state machine. It completes
96/96 nominal final policy/scenario cases across three training seeds; memoryless
imitation completes 54/96. All outcomes and teacher costs are retained. The
isolated `docs/phase-11/phase-memory-demo/` plays verified recordings of the
admitted method. This is reference-simulator evidence, not a learned-world-model
training result, a production runtime or field qualification. Earlier failed
PPO/model-assisted results and the authored default remain unchanged.

The 22 November ADR-0062 continuation adds isolated localhost synthetic execution
under `training/kessel_lab/` and `docs/phase-11/live-demo/`. It executes new physics
and frozen neural actions, with conventional phase memory, and has no machine
interface. A thirteen-family stress study retains all 416 cases; only nominal
and left-shifted receiver families pass its all-seed gate. Existing learned
world-model forecasts fail the new working-policy calibration gate and are not
used for assistance. Numeric observation validation and durable shadow logging
are prototypes, not implemented perception or qualified retrofit hardware.
Human visual acceptance and publication remain open at the maintainer's request.

The 23 November ADRs 0063/0064 add a separately named receiver-frame input
adapter, preserving the same neural weights, conventional phase memory and
reference physics. On eight fresh bases per family, each of the three adapted
seeds completes 8/8 nominal and 8/8 farther-receiver cases with zero collisions.
The original actors complete 24/24 nominal and 0/24 farther cases. This qualifies
only nominal/2 m farther synthetic receiver settings. It is an engineered input
representation, not new learning or a learned-world-model result. The optional
`kessel_lab.receiver_runtime` verifies the retained evidence and serves only
these families on practice seeds. The default runtime remains unchanged.

The 24 November retained-failure ranking analyses all 416 original stress cases
without new policy or simulator queries. Missing-range cases physically collect
material while remaining in approach; blocked boxes are absent from the pile-
height observation contract. Impaired sensing also exposes a distinct neural
lift/carry gap against the reference. The ranking proposes explicit missing-range
behaviour next. It implements no supervisor and admits no additional family.

ADR-0065 adds a separate conventional missing-range supervisor around the
original phase-memory actors. Its 33-case practice pilot meets all 15 declared
stop/hold criteria and preserves healthy/transient/recovered deliveries, but
fails all three partial-occlusion deliveries, including one collision. The
overall gate fails: no runtime admission or fresh qualification follows.
The wrapper freezes phase and pauses the task clock during overrides. All
neural proposals, applied synthetic actions and negative outcomes remain retained.

ADRs 0066/0067 add a separate canonical range adapter and complete-coverage
supervisor. Invalid/stale heights are zeroed without inventing valid cells.
The revised practice pilot meets all 24 partial-coverage stops and three moving-
carry complete-loss stops, with nine successful healthy/transient/recovered
deliveries. Six of twelve loaded-grade fixtures fail the ten-second holding gate.
No fresh qualification or runtime admission follows. Partial-input delivery is
not restored: the new method stops when coverage is incomplete. The aborted
serialization attempt and corrected capped run are both retained.

ADR-0068's first observed-motion holding law fails all twelve loaded-grade
criteria and remains rejected. ADR-0069 adds a distinct bootstrap law using
an initial gentle braking sample and an integral reset on transition to holding.
Its 57-case practice suite passes all 45 stops, nine supervised deliveries and
three original healthy comparisons, with exact replay and unchanged weights.
This includes loaded +/-0.8 m/s and cold-start fixtures on +/-0.06 rad grades.
It is conventional reference-specific control, not learned dynamics or fresh
qualification. Neither prototype is available in the existing runtimes.

ADRs 0070/0071 qualify the unchanged bootstrap controller on eight audited fresh
nominal-physics bases: all 24 healthy deliveries, 24 partial-carry stops, 24
complete-loss carry stops and 24 recovered deliveries pass, with zero collisions.
All 24 original healthy comparisons match exactly and replay is exact. A logging
abort consumes base 208700; it is excluded and replaced only after a separate
audit of 208708. The final cohort is 208701–208708. Qualification covers only
those four synthetic families, not noisy proprioception, low grip, other fault
phases, field equipment or composition with the receiver-frame adapter. Existing
runtimes and human visual/publication decisions remain separate.

ADR-0072 adds a separate qualified-stopping service, `kessel_lab.bootstrap_runtime`,
on loopback port 8095 and `/docs/phase-11/qualified-demo/`. It checks the retained
qualification/source identities before admitting the same four synthetic patterns.
Live sensor health and control ownership distinguish neural proposals from
conventional applied overrides. Explicit play/pause/step/reset and trace export
operate only on practice seeds. Ten-second hold endings do not count as deliveries
or physical termination. Consumed-practice integration checks are separate from
fresh qualification and human visual acceptance. No prior viewer or numerical
source is changed.

ADR-0073 adds a separate idealised clearance channel and latched conventional
stopping wrapper. All 24 declared obstacle/stale-input stops pass with exact
replay, but three healthy practice deliveries are intercepted by the wall guard.
The full pilot fails and no runtime admission follows. Failed first-pilot holds
and a logging abort remain retained. This is synthetic geometric sensing, not
implemented perception or obstacle avoidance.

ADRs 0074/0076 retain a rejected all-family robustness refit. Original policies
complete 17/39 practice deliveries with eight collisions; candidates complete
5/39 with 27 collisions. A separate forward-steering damping correction resolves
a conventional stability defect but its retest still fails delivery. All 221
episodes, source/weights and exact candidate/physical replay remain retained.
No existing runtime or qualification changes.

ADR-0075 refits models on isolated working-policy practice episodes. Position
MAE improves from 0.04416 to 0.02236 m and the observation model improves speed,
load and valid-height errors, but raw material errors worsen. Validation admits
a two-decision horizon; the all-family evaluation gate still fails, including
68.35% accepted high-error on left-receiver cases and zero coverage in several
other families.
All raw/filtered predictions and rare-class coverage shortfalls remain retained.
No assisted updates, fresh qualification or runtime admission follow.

ADR-0077 adds a separate clearance capture-order guard. Old/duplicate packets
cannot release a blockage latch even inside the freshness age limit. Contract
tests preserve ordered commands across all three checkpoints; frozen numerical
evidence and existing runtimes remain unchanged.

ADRs 0078/0079 add progress-driven conventional collection and ordered clearance
stopping. All eighteen frozen base-19022 task/stop/recovery/input checks pass with
exact replay; a separate regression delivers on previously intercepted base
19001. The selected rehearsal still fails one low-grip case, retained explicitly.
No physics, original weights, existing runtime or qualification is changed.

ADR-0080 fits a sparse learned linear feedback layer from successful progress
demonstrations. Conventional planning/braking remain explicit. Reference and
learned feedback each meet 12/13 final practice criteria, with the low-pile miss
retained. Applied learned commands, saved weights and physical replay verify;
no deep-RL, task-planning or assistance benefit is inferred.

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

**Recorded reference cycle**: a complete synthetic cycle executed by the
conventional observation-only controller, identified by configuration hash and
independently replayed actions. It is separately selectable from recorded learned
policies and the concept replay. Its successful delivery is not learned autonomy.

**Recorded material surface**: a presentation mesh derived from physical cell
means. Its per-cell triangle integrals preserve source volume and zero-height
holes. Cargo and event fragments are visual proxies, separate from the kilogram
ledger and physical collision reference.

**Phase-memory imitation policy**: a learned continuous-action network receiving
local observations and phase from a conventional observation-derived state
machine. Teacher queries are restricted to training. The explicit memory is
not a learned planner or a learned world model.
