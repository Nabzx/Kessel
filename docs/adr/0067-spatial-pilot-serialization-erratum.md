# ADR-0067: Spatial pilot serialization correction

Status: Accepted as a repo-local implementation correction on 25 November 2026.
Preserves ADR-0066's case plan, controller behaviour and stopping/delivery gates.

The first attempt at commit `ce96ddc` fails while serialising the first case:
the new health adapter returns a NumPy boolean in its journal. No case trace,
outcome table or replay has been written. The available frozen plan, exact
source archive, empty trace archive and error record are retained under
`docs/phase-11/spatial-range-evidence/aborted-attempt/`.

The failed process does not retain the first trajectory or exact query counts.
Report its cost conservatively as at most 600 environment decisions and 600
neural queries, with zero replay. The trace/source archive file timestamps span
about 1.80 seconds; this is an artefact span, not measured monotonic active time.
Do not describe the aborted attempt as a completed case or discard its costs.

Correct only JSON scalar typing: cast `health.usable` to Python `bool`. Keep
all gains, thresholds, canonical inputs, actions and criteria unchanged. Add a
regression test that serialises the healthy and overridden journal. Preserve
the earlier diagnostic's exact source separately; do not recompute its queries.

Restart once in a distinct repo-local output directory. Reduce the active cap
from 180 to 150 seconds and evaluation cap from 30,600 to 30,000, leaving the
600-decision allowance for the aborted first case. Retain original replay caps
and all 51 declared cases. Freeze the corrected sources and this erratum before
any restarted query. No retuning, re-selection, new cases or fresh-test claim.
If the corrected attempt fails or reaches a cap, retain it and stop the study.
