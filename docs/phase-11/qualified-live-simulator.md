# Qualified stopping live simulator

The separate ADR-0072 interface executes the frozen neural controls, conventional
phase memory and qualified stopping supervisor in local synthetic physics.
It is a working simulator, not a mine connection or a learned world model.
The original walkthrough, recorded viewer and earlier local services are unchanged.

From the repository root, start it when you want to use it:

```sh
PYTHONPATH=training training/.venv/bin/python -m kessel_lab.bootstrap_runtime --port 8095
```

Open <http://127.0.0.1:8095/docs/phase-11/qualified-demo/> yourself. Nothing opens
automatically. Stop the process with Ctrl-C. This is a loopback-only development
service. Static hosting alone cannot execute its Python API.

Choose a scenario, controller and practice seed, then **Start new run**. Settings
take effect on reset. **Run**, **Pause** and **One decision** execute the selected
run. Each decision advances 0.1 seconds of simulated time. Pause executes no
physics. Reset clears phase memory, observer, sensor fault timing and task clock.

| Scenario | Behaviour being inspected |
| --- | --- |
| Healthy range | Neural controls complete a delivery without override. |
| Partial moving-carry range | Ten invalid cells trigger conventional stopping and holding. |
| Complete moving-carry range loss | Stale input triggers conventional stopping and holding. |
| Range returns | Stop, require stable restored input, then resume the neural delivery. |

All three checkpoint seeds, 7/19/41, are selectable with the supervisor. Original
neural comparators support healthy input only. Interactive seeds are restricted
to consumed practice range 19000–19999. No receiver-frame adapter is composed with
this controller. No new training, fresh qualification or field evaluation runs
when the service starts.

The status panel shows the **last consumed** input's age and valid range cells,
the current control owner, and stopping/holding/recovery state. Its proposal time
precedes the displayed post-decision physical state by one decision. The command
table separates neural proposals from commands actually applied in the simulator.
During override, the conventional supervisor supplies the applied commands.

Persistent-loss playback ends after the ten-second hold observation window.
This does not set delivery success or mark the physical environment terminal.
Practice runs may fail; their actual outcomes remain visible. Recovery success
requires an override, resumed neural control and a completed delivery.

**Export trace** pauses playback and downloads every executed observation,
injected fault, neural proposal, applied command, physical state and material
transfer, with canonical inputs and observer diagnostics in supervised runs. The JSON includes checkpoint, qualification, runtime and
run identities and explicitly sets `applied_machine_commands=false`. It records
executed synthetic output, not commands sent to equipment.

Startup fails closed unless the [fresh qualification](bootstrap-qualification.md),
complete frozen source inventory, selected weights, reservation lineage, retained
archives and numerical library releases still match. Missing or changed evidence
does not enable a reference or recorded fallback. The machine and material meshes
are visual proxies; the reference simulator is uncalibrated.

Verification uses in-process Python session/handler tests and browser-free Node
tests for asynchronous playback and presentation. The bounded [regression report](qualified-runtime-evidence/report.json)
compares all 15 consumed practice cases exactly against ADR-0069: three checkpoints
across four supervised patterns, plus three original healthy comparators. A full
[recovery export](qualified-runtime-evidence/recovery-export.json.gz) is retained.
The 5,255 decisions matched exactly in 29.98 seconds, below the declared caps.
This checks runtime integration; it does not enlarge the qualification scope.
No browser, tab switching, desktop automation or listening service was used for
these checks. Human visual acceptance and publication remain open.

```sh
python3 scripts/verify-qualified-runtime.py
node --test scripts/tests/qualified-client.test.mjs
PYTHONPATH=training training/.venv/bin/python -m unittest discover -s training/tests_lab -p test_bootstrap_runtime.py -v
```

The practice execution script is retained at
`scripts/research/verify-qualified-runtime.py`. It refuses to replace existing
evidence and is capped at 15 cases, 9,000 decisions, one CPU thread and 120 seconds.
CI verifies the retained artifacts without repeating the experiment or opening a
browser. Existing CPU CI also runs the new session/handler tests.
