# Roadmap

One maintainer, working in linear phases. Every phase ends in something that
runs, even if narrow. This is a concept visualisation for a YC and EWOR
application, not a product: the roadmap is sized to that — weeks, not quarters
— and stops once the demo does its job honestly and well.

Each phase opens with a `wayfinder:map` issue that names the decisions the
phase depends on. Research and grilling tickets resolve them into ADRs before
build tickets start. See [`docs/agents/issue-tracker.md`](docs/agents/issue-tracker.md)
for the label taxonomy and the Wayfinder workflow.

## Ground rules

- Every change lands through a pull request with green CI, even though there
  is one maintainer. The trail is part of the point.
- An ADR is written before code for anything touching the rollout data schema,
  the sim/world-model panel split, the renderer's public shape, or the
  hosting/publish mechanism.
- ADR-0054 authorises closing merged, verified implementation work before a
  tag. Review and release tickets retain their own acceptance criteria.
- Nothing ships that presents scripted data as real model output. See the
  Invariants in `AGENTS.md`.

## Phases

### Phase 0 — Scaffold

Repository, agent docs (`AGENTS.md`, `CONTEXT.md`, `docs/agents/`), labels,
issue and PR templates, and CI skeleton. No demo code yet.

**Done when:** the repo is set up to the same standard as the maintainer's
other projects, and Phase 1's map issue can open against real labels.

### Phase 1 — Data contract

The `rollout.json` schema and `data/generate_rollout.py`, the scripted
placeholder generator. This is the seam the whole architecture depends on:
everything downstream reads this file and nothing else.

**Done when:** the schema is documented, the generator produces a valid,
reasonably sized rollout, and an ADR records the schema decision.

### Phase 2 — Scene core (simulation panel)

The tunnel shell, lighting, dust, the loader rig, and the instanced rock pile,
driven entirely by `rollout.json`. This is the left-hand "Simulation" panel.

**Done when:** the simulation panel renders a moody, legible underground scene
with a loader scooping from a shifting rock pile, matching the rollout data.

### Phase 3 — World-model panel

The right-hand panel: a glowing wireframe of the same pile at a predicted
future state, with a per-rock heatmap showing divergence from ground truth,
and the prediction-horizon scrubber.

**Done when:** the two panels sit side by side, visibly in sync on the
current frame and visibly diverging on the predicted one, and the scrubber
moves through the horizon.

### Phase 4 — Interaction, HUD and honesty

The three-card intro sequence, the HUD (connectivity, decision time,
prediction error, episode count), the Drop boulder control, and the permanent
caption and illustrative-value labelling.

**Done when:** a first-time viewer understands what they are looking at
within the first minute, unprompted, and cannot mistake it for live model
output.

### Phase 5 — Performance and mobile

Frame budget work: DPR caps, particle and post-processing scaling under
`IS_MOBILE`, resize and orientation handling, and a real on-device pass, not
just a desktop browser check.

**Done when:** the demo holds a smooth frame rate on a mid-range phone, and a
resize or orientation change does not break either panel.

### Phase 6 — Visual fidelity and advanced polish

Inserted ahead of publish on the maintainer's direction: the demo has to
look as realistic and as high-tech as the product story it's telling before
a public link goes out. Rendering realism (volumetric light, surface detail,
environment props, post-processing), UI/branding polish (typography, the
wordmark, micro-interactions, the sci-fi differentiation on the world-model
panel), and a correctness pass (cross-browser, long-run stability, payload
budget, cold-open timing) across everything built in Phases 1-5.

**Done when:** the demo reads as a polished, high-production-value piece of
software, not a prototype, without compromising the honesty invariants in
`AGENTS.md` or the Phase 5 frame-budget work.

### Phase 7 — Publish

A public mirror repository that serves the built static site over GitHub
Pages (this repo stays private), the CI workflow that syncs it on push to
`main`, and Dependabot.

**Done when:** a stable public URL loads the demo, and a push to `main` here
updates it without a manual step.

### Phase 8 — Submission polish

README with real screenshots and a captured clip, hosting and
screen-recording instructions, and a final honesty and QA pass against the
application use case.

**Done when:** the repo reads well cold, the README link works, and the demo
is ready to attach to the YC and EWOR applications.

