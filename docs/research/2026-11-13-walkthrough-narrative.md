# Walkthrough narrative, first-minute comprehension and camera study

Refs #407, #415 and #416. Recommendation:
[proposed ADR-0058](../adr/0058-task-first-narrative-study.md).

## Recommendation

Lead with one loader and one complete job. Connect observation, prediction and
policy learning to that job before showing the proposed retrofit. Keep Earth,
environment selection and the surface as optional context. Retain the current
production opening while the isolated research prototype is reviewed.

The [interactive study](../phase-11/narrative-study/index.html) compares two
openings with the same five-beat body. It executes no training. It reads the
existing hash-validated synthetic reference and curriculum bundles, using the
existing loader asset and replay sampler. The main walkthrough is unchanged.

## Current experience audit

The current primary CTA route is Earth, environment selection, surface, mine,
comparison, training and product detail. The persistent chapter rail already
allows direct jumps. The issue is first-entry emphasis, not missing navigation.

The authored training sequence shows three successful jobs. The UI combines
"World-model training", "Reinforcement learning", "TRAINING", represented
episodes and a relative reward curve. A nearby illustrative label and Source &
method explain its origin, but the largest visual cues resemble measured
learning success. Keep authored illustration separate from actual research.

Technical chapters already cover perception, prediction, policy export, offline
operation and fleet learning. They load different records for different views.
A new route needs an explicit hand-off whenever it changes experiment identity;
one loader mesh must not imply one continuous episode or a successful learner.

Current sources: `index.html`, `js/experience.js`, `js/training-stage.js`,
`js/technical-chapters.js`, ADR-0054/0055. The study retains current screenshots
of Earth, environment selection, surface and authored training, plus their
native Chrome diagnostics in its evidence directory.

## Design plan and critique

Preserve the existing industrial direction. This is a research interface within
Kessel's established identity, not a new marketing theme.

| Token | Value and purpose |
| --- | --- |
| Ground | `#050a0c`, the unlit space around the worksite |
| Ink | `#eeeae0`, copy and the reference-future point |
| Muted | `#a4ada9`, secondary explanation |
| Ore | `#d6aa6b`, primary action and contextual source identity |
| Observed | `#9cd6bc`, recorded height samples and action values |
| Forecast | `#9dbfe4`, the learned forecast marker |

Use the existing Space Grotesk for text. Reserve the existing JetBrains Mono
for numeric/action readouts. Put the recorded worksite on the left and the
explanation on the right. Keep source identity at the point of interpretation,
two physical metrics, a short action, and an optional source disclosure.

```text
Kessel         route comparison: Mine first / Current opening

Recorded worksite                         One question
  pile, loader, receiver                  Plain explanation
                                         Recording identity
  observed samples when requested         Payload / Delivered
                                         Inspect the source
  camera / replay controls                Back / Next

Task   Observe   Predict   Learn   Retrofit
```

The first visual pass had long headings and a forecast panel buried in the
copy column. Screenshots revealed that the explanation displaced navigation
and the quantitative comparison required scrolling. Shorten the headings and
move the labelled magnified forecast into its own reserved region. The final
desktop checks require primary copy/actions to fit without scrolling. This is
the intentional visual emphasis; do not add decorative telemetry cards.

## Route alternatives

| Route | Opening | Core body | Editorial duration target |
| --- | --- | --- | --- |
| Current opening | Earth → environments → surface | Same five task beats | About 90 s |
| Mine first, recommended | Task visible immediately | Same five task beats | About 60 s |
| Technical depth | Mine-first route, source disclosure and optional overlays | Same task and honest source boundaries | Self-paced |

These durations are editorial budgets, not measured comprehension or loading
times. The prototype pauses initially, including under reduced motion. The
viewer explicitly plays recordings; the story does not advance automatically.
The context-first prototype uses still captures of the existing opening, not
a rebuilt Earth or a new surface film. Neither route is a production replacement.

## First-minute storyboard and spoken script

| Time budget | View and viewer question | Suggested narration |
| --- | --- | --- |
| 0–10 s | Whole job: what work must happen? | "One loader needs to move at least two tonnes from this pile to that receiver. This recorded reference controller completes the task." |
| 10–22 s | Observed samples: what information is available? | "The machine observes nearby pile heights, its pose and its payload. These recorded samples are the inputs, rather than a complete map of everything underground." |
| 22–35 s | One action and forecast: what does the world model do? | "A learned world model predicts what happens after an action. We compare its forecast with the reference simulator. Here you can inspect the actual error." |
| 35–48 s | Explicit new recording: what does the policy do? | "Reinforcement learning trains the policy that chooses actions. This separate research run picks up material but hits a wall. We have not completed a learned delivery yet." |
| 48–60 s | Proposed retrofit: where is this intended to run? | "The proposed retrofit connects sensors, local compute and the machine interface. The goal is to keep the sensing and action loop onboard." |

