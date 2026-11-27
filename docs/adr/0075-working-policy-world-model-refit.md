# ADR-0075: Working-policy world-model refit

Status: Accepted for the same maintainer request. Extends ADRs 0040/0041/0062
with a separately identified consumed-practice refit; preserves earlier results.

## Decision

Fit new privileged residual dynamics and local-observation models on complete
working-policy episodes, including the robustness study's failed training cases.
Only base 19010/19011 trajectories may train. Validation uses 19012 and final
practice evaluation uses 19013, never mixing base identities across splits.
All are consumed practice data, not an untouched qualification cohort. Do not
train on prior held-out stress/qualification traces. Episode overlap, missing
transitions or truncated buffers must fail validation.

Reuse ADR-0074 raw episodes to avoid new simulator/teacher costs. Use the frozen
phase-memory-7 policy for a matched collection across all thirteen families on
the same four declared practice bases, capped at 31,200 decisions. These model
data are separate from teacher labels. Preserve complete episodes and all failures.

Train a 64-unit, three-member episode-bootstrap residual ensemble for at most
30 epochs and an observable 64-unit model for 20 epochs. Normalisers use training
only. Fit uncertainty thresholds and select supported horizons on validation only
using the unchanged ADR-0040 gate and fixed-action horizons 1/2/4/8. Compare the
old retained ensemble, new raw ensemble, separately identified bounded filter,
persistence and kinematic forecasts on the same final practice episodes.
Report physical component errors, material/bounds violations, event errors,
accepted high-error fractions, coverage and rare-failure episode counts.

Forecast eligibility still requires supported horizon >=1 and <=10% accepted
high-error rate with nonzero acceptance in every non-blocked family. No scalar
mixed-unit improvement replaces this gate. Raw neural forecasts and imposed
physics/filter corrections remain separate. A passing forecast gate would permit
only a later matched-budget assistance experiment, not prove policy benefit.
If it fails, keep assistance disabled and identify the remaining failure modes.

Cap new collection at 31,200 decisions and one CPU thread. Fit/evaluate at most
6,000 optimiser updates and 256 fixed-action windows per method, with 300 seconds
total wall time, 64 MiB retained artifacts and no subsequent hyperparameter sweep.
Retain data, complete metrics, checkpoint sidecars, source identities and failed
gates. In-process tests and offline CI verification only; no browsers/services.
Commit, push and merge the honest result independently of earlier stages.
