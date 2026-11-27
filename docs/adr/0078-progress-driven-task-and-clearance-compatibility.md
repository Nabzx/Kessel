# ADR-0078: Progress-driven collection and clearance compatibility

Status: Accepted for the maintainer's 27 November request to fix the remaining
controller, stopping, model and release-preparation work. Preserves all earlier
negative evidence, numerical kernels, selected actors and services.

## Diagnosis and implementation

Retained traces show the rejected fixed-timer reference carries an underfilled
bucket after twelve seconds. The original neural policy intercepted by the wall
guard remains in fill with about 2,311 kg while continuing forward. Do not weaken
the guard or count the resulting halt as a completed delivery.

Add a separate observation-only conventional task controller. Use current load,
local valid height, observed speed and odometry to detect pickup progress,
exhausted cuts and travel limits. Fill time begins at actual contact, rather than
the first distant crop cue. Retain load during collection manoeuvres; retract
and change collection lane when progress stalls. Keep damped direction-aware
steering and receiver-relative arrival. Commands, tactical memory, retries,
stopping handoffs and source identities are explicit. This is conventional
planning/control, not a learned world model or a successful neural policy.

Use the separate ordered-clearance sensor/supervisor for stop handoffs. Do not
give hidden pile geometry to the task controller. Local poses, load and a
preloaded receiver target are existing observations. Keep the original 2,000 kg,
600-decision empty-start task and material accounting. Never reset physics to
retry, continue a terminated run or fabricate obstacle/range recovery.

## Bounded development and evaluation

Spend at most 40,000 physical/teacher decisions and 300 seconds in explicitly
adaptive practice development on bases 19020/19021. Permit at most six documented
controller revisions, retaining every run/source revision and failed outcome.
Use component diagnostics before another full run. These are tuning data.

Freeze the chosen source before validation on base 19022 across all thirteen
families. Nominal, pile, shifted receiver/start, grip, resistance and impaired
sensing require actual delivery without collision. Complete loss and blocked
paths require controlled stop and ten-second holding instead. Recovery fixtures
must stop then resume. Keep unfulfilled gates open. No failed setting is removed
or assigned an easier criterion after evaluation.

The final validation/stop/recovery comparison is capped at 12,000 physical
decisions, 12,000 independent action replay steps and 180 seconds, one CPU thread.
Test malformed/stale/old clearance input, phase/task clocks and reset in-process.
Healthy compatibility means completed delivery while the guard remains active;
it does not mean copying unsuccessful old actions. Changing continuous commands
creates a new method with no inherited qualification.

If practice and validation gates pass, freeze a separately budgeted audited fresh
qualification before considering an isolated runtime. Only a feasible teacher
may supply another neural candidate's labels. No broad neural refit is authorised
merely to repeat the rejected data recipe. Record split and cost ledgers before
any fitting. All browser tabs and services remain untouched.

The new task composition accepts a fresh partial crop with at least five valid
cells. After initialisation it permits at most 0.2 seconds of explicitly recorded
missing-range grace while independent clearance remains usable. It never invents
valid cells. Uninitialised absence or longer loss requests the unchanged numeric
bootstrap brake law, with a zero conventional interface placeholder, not a neural
proposal. Phase/task time pauses during stopping. Require three usable and slow
samples before resumption. This new transient-input contract does not inherit the
old complete-coverage qualification or its detection timing. Persistent loss from
reset and blocked-path detection remain immediate; a moving range outage has
the declared grace plus at most one decision (0.3 seconds) to trigger stopping.
