# Five-stage task and retention implementation

16 November 2026. Refs #410, #423 and #424.
Protocol: [ADR-0057](../adr/0057-model-free-skill-proficiency-protocol.md).
[Measured reference cases](five-stage-evidence/report.json).

## Result

The conventional reference controller completes all 16 consumed validation
scenes in each of five stages: fill, retract, carry, tip and complete. All 80
traces replay from fresh simulators with zero state/reward error. There are
9,712 reference decisions and 9,712 independent action-replay decisions.
The largest material-ledger residual is 5.46e-12 kg. No policy training or
final-test evaluation occurs in this work.

This demonstrates feasibility in the nominal synthetic task. Prepared stages
initialise the reference controller's internal phase explicitly. The complete
stage starts empty and uses its ordinary initial phase. These are reference
results, not learned skill retention, learned chaining or a working learned
full-cycle demonstration. These validation scenes were already consumed by
the retraction study; this is not a new held-out capability claim.

## Implemented contract

`training/kessel_training/five_stage.py` adds a separate environment. The legacy
four-stage curriculum, raw reward and physical dynamics remain unchanged.

| Stage | Initial payload | Success |
| --- | ---: | --- |
| Fill | 0 kg | Carry at least 2,200 kg |
| Retract | 2,200 kg | Reverse 1 m, boom at least 0.2 rad, curl at least 0.4 rad, carry at least 2,100 kg |
| Carry | 2,200 kg | Existing receiver approach bounds, speed below 0.2 m/s, carry at least 2,100 kg |
| Tip | 2,200 kg | Deliver at least 2,000 kg |
| Complete | 0 kg | Deliver at least 2,000 kg |

Every prepared load is deducted from the pile. Tip begins with boom 0.35 rad,
curl 0.9 rad and the mouth centred over the receiver; it is not already dumping.
Every reset checks clearance before actions and refreshes observation caches.
Stage changes reset environment/history. Tip delivery is a stage success,
but only an empty-start complete-task delivery is a full success. Collisions
cannot count as stage success. Finished slots must be reset before stepping.

The shaping version is `five-stage-potential-v2`. Fill potential uses 2,200 kg;
tip potential is zero and its base incremental delivery reward supplies credit.
Other potentials follow the existing contract. Raw reward, shaping and stage
bonus remain separate telemetry fields. With shaping disabled the complete
stage receives only the unchanged raw task reward.

Checkpoint envelopes distinguish this environment from the legacy curriculum.
Cross-contract restores fail closed. Tests restore every stage and reproduce
observations, rewards and pile states exactly after subsequent actions.

## Retention gate

Automatic legacy advancement is disabled for this environment. The explicit
`advancement_gate` requires a qualifying latest 32-episode training window
(at least 23 successes), a 4,096-decision stage boundary within the 32,768-decision
budget, exactly 16 current-stage validation outcomes with at least 14 successes,
and exactly 16 outcomes for every prior stage with at least 12 successes each.
Missing, partial or non-Boolean results fail closed. The final stage cannot
advance. Tests cover regression, boundary and threshold cases.

The gate is a decision function, not an experiment runner. Its caller must bind
outcomes to the frozen policy and reserved validation identities, charge every
evaluation action separately and preserve optimiser/model state across stages.
This work does not claim that any learned policy passed these new gates.

## Evidence and checks

`five-stage-evidence/traces.json.gz` retains all actions, pre/post states and
training rewards for all 80 cases. `source.zip` contains the exact training
package, dependency declaration and lock. `files.json` hashes the retained files.
The result source is commit `46f7865`. The standard-library evidence verifier
runs in CI. The training suite passes 167 tests with one optional ONNX dependency
skip, including ledger, thresholds, collision precedence, masked reset,
cross-contract restoration and retention-gate tests.

To reproduce the reference audit from its recorded source:

```sh
cd training
.venv/bin/python -m kessel_training.verify_five_stage --output /tmp/new-five-stage-audit
.venv/bin/python -m kessel_training.verify_five_stage --verify --output /tmp/new-five-stage-audit
```

Each additional verification consumes another 9,712 replay decisions; it is not
additional training evidence. Later package changes require the archived source
for exact-source execution. Never reuse the consumed validation range as a fresh
test range.

## Next step

Implement the bounded conditional-comparison runner with stage-budget stopping,
checkpoint/resume, provenance-bound current/prior validation, deduplicated
empty-start checkpoint selection and separate evaluation counters. Reference
feasibility and gate unit tests now pass. Freeze and interruption-test that runner
before the proposed six-run comparison. Preserve the failed pilot seed and do
not assume 1,500 kg pilot policies transfer to this contract. The default
walkthrough and final-test role remain unchanged.
