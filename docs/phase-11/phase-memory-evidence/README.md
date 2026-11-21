# Phase memory and rehearsal evidence

The admitted method uses imitation-trained continuous controls with rule-based
phase memory. It completes 32/32 final scenarios for each of three training seeds,
96/96 policy/scenario cases total, without collisions. The memoryless comparator
completes 54/96 and is not admitted. See [the study](../phase-memory-study.md).

- `diagnosis.json`: retained old retraction/forgetting gates and scoped phase probe.
- `rejected-reservation.json`, `rejected-ranges.json`: prior scenario use found
  before new collection. These are rejected proposals, not fresh-data certificates.
- `reservation.json`: accepted validation 108200–108215 and final 207600–207631,
  with no archive/ZIP matches and no unreadable archives.
- `plan.json`, `report.json`, `selection.json`: frozen protocol, all training and
  evaluation outcomes, and validation-only selection before final collection.
- `artifacts.zip`: all acquisition episodes and labels, all round candidates with
  optimiser/RNG state, every validation record and every final action trace.
- `source.zip`: exact numerical package, dependencies and archive/replay/export tools.
- `consumption.json`: final-case collection after all six selections freeze.
- `independent-replay.json`: 96 selected validation cases plus 192 final traces,
  zero state/action/reward error, with teacher calls forbidden.
- `resume-check.json`: completed resume with episodes, teacher calls and optimiser
  work blocked; all decision/update deltas are zero and outcomes remain unchanged.
- `learning-curves.svg`: every declared method/seed, selected points highlighted.
- `hardware.json`, `portable-package-qa.json`: native host and Chrome/M1 rendering
  checks; these are playback checks, not model inference or field benchmarks.
- `portable-package-manifest.json`, `portable-package.json`: the independently
  served static preview, excluding Python tools and weights.
- `files.json`: SHA-256 manifest, excluding itself.

All final scenes are consumed by all six policies. Fresh tuning studies must
reserve new tests. The main concept walkthrough remains authored and separate.
