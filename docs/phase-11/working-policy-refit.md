# Working-policy world-model refit

The new models improve several measured forecasts but still fail the all-family
eligibility gate. Assistance stays disabled. No policy is trained inside these
models and no learning-efficiency gain, new runtime admission or fresh
qualification is claimed.

Protocol: [ADR-0075](../adr/0075-working-policy-world-model-refit.md).
[Complete report](working-policy-refit-evidence/report.json), raw trajectories,
train/validation/evaluation datasets, saved weights, predictions and source hashes
are retained in `working-policy-refit-evidence`. Existing models and their earlier
negative results remain unchanged.

## Data and fitting

All thirteen original families are represented by complete seed-7 phase-memory
policy episodes. Training uses bases 19010/19011 (26 episodes, 8,952 transitions),
validation uses 19012 (13 episodes, 5,993 transitions), and final practice
evaluation uses 19013 (13 episodes, 4,636 transitions). Base identities remain
separate across roles. These are consumed practice data, not audited untouched
tests or independent mines.

The thirteen original seed-7 evaluation episodes are reused from ADR-0074.
Its conventional teacher labels and rejected neural candidate trajectories are
excluded from model fitting. The remaining 39 complete trajectories execute the
frozen working policy, costing 14,945 new simulator decisions and no teacher calls.
All failed training episodes remain included; validation and evaluation outcomes
do not change the training corpus, weights or gate limits.

A three-member, episode-bootstrap, 64-unit residual ensemble fits for 30 epochs;
the predeclared raw validation score selects epoch 11. A separate 65-feature local
observation model fits for 20 epochs. Both normalisers use training only. The
privileged ensemble consumes 102-value physical state plus actions, including
hidden material/context and obstacle geometry. The observation model has only
current numeric local inputs/actions and does not reconstruct hidden pile mass.

## Matched forecast results

All methods use the same final practice trajectories. Errors below are raw,
unweighted rows in this synthetic corpus, not mine frequency.

| Method | Position MAE (m) | Pile-height MAE (m) | Mass-ledger MAE (kg) | High-error fraction |
| --- | ---: | ---: | ---: | ---: |
| Persistence | 0.04104 | 0.000209 | ~0 | 52.37% |
| Kinematic | 0.00115 | 0.000209 | ~0 | 5.03% |
| Retained ensemble | 0.04416 | 0.000396 | 0.680 | 100.00% |
| Refit raw ensemble | 0.02236 | 0.000581 | 1.416 | 12.60% |
| Refit with explicit bounded filter | 0.02236 | 0.000171 | ~0 | 11.56% |

The refit improves position and the combined error/event rule against the
retained ensemble, while worsening raw pile-height and material-conservation
errors. The filter's conservation and physical corrections are imposed, not
learned. Large corrections reject operational forecasts. The simple kinematic
baseline remains stronger on aggregate one-step position error, but its absent
contact/collision prediction does not establish material planning or safety.

The local observation refit improves speed MAE from 0.12638 to 0.03717 m/s,
observed load MAE from 23.41 to 14.67 kg, and valid-range height MAE from 0.03180
to 0.01787 m. Validity accuracy rises from 90.57% to 94.02%. Some individual
heading/lateral fields regress; the complete fifteen-field results remain in
their own units. The thirteen reused terminal rows have no measured following
observation, so observable evaluation excludes them and retains 4,623 rows.
Privileged terminal-event evaluation includes all 4,636 rows.

## Why assistance remains disabled

The unchanged validation gate now supports two decisions (0.2 s), against zero
for the retained ensemble, with a train-normalised disagreement threshold of
0.229424. This is a validation result, not operational qualification.

On final practice evaluation, left-receiver accepted high-error fraction is
68.35%, above the fixed 10% limit. Rubble, shifted-start and complete-dropout
families have no accepted forecasts; other families lose all operational
forecasts to physical/filter checks. The all-family gate therefore fails for
both raw and filtered refits. Raw negative outputs remain visible. Forecast
eligibility is not inferred from better average error or a successful nominal
subset. Full per-family coverage, false-safe/false-stop event counts and
fixed-action drift at 1/2/4/8 decisions are retained.

Training contains eight collision episodes and zero stuck episodes, below the
128 distinct training episodes per failure class acquisition target. Reweighting
or borrowing the validation/evaluation stuck cases cannot repair that coverage.
The finite experiment identifies both distribution/physical-validity problems
and this remaining acquisition shortfall without expanding the declared budget.

## Costs and checks

Collection, fitting, calibration, comparison and packaging take 83.85 seconds on
one CPU thread. There are 14,945 new simulator decisions, 4,636 reused evaluation
decisions, 3,880 optimiser updates, no teacher calls and no actor/assisted updates.
This stays below 31,200 new decisions, 6,000 updates, 300 seconds and 64 MiB.
Each method uses at most 128 validation and 128 evaluation windows; horizons
never cross episode boundaries. All rows remain in one-step/family metrics.

The standard-library verifier recomputes physical errors, event mistakes,
validation-only threshold selection and final family acceptance from retained
predictions. CPU tests reload saved weights, reproduce sample forecasts, verify
train-only normalisers and reject physically impossible/filter-rejected forecasts.
No browser, tab switching, desktop automation or listening service is used.

```sh
python3 scripts/verify-forecast-refit.py
PYTHONPATH=training training/.venv/bin/python -m unittest discover -s training/tests_lab -p test_forecast_refit.py -v
```
