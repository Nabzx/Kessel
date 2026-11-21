# Post-application research index

All 29 exploration tickets now have recorded findings or concrete proposals.
This is research coverage, not 29 closed implementation tickets. The PR stack
is open; proposed ADRs, visual judgement and future experiments remain distinct.

| Tickets | Output | PR |
| --- | --- | --- |
| #406 | [Artefact scope](2026-11-12-working-demo-scope.md), proposed ADR-0056 | #435 |
| #409, #420–#422 | [Simulator and reward readiness](2026-11-12-learning-readiness.md) | #435 |
| #410, #423–#426 | [Skill prerequisites](2026-11-12-learning-prerequisites.md), proposed ADR-0057 | #436 |
| #407, #415–#416 | [Narrative and camera study](2026-11-13-walkthrough-narrative.md), proposed ADR-0058 | #437; source/geometry hardening in #438 |
| #408, #417–#419 | [Retrofit/observations/logs](2026-11-13-retrofit-observation-contract.md), proposed ADR-0059 | #438 |
| #411, #427–#428 | [Scenario isolation and scorecards](2026-11-13-scenario-evaluation.md), proposed ADR-0059 | #438 |
| #412, #429–#431 | [World-model recommendation](2026-11-13-world-model-recommendation.md), proposed ADR-0060 | #438 |
| #413, #432–#433 | [Recorded/live runtime and controls](2026-11-13-demo-runtime-and-controls.md), proposed ADR-0060 | #438 |
| #414, #434 | [Evidence admission/integration](2026-11-13-evidence-admission.md), proposed ADR-0060 | #438 |

## Concrete artefacts

- [Interactive task-first narrative study](../phase-11/narrative-study/index.html),
  with current-opening comparison, retained recordings and camera/overlay controls.
- Eight reproduced learned evaluations and ten independently replayed reference
  traces in the readiness evidence.
- Six teacher-fit comparisons, 24 stage probes and bounded CPU execution checks
  in the prerequisite evidence.
- A 576-decision sensor boundary probe, 436-file metadata inventory and nine-case
  source-separated scorecard in the frontier evidence.
- Draft observation-record and evidence-admission contracts, explicitly unimplemented.

## Work still required

Update, 14 November: the [bounded retraction pilot](../phase-11/retraction-pilot.md)
has now run. Its selected baseline checkpoints score 16/16, 0/16 and 16/16 on
separate pilot tests. The runner, source-bound checkpoint/resume and available-
archive reservation audit are implemented. The pilot gate passes; a learned
full-cycle result remains unproven.

The main walkthrough has not changed. The narrative prototype is an isolated
local study; human comprehension review and existing visual acceptance are
unperformed. It does not qualify phone controls or rendering performance.

The next implementation is the coherent five-stage factory, its reference
feasibility and retention checks, followed by the separately bounded full-cycle
comparison. The completed pilot audits 601 unique available archive/history
blobs; it does not certify unretained external experiments. Validation and pilot
test cases are consumed, while final-test roles remain reserved and unqueried
by a policy. Preserve those roles before the next experiment.

Actual sensor acquisition/calibration, bounded machine logs, a full scenario
catalogue, live inference and production evidence integration remain implementation
work. Hardware deployment, a successful learned full cycle and model-assisted
learning gains are not demonstrated by these research reports.
