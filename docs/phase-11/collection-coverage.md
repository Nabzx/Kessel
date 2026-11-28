# Collection coverage comparison

The bounded follow-up completes all planned comparisons, but the full task gate
remains failed. No new controller replaces the existing qualified runtime.

[ADR-0082](../adr/0082-bounded-collection-coverage-correction.md) fixes two variants
before execution. Both use observed bucket-mouth lateral feedback, wider collection
lanes and shorter reversing manoeuvres. The physics, sixty-second task and 2,000 kg
delivery requirement remain unchanged. Conventional planning and braking remain
explicit even when the saved linear network supplies the continuous task commands.

The [report](collection-coverage-evidence/report.json) retains all eighteen tuning
runs and thirty-six final reference/learned comparisons. Both variants pass seven
of nine development cases. The declared tie-break chooses 1.35 m lanes and 3 m
reverse clearance. No final outcome influences selection or weight fitting.

On new practice base 19024, both sources pass 17/18 delivery, stopping, recovery and
clearance-input criteria. Low-grip starts become stuck before collecting material.
All runs are collision-free and every final controller/sensor/physical action
replays exactly. The learned actuator matches every reference pass/fail outcome;
this is not learned planning or a demonstrated improvement over the reference.

The consumed base-19023 low-pile miss also remains: the selected variant reaches
1,899 kg peak load and delivers 1,886 kg by the unchanged time limit. Returning
sooner addresses timing but does not recover enough material. The earlier
1,994 kg retained-load failure remains independently preserved too.

For the low-grip 19024 start, retained friction is 0.08763 and grade is 0.09860
radians. At the initial heading, maximum forward drive minus slope and rolling
resistance is about -3,208 N even before digging. This explains why the current
forward approach cannot move. It is not a proof that every possible manoeuvre is
impossible and does not justify relabelling the delivery criterion as a stop.

The study uses one CPU thread, 14,624 physical/planning decisions, 7,984 final
independent replay steps and 112.00 seconds, within the 300-second limits. There
are no weight updates. All unsuccessful outcomes and actual learned commands are
independently checked by:

    python3 scripts/verify-collection-coverage.py

Further work needs a separately bounded low-pile harvesting design and a grade/
traction-aware approach or explicit feasibility contract. Neither is presented as
completed qualification. Keeping the brake and failed gates intact is part of
this result.
