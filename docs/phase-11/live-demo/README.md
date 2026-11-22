# Live synthetic simulation

This route executes new reference-simulator transitions and frozen neural
inference in a localhost Python process. It is separate from recorded playback,
the authored default walkthrough and any real machine interface.

From the repository root, with the existing training environment installed:

```sh
PYTHONPATH=training training/.venv/bin/python -m kessel_lab.server --port 8090
```

Open <http://127.0.0.1:8090/docs/phase-11/live-demo/> in Chrome. If the environment
is missing, follow `training/README.md` to install the pinned CPU dependencies.
No API key or online service is needed after installation.

Choose a scenario, controller and practice seed, then **Start new run**. **Run**
executes decisions at up to 10 Hz, **Pause** holds the simulator and **One decision**
executes a single action. Reset starts empty and replaces the previous session.
The service supports one active run. Stale run IDs/counters cannot advance it.
Practice seeds are restricted to 19000–19999; they are not new held-out tests.

Each continuous command comes from the selected frozen neural policy, with
conventional observation-derived phase memory. The conventional reference is a
separate source. There is no teacher fallback for learned control. The simulator
supports thirteen finite scenario families. These are stress probes, not validated
mine distributions; collisions and incomplete jobs are retained as failures.

The browser displays actual returned pose, joints, wheel angles, pile cells and
material ledger. The vehicle mesh and material surfaces are visual proxies.
The service exports the executed trace, source/checkpoint and scenario identity.
No machine command stream or learned-world-model prediction is generated.

The server binds only to loopback, checks Host/Origin and bounded JSON requests,
serialises mutations and limits each request to ten decisions. It serves viewer
dependencies rather than training checkpoints or directory listings. Do not
expose this research service as a production API.

Native Chrome verification is retained in `evidence/`. It covers fresh nominal
success, blocked failure, source changes, reset/pause/step, keyboard controls,
reduced motion and three viewport profiles. Narrow coverage is functional,
not phone presentation qualification. Human visual acceptance remains separate.
