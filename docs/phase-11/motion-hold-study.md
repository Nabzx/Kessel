# Observed-motion holding experiment

25 November 2026. [ADR-0068](../adr/0068-observed-motion-holding-pilot.md),
[complete report](motion-hold-evidence/report.json).

The first observed-motion prototype is rejected. It preserves all 27 task
stop/hold criteria and nine healthy/transient/recovered deliveries, but meets
none of the twelve loaded-grade criteria. The preceding controller met six.
The same four physical fixture conditions repeat across three neural weights;
these are not twelve independent machines. Neither controller is promoted.

The wrapper estimates longitudinal disturbance from consecutive observed speed,
observed load, elapsed time and the last applied drive command. It uses the
reference force-response coefficient and nominal rolling term, not true grade,
privileged state, a reference action or a learned world model. Eligible moving
samples exclude near-limit acceleration. The estimate adds feedforward to the
existing conventional PI command; neural proposals remain separately recorded.

| Grade rad | Initial speed m/s | Hold path m | Hold peak speed m/s | Ending | New gate |
| ---: | ---: | ---: | ---: | --- | --- |
| -0.06 | -0.8 | 0.043 | 0.116 | Nonterminal ten-second window | Fail |
| -0.06 | +0.8 | 0 | 0 | `stuck` before ten-second hold | Fail |
| +0.06 | -0.8 | 0 | 0 | `stuck` before ten-second hold | Fail |
| +0.06 | +0.8 | 0.043 | 0.116 | Nonterminal ten-second window | Fail |

In the initially uphill cases the first eligible estimate arrives at about
1.0 seconds, after the first low-speed settling event at 0.7 seconds. Downhill
rollback has already violated the 0.10 m/s hold-speed limit. The estimate settles
at about +/-0.5886 m/s2 and reduces subsequent travel, but does not repair that
earlier failure. The ten-second evaluator never restarts its window to hide it.

In the initially downhill cases the estimate is available after about 0.1 seconds.
Feedforward is about +/-0.348 command. Residual PI integral bias raises the applied
holding magnitude to about 0.440. The physical machine remains stationary, but
the unchanged kernel's high-drive immobility detector terminates it as `stuck`
before ten seconds of hold. This is a task-contract failure, distinct from
physical rollback. Termination is not disabled or relabelled to pass the gate.

The evidence narrows two next design needs: obtain an identifiable force sample
before aggressive braking clips acceleration, and make the transition to
feedforward holding without retaining unnecessary integral bias. It does not
establish an observer for noisy proprioception, unknown grip, digging contact
or real machines. No gains or eligibility rules are changed in this frozen run.

All 51 cases and original healthy comparators complete in 111.86 seconds, under
the 150-second cap, with one CPU thread and no GPU. Evaluation uses 11,426
environment decisions and 11,426 neural queries. Independent replay uses 10,277
additional physical decisions across all 48 supervised cases and 11,426 actor
queries across all 51. State, action, observation and observer replay are exact.
The trace archive is 3,150,380 bytes. Teacher queries, optimiser updates and
held-out cases are zero. Healthy actions, phases and states remain exact.

The [preceding coverage study](spatial-range-study.md), its aborted logging
attempt and both rejected control laws remain retained unchanged. These new
costs are additional to that earlier work. This is consumed practice evidence,
not qualification, runtime admission or a field-safety result.

```sh
python3 scripts/verify-motion-hold.py
```
