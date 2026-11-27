# Structured local dynamics

The privileged synthetic hybrid predictor passes the unchanged practice forecast
gate. It is not an onboard perception model, fresh qualification or evidence that
model assistance improves policy behaviour. Existing runtimes remain unchanged.

[ADR-0081](../adr/0081-structured-local-dynamics-and-rare-events.md) freezes the
architecture, splits, comparisons and budgets. The complete
[evidence report](structured-dynamics-evidence/report.json) retains every source,
transition, weight, training update and unsuccessful comparator.

## What is learned

Three seeded members fit local acceleration and a shared per-cell extraction
factor. Inputs use current privileged synthetic state, local bucket geometry and
normalised actions. Prediction does not call an environment transition or look up
a future trajectory. Saved weights independently replay retained predictions.

Known kinematics, joint/speed limits, swept geometric collision, throughput,
bucket capacity, material conservation, release, reward and event thresholds are
explicit decoder priors. They are not learned perception or learned conservation.
The separately fitted event logits are evaluated without these event priors too.

## Data

The study reuses complete progress-controller training episodes on 19020/19021,
validation on 19022 and fitted-feedback evaluation on 19023. Failed task episodes
remain present. A controlled ten-second hold is not labelled as an environment
terminal. No final labels enter fitting or uncertainty calibration.

Prepared failure fixtures add 128 actual collision and 128 actual stuck training
episodes, each with distinct seed and initial-state identity. Eight separate
validation/evaluation fixtures complete 316 episodes. All 14,562 new physical
decisions replay exactly. Prepared failures are not successful autonomous tasks.

## Results

| Method | Position MAE, metres | High-error fraction | All-family practice gate |
| --- | ---: | ---: | --- |
| Persistence | 0.06579 | 62.83% | Diagnostic baseline |
| Kinematic | 0.00140 | 9.91% | Diagnostic baseline |
| Earlier retained ensemble | 0.06653 | 99.65% | Fail |
| Previous refit | 0.04183 | 49.56% | Fail |
| Hybrid, explicit event priors | 0.000344 | 0.76% | Pass |
| Same model, learned event logits | 0.000344 | 1.31% | Fail |
| No learned acceleration or extraction | 0.00118 | 6.97% | Diagnostic ablation |

The selected validation threshold supports two decisions, nominally 0.2 seconds.
Every non-blocked family has accepted physically valid predictions and at most
10% accepted high-error rows, including the prepared collision/stuck families.
There are no raw capacity, joint, speed, negative-material or non-finite
violations. Maximum material-ledger error is 5.46e-12 kg, enforced by accounting.
Contact classification still has 117 false negatives and 79 false positives;
passing the declared gate is not perfect event prediction. The event-prior
comparison and ablation show why the model boundary matters.

The one-thread study uses 2,250 Adam updates and 146.55 seconds, within the
420-second and 96 MiB limits. No policy updates, teacher calls or assisted
rollouts occur. New seeds need a separately audited qualification protocol before
runtime admission; assistance needs a matched-budget benefit experiment.

## Reproduce verification

    python3 scripts/verify-structured-dynamics.py
    PYTHONPATH=training training/.venv/bin/python -m pytest training/tests_lab/test_structured_model.py -q

The first command uses only the standard library. It independently reconstructs
coverage, complete transition labels, raw errors, validation-only threshold
selection and per-family eligibility. The numerical test reloads trained weights,
checks training-only normalisation and forbids simulator calls during prediction.
