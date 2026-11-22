# Continuation review and remaining acceptance

22 November 2026. Decision: ADR-0062. The maintainer explicitly chose to keep
human visual reviews **#351 and #385 open**. This report does not accept the
visuals, publish the site or close final release review #276.

## Delivered technical work

- [Frozen-policy stress study](shift-study.md): all 416 cases, all failures,
  exact independent physical/action replay and a per-family admission gate.
- [Interactive synthetic runtime](live-demo/README.md): newly executed physics
  and frozen neural actions, practice seeds, run/pause/step/reset and export.
- [Numeric observation and shadow recording](runtime-and-observations.md):
  timestamps/units/calibration identity, bounded durable recording and exact
  independent replay of 100 shadow proposals.
- [Simulator probes](continuation-evidence/simulator.json): material accounting,
  actuation, contact-step sensitivity and reward counterexamples.
- [Working-policy forecast diagnostic](working-policy-models.md): existing models
  fail the assistance gate. No assisted training or world-model benefit is claimed.

The original 96/96 nominal imitation result is retained. Broader robustness
fails; source labels keep neural controls, conventional phase memory, the
conventional reference, learned dynamics and authored playback separate.

## Native walkthrough checks

The final static package contains **144 files, 43,999,980 bytes**, with
presentation version `2026-11-22.01`. Its [manifest](continuation-evidence/static-package.json)
excludes training environments, weights and raw research archives. All dependencies
are local. The external-network-denial test opens all seven chapters and the
kit while allowing only loopback requests: no external requests are attempted.
This is simulated loss of internet connectivity, not disabling the local server
or changing the machine's network settings.

The original full-walkthrough suite passes at 1440 × 900 Retina, 1365 × 768 and
1280 × 800 reduced motion in Chrome 157 on Apple M1 Metal. Visible-frame mean
rates are **59.67–60.00 fps**, with p95/p99 about **16.8 ms**. It checks seven
chapters, film pause/replay, finite three-job authored training, retained chapter
state, technical dialogs, keyboard navigation, interruption and missing-data retry.
See [corrected full review](continuation-evidence/full-site-corrected-review.json).
The live route separately passes three viewport profiles, real nominal success,
blocked failure, source changes, pause/reset/step, keyboard and request boundaries.
Narrow checks are functional, not phone presentation qualification.

### Correcting the measurement boundary

The first cold review reported 29.89 fps on Retina and 47.37 fps on compact Earth
entry. Investigation found that the rolling FPS window included hidden loading
frames before the canvas became ready. The [original report](continuation-evidence/full-site-cold-review.json)
is retained. A separate [settled review](continuation-evidence/full-site-settled-review.json)
also remains available; it does not erase the original measurement.

The application now records initialisation separately and begins visible-frame
statistics at readiness. The original acceptance script then passes without
relaxing its threshold or adding a warmup. This is a measurement correction,
not a claim that textures download or compile faster. The earlier narrative
comparison's exact HTML/JavaScript baseline is retained with its original hashes,
rather than rewriting historical screenshots to certify changed source.

### Sustained navigation and memory

The [native profile](continuation-evidence/presentation-profile.json) runs fifty
cycles of training, retrofit, Earth and mine: **200 chapter transitions over
217.2 seconds**, with one second per chapter. The DOM remains at **455 nodes**
and the renderer at **38 textures**. Post-warmup JS heap after explicit collection
ranges from about **36.22 to 36.66 MB**. This is a bounded soak, not proof against
all future leaks or an overnight endurance test.

On that local run, module initialisation is 660 ms and navigation-to-ready about
970 ms. The first measured preparation costs are about 175 ms for authored
learning, 87 ms for the kit and 307 ms for the mine. Resource timings record
21.04 MB transferred during the exercised route. Explicit image decode calls
range from 46.5 to 104.7 ms, with a 10.8 ms image-bitmap call. Native implicit
decode is not separately observable through this probe. Texture count is the
browser's renderer-memory counter, not measured GPU VRAM bytes. No software-
renderer measurement is substituted for native M1 evidence.

The [visibility/resize check](continuation-evidence/visibility-resize.json)
exercises the actual handler with a synthetic `document.hidden` change and
visibility event in native Chrome. The clock holds while hidden and resumes
without catch-up; resize during rapid navigation preserves the latest chapter,
framing and paused clock. This is not an OS sleep or real background-throttling
test. Those manual checks remain part of the open complete visual/interaction
review; no automation is presented as human judgement.

## Verification and release disposition

The CPU suite passes 195 tests with one optional ONNX dependency skip. CI also
runs the existing bounded PPO/checkpoint smoke workloads; their execution does
not imply learned task proficiency. The new stdlib evidence verifier checks all
416 traces, every ledger, frozen checkpoint/source identities, numerical budgets,
model gates, independent replay and native-source hashes. Prior negative policy
and world-model evidence remains protected by its original verifiers.

Technical evidence for #271/#272/#273/#275 is available for closure after merge
and passing CI. Keep #274 open for its remaining real-tab/background and manual
readability/contrast acceptance, together with #351/#385 and #276. No release or
public deployment is performed. Closing research or verified technical tickets
is not a publication decision.

## Next research boundaries

1. Diagnose shared reference failures and collect broader imitation training
   coverage, then freeze new validation/final cases before tuning the actors.
2. Acquire independent rare-event training episodes and recalibrate event heads
   before another matched-budget world-model assistance study.
3. Select concrete read-only hardware interfaces and measure calibration, timing,
   missing data, storage and power-loss behaviour before any machine integration.
4. Complete the maintainer's visual judgement and remaining manual interaction
   checks before production-entry adoption or publication.

These are remaining capability and acceptance boundaries, not successes inferred
from a convincing animation or a few selected runs.
