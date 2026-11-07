# Reference and geometry repair

Refs #307–#312. Decision: ADR-0047. These are synthetic reference-controller
results, separate from learned policy proficiency.

The recorded loader now uses the physical rear axle as its origin, a 1.8 m
rear-to-joint offset, 1.6 m joint-to-front offset, 0.55 m tyres and a bucket mouth
computed from the logged boom/curl. Both body sections articulate. Five browser
fixtures independently check straight, reverse, turning, scooping and high-boom
poses against exported Python geometry; rear/joint/front/mouth and four axle
centres agree to numerical precision. The authored concept rig is unchanged.
An optional Collision geometry overlay shows the three reference envelopes.

The audited reference exports every action, pre/post state, transfer, footprint
and phase boundary. A fresh simulator independently executes the actions and
checks each state and mass ledger. The legacy and opt-in ridge/rubble families
complete held-out cycles; low and steep piles retain failures. New pile families
are seeded height-field approximations with explicit density and no cohesion
or fracture claim. Legacy random draw order and scenario digests are preserved.

Integration probes compare fixed physical durations at 0.05, 0.1 and 0.2 second
decision intervals; physics increments remain at most 20 ms. The full contact
matrix uses 60 physical seconds rather than confounding intervals with a fixed
number of decisions. The default remains 0.1 seconds. The reset audit checks 32
held-out family/seed combinations before any action and separately rejects a
deliberately overlapping start. Success, collision, stuck and truncation remain
separate outcomes; no invalid start is accepted as an evaluation episode.

Evidence: [report](reference-repair-evidence/report.json),
[browser geometry](reference-repair-evidence/browser-geometry.json), and
compressed per-case action/state traces in the same directory. Reproduce with
`python -m kessel_training.reference_audit --output <new-directory>` from the
training environment. The browser check is `scripts/verify-reference-rig.cjs`.
The CPU suite passes 125 tests. Build completion does not establish granular
physics fidelity or learned autonomous haulage. Release tickets are untouched.
