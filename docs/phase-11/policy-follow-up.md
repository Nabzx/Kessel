# Bounded policy follow-up

Refs #313 and #314. Protocol: [ADR-0049](../adr/0049-bounded-learning-follow-up.md).
[Retained report, weights and test traces](policy-followup-evidence/report.json).

Twelve CPU runs compare PPO, one-step observation history, a gated curriculum
and reference-supervised warm-start across seeds 7, 19 and 41. Every run charges
4,096 training reference decisions. The warm-start spends 1,024 of these on
training-only reference pairs and 3,072 online; supervised reuse and all evaluation
steps are reported separately. Models have two 64-unit hidden layers. We retain
initial, warm-start where applicable, and final checkpoints with SHA-256 files.
Selection uses validation delivery, full successes and collisions, with the
later candidate breaking ties. Held-out test results never select checkpoints.

All twelve runs fail to complete a held-out full delivery cycle. The gated
curriculum does achieve partial pickup: its six test peaks are 188, 177, 1,716,
2,052, 1,922 and 2,358 kg. Every case then hits a wall and delivers zero ore.
Observation history and the supervised warm-start do not improve this outcome
within the declared budget. Prepared-load stage successes are reported separately
from empty-start full cycles. The reference controller completes the same two
held-out full-cycle scenarios; it is a diagnostic baseline, not a learned policy.

The curriculum requires both a recent training window and held-out current/prior
stage retention before advancing. History is advanced once per physical step;
repeated encoding cannot manufacture observations. Masked resets clear only the
selected slot. Normalised 130-feature history and legacy 65-feature PPO share the
same bounded-action likelihood implementation. Tests cover these boundaries,
finite updates, teacher repeatability and safe checkpoint reload.

The complete study took 246.89 seconds, including evaluation. This is a bounded
synthetic experiment, not a deployment or a training-budget sufficiency claim.
Reproduce from clean source with `python -m kessel_training.followup_study --output
<new-directory>`. Recorded source is commit `09e713a`; its training package is clean.