The goal is a clear causal story, not an implication that model-free policies
were trained inside the displayed learned world model. Reference simulation,
learned prediction and the policy are different components.

## Recording hand-offs and progressive disclosure

- **Task → Observe → Predict:** first reference episode. The observation uses
  its first loaded scoop record. Prediction uses its first scoop-phase record
  with a retained four-decision forecast. That is an explicit time seek within
  the same episode, not continuous playback from the preceding frame.
- **Predict → Learn:** change to the first declared curriculum policy episode.
  Show "New recording · learned policy · seed 7" and its actual terminal failure.
  Replaying exposes its earlier actions. Do not describe it as a later checkpoint
  of the successful reference controller.
- **Learn → Retrofit:** return to the reference machine illustration as a
  backdrop and switch the source to proposed architecture. This is an
  explanation of intended hardware roles, not an installed kit or a field test.

The first level contains the task, plain copy, current source and physical
payload/delivery. The second level offers recorded observation points, signed
normalised actions, replay/scrub and a forecast horizon. The third level gives
run identity, controller/checkpoint hash, outcome and limitations. Do not make
a viewer read hashes to understand the task, or open details to learn that a
conventional controller is responsible for the successful cycle.

## Camera and annotation findings: #416

Use a fixed whole-job camera for the primary route. Build its envelope from
the visible articulated mesh at every recorded pose and interpolated midpoint,
plus source pile and receiver bounds. Reserve header, copy, playback and rail
space before fitting. Do not move a machine, cut a failed frame or clamp pose
coordinates to make the composition attractive.

The study compares that camera with an explicitly selected contact-detail view.
The latter may exclude the receiver and can lose a moving loader; it is an
inspection tool, not a replacement for the full-task camera. Label that loss of
context and preserve the recording time/pose when switching lenses. An automatic
follow camera is not recommended here because it changes orientation and hides
the source-to-receiver relationship.

Show the observed heights in their recorded bucket-relative frame. Invalid
samples remain absent. These points represent pile heights; they do not prove
wall, person or obstacle detection. Put drive/steer/boom/bucket values in a
readout instead of drawing an invented future route.

At full job scale, the retained rear-axle forecast difference is too small to
explain with large ghost machinery. Use a separate magnified displacement view
with its axis extent in metres, actual future point, learned point and measured
position error. Freeze its anchor and disable playback/scrubbing while comparing
horizons. Physical-check failures remain visible. No forecast is fabricated for
a missing horizon, and a model spread is never presented as a probability.

Annotated frames are retained for Task, Observe, Predict, Learn, Retrofit and
contact detail in the study evidence directory. Captured poses and source
identities are available in the accompanying browser report.

## Comprehension review: #415

This review has not been conducted. Automated browser checks cannot establish
that a first-time viewer understands the story. When reviewers are available,
use six independent viewers unfamiliar with the repo, three assigned to each
opening. Keep the five-beat body and prompts identical. Do not teach terms in
advance or reuse a viewer across both routes for a first-exposure comparison.

After the first minute, hide the screen and ask:

1. What job was the loader trying to complete?
2. What controlled the successful run you saw?
3. What did the learned world model predict, and what was it compared with?
4. What happened in the learned-policy recording? Was it the successful run?
5. Which part of the retrofit is demonstrated hardware, and which is proposed?

Score each answer 0 or 1 using the script's stated facts. A session passes at
4/5 only if answers 2 and 4 are correct. Treat confusing reference success with
learned success as a failed comprehension boundary regardless of total score.
Record exact misunderstandings, time to identify the task, route, optional
details opened and source labels noticed. With six viewers, report qualitative
findings and raw counts; do not claim statistical superiority.

Use the results to revise wording and ordering. Existing visual acceptance
#351/#385 remains separate. No reviewers were contacted by this investigation.

## Follow-on implementation proposal

After the route recommendation is settled, specify a production task entry
using existing chapter preparation/state logic; a first-run guide linking the
same source through observation/prediction; explicit recording hand-offs; and
the tested whole-job/detail camera contract. Preserve the existing globe,
surface film, kit inspection, keyboard rail and reduced-motion behaviour.

Do not rebuild already implemented technical chapters, publish the research
page as the product, or present the chosen successful reference case as a
benchmark aggregate. Broader scenarios and complete failed outcomes remain in
the retained research. This route explains the product direction while the
separate capability work establishes whether a learned policy can do the job.
