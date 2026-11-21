# Full-cycle comparison evidence

All six bounded runs and all 192 final policy cases are complete. Both methods
score 0/96 complete deliveries. Independent replay reproduces all 96 selected
validation cases and 192 final traces with zero state/action/raw-reward error. Prepared fill success is separate from full-task
proficiency. See [the report](../full-cycle-study.md).

- `report.json`: every candidate, gate, transition, training update, selected
  checkpoint, final outcome and actual collection counter.
- `plan.json`, `selection.json`: predeclared study and all six frozen selections.
- `reservation.json`: final-test non-use audit, allowing only exact prior
  registration/non-use documents, including available archive and ZIP scans.
- `pre-test-freeze.json`, `consumption.json`: zero final decisions before every
  selection freezes, plus final-test consumption and file ordering.
- `scheduling-amendment.json`, `hardware.json`: actual serial/two-worker execution
  and host/software identity. No wall-speed comparison is claimed.
- `artifacts.zip`: all 71 candidate checkpoints and hashes, four gate checkpoints,
  the interruption checkpoint, six event logs and all 192 final traces.
- `source.zip`: exact training source, locked dependencies and orchestration,
  archive, plotting and independent replay scripts.
- `interruption-check.json`, `resume-check.json`: actual graceful interruption
  continuity and completed-study resume with zero additional decisions.
- `independent-replay.json`: repeated selected validation and final action/state/
  raw-reward checks, with verification decisions separate from collection.
- `learning-curves.svg`: all six seeds/method combinations, including failures.
- `files.json`: SHA-256 manifest, excluding itself.

Collection costs: 544,768 training decisions, 571,806 full-task selection decisions,
4,503 gate decisions and 104,903 final-test decisions. The previous pilot and
post-study verification are counted separately. The final 32 scenes are now
consumed by every selected policy; a future tuned study needs new unused tests.

Current exact-source replay from the repository root:

```sh
training/.venv/bin/python scripts/research/replay-full-cycle.py \
  --evidence docs/phase-11/full-cycle-evidence \
  --output /tmp/new-full-cycle-replay.json
python3 scripts/verify-full-cycle-evidence.py
```

If the training package later changes, reconstruct the archived training source
in an isolated checkout first. Repeated replay is verification of the same cases,
not another held-out generalisation set. Do not use this consumed reservation
certificate to start a fresh tuning experiment.
