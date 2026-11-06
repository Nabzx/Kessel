# Initial CPU tooling and static package verification

Date: 5 November 2026. PRs #282 and #283. This is the initial foundation
batch, not completion of Phase 11 or evidence of a trained machine policy.

## Automated checks

- Nineteen focused tests pass on macOS. Linux CPU CI also passes.
- Existing experience and tunnel-network validators pass.
- Scene JavaScript syntax and whitespace checks pass.
- Checks cover units, handedness, action/configuration validity, deterministic
  workload traces, material bookkeeping, reset isolation and separate counters.
- Packaging checks exclude environments/raw experiments, retain licences and
  validate the actual entry-point import map and declared experience assets.

## Browser package

The final allowlist package contains 60 files, 13,516,974 bytes. Chrome
156.0.8078.80 used native ANGLE Metal on Apple M1 at 1440 x 900, DPR capped at
1.5. The runner also exercised 1280 x 800 and reduced motion. The existing
uncommitted hero-position CSS adjustment was present in this QA package; it is
excluded from the PR commits. Source and workspace details are in the
[structured report](package-verification.json).

All eight acceptance groups pass: environment selection, arithmetic, repeatable
comparison, training replay controls, world-model return/scroll restoration,
proposed-kit controls, laptop/dialog behaviour and failed-terrain retry with
reduced motion/restart. No page errors or HTTP errors were recorded in the
successful run. The current authored 2.4-million episode display is tested as
illustrative content, not as a measurement of the new CPU tooling.

All six steady-state samples were approximately 60 fps. The final cumulative
mean was 55.96 fps with p95 16.8 ms. Mine entry had p95 33.4 ms and a maximum
316.8 ms frame, so this does not claim hitch-free transitions. Later visual
and performance tickets still need to improve and measure their own changes.
Local ready time was 941 ms; this is not an internet-hosting load benchmark.

The browser run caught two omissions before the final pass: vendored modules
and JSON rig descriptors. Both were corrected and now have regression checks.
The failed runs are not counted as passing evidence.

Screenshots, complete runner output and video are at
`/private/tmp/kessel-phase11-package-evidence-v3/` on the test machine.
These local QA artefacts are not presentation assets.

## Learning workload

See [CPU feasibility](cpu-feasibility.md) for the separate numerical workload,
raw counters, cold import cost and provisional run budgets. The browser still
uses authored scene data. Full simulator, PPO, learned-dynamics and recorded
playback work remain in their respective open tickets.

## Recorded experiment integration

The historical checks above describe the initial foundation snapshot. Subsequent
simulator/RL/world-model work and recorded playback have their own measured
reports. See [recorded integration](recorded-integration.md) for actual browser
playback, model residuals, source separation and isolated CPU export results.
This does not qualify the remaining Phase 11 visual/release work.
