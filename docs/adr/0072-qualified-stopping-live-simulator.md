# ADR-0072: Qualified stopping in the isolated live simulator

Status: Accepted for the maintainer's implementation and merge request on
27 November 2026. Extends ADRs 0062/0070 for this separate runtime interface.
Frozen numerical methods, qualification files and existing viewers stay intact.

## Runtime boundary

Add `kessel_lab.bootstrap_runtime` and a separate `/docs/phase-11/qualified-demo/`
route, using loopback port 8095 by default. Reuse the frozen simulator, controller
and fault injector. Offer neural seeds 7/19/41 with the qualified supervisor for
healthy, partial moving-carry loss, complete moving-carry loss and recovery.
Original neural comparators are selectable for healthy runs only. Reject all
other combinations. No reference fallback, receiver-frame composition, new
training or arbitrary weights. Interactive seeds remain 19000–19999, never the
held-out ranges. Practice runs may fail and retain their actual outcomes.

Before creating a session, verify complete qualification, every per-seed/family
gate, exact healthy comparisons/replay, weight identity, budgets, reservation
lineage, retained report/source/trace hashes, complete source inventory, lockfile
and numerical library releases. Fail closed if evidence or source changes.
Bind report, runtime, selected checkpoint, scenario and method identity to a run.

Session controls explicitly implement reset, play, pause and bounded stepping.
No autonomous backend simulation clock. Serialise mutations; validate run IDs,
decision counters, request sizes, same-origin loopback requests and step counts
1–10. A playback epoch invalidates automatic requests issued before pause/reset;
manual steps require confirmed pause. Pausing executes no physics. Reset clears
observer, phase, fault timing and task clock without altering the preceding log.

Persistent-loss runs stop playback after the same ten-second hold observation
window used in qualification, retaining pass/fail and actual physical state.
This is a distinct execution ending: never set simulator termination or delivery
success to make a fault stop look like a completed delivery. Recovery must stop,
observe stable restored input and resume before successful delivery is counted.

Expose last-consumed sensor freshness, age and valid cells; control owner and
stopping/holding/recovery state; neural proposals beside applied synthetic commands;
qualification/checkpoint/run identity and complete trace export. Label proposal
time separately from the returned post-step state. Export pauses playback first,
retains raw/injected/canonical observations and every applied override, and declares
`applied_machine_commands=false`. Read/export calls execute no model or physics.

## Viewer design

Use the existing mine palette: ground #050a0c, ink #eeeae0, muted #a4ada9,
rule #34403f, ore #d6aa6b and observed state #9cd6bc. Use the existing local Space
Grotesk face, left-aligned text, a fixed readable status column and an unobstructed
machine view. The distinctive content is sensor-to-control ownership, not new
decorative chrome. Put sensor health, current owner and override state above the
existing carried/delivered ledger. A compact proposal/applied table makes the
control distinction directly comparable. Keep focus visible and status changes
textual, with no added non-user-triggered motion.

Retain the familiar viewport/playback structure; let the status column scroll
on shorter screens and stack it below the scene on narrow screens. No redesign
of the main authored walkthrough or older viewers. This follows the repository's
frontend-design guidance while preserving the established simulator vocabulary.

## Verification and delivery

Use in-process Python session/handler tests and browser-free JavaScript client/
presentation tests. Cover stale requests, pause with in-flight automatic work,
reset during a run, manual stepping, recovery, terminal/hold endings, exports,
source labels and evidence rejection. No browser, tab switching, desktop
automation or listening service is started by the agent.

Run a bounded practice-only integration check against retained ADR-0069 traces:
four qualified patterns and original healthy comparators for all three weights,
15 cases, at most 9,000 evaluation decisions, one CPU thread, 120-second cap.
Compare actual applied actions, proposals, observations, phases and physical
traces exactly; this is regression evidence on consumed practice data, not new
qualification. Keep export/identity checks and measured costs. Retain failed or
incomplete checks rather than expanding caps. Human visual acceptance stays open.

Commit regularly, push to Nabzx/Kessel and merge into main after checks, as
requested. No release tag, public service deployment or machine connection.
