# ADR-0059: Observation and evaluation boundaries

Status: Proposed

Refs #408, #411, #417–#419, #427 and #428.

## Recommendation

Retain the proposed kit's existing engineering views and connect their roles
to the loader's actual observation contract. Begin integration at read-only
recording, then shadow policy proposals. Machine-specific applied control is
a separate interface. Do not imply stereo images are consumed by the current
65-feature actor or that synthetic height crops are implemented perception.

Version channel timestamps, units, frames, calibration and validity before
feeding machine data into the actor. Keep full simulator state privileged.
Use independent observation/proposal/applied-command streams, explicit loss
and restart handling, and bounded recording/storage measurements. Existing
training EventLog is a useful integrity pattern, not a machine logger.

Separate connectivity from local sensing and physics. The bounded fixed-action
probe verifies that the current sensor wrapper preserves that boundary; it
does not establish policy robustness or a safe response to missing inputs.

Freeze episode-level scenario identities before collection and keep training,
validation and test distinct. Audit seed metadata, schedules, raw archives and
history before reserving untouched tests. Absence of a JSON hit never sets a
reservation to verified. Preserve controller feasibility, expected infeasibility,
prepared starts, collisions and timeouts as separate scorecard categories.

Use all cases in each declared evaluation and show the export's selection rule.
Do not turn selected reference successes into a learned generalisation rate.
Broad robustness testing follows nominal learned proficiency, not the existence
of a visually plausible scene generator.

## Evidence and follow-on work

[Retrofit/observation report](../research/2026-11-13-retrofit-observation-contract.md),
[scenario/evaluation report](../research/2026-11-13-scenario-evaluation.md) and
the retained demo-frontier audit document inputs, probes and unresolved gaps.
Implement observation/log adapters, reservation/identity checks and scorecard
exports before real data/runtime integration. The draft contracts are proposals.

This does not select hardware, change control semantics, grant calibration,
certify unused seeds, supersede production runtime ADRs or publish anything.
Acceptance is limited to future named implementations with their own tests.
