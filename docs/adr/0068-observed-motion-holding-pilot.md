# ADR-0068: Observed-motion holding pilot

Status: Accepted for the maintainer's continuation on 25 November 2026.
Adds a separately named prototype. ADR-0066/0067's failed holding gate remains.

## Decision

The retained loaded-grade probes brake successfully but can roll downhill during
the following hold. Add `observed_motion_hold` around the complete-coverage
supervisor, retaining its input semantics, phase/clock behaviour and recovery.
Keep original weights, simulator physics, task and checkpoint selection unchanged.

Use only successive observed speed, observed load, elapsed time and the last
applied synthetic drive command to estimate a longitudinal disturbance during
an override. The reference-specific response coefficient is

    b = min(22000, 28000 / max(abs(previous_speed), 0.5))
        / (10500 + clip(previous_observed_load, 0, 3500))

For a consecutive 0.1-second sample, previous override active, previous speed
above 0.1 m/s in magnitude and observed acceleration below 1.4 m/s2 in magnitude,
estimate `d = b * previous_command - observed_acceleration
- 0.1962 * sign(previous_speed)`. Clip d to +/-0.8 m/s2. Replace the estimate
with each eligible sample; do not update at rest or near the kernel acceleration
limit. Reset it at each new override. These are declared engineered assumptions,
not a learned world model, hardware calibration or access to true grade.

During stopping/holding add `d / current_b` feedforward to the existing speed PI
command. Keep its 2/1 gains, +/-0.45 integral and conditional integration.
Other joint rates remain zero. Log accepted/rejected observer samples, estimated
disturbance, response coefficient, feedforward and the actual applied command.
Healthy operation applies the original neural proposal unchanged. Teacher/reference
actions, privileged load/grade, force diagnostics and future samples are forbidden.

This simple observer assumes adequate grip, the reference force law, reliable
proprioception and no unmodelled digging force. Its limitations must be reported.
The pilot does not establish those assumptions for a mine or a noisy sensor feed.

## Frozen comparison and bounds

Repeat exactly ADR-0066's 51 declared practice cases, including 24 partial stops,
three moving-carry complete-loss stops, nine healthy/transient/recovered deliveries,
twelve loaded-grade stopping fixtures and three original healthy controls.
Keep all ten-second hold, speed, distance, detection, trigger and delivery gates
unchanged. Preserve the earlier failed trajectories and compare each grade/speed
condition explicitly. No grade-specific gain or source selection.

One CPU thread, no GPU, 150-second active cap including independent replay,
30,000 evaluation decisions, 28,800 physical replay decisions, 30,600 actor replay
queries, 16 MiB trace archive. Freeze the complete source snapshot and case plan
before any pilot query; outcomes before replay. Guard against teachers. Replay
physical state, observations, canonical input, proposals, actions, phase, clocks
and observer state exactly. Count all costs, including failed or capped work.

Every case/seed, exact healthy comparison and replay must pass to advance the
hypothesis. Do not retune or expand caps after results. This repeats consumed
practice conditions, not held-out evidence or runtime admission. Fresh qualification
still needs its own audited unused cases and predeclared gates. Keep work local
with regular commits; pushing this branch follows the maintainer's separate
authorisation. No browser/service, vehicle interface, release or deployment.
