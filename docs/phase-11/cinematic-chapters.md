# Cinematic chapters and illustrative loader training

Implements #395–#400 under [ADR-0054](../adr/0054-cinematic-surface-and-resumable-chapters.md).
Presentation revision: `2026-11-09.01`. Release and publication remain excluded.

The walkthrough has seven full-screen chapters: Earth, Environments, Surface,
Mine, Training, Inside Kessel and Retrofit. A persistent keyboard-accessible rail
allows direct jumps. Destinations prepare before a short fade; the latest request
wins. Returning retains the environment, mine comparison, film playback position,
training clock, technical chapter step and kit assembly. Replay is separate from
navigation. Document scrolling no longer connects the mine and product pages.

The accepted trained mine, licensed excavator, observation-to-action technical
chapters and proposed retrofit are retained. Enter the mine is rounded with a
green hover/focus state. Discover Kessel is larger and opens Inside Kessel. The
second product world-model button and the confusing experiment selector are gone.

## One training sequence

The authored sequence shows a missed scoop, a partial pickup and three complete
work orders. Each successful order scoops 2 t, reverses clear, hauls along an
articulated turn, raises the bucket and tips into an open receiver. The last order
holds at a detected obstacle and follows a wider clear route. Three separate
evaluation jobs deliver 6 t. Resets between independent episodes are explicitly
labelled. The complete endpoint holds instead of looping or driving away.

Retained samples carry machine pose, velocity, articulation, bucket actuation,
individual tyre rotation, source mass, payload, material in flight and receiver
mass. The display reads this trace. It does not invent success at render time.
Bounded acceleration, rear-axle tangency and the front axle rolling constraint are
checked independently. Dense samples check body and tyre clearance, bucket
clearance past the obstacle, scoop engagement, tipping height and receiver
alignment. Minimum tyre clearance to scene obstacles is 0.45 m. Every displayed
interpolation conserves the per-episode 3,000 kg material ledger.

The compact panel shows represented episodes, relative reward, current work
order, completed jobs, payload, delivery, simulated time and observation/action/
reward. Floor labels identify the load, receiver and physical obstacle. The
transparent rollout boxes and ghost forecasts are absent from this main view.

This is an illustrative kinematic demonstration, not a granular physics solver,
live training run, measured learned policy success or calibrated mine digital
twin. Episode counts and reward values are authored. The measured experiments and
their unsuccessful learned delivery outcomes remain unchanged in research files
and the retained adapter. Contextual labels and Sources explain the distinction.

## Original surface animation trial

The local Blender scene uses scanned CC0 metal, concrete, rock and ground
references, a CC0 MakeHuman core body with original workwear/PPE, an original
Kessel truck and a representative cleared HDR sky. The packed `.blend`, reviewed
scripts, source references, credit links and output hashes are retained.

The film is a 24-second, 1296 × 810 H.264 loop, 1.71 MB. Source motion uses a
9 m rear-axle radius at 2.36 m/s, per-side Ackermann steering and individual tyre
travel. There is no engine smoke or dust plume in the film. The real-time fallback
emits restrained dust at retained rear tyre contacts, then advects it in world
space. It no longer uses a stationary trail beside the truck.

The render samples alternate frames from the 24 fps source and blends to a
24 fps output. The encoder fully decodes a temporary MP4 before atomically
replacing the served asset. The integrity check reads the actual MP4 movie clock
as well as checking file hashes. The browser pauses media outside the chapter,
resumes it on return and uses a still by default for reduced motion. A failed
video switches to the prepared real-time surface. No remote service or key is
required by playback.

This visual direction is a trial for maintainer judgement. It is original CGI,
not real Rutongo footage or an approved photorealistic reconstruction. #385
remains the visual review; the prototype judgement in #351 is also kept open.

## Verification

The native walkthrough passes on installed Chrome 156 with the Apple M1 Metal
renderer at 1440 × 900 / DPR 2, 1365 × 768 / DPR 1 and 1280 × 800 / reduced motion.
The [retained report](cinematic-evidence/report.json) records zero console, page
or HTTP errors on the complete routes. Settled samples range from 59.7 to 60 fps,
with p95 frame time 16.8 ms. These are local laptop measurements, not mobile or
universal hardware qualification.

The browser checks all seven chapters, movie progress and pause/resume, green
entry hover, trained-mine restoration, training pause/resume, all three successful
jobs and final material totals, terminal hold, replay, five resumed technical
chapters, resumed kit assembly, rapid navigation, keyboard controls and the absence
of document scrolling. An unavailable training trace retains the old chapter and
recovers on retry. The [HTTP-cache and mine-asset recovery checks](cinematic-cache-evidence/report.json),
[media fallback and cancellation checks](cinematic-recovery-evidence/report.json),
and [orbital-home checks](cinematic-home-evidence/report.json) retain separate evidence. The encoded film also passes a full local FFmpeg decode.

The geometry/material audit, interpolation and clock tests, recorded adapters,
height-field tests, reference preparation tests and static asset/evidence checks
pass. Packaging includes the film and training trace while excluding Blender
sources and experiment tooling.

ADR-0054 also records the maintainer's explicit permission to close implemented
work before a tag. The [closure record](implemented-ticket-closure.json) lists
219 previously merged implementation tickets closed from the pre-change baseline.
This does not close outstanding review work or authorise a release.
