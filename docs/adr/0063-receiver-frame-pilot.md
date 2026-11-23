# ADR-0063: Receiver-frame carry pilot

Status: Accepted for the maintainer's bounded, repo-local continuation on
23 November 2026. Extends ADR-0062 only for this separately named experiment.
Old policies, studies, source labels and recorded results remain unchanged.

## Evidence and decision

The retained nominal acquisition fixes receiver x at -1.5 m, making absolute
odometry and relative receiver displacement nearly redundant. All 24 farther-
receiver learned cases stay loaded in carry rather than reaching tip. Input
interventions and force accounting support testing the receiver-frame hypothesis.

Add a conventional observation adapter for phases 3 and 4 only. Replace the
network's odometry-x input by:

    x_encoded = -1.5 - receiver_forward * heading_cos
                       + receiver_left * heading_sin

This expresses the current x coordinate in the nominal receiver frame using
current observations alone. Other features are unchanged. Phase memory updates
from the original observation. Every continuous command still comes from the
unchanged neural weights. This is an engineered input representation, not a
newly learned planner, reinforcement learning gain or world-model result.

## Bounded pilot

Before execution, freeze one training-partition practice seed, 19000. Compare
the original and receiver-frame versions of all three selected phase-memory
actors on nominal and 2 m farther-receiver scenes. Include the conventional
reference as a separate comparator. Run all fourteen declared cases in a fixed
order, at most 600 decisions each and 8,400 total. Use one CPU thread and a
60-second execution cap, checking at every decision. Retain incomplete cases
and mark the pilot incomplete if the budget expires.

No optimiser updates, new training labels or final-test claim. Guard learned
executions against reference-controller calls. Record checkpoint and adapter
source hashes, every action/observation/state and complete material accounting.
Do not change physics, termination, payload, phase thresholds or delivery target.

Advance the hypothesis only if every adapted seed completes both declared
practice cases with zero collisions and unchanged weights. Original/modified
comparisons remain diagnostics on training data. No method is admitted to the
live viewer, and no generalisation rate is inferred from this pilot.

A subsequent qualification study, if warranted, needs its own frozen protocol,
audited fresh cases, all-seed nominal/farther criteria and separate replay costs
before any controller promotion. Keep all work in the repo, with no visible
browser automation, system changes, remote publishing or large unbounded jobs.
