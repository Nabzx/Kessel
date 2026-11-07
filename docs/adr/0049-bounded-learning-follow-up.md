# ADR-0049: Bounded learning follow-up

Status: Accepted

## Decision

Extend ADR-0047's declared CPU protocol before collecting follow-up results.
Compare four policy alternatives on three fixed seeds (7, 19, 41): ordinary
PPO, two-frame observation stacking, held-out-gated curriculum and reference
behaviour-cloning warm-start followed by PPO. Keep the same 64-unit policy,
four environments, 64 decisions per rollout and at most 16 PPO rollouts.

Charge 4,096 optimisation reference decisions per method: ordinary/history/
curriculum use 16 online rollouts; the warm-start uses 1,024 training-only
reference-controller pairs and 12 online rollouts. Predeclare 500 supervised
minibatches, learning rate .002, balancing the teacher's five phases. Retain
warm-start and final weights, failures and validation/test evaluation separately.
This is a supervised-reference baseline, not pure RL or DAgger. Do not query an
expert or train on held-out evaluation trajectories. Report evaluation and
shared development costs separately; make no sample-efficiency claim from
online-only accounting.

A curriculum transition requires 32 training episodes with 70% subtask success,
at least 70% held-out success in the current stage and at least 50% retention
on preceding stages. Empty-start pickup and complete delivery are measured
separately from prepared payload. Budget exhaustion may leave gates unmet.
Stacked observations advance in the environment, not in policy encoding;
bootstrap encoding must not append an extra frame or cross a masked reset.

World-model follow-ups preserve episode-level partitions and record contact,
pickup, tipping, collision and truncation strata. Keep observable-only models
separate from privileged-state baselines. Compare raw neural losses with
explicit material-conservation losses and separately labelled imposed filters.
Use action-conditioned horizons 1, 2, 4 and held-out horizon 8; at most three
members and 40 epochs per declared model variant. Fit thresholds on validation,
never test. Count false-safe and false-stop events and rejected branches.

For the subsequent assistance comparison, train a fresh model from exactly
768 targeted reference rows plus 256 calibration rows, charged alongside 3,072
online decisions against the 4,096-decision model-free budget. The broader
world-model benchmark corpus is development evidence and cannot initialise
this comparison. Report its separate collection/fit cost, all imagined updates
and wall time. This boundary prevents uncharged corpus selection from being
presented as improved sample efficiency.

Sources: [PPO](https://arxiv.org/abs/1707.06347),
[observation histories](https://arxiv.org/abs/1312.5602),
[sequential imitation error](https://proceedings.mlr.press/v15/ross11a.html),
[DreamerV3](https://arxiv.org/abs/2301.04104). These motivate controlled
comparisons, not a claim that this prototype implements Dreamer or calibrated
mine physics. Refs #313–#322.
