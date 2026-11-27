# Blocked-path observation and stopping

The separate `LatchedClearanceStop` controller meets all 24 declared obstacle,
loaded forward/reverse and stale-input stop/hold checks. It preserves all three
healthy deliveries on practice base 19000, with exact original neural actions.
On base 19001 all three healthy cases encounter the wall guard and stop before
delivery. The complete 30-case pilot gate therefore fails. This method is not
admitted to an existing runtime and has no fresh or field qualification.

The new channel supplies four world-aligned body-envelope clearance distances,
a timestamp, range limit and validity. Its producer is an idealised privileged
geometric sensor, not implemented perception. The controller reads only these
packets and local observations. The existing pile-height input still does not
observe obstacles. No raw scene boxes are given to the neural network.

The first execution aborts after one decision because of transfer-grid logging.
Its report/source/empty archive remain in [the aborted evidence](clearance-evidence/report.json).
The corrected [first pilot](clearance-stop-evidence/report.json) reveals a real
control failure: the speed-dependent threshold shrinks during braking and permits
premature resumption. Every failed hold remains retained. The separately named
latched correction preserves a release clearance until the blockage clears.
The [final report](clearance-latched-evidence/report.json) and all raw traces
record packets, masked stop handoffs, neural proposals, applied conventional
commands, physical state and material ledgers. Proposals during a clearance
override use an explicitly recorded range-mask handoff. They are not proposals
from the unchanged healthy input.

Across all three attempts, evaluation charges 10,403 decisions and independent
replay charges 10,402 decisions. Combined measured wall time is 107.74 seconds,
with one CPU thread, below the original 12,000/12,000/180 limits. Applied commands,
sensor packets and physical replay match exactly. Stop/hold outcomes are never
counted as deliveries or physical environment termination. Loaded fixtures are
declared prepared starts with 2,500 kg, not learned material pickup.

The implementation and contract tests address the previously absent obstacle
boundary and premature-resumption defect. Remaining work is delivery compatibility
and independently reserved qualification, not a claim that blocked-path autonomy
is solved. No obstacle avoidance, dynamic sensing, machine safety or field
perception is established. All original numerical sources and viewers remain
unchanged. No browser or listening service was used.

```sh
python3 scripts/verify-clearance-evidence.py
PYTHONPATH=training training/.venv/bin/python -m unittest discover -s training/tests_lab -p test_clearance_stop.py -v
```
