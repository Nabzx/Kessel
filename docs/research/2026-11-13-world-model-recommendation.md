# World-model data, uncertainty and assistance recommendation

Refs #412 and #429–#431. Recommendation: proposed ADR-0060.
Sources: retained world-follow-up report, coverage comparison and executable
weights, verified by `scripts/verify-world-followup.py`; compact facts are in
the [new audit](../phase-11/demo-frontier-evidence/report.json).

## Decision for the next demo: #412

Keep model assistance experimental. The latest equal-reference-budget comparison
has zero complete learned cycles, zero imagined transitions and zero auxiliary
critic updates. It does not show that assistance cannot help; the declared gate
rejects the branches, so there is no successful assisted-learning treatment to
promote. Establish model-free task proficiency before another assistance study.

A retained forecast is useful for explaining the architecture even when wrong.
Show its actual error and raw/filter identity. It is not evidence of successful
policy training inside a learned world model or a deployment-ready digital twin.

## Event-balanced data: #429

The previous targeted collection already increased contact-without-transfer
from 8/8192 to 97/4096 training rows. The newer training corpus has 2,860 free-
motion, 97 contact-only, 1,131 transfer and just eight collision/stuck rows.
It uses inverse-regime sampling. Further weighting repeats the same few failures;
it does not create new failure geometries or improve their independence.

Propose a new bounded corpus only after the intended task/observation contract
is fixed. Cap collection at 8,192 training, 4,096 validation and 4,096 test
transitions. Target 128 distinct training episodes for each collision/stuck
class, not 128 adjacent frames, and report any shortfall at the cap. This is
a proposed coverage goal, not a guarantee that the collection fits the budget.
Include successful contact, missed contact, pickup, retained carry and tipping.
Keep prepared starts explicit and split episodes before balancing rows.

Report both the unweighted declared-corpus result and equal-regime macro result.
Neither is mine-operating frequency. Freeze the collection/controller mixture,
normalisation and selection protocol before fitting. Charge teacher/reference
collection and model calibration separately from subsequent on-policy data.

## Drift and uncertainty: #430

All three latest raw models support zero imagined horizon under their declared
validation gate. The event-head test set has only two collisions and one stuck
event; it misses all three. The stop trade-off reports three false-safe events.
High overall accuracy in such a sparse dataset is not reliable event coverage.

Use common action sequences and episode windows for horizons 1/2/4/8 without
crossing resets. Report position, material, contact/termination timing and
physical violations separately. Keep diagnostic open-loop forecasts, rejected
branches and operationally admitted branches distinct. Do not truncate a bad
diagnostic forecast merely to improve mean error.

Calibrate thresholds/intervals using validation only. On frozen test and shifted
scenes, report coverage, accepted high-error frequency, false-safe, false-stop
and confidence-bin counts. Ensemble disagreement, empirical marginal residual
intervals and hard physical constraints answer different questions. Never label
an ensemble score as a calibrated probability or call an interval a safety bound.

## Observable, privileged and constrained baselines: #431

| Raw model | Position MAE | Mass-balance MAE | Reward MAE |
| --- | ---: | ---: | ---: |
| One-step ensemble | 0.02366 m | 2.735 kg | 0.1569 |
| Material-loss ensemble | 0.02435 m | 1.056 kg | 0.1520 |
| Multistep/material ensemble | 0.04482 m | 0.394 kg | 0.0206 |

Conservation-oriented training improves some metrics while position gets worse.
The imposed bounded filter is a separate method, not evidence the network
learned conservation. Raw violations remain reportable even if a filter repairs
them. Keep persistence and kinematic baselines on the identical cases.

The existing observable model consumes the policy's 65 features plus actions;
the privileged model consumes 102 simulator-state values. Do not compare a
mixed-unit proprio MAE as though it were one physical error or use hidden full
pile mass in the onboard baseline. Compare per-field quantities and validity-
masked range error, and keep latent/hidden-state predictions explicitly privileged.

For a future assistance comparison, freeze a useful model-free baseline, count
all collection/fitting/calibration interactions, isolate actor likelihoods from
imagined critic targets and predeclare a task-success or sample-efficiency goal.
A shorter on-policy run after spending extra offline data is not itself a gain.

## Follow-on specifications

The next work is episode-level rare-event acquisition and per-field observable
evaluation, followed by validation-only calibration and matched-budget assistance
only when its model gate and policy baseline qualify. No new model fit, task
training or model-assisted gain is claimed by this research.
