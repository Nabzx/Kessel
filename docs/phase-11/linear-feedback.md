# Learned linear feedback with conventional planning

The fitted feedback layer matches the corrected reference's outcomes on all
thirteen final practice settings. Each method meets 12/13 criteria: ten deliveries
and two controlled stops. The low-pile case times out with 1,994 kg carried and
no delivery. It remains a failure for both methods. No runtime is broadened and
no all-family qualification or improvement over the matched reference is claimed.

Protocol: [ADR-0080](../adr/0080-linear-feedback-imitation.md).
[Complete report](linear-feedback-evidence/report.json), training data, fitted
weights, raw traces and fit ranks are retained. The original deep imitation
policies and their earlier results remain unchanged.

## What is learned

A four-output sparse linear layer with a hard normalised action limit learns
six feedback gains from current error/integral/direction features. Rank-checked
least squares uses unsaturated teacher outputs. No coefficient is copied from
the reference implementation. The recovered drive gains are approximately
1.8, 1.0 and 0.12; articulation, boom and bucket gains are approximately 2, 4 and 4.
The offline verifier reconstructs every applied learned task command from the
retained matrix and current six-feature input. CPU tests reload actual weights
and reproduce the training labels.

Tactical memory, collection lanes, setpoints, range grace, integral state and
stopping remain conventional. These form the explicit controller context.
The learned layer supplies task commands during evaluation with no reference
fallback or weight update. Conventional stopping overrides are identified
separately. This is deterministic linear imitation, not deep RL, learned task
planning, implemented perception or learning inside a learned world model.

Training labels come only from the selected successful development episodes on
bases 19020/19021. The failed low-grip episode is excluded from labels by the
predeclared rule and remains fully retained in the original study. Override
commands never label the learned task layer. No validation/final label is used.
Final comparison uses base 19023 for every family and both sources, without
removing the underfilled result or calling a timeout a delivery.

## Costs and verification

Four least-squares solves and no gradient optimiser updates fit the model.
The matched comparison charges 6,432 physical/planning decisions and 3,216
independent replay steps in 46.71 seconds on one CPU thread, below the
16,000 / 8,000 / 180-second caps. The legacy counter named `teacher` measures
conventional planning calls for both sources; no new labels are queried while
fitting or evaluating. Learned inference and action-replay calls are recorded
separately. Independent physical and controller replay is exact for the applied
learned commands. Nothing is sent to a vehicle.

The known low-pile miss still needs collection coverage/return-time work before
a broader controller admission. A passing practice setting alone would not
replace independently reserved qualification.

```sh
python3 scripts/verify-linear-feedback.py
PYTHONPATH=training training/.venv/bin/python -m unittest discover -s training/tests_lab -p test_linear_feedback.py -v
```
