# Evidence admission and walkthrough integration

Refs #414 and #434. Recommendation: proposed ADR-0060.

## Integration recommendation: #414

Retain the existing concept walkthrough and add a clearly identified technical
evidence route before considering a new production default. The task-first
narrative study is a concrete communication prototype, not proof that a learner
can complete the work. It can already explain current reference feasibility
and failed learning honestly. Future successful runs must enter through the
same evidence checks rather than replacing captions with stronger claims.

The current static packager includes allowlisted index/css/js/data/assets,
including curated recorded JSON bundles, but excludes `docs/`, Python tools,
training environments and raw checkpoints. Therefore the narrative research
page and new audit reports are not silently added to the public presentation.
Do not change packaging or publish while deciding where the evidence route fits.

A production integration should connect the task, observation, forecast and
policy explanation with explicit source/time hand-offs. Hardware views retain
proposed wording. A human comprehension review is still unperformed; human
visual acceptance #351/#385 is separate from the automated research checks.

## Run manifest and admission contract: #434

The existing catalogue already binds bundle bytes to SHA-256 and the adapter
validates units, counters, finite state, terminal boundaries, model/controller
identity and action replay evidence. The new research adds source/evidence
manifests and independent consistency checks. Reuse these boundaries rather
than creating a renderer that trusts arbitrary counters from a UI control.

The proposed [admission contract](demo-contracts/evidence-admission.json)
requires the following chain:

1. Source commit/package hash; simulator and task versions; exact configuration.
2. Dataset split, generator/seed/stream/episode identity, realised start hash,
   prepared-state flag and initial payload.
3. Agent kind and controller or executed checkpoint hash. No null identity for
   a result called learned. Browser playback is recorded actions, not browser
   checkpoint execution.
4. Actual actions/states, event/transfer times, reward decomposition, delivered
   and spilled mass, terminal/truncated outcome and simulator step counts.
5. Forecast model identity, raw/filter designation, anchor/action, horizon,
   reference index, missing/rejected flags and physical-unit error.
6. Training/validation/evaluation/data-fitting costs and checkpoint-selection
   rule, plus retained failed cases and complete result inventory.
7. Independent replay, configured tolerances, conservation/geometry checks and
   a byte-hashed static export with matching source labels.

Separate structural admission from proficiency admission. A verified failure
is admissible evidence and must remain a failure. Calling a policy proficient
requires the separately predeclared complete-task gate; for the proposed nominal
study that is at least 28/32 empty-start successes per training seed with its
collision limit. Those results do not exist yet. A conventional controller,
prepared bucket or authored animation cannot satisfy the learned gate.

Invalidate results when source, weights, observation normalisation, simulator,
task or scenario changes. Retain the previous artefact under its original
identity; do not update its manifest to imply that a new binary produced old
results. An export that cannot replay independently remains inspectable research
and is excluded from capability claims.

## Concrete next implementation order

- Observation/log adapter and scenario-reservation audit from ADR-0059.
- Bounded retraction pilot infrastructure and coherent stage factory from
  proposed ADR-0057, preserving legacy defaults and failures.
- Recorded catalogue, scorecard and transactional source selection.
- Evidence-route integration with the narrative's camera/source contract.
- Fresh native/browser verification, comprehension review and any later
  separately authorised release work.

Existing #272–#276 already cover provenance, native performance, accessibility,
packaging and final release review. Add missing acceptance details to those
work items when the implementation is settled; do not create duplicates or
close visual/release tickets because a research recommendation is complete.