### Phase 9: Interactive mission

Replace the earlier single-loader sequence with Earth, environment selection,
a descent to Rutongo, an illustrative fleet, a pre-computed optimisation
preview and truck inspection. The loading scene reuses the licensed excavator
and PBR mine assets. Google satellite reconnaissance and a local terrain
alternative provide the surface context. Offline machine autonomy is the
product story; manual waypoint controls are removed.

**Done when:** the complete story is usable on localhost, all active controls
work, the retained assets are credited, the original truck is correctly
oriented through a full haul cycle, and payload and browser measurements are
reported honestly. See [ADR-0027](docs/adr/0027-phase-9-demo-completion.md) and
the [verification report](docs/demo/phase-9-verification.md). Real-device
performance evidence must be distinguished from browser emulation.

### Phase 10: Cinematic offline-autonomy experience

Map: [#173](https://github.com/Nabzx/Kessel/issues/173), with child tickets
#174–#195. The approved storyboard replaces the Phase 9 presentation. It
centres realistic Earth and a custom wordmark, adds five themed environments,
flies continuously into Rwanda, exposes a tilted mine cutaway, compares six
GBP operating measures, and branches into technical loader learning. Ordinary
scrolling explains dynamics, RL, distillation and onboard compute, followed by
a proposed exploded kit. Pricing and manual override are excluded.

The MacBook Pro M1/Chrome is the presentation target. See
[design and timing](docs/phase-10/design.md),
[verification](docs/phase-10/verification.md), and
[visual review](docs/phase-10/visual-review.md). Functional implementation and
maintainer visual acceptance are recorded separately.

### Phase 11: Synthetic robot learning and realistic presentation

Map: [#197](https://github.com/Nabzx/Kessel/issues/197), with 84 child tickets
#198–#281 and 142 native blocking dependencies. Public-asset research precedes
the visual specifications; see
[the shortlist](docs/research/2026-11-04-public-assets-and-phase-11.md).

Build a CPU-first synthetic loader environment, establish a conventional and
model-free baseline, evaluate a learned dynamics ensemble and short imagined
rollouts, then export genuine checkpoints and predictions to the static viewer.
Improve geological materials, cutaway geometry, machinery, lighting,
application layout, technical HUDs and continuous transitions while retaining
the approved story and sparse copy.
Architecture changes require the superseding ADRs in the foundation tickets.

**Done when:** reproducible experiments and honest recorded playback accompany
the realistic presentation, with measured native M1 performance, asset notices,
offline verification and maintainer visual acceptance. The initial architecture
and measured CPU feasibility batch are in PRs #282 and #283. World-model
experiments, recorded integration and bounded CPU export/compression comparisons
are implemented. Full task proficiency, visual changes and complete Phase 11
qualification remain open work.
The remaining RL tools and bounded comparisons are now implemented in PRs #290
and #291; [the measured study](docs/phase-11/rl-experiments.md) found no complete
learned delivery cycle. Research-tool completion does not imply task proficiency.

The [world-model comparison](docs/phase-11/world-model-experiments.md) implements
#231-#242 under ADRs 0040-0042. Its two declared studies retain raw failures and
a separately identified physical filter. The filter executes 45 critic updates
from 4,719 imagined transitions, with no complete learned cycle or measured
sample-efficiency gain. Prototype judgement and Phase 11 release remain pending.

[Recorded integration](docs/phase-11/recorded-integration.md) implements #243-#252
under ADRs 0043/0044. Validated checkpoint replay and measured prediction
inspection are available in the optional viewer. The CPU comparison recommends
float32 ONNX for fidelity; smaller variants regress action accuracy and all
variants retain zero complete learned cycles. Prototype judgement, remaining
visual/layout work and the verified Phase 11 release are still pending.

## Resumable cinematic walkthrough (ADR-0054)

The maintainer accepted seven full-screen chapters, a simplified authored
training progression with three complete jobs and obstacle avoidance, and a
trial original Blender surface film. Work is tracked in #395–#400 under #349.
Historical learned failures remain retained; illustrative success is separate.
See [the implementation and verification report](docs/phase-11/cinematic-chapters.md).
Release and publication remain outside this work.
