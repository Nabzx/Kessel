# Agent guide

How an engineering agent should work in this repo.

## Skills

### Issue tracker

Issues and specs live in this repo's GitHub Issues. See
[`docs/agents/issue-tracker.md`](docs/agents/issue-tracker.md).

### Domain docs

Single-context layout: [`CONTEXT.md`](CONTEXT.md) and [`docs/adr/`](docs/adr)
at the repo root. See [`docs/agents/domain.md`](docs/agents/domain.md).

### Wayfinder

Each phase in [`ROADMAP.md`](ROADMAP.md) opens with a `wayfinder:map` issue.
Research and grilling tickets hang off it and resolve into ADRs before build
tickets start. The frontier is the set of open child tickets with no open
blocker.

## Invariants

These do not change without an ADR that supersedes this list.

### One maintainer

Kessel has a single maintainer, Nabil Shah. Every commit, issue and pull
request is authored by him. No commit carries a co-author trailer — including,
specifically, no AI tool attribution of any kind. An engineering agent working
in this repo commits as the maintainer, not as itself.

### Nothing here is presented as real model output

This repo ships a **concept visualisation**, not a product demo backed by a
trained policy. The permanent on-screen caption and the "illustrative"
labelling on HUD values (`index.html`, `js/app.js`) are load-bearing, not
decoration. A change that would make scripted data read as live inference —
removing the caption, dropping the "illustrative" label, renaming the scripted
rollout to imply it is real — needs an ADR, not a drive-by edit.

### The front end is data-only

`index.html`, `css/`, and `js/app.js` never hardcode scene content. Everything
the renderer draws — loader pose, rock positions, predicted horizon, HUD
values — comes from `data/rollout.json`, in the schema documented in
`data/generate_rollout.py`'s docstring and `CONTEXT.md`. Swapping the scripted
rollout for a logged rollout from the real policy and world model must require
zero changes to the front end. If an implementation needs the front end to
change to consume real data, the schema was wrong, not the invariant.

### No build step

The site is plain HTML, CSS and JavaScript, loaded via an import map and CDN
ES modules (Three.js). No bundler, no transpiler, no `node_modules` in the
shipped site — it must run by opening `index.html` on a static file server, and
deploy as-is to GitHub Pages. Tooling used only for local QA (Playwright
screenshots, a lint script) lives outside what gets published and is excluded
in `.gitignore`.

### Runs smoothly on a phone

The demo must hold a smooth frame rate on a mid-range mobile device, not just
a development laptop. Pixel ratio is capped, particle counts and
post-processing scale down under `IS_MOBILE`, and any change that adds
per-frame cost needs to be checked against that budget before it merges.

## House style

British English. Plain, short sentences. No marketing tone in commits, issues
or ADRs. No em dashes.

Commit messages and pull request titles follow Conventional Commits:
`<type>(<scope>): <description>`, lowercase, imperative, concise, for example
`feat(renderer): add instanced rock pile to the simulation panel`. The body,
when present, stays plain and explains why. Reference an issue with
`refs #<n>` in the body, never a closing keyword; a build issue carries
`pending-release` and closes in a batch when tagged, not on merge. Docs and
small fixes may close on merge.
