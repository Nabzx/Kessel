# Working demo runtime, scenarios and reset semantics

Refs #413, #432 and #433. Recommendation: proposed ADR-0060.
Sources: `recorded-data.js`, its tests, the narrative study, the static package
allowlist and `docs/phase-11/offline-policy-evidence/comparison.json`.

## Architecture choice: #413

Recommend validated recorded evaluations as the first working technical demo
interface. The renderer already samples exact saved decisions and interpolates
visual poses without inventing material or actions. This can demonstrate a
real synthetic result while remaining a static, offline-capable presentation.
It cannot demonstrate a live controller or acquire new scenario outcomes.

| Option | What it demonstrates | Additional work and limits |
| --- | --- | --- |
| Recorded evaluations, recommended first | Actual saved policy/reference actions and outcomes | Finite scenario coverage; source identity and terminal failures remain visible |
| Local live simulator + inference | Outcomes for supported parameter changes | Process/session ownership, reset/cancellation, deterministic seed/config binding and an accepted runtime boundary |
| Browser inference | A compatible actor evaluated in the browser | Runtime/model loading, preprocessing parity, simulator availability and hardware testing are not implemented by the current Python CPU export |
| Hybrid | Live technical mode plus recorded fallback | Must announce a mode change; failed live inference must not silently show a successful recording |

Keep the polished concept walkthrough separate from this evidence interface.
No browser training is required to prove a saved policy's proficiency. Live
simulation would reopen the current data-only/runtime ADR boundary and should
follow a concrete technical reason rather than an expectation that a demo must
train in front of its viewer.

## Scenario and reset contract: #432

Use a catalogue of supported recordings, not independent pile/grip/obstacle
sliders that imply an arbitrary physics rerun. A case identity binds generator,
configuration, initial state, seed, source kind, checkpoint/controller and result.
Offer only combinations with a matching result. If the learner lacks a rubble
case, show that absence rather than swapping in reference control.

Changing a scenario pauses first, invalidates displayed metrics/forecasts and
loads/validates the destination before committing the new selection. Latest
request wins. On failure keep the last settled case usable and identify the
failed request; never relabel old output as the new scenario. Bind camera,
caption, source, clock, controls and metrics in the same transaction.

Replay restarts the same case with the same identity. Seeking changes the one
recorded clock, not simulator state generation. Terminal records have no next
action and hold until explicit replay/selection. Pause survives disclosure or
camera changes. An episode reset is labelled, including prepared payload and
whether the machine returns to a new initial state. Missing horizons remain
missing. Forecast comparison freezes an exact action/anchor and actual future.

The narrative prototype already exercises source hand-offs, frozen horizons,
manual replay and camera changes without modifying poses. Existing adapter
tests cover interpolation, terminal boundaries, pause and reduced motion.
A future catalogue UI still needs cancellation/race and counterpart-coverage
checks; the study is not that complete catalogue implementation.

## Inference trade-off: #433

Retained CPU export evidence measures float32 ONNX at 25.291 µs warm median,
14,306 bytes and maximum nominal action deviation 4.35e-7 against its teacher.
Int8 is smaller at 6,825 bytes but has a 0.03934 maximum nominal action error
and a 28.791 µs warm median. Smaller is not a measured speed or fidelity win
in this experiment. Every evaluated variant still has zero complete cycles.

These are old retained CPU actor measurements, not end-to-end control latency,
new browser measurements, edge-device results or proof of useful autonomy.
Cold session scope excludes import and does not flush the OS cache. Do not
transfer the numbers to the proposed hardware. A browser-compatible model
path must reproduce preprocessing, action bounds and outcomes independently.

For a bounded future live spike, compare identical frozen observations and
actions first, then whole rollouts. Record load/first/warm timings, memory,
cancel/reset behaviour and invalid input handling. Report changed trajectories
under a new executable identity rather than retaining the teacher's result label.
Prefer float32 fidelity before compression, and spend effort on task proficiency
before squeezing a currently unsuccessful actor.

## Follow-on specification

Implement a recorded case catalogue and transactional selection using existing
adapters, source-aware scorecards and the task-first explanation. Test missing
files, wrong hashes, rapid selection, absent counterpart cases, frozen forecasts,
terminal holds and navigation during preparation. Live inference remains a
separate optional prototype; it must not delay the first trustworthy recording.
