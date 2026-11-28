# ADR-0089: Partial terminal snapshots in sensor conversion

Status: Accepted. Supersedes ADR-0088 only on retaining partial terminal snapshots
inside the converted packet stream. All split, budget, model and error gates stay
unchanged.

The first import stopped before optimisation: three retained synthetic terminal
snapshots report range ages measured over a full decision despite a shorter final
physical interval. Reconstructing capture time as use time minus age then moves
the range clock backwards. Keep that rejected capsule at
`sensor-forecast-evidence/`, including its source and partial conversion archive.

Conversion now omits a final snapshot when its interval is below 0.09 seconds.
Keep the original source archive and hash, and report omitted snapshot counts for
each recording. These intervals were already excluded from 0.1-second targets;
no full target or historical controller input is removed. Do not interpolate,
clamp timestamps, relax the packet validator or repair external recordings.

Run the same predeclared sensor study once at `sensor-forecast-v2-evidence/`.
Its extra budget is 240 seconds, 2250 updates, one thread and zero physical
queries. The failed first import used zero updates and 2.31 seconds. Preserve
both attempts and do not tune against final results.
