# Working-policy forecast diagnostic

Frozen 22 November 2026, before calibration/test outcomes. Extends ADR-0062.

Use the retained multistep/material privileged ensemble and observable model,
with their immutable sidecar hashes, plus persistence and kinematic baselines.
No model fitting, actor updates, forecast filtering or assisted learning occurs.
This asks whether existing forecasts qualify for assistance on a newly useful
controller, before paying for another training experiment.

Calibration executes the seed-7 phase-memory actor on eight fresh bases
108400–108407: nominal, nominal, low, ridge, rubble, steep, blocked and
range_dropout respectively. Retain complete episodes, at most 4,800 decisions.
Fit residual thresholds on calibration only. Test all 104 phase-memory-7 episodes
from the thirteen-family stress test. Other policy seeds and the reference are
not silently added to this world-model score. Reuse existing test trajectories,
not fresh simulator collection. Both groups are now consumed by this evaluation.

Forecast horizons are 1/2/4/8 common fixed-action windows, up to 256 windows,
never crossing episode boundaries. Report raw metrics and violations, per-field
observable errors and masked range error, calibration-only intervals, accepted
high-error fractions and event false-safe/false-stop. A scalar mixed-unit error
is not a physical metric. Observable terminal rows without a measured following
observation are excluded and counted; privileged terminal events remain included.

Use the existing ADR-0040 validation gate without tuning its limits. Operational
assistance requires supported horizon >=1 and <=10% accepted high-error rate
in every non-blocked shifted family. Otherwise retain the no-go result. This
forecast diagnostic cannot demonstrate an assisted policy improvement even if
its gate passes; that would require a separate matched-budget learning study.

Count rare collision/stuck episodes and contact/transfer windows. Compare coverage
with the earlier proposed 128 independent training episodes per failure class.
This diagnostic collects no new training corpus and cannot meet that acquisition
goal through calibration/test rows or repeated weighting. Report that shortfall
and specify the follow-up before any training claim.
