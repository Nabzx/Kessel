# Fresh moving-carry stopping qualification

25 November 2026. [ADR-0070](../adr/0070-bootstrap-hold-fresh-qualification.md),
[logging/replacement erratum](../adr/0071-fresh-qualification-logging-erratum.md),
[complete report](bootstrap-qualification-evidence/report.json).

## Result

The frozen controller passes the declared fresh qualification: every supervised
family/seed meets 8/8, with zero collisions, unchanged weights and exact independent
replay. Healthy actions, phases and physical states match all 24 original
comparators exactly. Qualification is limited to the four declared synthetic
families; this does not promote the method into an existing runtime.

| Family | Neural seed 7 | Neural seed 19 | Neural seed 41 | Total |
| --- | ---: | ---: | ---: | ---: |
| Healthy delivery | 8/8 | 8/8 | 8/8 | 24/24 |
| Partial range during moving carry: stop and hold | 8/8 | 8/8 | 8/8 | 24/24 |
| Complete range loss during moving carry: stop and hold | 8/8 | 8/8 | 8/8 | 24/24 |
| Two-second loss, stop, recovery and delivery | 8/8 | 8/8 | 8/8 | 24/24 |
| Original healthy neural comparators | 8/8 | 8/8 | 8/8 | 24/24 |

All 120 evaluations have zero collisions. The supervised method completes 48
empty-start deliveries and 48 fault stop/hold cases; the latter are not deliveries.
The additional 24 cases are original healthy neural comparators. Every family
must pass at least 7/8 for each training seed, with zero collisions across all
eight. No pooled score can override a failing seed/family or incomplete replay.

These are eight paired nominal-physics base scenes, not 120 independent mines.
All fault families and neural sources derived from a base stay together. The
frozen method is `bootstrapped_motion_hold`, combining existing neural weights,
conventional phase memory, canonical range inputs and conventional stopping.
This is not new RL, learned perception or learned-world-model training evidence.

## Declared domain and measured stops

The moving-carry trigger requires observed phase 3 and reverse speed at least
0.5 m/s. Partial loss invalidates and zeros the near two rows of the crop;
complete loss retains a stale raw crop but invalidates all cells. The canonical
input zeros invalid heights. Recovery restores actual observations after two
seconds, then requires stable health and low speed before resuming the task.

Stops must detect loss within 0.1 seconds, settle within 2.5 seconds and travel
at most 2 m before settling. The following ten-second physical window must remain
nonterminal, collision-free, at speed <=0.10 m/s and path <=0.25 m. An unreached
trigger or a simulator termination fails its case. The evaluator retains the
first settling event and never restarts the window to obtain a favourable result.

The largest recorded stopping path is below 0.190 m. All recorded hold speeds
and hold paths are zero in this reference kernel. Payload at loss ranges from
about 2,462 to 2,705 kg. The eight naturally randomised initial grades range from
-0.058940 to +0.057825 rad. These are observations of the declared samples, not
a continuous-domain guarantee or calibrated machine stopping distances.

Qualification is limited to healthy delivery and these partial/full moving-carry
loss/recovery cases with noiseless proprioception and adequate grip. Persistent
partial coverage causes a controlled hold; useful partial-observation delivery
is not restored. Other fault phases, noisy speed/load, low grip, longer/repeated
faults and real equipment remain unqualified. The fixed loaded-grade/cold-start
[component fixtures](bootstrap-hold-study.md) remain practice evidence, not new
held-out physical conditions. Composition with the receiver-frame adapter is
also untested; their separate results must not be combined into one claim.

## Freshness and aborted first attempt

The first audit accepts 208700–208707 after checking 7,098 unique raw/container/
member blobs, including historical ZIP versions, with no hits or errors. It takes
169.67 seconds within its 180-second cap. The auditor makes no policy queries.

The first execution then fails while constructing its first trace identity:
a local source-hash name shadows the identity function. The first case's trajectory,
outcome and exact query count are lost before writing. Its plan, exact source,
empty trace archive and [error record](bootstrap-qualification-evidence/aborted-attempt/abort.json)
remain retained. Its cost is at most 600 environment decisions and 600 neural
queries, with no replay. The 2.32-second artefact timestamp span is not measured
monotonic active time.

Base 208700 is consumed and excluded across all families/sources. It is never
rerun or counted as fresh. ADR-0071 corrects only logging/cohort bookkeeping,
keeps the controller byte-identical, and requires a separate full audit for
replacement 208708. That audit checks 7,102 unique blobs in 167.15 seconds,
again with no hits/errors or policy queries. The [combined certificate](bootstrap-qualification-evidence/reservation-corrected.json)
binds untouched 208701–208707 from the first audit and 208708 from the second,
including both certificate hashes and the consumed-base exclusion.

The corrected cohort is exactly 208701–208708. A practice-only journal regression
test passes before restarting. No control gain, weight, observation rule, action
law or qualification criterion is fitted or selected against either attempt.
The corrected execution cap is reduced to 400 seconds and its evaluation cap
to 71,400, leaving the aborted attempt's allowance within the former 72,000.
No more replacement, retuning or rerun is permitted after the corrected results.

The audit covers available local Git history, current repo data/docs/training/
.local raw inputs and ZIP members. It cannot rule out unretained external runs.
Exact and float32 initial-state/pile fingerprints are checked, with tested
necessary-first-cell filtering and independent seed checks.

## Verification and presentation boundary

The frozen source, checkpoint identity, case plan and reservation lineage are
bound before querying. Evaluated outcomes freeze before replay. Physical replay
must cover all 96 supervised cases; action/proposal/phase/clock/observer replay
must cover all 120 cases. Original comparators' physics is not separately replayed;
their recorded actions are checked and all healthy traces must match the
corresponding supervised run exactly.

Corrected execution completes in 378.17 seconds, within the reduced 400-second
cap, on one CPU thread with no GPU:

- 42,161 evaluation decisions and 42,161 neural queries;
- 32,950 additional physical replay decisions across all 96 supervised cases;
- 42,161 additional actor queries across all 120 cases;
- zero state, action, observation or observer replay error;
- zero teacher queries or optimiser updates;
- 13,699,057-byte trace archive, below the 32 MiB cap.

The aborted allowance makes the evaluation/query total at most 42,761, not an
exact measured total. Replay is additional as listed. Both audit runs are
separate costs: 169.67 and 167.15 seconds, each below its 180-second cap. These
qualification costs are additional to the retained practice and failed studies.

```sh
python3 scripts/verify-bootstrap-qualification.py
```

The evidence verifier reads retained files, independently checks the material
ledger, initial identities, observer arithmetic and stopping/delivery gates,
and enforces the per-seed result. It starts no simulator, browser or service.
All previous failed experiments and the earlier practice suite remain unchanged.
Existing runtimes, human visual acceptance and publication remain separate.
