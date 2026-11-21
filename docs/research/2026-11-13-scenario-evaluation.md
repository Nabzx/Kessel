# Scenarios, isolation and robustness scorecards

Refs #411, #427 and #428. Recommendation: proposed ADR-0059.
Evidence: [metadata and scorecard audit](../phase-11/demo-frontier-evidence/report.json).

## Scope and supported variations: #411

Separate nominal task proficiency from generalisation. First establish the
empty-start complete task under ADR-0057's proposed gate. Then change one axis
at a time: start pose, supported pile family, grip/grade and range impairment.
Retain infeasible blocked cases in their own category. An obstacle collision
is an outcome, not demonstrated obstacle avoidance or correct stopping.

Use the existing legacy/low/ridge/rubble/steep pile generators and standard,
low-grip/occluded/blocked families. These are synthetic height fields and planar
clearance approximations. Do not add unsupported rock fracture, moving people,
surveyed site geometry or arbitrary obstacles as cosmetic controls. Current
policy observations do not measure obstacle boxes or corridor width.

Proposed evaluation matrix: 16 frozen starts per single-axis family and three
independent policy-training seeds, with both the reference controller and saved
policy evaluated on identical starts. Report baseline feasibility before scoring
a learned failure. Keep combined shifts separate and run them only after the
single-axis results are known. No new policy is trained on these evaluations.

## Isolation and procedural identity: #427

Seed partitions already exist: training 0–99999, validation 100000–109999 and
test 200000–209999. A disjoint integer range is necessary but not sufficient:
record generator/version, scene parameters, stream/episode index, realised pose,
pile hash, prepared payload and initial state hash. Partition whole episodes
before transition extraction. Do not split adjacent steps across datasets.

The new audit scans 436 JSON/JSON.gz metadata files and finds 304 distinct
explicit seed values. It finds no explicit seed-field hits in ADR-0057's proposed
validation, pilot-test or final-test ranges. **They remain unverified reservations.**
The audit excludes NPZ arrays, PT checkpoints, JSONL streams, deleted history,
implicit generator offsets and external/unretained runs. Its output deliberately
keeps `reservation_verified: false`, even when there are no hits.

Before collection, audit those exclusions and generator schedules, freeze a
manifest of actual initial identities and check exact cross-split collisions.
Hash related procedural families into the same split when they derive from a
shared base scene. Preserve test scenes untouched after reservation. Any later
inspection or tuning must be logged as consumption and requires fresh final tests.
The current metadata snapshot is research evidence, not a certification of
complete experiment-history isolation.

## Scorecards and failures: #428

The shipped exports contain these selected cases:

| Source | Cases | Complete empty-start successes |
| --- | ---: | ---: |
| Conventional reference: baseline/rubble/steep | 3 | 2 |
| Curriculum policy: seeds 7/19/41, first test scene | 3 | 0 |
| Earlier policy: initial/intermediate/final checkpoints | 3 | 0 |

These exports are illustrations of declared results, not a broad efficacy
estimate. The reference's steep case is stuck; curriculum cases hit walls;
the earlier policy includes wall collisions and timeout. Keep all outcomes and
the original selection rule. Never combine reference and learned successes into
one improvement percentage or call pickup a completed delivery.

For every case report actor/checkpoint, exact scenario, initial payload, carried
peak, delivered/spilled mass, termination/truncation reason, collision and duration.
Aggregate by agent, scenario family and training seed. Use complete successes
and collisions first; reward is diagnostic. Report all-case duration separately
from successful-cycle duration to avoid rewarding quick collisions. Keep valid
starts, expected infeasibility, timeout and invalid initialisation distinct.

Display a compact source-aware table before a viewer selects a replay. Missing
results remain missing, with an explanation. No averages over a curated three-
episode export can establish a generalisation rate. The same scorecard fields
should serve research reports and the future demo catalogue.

## Follow-on specifications

Implement a reservation registry that audits manifests and rejects consumed or
duplicate initial identities; an episode-level scenario catalogue with frozen
generator parameters; and a scorecard exporter that preserves failed cases.
Validate with deliberate cross-split duplicates, changed generator versions,
prepared starts and a missing learned/reference counterpart. No additional
training or fresh generalisation claim is produced by this investigation.
