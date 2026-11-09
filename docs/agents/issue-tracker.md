# Issue tracker: GitHub

Issues and specs for this repo live as GitHub issues. Use the `gh` CLI for all
operations. `gh` infers the repo from `git remote -v`.

## Conventions

- **Create**: `gh issue create --title "..." --body "..."`, heredoc for
  multi-line bodies. Issue titles are a plain description of the job, not a
  Conventional Commits line (that is for the PR).
- **Read**: `gh issue view <n> --comments`.
- **List**: `gh issue list --state open --label phase-2 --json number,title,labels`.
- **Comment**: `gh issue comment <n> --body "..."`.
- **Label**: `gh issue edit <n> --add-label "..."` / `--remove-label "..."`.
- **Close**: `gh issue close <n> --comment "..."`. ADR-0054 authorises closing merged and verified implementation tickets
  without a tag. Keep review and release work open until its own acceptance
  criteria pass. Closing a ticket does not publish a release.

## Issues are for bugs and maintainer work items

The issue tracker holds reproducible bugs (the `bug.yml` form) and
maintainer-created work items (wayfinder tickets, the `wayfinder.yml` form).
Feature ideas, direction and questions use the `feedback.yml` form or
Discussions if enabled; blank issues are disabled.

## Labels

**Phase**

- `phase-0` to `phase-7`: which roadmap phase the work belongs to (see
  `ROADMAP.md`). Every issue carries one.

**Wayfinder**

- `wayfinder:map`: the single map issue for a phase.
- `wayfinder:research`: an autonomous investigation. Output is an ADR
  recommendation.
- `wayfinder:prototype`: a throwaway spike that needs a human to judge the
  result.
- `wayfinder:grilling`: pressure-test a decision with the maintainer before
  it is locked.
- `wayfinder:task`: build work.
- `ready-for-agent`: the spec is settled; an implementation agent may build
  it.

**Priority** (bugs carry one)

- `p1`: serious. The demo is broken or an honesty guarantee (the caption, the
  illustrative labelling) is violated.
- `p2`: an ordinary defect with a workaround or a limited blast radius.
- `p3`: minor. Cosmetic, or a nice-to-have with no urgency.

**Triage state**

- `needs-repro`: plausible but not yet reproduced. On the `bug.yml` form by
  default.
- `needs-decision`: blocked on a design decision (an ADR or a grilling).
- `needs-research`: blocked on a `wayfinder:research` investigation.
- `regression`: worked on an earlier tagged build, broken now.
- `pending-release`: historical merged implementation marker. ADR-0054 permits
  verified implementation tickets to close before a release tag.

**Area**

- `rendering`: the Three.js scene — tunnel, lighting, loader rig, rocks, dust,
  bloom.
- `data`: `data/rollout.json`, the generator script, the schema.
- `hud`: HUD bindings, connectivity/decision-time/error/episode display.
- `interaction`: intro sequence, Drop boulder control, horizon scrubber.
- `performance`: frame budget, mobile and DPR handling.
- `publish`: GitHub Pages mirror, CI, Dependabot, hosting docs.
- `docs`: README, ADRs, and this directory.
- `adr`: the issue needs or updates an ADR.

## Wayfinder

The **map** is one issue labelled `wayfinder:map`, holding three sections in
its body: Notes, Decisions so far, and Fog (what is still unknown).

**Child tickets** are GitHub sub-issues of the map, each labelled
`wayfinder:<type>` and `phase-N`.

**Blocking** uses GitHub's native issue dependencies. Add an edge with
`gh api --method POST repos/Nabzx/Kessel/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`,
where the blocker db id comes from `gh api repos/Nabzx/Kessel/issues/<n> --jq .id`.

**Frontier**: the map's open child tickets with no open blocker. Work them in
map order.

**Resolve** a research or grilling ticket: comment the answer, close it, then
append a one-line pointer to the map's Decisions so far, linking the
resulting ADR.
