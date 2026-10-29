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
- A build issue is not closed on merge. It carries `pending-release` and
  closes in a batch when its phase is tagged.
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

### Phase 6 — Publish

A public mirror repository that serves the built static site over GitHub
Pages (this repo stays private), the CI workflow that syncs it on push to
`main`, and Dependabot.

**Done when:** a stable public URL loads the demo, and a push to `main` here
updates it without a manual step.

### Phase 7 — Submission polish

README with real screenshots and a captured clip, hosting and
screen-recording instructions, and a final honesty and QA pass against the
application use case.

**Done when:** the repo reads well cold, the README link works, and the demo
is ready to attach to the YC and EWOR applications.
