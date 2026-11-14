# Retraction pilot evidence

This bundle contains the original completed pilot report, frozen plan/selection,
preflight reservation, reference feasibility, source snapshot and all candidate
checkpoints. It demonstrates an isolated prepared skill, not full delivery.

- `artifacts.zip`: 54 candidates and sidecars, six event logs, three test summaries
  and 48 recorded test traces. Paths are setting/seed scoped.
- `source.zip`: exact Python package, `pyproject.toml` and `uv.lock` used for the run.
- `independent-replay.json`: 96 selected validation executions and 48 action
  replays, charged as separate post-study verification.
- `resume-check.json`: completed-study resume was idempotent. The primary report
  and archived event logs remain the original pre-check snapshot.
- `consumption.json`: distinction between preflight reservation and later use.
- `files.json`: SHA-256 integrity manifest, checked independently in CI.

From the repository root:

```sh
python3 scripts/verify-retraction-pilot.py
training/.venv/bin/python scripts/research/replay-retraction-pilot.py --output /tmp/pilot-replay-new.json
```

Executable replay requires the recorded clean package and pinned libraries.
Restore the recorded source commit/package if current training code differs.
The replay tool refuses package mismatches. It never trains or changes selection.

From `training/`, a new study needs newly reserved scenarios. Existing cases
are consumed; use the sealed reservation only to resume this exact study:

```sh
uv run --locked python -m kessel_training.retraction_pilot --output runs/retraction-pilot-2026-11-14 --reservation ../docs/phase-11/retraction-pilot-evidence/reservation.json --resume
```

Do not rerun/tune on the pilot test set and call it fresh validation. Full-cycle
test seeds were fingerprinted only and remain reserved for their stated role.
