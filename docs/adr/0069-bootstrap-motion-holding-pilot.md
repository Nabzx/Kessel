# ADR-0069: Bootstrap observed-motion holding

Status: Accepted for the maintainer's continued work on 25 November 2026.
Adds a new method; ADR-0068's rejected observer and all gates stay unchanged.

## Frozen changes

Add `bootstrapped_motion_hold`, retaining the complete-coverage contract,
original neural weights, phase/clock rules, speed PI gains and reference kernel.
Use ADR-0068's observed-motion response coefficient and disturbance equation,
with no true grade or privileged load.

At the first override, if observed speed magnitude exceeds 0.03 m/s, apply a
gentle -0.25 * sign(speed) drive for one decision. Otherwise use the existing
speed PI command. Log this initial probing command separately from the proposal.
This intentionally changes braking availability/response and must pass the same
stopping-distance and detection gates. It is not guaranteed for arbitrary speeds.

Accept force samples only when previous and current observed speed magnitudes
both exceed 0.03 m/s, their signs agree and observed acceleration magnitude is
below 1.4 m/s2. Reset disturbance/validity at each new override. Clip the estimate
to +/-0.8 m/s2. Do not fit it at rest, across reversal or at the acceleration
limit. The first eligible estimate becomes available without a filter.

Once an estimate is valid, add its feedforward as before. When speed is within
0.08 m/s, clear the old PI integral before applying the hold command; otherwise
retain the parent's bounded conditional integration. Log every accepted/rejected
sample, probe, estimate, validity and integral reset. Healthy neural controls
remain unchanged. All malformed-input and recovery boundaries are retained.

This is an engineered reference-specific law with reliable-proprioception and
adequate-grip assumptions. Static force is not inferred from a resting sample.
The grade observer can become valid only after observed motion. No model,
threshold or gain is trained or reselected after this protocol.

## Cases and limits

Repeat all 51 ADR-0068 practice cases with unchanged criteria. Add six declared
nonempty stopping fixtures: each neural seed, each +/-0.06 rad grade, initial
speed zero, 2,500 kg onboard. Preserve material mass as in the existing fixtures.
They test acquisition of a disturbance estimate after cold-start motion; they
are not empty-start deliveries or fresh held-out conditions.

Total 57 cases, including 54 supervised physical traces and three original
healthy comparators. Every one of 45 stops and nine supervised deliveries must
meet its own unchanged criterion. Require ten-second nonterminal holds, peak
speed <=0.10 m/s, hold path <=0.25 m, settling within 2.5 seconds and path <=2 m,
all-seed zero collisions and exact healthy comparisons. Unreached triggers fail.

One CPU thread, no GPU, 150-second total active cap including replay, at most
30,000 evaluation decisions, 28,800 physical replay decisions and 30,600 actor
replay queries, 16 MiB trace archive. Keep the 600-decision per-case limit; the
global cap takes precedence over completing all cases. Freeze exact sources and
case plan before querying; outcomes before replay. Guard teacher calls and count
all costs. Preserve partial/capped and failed results without retuning or reruns.

Replay observations, canonical input, raw proposals, applied actions, phase,
task clock and complete observer state exactly. Advance only if every declared
case, unchanged weights and all replay/healthy gates pass. Fresh qualification
needs a separate protocol and audited unused scenarios. No runtime promotion,
field-safety claim, browser/service activity or deployment. Local commits and
the separately authorised branch push remain the work boundary.
