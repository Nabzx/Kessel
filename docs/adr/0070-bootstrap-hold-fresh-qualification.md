# ADR-0070: Fresh moving-carry stopping qualification

Status: Accepted for the maintainer's continued, bounded work on 25 November 2026.
Freezes ADR-0069's unchanged controller for a narrow synthetic qualification.

## Scope and cases

Reserve bases 208700–208707 only if the full available local history/archive
audit passes before any policy query. A text search is not a reservation.
Initialisation to fingerprint a scene is allowed; policy/teacher calls are not.
All derived cases remain with their base. A consumed hit, unreadable input or
timeout blocks evaluation; do not silently choose another range or expand caps.

For each base and frozen neural seed 7/19/41 run four nominal-physics cases:
healthy delivery, partial near-two-row zero-height occlusion during moving carry,
complete loss during moving carry, and two-second complete loss during moving
carry followed by recovery/delivery. Moving carry means observed phase 3 and
speed <= -0.5 m/s, as in the frozen practice injector. Keep empty starts, the
2,000 kg target and all existing physics, weights and thresholds unchanged.
Include an original neural healthy comparator for each base/seed: 120 cases.

Healthy and recovered cases require successful delivery without collision;
recovery also requires an actual override and subsequent resumption. Persistent
partial/full loss requires detection within 0.1 seconds, settling within 2.5
seconds (three physical speed samples <=0.08 m/s), stopping path <=2 m, then a
ten-second nonterminal hold with speed <=0.10 m/s and path <=0.25 m. A trigger
that never occurs fails. Fault stops are not deliveries. Every family/seed must
meet at least 7/8 of its own criteria, with zero collisions across its eight
cases. No pooled override. Healthy actions/phases/states must match all 24
original comparators exactly, including failures. Every weight remains unchanged.

Qualification applies only to these four nominal-physics families, including
their naturally randomised grade/load/geometry. The six fixed loaded-grade/cold-
start component conditions remain practice evidence, not new held-out physical
conditions. No noisy-proprioception, low-grip, other fault phase, field reliability,
partial-observation delivery or learned-world-model claim follows.

## Audit and execution limits

One serial CPU thread, no GPU. Audit all available Git versions of recognised
JSON/gzip/JSONL/PT/NPZ inputs and ZIP members, plus current repo data/docs/training/
.local inputs, deduplicated by content. Include historical ZIPs before querying.
Exclude only the audit's scratch/output, environments and Git internals.
Check candidate seeds, recorded initial-state/pile hashes and float32 equivalents.
An exact float32 first-pile-cell prefilter may avoid impossible fingerprint
matches; it must never replace seed checks and must have regression tests.
Use batched Git reads, with a 180-second parent cap and a 175-second worker
deadline. Reject raw members above 256 MiB or certificates above 16 MiB.

After reservation, freeze case plan, complete numerical source, checkpoint and
reservation hashes before the first query. Evaluation/replay share a 420-second
active cap. At most 72,000 evaluation decisions, 57,600 additional physical
replay decisions for all 96 supervised cases, and 72,000 actor replay queries for
all 120 cases. Trace archive cap 32 MiB. Guard every learned execution/replay
against reference-controller calls. Keep original baseline physics separate;
their actions are independently replayed, while all supervised physics and
fault-injected observations are independently re-executed.

Seal all outcomes before replay. Recompute proposals, applied actions, phase,
canonical inputs, task clocks and observer state exactly. Preserve every failed
or incomplete case and all costs. Any cap, incomplete replay, changed weights,
teacher call or source mismatch blocks admission. No retuning or extra attempts
after results. A failed test range is consumed and cannot become a fresh retest.

This work stays in the repository with regular commits and the maintainer's
requested merges into main after checks. No browser, desktop automation, vehicle
connection, runtime promotion, release tag or deployment is part of this protocol.
