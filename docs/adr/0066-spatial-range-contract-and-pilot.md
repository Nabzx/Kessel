# ADR-0066: Spatial range contract and conservative coverage pilot

Status: Accepted for the maintainer's repo-local continuation on 25 November 2026.
Adds separately named experiments. ADR-0065 and its failed gate stay unchanged.

## Input contract and decision

The old 20%-valid rule accepts a 60%-valid input on which every tested neural
seed fails. The feature encoder consumes heights and validity separately; the
phase rule masks heights. Invalid heights can therefore influence neural output.
Do not silently interpret a stale crop as fresh observed ground.

Add an isolated canonical adapter for the existing single-slot observation.
Require finite (1,15) proprioception, finite nonnegative (1,5,5) heights and a
binary (1,5,5) validity mask. Freshness is binary; age and elapsed time are
nonnegative. Malformed input is an error, not a demonstrated stop. Keep raw input
unchanged. For freshness 0 invalidate all cells. Set every invalid canonical
height to zero without inventing a valid observation. Distinguish fresh complete,
fresh partial and stale inputs. A fresh complete zero-height crop is healthy.

No tested regional subset is yet qualified for the frozen actor. A new
`complete_range_supervisor` therefore requires all 25 cells valid, fresh and age
at most 0.2 seconds. This is a conservative availability choice, not proof that
every cell is physically necessary. Stop on the first unusable sample, including
a transient; remove ADR-0065's grace. Raw neural proposals on canonical inputs
remain logged separately from applied conventional stopping controls.

Retain ADR-0065's speed-only PI gains (2 proportional, 1 integral, +/-0.45
integral, conditional anti-windup), zero joint rates, frozen phase, paused task
clock and three-healthy/three-slow-sample recovery. No grade, true load, obstacle
or reference action enters the wrapper. Healthy complete inputs must preserve
original neural actions, phases and states exactly. This is a new source identity,
not a revision of the old supervisor or a learned stopping policy.

## Bounded spatial diagnostic

Read only the three retained ADR-0065 supervised healthy practice traces. For
each neural seed and each phase 0–4, use the middle decision of that phase.
Freeze phase for inference. Compare the original input with eight invalid-cell
patterns: near two rows, far three rows, centre column, left column, right column,
centre 3x3, single centre cell and all cells. Test both stale-value-plus-mask and
zero-height-plus-mask encodings. Retain masks, all raw proposals, per-action
differences and height-cue changes. Check the original proposal matches exactly.

Exactly 15 baselines + 240 interventions = 255 neural forward calls; zero
physics, teacher, training or phase-update calls. One CPU thread, no GPU,
45-second active cap, at most 2 MiB JSON. Hash original report/traces/checkpoints,
plan and source. This measures local input sensitivity, not regional sufficiency,
causality for a trajectory or qualification. Do not select a smaller required
region from these consumed snapshots.

## Frozen revised practice pilot

Use original phase-memory actors 7/19/41, practice seed 19000 and unchanged
nominal physics for full task cases. No receiver-frame combination or training.
For each seed run healthy delivery, a single lost frame after one second and
two-second complete loss during moving carry followed by recovery. A moving-
carry trigger is observation-derived phase 3 and observed speed <= -0.5 m/s.

For each seed also run partial loss from reset, on fill entry, on lift entry
and during moving carry. Test both masks with retained height values and masks
with hidden heights zeroed, independently. Invalidate the near two rows (40%).
The zeroed variant matches native occlusion's height/mask semantics, but is a
deterministic pattern, not the native random visibility sampler. Add complete
loss during moving carry. These are 12 cases per seed, 36 full-task executions.
Phase-entry triggers use a separate observation-derived memory. A trigger that
never occurs fails its case, even if the underlying task otherwise completes.

Partial and permanent full-loss cases are explicitly expected to stop and hold,
not deliver. This differs from ADR-0065's partial-input delivery gate, which
remains failed. Report the availability tradeoff; do not claim restored partial-
observation delivery. Require detection within one 0.1-second decision, settling
within 2.5 seconds of loss (three physical speed samples <=0.08 m/s), path before
settling <=2 m, then a ten-second nonterminal hold with speed <=0.10 m/s and
path <=0.25 m. Require zero collision and no simulator termination during hold.
Healthy/transient/recovered cases must deliver 2,000 kg from empty, collision-free;
recovery must actually stop and resume. Include three original healthy comparators.

Add twelve declared initial-condition stopping probes: each neural seed, grade
-0.06/+0.06 rad crossed with initial speed -0.8/+0.8 m/s and 2,500 kg onboard.
Use `SceneConfig(randomise=False)` with the specified grade and practice seed,
unchanged kernel, pose x=0/y=0/yaw=0, joints articulation 0/boom 0.35/curl 0.95.
Transfer 2,500 kg uniformly from initial pile cells into payload, preserving
initial material mass. Set conventional phase 3 explicitly for this fixture.
Update initial observations and record exact initial states. These nonempty
fixtures are stop-only component tests, never successful empty-start deliveries.
Inject complete loss immediately; use the same stopping and ten-second hold gate.
The supervisor sees only local observation; evaluator-only grade/load are logged.

Total 51 cases: 48 revised-supervisor executions and 3 original healthy controls.
Fixed order, at most 600 decisions each, 30,600 evaluation decisions, 28,800
independent physical replay decisions and 30,600 independent neural-action replay
queries. Use one CPU thread, no GPU, 180-second total active cap including replay,
16 MiB trace archive. Guard against reference-controller calls. Replay actual and
injected observations, canonical inputs, proposals, actions, phase and task clock
exactly. Seal sources and case plan before any pilot query; outcomes before replay.

Every case must pass its own declared criterion, healthy controls must match
exactly, all weights unchanged and every replay exact to advance the hypothesis.
No pooled override of failures. Retain all failures or partial/budget-limited
outputs; never expand caps, retune or reselect after observing results. This is
practice evidence only. Fresh qualification needs its own unused-case audit,
protocol and stopping/recovery/delivery gates. No runtime promotion, field safety,
RL gain, browser/service interaction, remote publication or machine connection.
