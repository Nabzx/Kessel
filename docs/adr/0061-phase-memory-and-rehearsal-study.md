# ADR-0061: Phase memory and rehearsal follow-up

Status: Accepted for this bounded follow-up. The maintainer requested diagnosis,
a targeted experiment, new training/final evaluation, conditional recorded demo
and PR/narrative review on 21 November 2026. Supersedes ADR-0057's fixed-architecture,
model-free-only boundary only for this separately named study. Historical studies
and all negative results remain unchanged. Extends ADR-0060 for an isolated
recorded technical demo, conditional on the admission gate below.

## Evidence and hypothesis

The full-cycle study scores 0/96 final deliveries for both recipes. All curriculum
seeds pass fill; none advances past retract. Seed 41 regresses from 16/16 fill to
0/16 while reaching only 12/16 retract. Seeds 7/19 end with 0/32 retract training
successes. The earlier imitation dataset covers only two complete teacher episodes.
A low fitted action error is not closed-loop proficiency.

Test broader complete-episode teacher coverage and mixed-phase supervised replay
without subsequent PPO forgetting. Compare memoryless imitation and imitation
conditioned on explicit observation-derived five-state memory. Both use the same
70-input, two-layer 128-unit network, data and update budget. In the memoryless arm
five phase inputs are zero. This is a practical imitation comparison, not an RL
improvement or a proof of the unique cause of previous failures.

The memory transitions follow the reference controller's observed contact, load,
boom/curl, receiver displacement and speed thresholds, with a fill timer. The
memory computes no continuous control. Every deployed continuous action comes
from the network. Label the result as learned actions with rule-based phase
memory, never fully learned planning or learned-world-model training. Teacher
queries are allowed only during training collection, never validation/final tests.

## Frozen budget and selection

Use training seeds 7/19/41 in both arms. Collect 32 complete reference episodes
on train seeds 19000–19031, retaining failures. Then three DAgger rounds collect
all six learners on eight shared training seeds per round: 19100–19107,
19116–19123 and 19132–19139. Query the teacher once per visited training state;
execute learner actions, retaining failures. Aggregate all arms' data into a
common replay dataset so phase replay is retained. Every rollout is at most
600 reference decisions. Shared acquisition is capped at 120,000 decisions and
teacher queries. No teacher queries on validation or final cases.

Train 1,500 minibatches initially and 750 after each DAgger round, batch 512,
Adam learning rate 0.001, clipped gradient norm 1.0, uniform sampling across
observed teacher phases. Six runs cap at 22,500 optimiser minibatches. Cold-start
all six policies from matched seed-specific weights. No PPO or simulator dynamics
changes. Save optimiser/RNG/source/data identities and resumable progress every
250 updates. Save collected episodes individually so committed cases are not
requeried on resume. Retain all round candidates and all outcomes.

Audit available Git/local JSON/PT/NPZ archives and ZIP members before collection.
Reserve validation 108200–108215 and final 207600–207631. The original
108100 proposal was touched by a unit-test policy fixture before collection,
so it is excluded rather than represented as unused. Fixtures now use the old
consumed validation range. Final proposals 209800–209831 and 209600–209631 were rejected because the
audit found prior world-model contact and high-resistance data. The replacement
207600–207631 is outside all explicit historical metadata seed intervals. No query was
made on the replacement final cases. If used, choose unused
ranges before any outcomes and record the change. Freeze realised initial-state
and pile fingerprints. The old final range is consumed and excluded.

Evaluate all six candidates after each of four rounds on 16 validation starts.
Select each run by complete deliveries, fewer collisions, shorter successful
cycles and earlier exact tie. Freeze all six selections before evaluating either
arm on 32 final starts, 192 final cases. Admission requires every seed of a method
to achieve at least 28/32 deliveries of 2,000 kg from empty, with at most one
collision per seed. No test-based reselection. Count collection, teacher queries,
reused training samples, validation, final evaluation and independent replay
separately. Global active study wall cap 5,400 seconds, reserving 600 for final
policy evaluation; partial validation cannot select. If capped, retain the
smaller actual budget and failure rather than expanding it silently.

## Presentation and review

Only an admitted method can supply a successful learned-action technical demo.
Retain finite recordings, model/split/source identity and matching measured
metrics. Use the first successful final case by seed order, never hide failure
counts or the conventional memory. Verify all final traces independently. The
main authored concept and world-model claims do not change.

Review and merge the completed PR stack in dependency order after required checks.
Review the task-first prototype in native Chrome for framing, source transitions,
keyboard/reduced-motion behaviour and readability. Agent visual review does not
constitute a human comprehension study or certify target hardware performance.
