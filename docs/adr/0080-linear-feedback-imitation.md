# ADR-0080: Learned linear feedback with conventional task planning

Status: Accepted for the remaining controller/policy request. No RL or learned
planning claim; earlier deep imitation failures remain unchanged.

The progress-driven planner produces six current feedback features: target-speed
error, bounded integral, target direction, articulation error, boom error and
bucket error. Fit a sparse four-output linear layer with a hard [-1,1] limit.
Drive uses the first three features; each joint head uses its own error. These
are known planner/feedback features, not a teacher action supplied as input.
Learn all six nonzero gains from training labels using rank-checked least squares
on unsaturated rows. Keep the sparse hypothesis class explicit. No initial
coefficient is copied from the conventional controller. A rank-deficient fit fails.

Use only the selected ADR-0078/0079 development revision, bases 19020/19021.
Only successfully completed delivery/expected-stop episodes provide labels;
stopping overrides never label task controls. Retain unsuccessful episodes in
their original archives and report the selection. Do not use validation/final
labels. This is deterministic linear imitation, not a new deep-network or RL
study. Conventional tactical memory, setpoints, integral, sensing grace and
braking remain visible. Model assistance is not involved.

Save learned weights, complete feature/label data, source hashes, fit rank and
all residuals. Reload weights for evaluation. Compare conventional and learned
feedback over every original family on base 19023, with the same delivery/stop
criteria. No reference fallback or learned-weight updates during evaluation.
All applied learned actions replay independently; include original-model/source
identity. Permit at most four least-squares solves, 16,000 physical/planning
decisions, 8,000 replay steps, one CPU thread and 180 seconds including fitting.

Successful imitation demonstrates recovery of a feasible feedback mapping. It
does not demonstrate learned task planning, general neural robustness, RL benefit
or learning inside a world model. Any remaining failed family remains failed.
Existing runtimes and recorded experiments stay unchanged. Fresh qualification
needs its own reservation and protocol before runtime admission.
