# Receiver-position robustness

23 November 2026. Refs the receiver-distance failure identified in ADR-0062.

## Retained-case diagnosis

All 24 farther-receiver learned cases fail before tipping, while the reference
completes all eight matched cases. The failed neural actors keep their payload
in phase 3. This is a carry/arrival failure rather than failed pickup.

The original 176 acquisition episodes contain 40,815 carry rows. Reconstructing
receiver x from their numeric features gives -1.5 m within about 2e-6 m.
Odometry x and receiver-forward displacement have correlation -0.999986.
Marginal x coverage extends beyond the failed final positions: this is not
explained simply by an x value outside the training minimum/maximum. The
farther receiver breaks a near-deterministic relationship between the inputs.

In the first retained failed case, holding goal displacement and all other
inputs fixed but changing odometry x by +2 m changes seed 7's reverse command
from -0.310 to -0.951. A -2 m change instead gives +0.813. These are deliberate
input interventions on consumed data, not newly simulated episodes or
evidence of qualification.

The failed seed-7 state has about -6.82 kN drive and -5.92 kN slope force,
leaving only -0.90 kN against about 2.57 kN rolling resistance. The reference
kernel therefore holds it near rest. A negative command alone does not
guarantee reverse travel. Other failed states can oscillate around that
threshold; the report keeps their individual force margins.

This supports testing a representation that preserves the relative receiver
goal during carry. It does not prove a unique neural mechanism, justify changing
the simulator's forces or certify a controller fix.

## Costs and scope

The [diagnostic](receiver-evidence/diagnosis.json) analyses 64 existing nominal/
farther cases and all 176 training acquisitions. It makes 72 counterfactual
neural queries, no teacher queries, no environment decisions and no optimiser
updates. Execution uses one CPU thread and a 45-second cap; the measured run
takes about nine seconds. The sandbox denied lowering process priority, so it
runs at the unchanged priority rather than escalating.

Existing weights, physics, recorded outcomes and the default demo remain intact.
Any new method must be named separately and tested without reusing these
consumed cases as untouched final evidence.

## Training-partition pilot

[ADR-0063](../adr/0063-receiver-frame-pilot.md) freezes a conventional input
adapter: during carry/tip, reconstruct odometry x in the nominal receiver
frame from the observed relative goal and heading. Other inputs, phase
transitions, model weights and all physical dynamics stay unchanged.

The fourteen-case pilot on training seed 19000 completes within 30.8 seconds
using one CPU thread and 6,103 environment decisions. Each of the three
original policies completes the nominal task and fails the farther receiver.
Each adapted policy completes both cases; the separate reference does too.
All weights remain byte-identical. There are no training labels, optimiser
updates or held-out cases. The pilot supports the hypothesis but does not
qualify robustness or replace the existing demo's controller.

The [report](receiver-evidence/pilot.json) and all pilot traces are retained.
The fresh qualification protocol is separate and must freeze before any new
test policy query.

## Fresh receiver-distance qualification

[ADR-0064](../adr/0064-receiver-frame-qualification.md) freezes the method,
weights, cases, all-seed gate and resource limits before evaluation. The
[reservation certificate](receiver-evidence/reservation.json) covers eight
previously unused bases, 205800–205807, with nominal and 2 m farther-receiver
settings kept together. No tuning or training follows the pilot.

The pre-query audit checks historical raw blobs and current retained ZIP
members. A [supplemental check](receiver-evidence/zip-history.json), performed
after the outcomes freeze, checks twelve historical ZIP versions. Every relevant
member was already covered by the pre-query audit; there are zero additional
member blobs and zero consumed hits. The supplement makes no policy queries.
It supplements the audit record rather than changing the pre-query certificate.

The [qualification report](receiver-evidence/qualification.json) retains all
112 outcomes: sixteen derived settings, three original neural actors, their
three adapted versions and a separate conventional reference.

| Controller | Nominal | Farther receiver | Collisions |
| --- | --- | --- | --- |
| Original phase-memory neural policies | 24/24 | 0/24 | 0 |
| Receiver-frame neural policies | 24/24 | 24/24 | 0 |
| Conventional reference | 8/8 | 8/8 | 0 |

Each adapted seed, 7, 19 and 41, completes 8/8 in each family. All pass the
predeclared minimum of 7/8 per seed and family with zero collisions. The result
qualifies only this nominal/farther synthetic comparison. It does not qualify
other pile shapes, traction, sensing faults, hardware or real mines. The
earlier thirteen-family stress study remains unchanged.

All adapted physical traces replay exactly: 48 cases and 17,944 decisions.
All neural actions and phase transitions replay exactly against the recorded
observations: 96 cases and 40,991 policy queries. The reference traces remain
retained comparators; this study does not independently replay their physics.
Maximum adapted state error and neural action error are both zero.

The run takes 315.63 seconds within its 420-second cap, on one CPU thread with
no GPU. Evaluation uses 46,845 decisions, including 5,854 separate reference
queries. Replay costs are additional and recorded above. The trace archive is
13,574,790 bytes, below the 32 MiB cap. There are no teacher training queries,
optimiser updates or weight changes. Frozen source, initial states, observations,
actions, material ledgers and both failed and successful traces are retained.

This is an engineered receiver-frame input combined with conventional phase
memory and existing imitation-trained continuous controls. It is not new
reinforcement learning, learned planning or a learned-world-model improvement.
The new test bases are now consumed.

## Optional local interface

A separate runtime offers only the qualified nominal/farther families and
explicit receiver-frame sources. It verifies qualification, source/checkpoint
identity, numerical library releases and dependency lock before binding.
It uses practice seeds 19000–19999 and rejects the qualification seeds.

To start it manually from the repository root:

```sh
PYTHONPATH=training training/.venv/bin/python -m kessel_lab.receiver_runtime --port 8094
```

The existing viewer route is `/docs/phase-11/live-demo/` on that service.
The default service, original controllers and static walkthrough are unchanged.
No service or browser was started for this integration. In-process tests cover
reset, stepping, source identity and input rejection; they do not establish
visual acceptance. Human visual reviews and publication remain open.

Run `python3 scripts/verify-receiver-evidence.py` for the retained-data checks.
This validates hashes, coverage, material accounting and recorded replay results;
it does not repeat the numerical experiment or start an interface.
