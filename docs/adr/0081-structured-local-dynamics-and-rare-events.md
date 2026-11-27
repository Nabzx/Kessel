# ADR-0081: Structured local dynamics and rare-event coverage

Status: Accepted for the remaining forecast-reliability request. Preserves raw
MLP/filtered studies and rejects transferring their results to this new model.

## Model boundary

Fit learned local acceleration and shared per-cell extraction factors. Combine
them with explicit known kinematics, joint/speed bounds, swept-envelope collision
rules, event thresholds, reward accounting and nonnegative material-flux decoding.
The architecture enforces conservation; do not describe it as learned conservation
or present known geometry as implemented perception. It is a privileged synthetic
hybrid predictor, not an onboard observation model or a copy of LoaderEnv.step.
Prediction may use pure kinematic geometry but never query a simulator transition,
teacher, stored future trajectory or future observation.

Use receiver/position translation-independent local features for learned heads.
Predict extraction with a shared cell network on height, bucket-relative geometry,
current load/joints/speed and actions. Bound each removal by available material,
bucket room and declared throughput. Delivery/spill and event semantics are
explicit prior rules. Preserve a no-learned-flux/acceleration ablation and the
kinematic/persistence baselines to show what the fitted components contribute.
Retain every prior and all raw errors, including confident wrong forecasts.

## Data and budgets

Reuse the selected complete progress-controller episodes on training bases
19020/19021. Validation uses 19022 primary family runs and final practice uses
19023 primary family runs, never mixing bases or fitting on final labels.
Source is identified per episode; retain failed task runs rather than manufacturing
successful trajectories. Executed stop windows are not environment terminals.

Add exactly 128 distinct training collision episodes on 19100–19227 and 128
training stuck episodes on 19228–19355. These are declared prepared synthetic
fixtures with distinct seed/pile/initial-state identity, not learned task success.
Collision fixtures have a valid forward obstacle gap. Stuck fixtures put the
front axle at a sampled high pile cell with unchanged frozen physics and hold
constant drive/joints until the actual stuck terminal. Do not shorten stuck time,
reset/duplicate episodes or relabel missing classes to meet counts. Validation
fixtures use 19360–19363; evaluation fixtures use 19370–19373. Report any shortfall.

Cap new collection at 32,000 physical decisions and independent fixture replay
at 20,000 steps. Train three seeded 64-unit motion/32-unit shared-cell members
for exactly 750 minibatch updates each, no sweep or final-driven refit. Fit target
normalisation on training only; input physical scales are declared constants.
Charge all 2,250 updates and permit 128 fixed-action windows per split/method.
One CPU thread, 420 seconds total and 96 MiB retained artifact cap.

Use the unchanged ADR-0040 validation error/horizon gate and the ADR-0075
non-blocked-family coverage/<=10% accepted high-error gate. Apply raw physical
admissibility as well. Fit uncertainty thresholds on validation only. Report
per-family errors, actual rare-class coverage, violations, event false-safe/
false-stop, common 1/2/4/8 drift, fitted-weight replay and architectural ablations.
A passing practice gate still requires fresh qualification and a separately
matched-budget assistance experiment before any policy-benefit claim.
No browser, service or public deployment is part of this experiment.
