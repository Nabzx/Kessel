# Guided walkthrough and engineering chapters

Implements the remaining presentation work in #349 under ADR-0053. Presentation
revision: `2026-11-08.10`. Release and publication work remains excluded.

The learning entry now plays one complete conventional reference cycle and holds
its successful terminal record. Policy checkpoints and curriculum seeds remain
separate, inspectable experiments with their actual failed delivery outcomes.
The main panel shows phase, payload, delivered mass and simulated time. Source,
checkpoints, forecasts, curves, timeline and provenance use progressive disclosure.
Continue returns to the product explanation.

Camera fitting uses visible articulated mesh bounds at every recorded pose and
midpoint, source/receiver bounds and the actual panel/header rectangle. The same
fit is recalculated on resize. Ghost predictions never force the task camera away.
No physical pose is clamped, deleted or moved to keep it visible. Constant source
rates and tolerance for rounded range-input endpoints fix abrupt speed changes and
terminal seeks. Reference replay respects the selected case; initial guided entry
starts at the successful baseline. The material ledger is unchanged.

The surface includes a closed Blender excavation with a horizontal adit cavity,
an axial tunnel shell, steel sets, dark depth, cleared photographic sky, broken
foliage silhouettes, two authored workers, an unobstructed gate and one slow hauler.
Wheel travel follows the authored route derivative. Ground and source geography
retain their existing scanned materials and regional data. The underground section
uses fractured closed masses, supported edges, rock-textured caps and narrower
route lines. The licensed excavator remains in use.

Prepared fades replace the problematic portal flight. Cancellation, retry, stale
source requests, visibility changes and reduced motion leave usable states. Models
are requested with the presentation version and vehicles finish loading their
visual detail before scene preparation. A cached model cannot conceal an update.

The proposed kit begins assembled on a mounting plate. Sensors detach first, then
the lid and boards. It includes fasteners, fins, gasket land, connector contacts,
board supports, spreader, headers, capacitors and routed harnesses. Next/previous,
pause and assembly use one presentation amount. The detailed physical source and
browser magnification remain distinct. See the [hardware brief](../research/walkthrough-completion.md).

Five optional chapters use a lightweight canvas alongside the existing renderer:

- Perception: retained 5 × 5 height crop and validity mask, schematically projected.
- Prediction: one recorded anchor with actual action and 1/4/8-decision futures,
  reference residuals and visible physical violations.
- Training/export: measured PPO counters/curve and integrity-bound CPU export sizes.
- Offline operation: an authored communications event alongside recorded reference
  motion, with local sensing/policy/actuation kept distinct from the external link.
- Fleet learning: proposed buffering, conditional synchronisation, evaluation and
  policy release, followed by future environment directions.

The original world-model experiments remain unchanged. No learned complete delivery
cycle, field deployment, certified kit or Jetson latency has been demonstrated.

## Verification

Native Google Chrome 156 with ANGLE Metal / Apple M1. Full normal-motion Retina,
compact and reduced-motion routes are retained in [the report](walkthrough-evidence/report.json).

| Profile | Viewport / DPR | Settled mean | p95 |
|---|---|---|---|
| Retina | 1440 × 900 / 1.5 capped | 60 fps | 16.7–16.8 ms |
| Compact | 1365 × 768 / 1 | 60 fps | 16.7–16.8 ms |
| Reduced motion | 1280 × 800 / 1 | 60 fps | 16.7–16.8 ms |

The [final route video](walkthrough-evidence/walkthrough.webm),
[route diagnostics](walkthrough-evidence/final-route.json) and
[cache recovery](walkthrough-evidence/cache-recovery.json) accompany the frames.
The main-route response bodies, including the proposed kit, total
20.67 MB, below the 28 MB budget.

These are settled samples, not a claim that first-use uploads have no long frames.
The first visual pass exposed an early Retina surface sample at 53 fps. Vehicle
readiness, preparation and foliage cost were corrected; final settled samples pass
the 55 fps / 20 ms budget. No browser or normal-route HTTP errors were recorded.

The browser regression checks all recorded sources/checkpoints, start/intermediate/
terminal seeks, full projected envelope, bucket-mouth alignment, conserved material,
forecast horizons, authored-source labelling, chapter navigation and assembled/open
kit states. Recovery checks cover cancelled arrival, missing sky, missing reference,
retry, failed-case classification and latest-source selection. Real browser-cache
migration and missing-entrance recovery are checked separately.

Run `node scripts/verify-walkthrough-completion.cjs` with localhost:8080 available.
Playwright remains installed in the parent tooling directory. Historical recorded
and cycle-viewer commands delegate to this current acceptance suite. Use
`KESSEL_QA_VIDEO=1` to retain a complete route video. Source/asset validators,
height-field/clock tests and official Khronos glTF validation also pass. New and
changed GLBs have zero validator errors; the retained licensed excavator has its
existing warning. Editable Blender sources and authoring scripts remain in tools.

## Visual review

Captured frames were inspected for portal depth, section support, full loader
visibility, hardware seating, material response and short-screen layout. The source
pile is still a coarse synthetic height field; its cell volumes are preserved
rather than replaced with an invented physical result. Visual approval belongs to
the maintainer and is not inferred from these tests. #351 and #385 remain review
items. Merged build tickets await the explicitly deferred tagged release.
