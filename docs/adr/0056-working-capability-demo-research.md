# ADR-0056: Working capability demonstration research

Status: Proposed

Refs #406, #409, #420, #421 and #422.

## Context

The application video has been sent. The maintainer requests investigation of
the walkthrough and a working simulation demonstration. The current site is
a concept visualisation. Its authored successful jobs do not establish a
learned policy's proficiency. The synthetic simulator and retained learned
experiments already exist, but no retained learned policy completes delivery.

The [scope recommendation](../research/2026-11-12-working-demo-scope.md)
separates the presentation, technical prototype and eventual customer product.
The diagnostic report is linked from that recommendation.

## Recommendation

Keep the existing static concept walkthrough as the presentation artefact
while developing a separately identified synthetic capability demonstration.
The first capability milestone is one loader starting empty, collecting
material and delivering at least the reference task's 2,000 kg threshold.
Measure the outcome across declared scenarios and seeds. A conventional
controller establishes feasibility, not learned proficiency.

Diagnose and address retraction and transport before adding learned world-model
assistance. The retained curriculum reaches retraction but does not train
carry or complete stages within its budget. Preserve the failed results.
Decide the next bounded training protocol under #410 and its focused children.
The diagnosis alone does not justify changing reward weights or claiming that
a longer run will solve the task.

Use actual checkpoint actions and outcomes in recorded synthetic evaluation
playback first. Assess live inference separately under #413. Admission to the
main presentation is governed by #414, including failed runs, identity checks
and source labels. A successful synthetic capability demonstration is not an
MVP for a mine-data product or evidence of deployment readiness.

## Alternatives

- More cinematic presentation work improves explanation but cannot establish
  policy proficiency. Retain the current scenes while investigating the
  underground-first route under #407.
- A new physics engine could improve some approximations but would discard
  working diagnostics before the cause of the learning failure is established.
  Reconsider only if measured task-relevant limitations justify replacement.
- A mine-data ingestion prototype would test a different product hypothesis.
  It needs input sources, a consumer workflow and a useful output that this
  repo does not currently implement. Do not silently turn the autonomy work
  into that product.
- Learned world-model assistance adds an additional failure boundary before
  model-free task proficiency is established. Existing studies retain negative
  results, including rejected imagined branches.

## Consequences and boundaries

This proposal does not supersede ADR-0030, ADR-0054 or ADR-0055, change the
default route, authorise hardware purchases or publish a release. Changes to
those decisions require a further accepted ADR. The scope decision can be
reviewed independently of presentation taste or training outcomes.

Follow-on implementation must specify independent validation, frozen test
scenarios, compute/data costs, evidence export and failure behaviour before
running an experiment. Current diagnosis scenes are reused research evidence
and cannot become an untouched final test set.
