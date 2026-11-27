# ADR-0077: Clearance capture-order guard

Status: Accepted to complete the ADR-0073 input contract in the maintainer's
blocked-path work. No new numerical study or runtime admission.

The frozen clearance pilot validates frame, finite distances, validity and age,
but its stateless health helper cannot detect a packet whose capture time moves
backwards while still falling within the 0.2-second age limit. A duplicate can
also appear fresh. This falls short of the predeclared ordering requirement.

Add a separate `OrderedClearanceStop` wrapper. Preserve the pilot's controller,
source capsules and all positive/negative results byte-for-byte. For otherwise
well-formed fresh packets, require a nonnegative, strictly increasing capture
clock. An old/duplicate packet requests stopping before it can mutate the
blockage release latch. Bad packets never advance the accepted capture clock.
Subsequent correctly ordered input may recover through the existing three-sample
stopping supervisor, without resetting physical state or task memory.

Keep an explicit method identity and accepted clock in diagnostics. Verify the
contract in-process: old/duplicate/negative timestamps, preservation of a latched
blockage, later fresh recovery and identical commands on ordered healthy input
for all three frozen checkpoints. These small tests are interface checks, not
new physical efficacy evidence or fresh qualification. No service or browser is
started. The wrapper remains outside the existing runtimes and is merged
separately after the model-refit stage.
