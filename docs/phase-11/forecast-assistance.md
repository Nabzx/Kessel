# Matched forecast assistance comparison

The bounded comparison is complete. All 48 arm-runs passed their scoped delivery,
stop or recovery criterion with zero collisions and exact independent replay.
The 24 pairs share initial states, seeds, frozen weights, guards and per-decision
model budgets. Candidate refinement changed 126 actions. Median paired delivery
cycle reduction was **0.0811%**, below the predeclared 10% benefit threshold.
There is no demonstrated control benefit. Assistance stays outside the live
runtime; its qualified controller and shadow-only forecast remain unchanged.

Both arms query the same five action candidates at every unguarded decision.
The shadow arm always applies the original proposal. Refinement may select a
candidate during collection, sweeping or backing out only when the raw prediction
passes physical/uncertainty checks and its declared material/effort score exceeds
the original by five. Independent guards bypass this selection. The chosen
action's shadow forecast reuses an identical state/action prediction, with cache
hits counted explicitly. Guards still receive a separately counted shadow query.

The [complete receipt](assistance-comparison-evidence/report.json) retains both
arms, every candidate forecast, raw score, acceptance and selection, controller
input, applied action, physical state and independent replay accounting. It used
12,127 physical decisions plus 12,127 replay decisions, 113,462 model rows and
408.23 seconds on one CPU thread, within 600 seconds and its declared row caps.
No optimisation, teacher labels or machine commands were used.

    python3 scripts/verify-forecast-assistance.py
    PYTHONPATH=training training/.venv/bin/python -m pytest training/tests_lab/test_forecast_assistance.py -q

This is a narrow synthetic, one-step candidate comparison using privileged state.
It is not RL, learned sensing, field validation or a sample-efficiency result.
The failed benefit gate is retained without tuning against the final cohort.
