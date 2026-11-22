# Forecasts on the working-policy task

22 November 2026. Refs #412 and #429–#431.
[Predeclared protocol](world-model-shift-protocol.md),
[complete measured report](working-policy-model-evidence/report.json).

## Decision

**No-go for model assistance.** The retained privileged multistep/material
ensemble supports zero horizon under the unchanged validation gate. It receives
no actor or model updates and contributes no imagined training transitions.
There is no new assisted-learning treatment or improvement claim.

A useful nominal controller now exists, so this diagnostic tests whether existing
forecasts qualify on its actual state/action distribution. They do not. This is
a distribution-specific negative result for the retained models, not proof that
world models cannot help or a comparison with a newly trained dynamics model.

## Cases and roles

The seed-7 phase-memory actor executes eight reserved calibration episodes on
108400–108407, using the declared nominal, low/ridge/rubble/steep, blocked and
range-dropout schedule. Collection costs **2,224 reference decisions**, below
the 4,800 cap. Calibration trajectories, hashes and the unchanged protocol are
retained. No teacher is queried and no model is fitted.

Evaluation reuses all **104 seed-7 episodes and 39,099 decisions** from the
thirteen-family frozen-policy test, rather than collecting another held-out set.
Other neural seeds and the conventional reference are not silently pooled into
this forecast score. Calibration alone selects residual thresholds; no test
outcome changes model weights, the acceptance rule or the actors.

Every method sees the same privileged state/actions for its permitted input
role. The observable model sees only 65 current numeric observations and four
actions. Its 104 terminal rows lack a measured following observation in this
trace format, so they are explicitly excluded from its next-observation metrics:
**38,995 evaluated observable rows**. Privileged terminal-event metrics retain
those rows. Hidden full-pile mass is never invented for the observable model.

## One-step comparison

These are unweighted rows in this declared synthetic corpus, not mine-operating
frequency. Family/regime results and common 1/2/4/8-decision windows are retained
separately in the report. Windows never cross an episode boundary; predicted
failures do not truncate a diagnostic forecast to make its error look smaller.

| Method | Position MAE (m) | Pile-height MAE (m) | Mass-ledger MAE (kg) | High-error fraction |
| --- | ---: | ---: | ---: | ---: |
| Persistence | 0.04047 | 0.000183 | ~0 | 42.12% |
| Kinematic | 0.00160 | 0.000183 | ~0 | 3.75% |
| Retained privileged ensemble | 0.04290 | 0.000359 | 0.903 | 97.59% |

The high-error rule includes position, carried mass, pile error, reward and
terminal mismatch. The learned event head produces 38,086 false terminal
positives. Its raw collision head misses 2 of 22 collision events and produces
35,017 false positives at the fixed 0.5 threshold. These are diagnostic false-
safe/false-stop counts for that head, not a deployed stopping system. Since
no horizon is admitted, none of these branches is used operationally.

The kinematic baseline's strong aggregate one-step result does not establish
contact modelling or task planning: it misses all 11,953 contact positives and
all 22 collision positives. Persistence also misses them. Long free-motion runs
must not turn that aggregate score into a claim of reliable material prediction.
All raw physical violations and open-loop drift are retained without projection.

The observable model has 0.02385 m odometry-x MAE, 0.10784 m/s speed MAE,
30.05 kg load MAE and **0.02519 m valid-range MAE**. Range-validity accuracy is
91.17%. Other proprio fields are reported separately in their own units;
there is no physically meaningful combined metres/radians/kilograms MAE.

The calibration-only 95% marginal position-residual radius is 0.08815 m. Coverage
varies by shifted family, including only 88.24% for blocked cases. It is neither
a joint-state safety bound nor a calibrated ensemble probability. The actual
gate selects no uncertainty threshold and supports **zero horizon**.

## Coverage and the next model experiment

The test corpus contains 22 collision episodes, nine stuck episodes and 31
collision/stuck transition rows. It has 27,126 free-motion, 434 contact-only and
11,508 material-transfer rows. These held-out rows are not new training data.
The earlier target of 128 distinct **training** episodes per failure class is
not achieved by this diagnostic. Reweighting the same few failures cannot meet it.

Next acquire a bounded, episode-isolated corpus on varied training geometry and
successful closed-loop trajectories, plus distinct contact/collision/stuck cases.
Freeze collection mixture, normalisation, per-field losses, validation-only
calibration, budgets and a new final split before fitting. Report shortfalls at
the cap rather than expanding it after seeing results. Compare observable,
privileged, kinematic and explicitly constrained methods on identical cases;
keep any imposed filter labelled separately from learned conservation.

Only after a forecast gate qualifies should a matched-budget assistance study
compare actual full-task success or learning cost. Charge collection, fitting,
calibration and imagined updates separately. A successful imitation policy plus
a rejected world model does not demonstrate training inside a learned world model.
