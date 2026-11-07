# ADR-0047: Reference repair and replay evidence

Status: Accepted

## Decision

Resolve #305 with an audited synthetic reference before new optimisation.
Preserve the legacy default dynamics and retained failures. Add explicit opt-in
pile families, independent action replay, integration/reset/material reports
and a renderer rig whose rear axle, articulation joint, front axle and mouth
share ADR-0036's physical frame. A reference-controller success is never a
learned-policy success. Keep failed cases and prepared-start payload labelled.

Use held-out validation/test seed ranges and split episodes before sampling
rare-event rows. Add explicit observable-only and privileged model variants.
Sensor latency/dropout wrappers may alter observations but never communication
status or reference dynamics. Conservation-constrained model outputs remain
separate from raw predictions. Evaluate multistep pose, material and event
errors, false-safe forecasts and calibrated rejection on held-out episodes.

Bound the follow-up CPU study before execution: three seeds (7, 19, 41), at
most 16 PPO rollouts per declared alternative, four environments and 64 steps
per rollout; no checkpoint selection on test seeds. Compare feed-forward,
stacked-observation and model-assisted alternatives against untrained and
observation-only reference controllers on identical held-out complete starts.
Use at most three ensemble members and 40 epochs per declared model variant.
Report actual environment decisions, fit time, imagined updates, rejected
branches and full-cycle outcomes. An unsuccessful comparison completes a
bounded research question, not a proficiency claim.

Recorded playback uses one configurable clock with explicit terminal holds and
selection metadata. Pose interpolation never changes material or event timing.
A coherent cell-boundary height surface replaces floating columns without
changing the authoritative height integral. Material displays use logged ledgers;
visual fragments never add material. Reference, observed crop and raw forecast
retain distinct shapes and labels. Verify independent exports and native Chrome
before merging. No release/tag/publication work is authorised by this decision.

Refs #305, #307–#330, #261.
