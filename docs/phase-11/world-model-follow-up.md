# Bounded world-model follow-up

Refs #315–#322. Protocol: [ADR-0049](../adr/0049-bounded-learning-follow-up.md).
[Report](world-followup-evidence/report.json),
[coverage comparison](world-followup-evidence/coverage-comparison.json), and
[retained file hashes](world-followup-evidence/integrity.json).

The benchmark collects 4,096 training, 1,536 validation and 1,536 test decisions,
plus 512 held-out steep-pile decisions. Prepared payloads, spill, stuck, blocked,
static contact and range impairment are declared strata with isolated seed
partitions. Contact without transfer rises from 8/8,192 rows in the previous
corpus to 97/4,096. Rare failure rows remain sparse. Episode-bootstrap ensembles
sample inverse regime frequency; evaluation reports both unweighted synthetic
corpus metrics and equal-regime macro metrics. Neither represents mine frequency.

A separate 65-feature onboard model sees local range/validity, odometry and
encoders, plus actions. It does not receive the 102-value privileged physical
state, future observations or hidden pile mass. The privileged baseline retains
that state explicitly. Delay, dropout, occlusion and recovery are independently
seeded. Communications availability cannot change local observations or physics.
Receiver displacement assumes a preloaded target map; it is not GPS.

Three 64-unit, three-member ensembles compare one-step residual learning,
soft material/conservation losses, and autoregressive horizons 1, 2 and 4.
Evaluation also includes unseen horizon 8, persistence and kinematic baselines.
Raw test mass-balance MAE falls from 2.735 kg to 1.056 kg with material losses,
and 0.394 kg with multistep/material losses. Position MAE worsens from 0.0237 m
to 0.0448 m in the latter. This is a trade-off, not general improvement. Raw
negative values, violations and errors are retained before the explicitly
labelled bounded filter. The filter's corrections are imposed physics.

Five event heads report precision, recall, Brier error, false-safe forecasts,
false stops and event timing. Thresholds use validation only. Ensemble spread
bins, empirical 95% marginal position intervals, input envelope and physical
admissibility are separate diagnostics. The nominal and steep-pile test reports
retain confident errors. None of the raw ensembles qualifies an imagined horizon
under the declared gate.

The assistance comparison fits a fresh ensemble on 768 new training decisions
and calibrates on 256 new validation decisions. It never reuses benchmark weights.
Across three seeds, model-free PPO spends 4,096 online decisions; assisted PPO
spends 3,072 online plus 1,024 offline. Its gate rejects imagined branches, so
there are zero imagined critic updates. Every held-out learned full-cycle test
still fails with zero delivery. No efficiency or task-proficiency improvement is
claimed. Benchmark research data, fitting, evaluation and wall time are disclosed
separately. The complete follow-up took 127.85 seconds on the local CPU.

Reproduce with `python -m kessel_training.followup_world_study --output
<new-directory>`. Source `34ed3fc` was clean before collection. These are bounded
synthetic feature models, not perception, granular fracture or deployed robotics.
