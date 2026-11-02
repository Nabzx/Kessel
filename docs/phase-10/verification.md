# Phase 10 verification

## Target and method

Verified in installed Google Chrome 156.0.8078.74 on the Apple M1 using native
ANGLE Metal graphics. Laptop layouts: 1280 x 800 and 1440 x 900. The main
recording used device scale factor 2; render DPR is capped at 1.5. This is a
local static-server run, not a claim about cold internet delivery or phones.

`node scripts/verify-experience.cjs` passes eight acceptance groups. The
report and [browser frames](visual-review.md) are retained. The full recording
is attached to the v0.10.0 release. The recorder includes optional exploration
and repeated comparisons, so it is longer than the 60-second presenter route.

## Measured steady rendering

| Scene | Mean fps | p95 frame ms | Draw calls | Triangles |
| --- | ---: | ---: | ---: | ---: |
| welcome | 60.0 | 16.7 | 15 | 71176 |
| surface | 60.0 | 16.7 | 55 | 129126 |
| baseline | 60.0 | 16.8 | 145 | 48538 |
| trained | 60.0 | 16.8 | 144 | 47338 |
| learning | 60.0 | 16.7 | 45 | 8990 |
| kit | 60.0 | 16.8 | 30 | 3046 |

Earth became interactive after 743 ms on localhost. Loaded mission
assets total 7.85 MiB; vendored libraries and fonts add 1.40 MiB.
These are encoded transfer sizes, not decoded GPU memory. The prepared kit
lighting adds 1.5 MiB and removes live reflection prefiltering. The first globe
loads under the 3 MiB mission-asset target; the full experience stays below the
10 MiB stage-asset target. Geography, materials and the excavator load
progressively; training and kit assets are optional.

The final diagnostics report 30 textures after visiting all views. The focused run measured
20.4 MiB of JavaScript heap after entering the mine and comparing policies; actual driver VRAM is
not exposed and is not inferred from compressed image size.

## Transition tails

The recording includes first shader/texture use and screenshot overhead.
Its worst observed entrance frame was 750 ms; the flight max was
167 ms and comparison max 367 ms. Their p95 intervals were
33.4, 16.7 and 16.8 ms respectively. These tails
are disclosed separately from warmed scene rendering. New scene assets still
incur first-use GPU work. The comparison retains its light inventory while
fading machines to avoid unnecessary shader variants.

## Acceptance

- Five carousel themes; only underground deploys.
- All six GBP measures match same-batch arithmetic.
- Before/after is repeatable; weak connectivity retained.
- Training pause, resume, 2.4m completion, three checkpoints, replay and Escape return.
- World-model entry from product restores scroll and result.
- Seven proposed kit parts; assembly and keyboard focus.
- Laptop layouts, sources and native dialog dismissal.
- Missing terrain retries, reduced motion and full restart.

No console errors, JavaScript exceptions or unexpected failed asset requests
were reported in the main run. The failure-recovery run deliberately aborts
terrain once, then retries successfully. The data validators check route
references/directions, rock clearance, vehicle count, GBP same-batch arithmetic,
training keyframes and kit references. Legacy mission validation remains green.

## Visual corrections

The maintainer approved the direction and requested an upright Earth,
correct labels and smoother trained-site switching. Bitmap resizing now
specifies imageOrientation: flipY, matching the north-up day, night and cloud
textures. Markers and labels remain fixed to latitude/longitude on the rotating
globe. The comparison uses a moving scan, eased machine/route opacity and a
soft metrics hand-off. Captures show the corrected geographic orientation.

## Limits

The surface and mine foreground are authored. Sentinel imagery is 10 m
regional context; no survey of underground Rutongo is claimed. Checkpoints,
2.4 million represented episodes, rewards and operating figures remain
illustrative. The kit is proposed. The pipeline does not run learned dynamics,
RL training, policy distillation or autonomous machine control in this browser.

A focused native-GPU run without screenshot/video capture exercised the normal
3.8-second scan after the final light-inventory correction. Its maximum
comparison frame interval was 16.8 ms across 228 frames; the following warmed
mine sample averaged 58.7 fps. No console error was reported. See
[focused measurements](focus-verification.json).
