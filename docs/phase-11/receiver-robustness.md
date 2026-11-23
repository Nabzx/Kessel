# Receiver-position robustness

23 November 2026. Refs the receiver-distance failure identified in ADR-0062.

## Retained-case diagnosis

All 24 farther-receiver learned cases fail before tipping, while the reference
completes all eight matched cases. The failed neural actors keep their payload
in phase 3. This is a carry/arrival failure rather than failed pickup.

The original 176 acquisition episodes contain 40,815 carry rows. Reconstructing
receiver x from their numeric features gives -1.5 m within about 2e-6 m.
Odometry x and receiver-forward displacement have correlation -0.999986.
Marginal x coverage extends beyond the failed final positions: this is not
explained simply by an x value outside the training minimum/maximum. The
farther receiver breaks a near-deterministic relationship between the inputs.

In the first retained failed case, holding goal displacement and all other
inputs fixed but changing odometry x by +2 m changes seed 7's reverse command
from -0.310 to -0.951. A -2 m change instead gives +0.813. These are deliberate
input interventions on consumed data, not newly simulated episodes or
evidence of qualification.

The failed seed-7 state has about -6.82 kN drive and -5.92 kN slope force,
leaving only -0.90 kN against about 2.57 kN rolling resistance. The reference
kernel therefore holds it near rest. A negative command alone does not
guarantee reverse travel. Other failed states can oscillate around that
threshold; the report keeps their individual force margins.

This supports testing a representation that preserves the relative receiver
goal during carry. It does not prove a unique neural mechanism, justify changing
the simulator's forces or certify a controller fix.

## Costs and scope

The [diagnostic](receiver-evidence/diagnosis.json) analyses 64 existing nominal/
farther cases and all 176 training acquisitions. It makes 72 counterfactual
neural queries, no teacher queries, no environment decisions and no optimiser
updates. Execution uses one CPU thread and a 45-second cap; the measured run
takes about nine seconds. The sandbox denied lowering process priority, so it
runs at the unchanged priority rather than escalating.

Existing weights, physics, recorded outcomes and the default demo remain intact.
Any new method must be named separately and tested without reusing these
consumed cases as untouched final evidence.
