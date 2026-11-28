# Qualified harvest live view

The isolated harvest service executes new reference physics, frozen fitted
feedback and the qualified conventional planner/guards on demand. A frozen hybrid
predicts each applied action's next state before physics advances. It is a shadow
forecast: it never chooses or changes the command. Position, carried-mass and
material errors are measured against the actual resulting state.

The [viewer](harvest-demo/index.html) uses an amber wireframe forecast over the
solid executed loader and exposes forecast source, inputs, proposals and actual
commands. The prediction uses privileged simulator state and known kinematic,
event and accounting priors. It is not sensor-only prediction or field perception.
A short terminal interval is labelled separately from the nominal 0.1 s horizon.

The [38-case equivalence report](harvest-live-evidence/report.json) compares every
new live run with the frozen qualified control path. All observations, controls
and physical states match exactly across both controller sources, thirteen primary
families, the accepted prepared no-progress hold and five nominal input/recovery
patterns. Source snapshots and complete forecast/error traces are retained.
The bounded check uses 15,480 physical decisions in 168.43 s, within its
360-second/30,000-step limits. No socket, browser or machine command is used.

## Deliberate local launch

    PYTHONPATH=training training/.venv/bin/python -m kessel_lab.harvest_runtime --port 8096

Then open `http://127.0.0.1:8096/docs/phase-11/harvest-demo/` when you choose to.
This work does not start that service or touch existing ports/tabs. Older
qualified/live viewers remain available through their original services.

Startup verifies the original fresh qualification, accepted refusal decision,
numerical library releases and weights, then requires this live implementation's
own current equivalence receipt. Practice seeds are restricted to 19000–19999.
Primary cases require the existing synthetic initial feasibility certificate;
unsupported requests are rejected without replacing or advancing the active run.
The prepared no-progress scenario has its own accepted hold scope. Fault patterns
remain limited to the nominal family, matching qualification.

Run, pause, single decision and export are request-driven. There is no background
physics clock. Old run IDs, stale counters/epochs and oversized batches cannot
advance the simulation. Export pauses through the client and supplies an
independent snapshot of all executed inputs/actions, states and causal forecasts.
The normal delivery goal remains 2,000 kg; controlled holds stay separate.

## Verification and limits

    python3 scripts/verify-harvest-live.py
    PYTHONPATH=training training/.venv/bin/python -m pytest training/tests_lab/test_harvest_runtime.py -q
    node --test scripts/tests/harvest-presentation.test.mjs

Backend sessions and HTTP handlers are exercised in-process. Node tests check
source/outcome presentation and short-terminal/withheld forecasts. Existing
race-tested playback logic is reused. No browser rendering or visual acceptance
is inferred from those tests. #351/#385 and publication remain open.
