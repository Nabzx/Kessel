# Spatial range inputs and revised stopping pilot

25 November 2026. [ADR-0066](../adr/0066-spatial-range-contract-and-pilot.md),
[serialization erratum](../adr/0067-spatial-pilot-serialization-erratum.md),
[diagnostic](spatial-range-evidence/diagnostic.json),
[complete pilot report](spatial-range-evidence/report.json).

## Result

The revised supervisor meets all 24 partial-coverage stop/hold criteria and all
three complete-loss moving-carry criteria. All nine healthy/transient/recovered
deliveries pass, with healthy actions and states exactly matching the original
controllers. However, **six of twelve loaded-grade probes fail holding limits**.
The full gate fails. No fresh qualification or runtime promotion follows.

This resolves invalid-height leakage in the new canonical input and gives
partial coverage an explicit stopping response. It does not restore delivery
under partial observations. ADR-0065's failed partial-delivery gate stays failed.
Its old supervisor, original policies, simulator and receiver-frame evidence
remain unchanged.

| Revised-supervisor condition | Cases | Criterion met |
| --- | ---: | ---: |
| Healthy empty-start delivery | 3 | 3 |
| One missing frame, then delivery | 3 | 3 |
| Two-second loss during moving carry, recovery and delivery | 3 | 3 |
| Partial-validity masks: reset/fill/lift/moving carry | 12 | 12 |
| Zeroed-height occlusion: reset/fill/lift/moving carry | 12 | 12 |
| Complete loss during moving carry | 3 | 3 |
| Loaded initial-condition stops on +/-0.06 rad grades | 12 | 6 |

Three additional original healthy neural comparators also deliver, making 51
cases in the corrected pilot. All counts cover three frozen neural seeds on
practice base 19000 or declared stopping fixtures. They are not reliability
estimates or fresh independent environments.

## Input contract

`training/kessel_lab/range_contract.py` adds a separately named
`complete_range_supervisor`. It preserves the existing local observation fields
and rejects malformed shapes, nonfinite proprioception/heights, negative heights
or nonbinary validity. Such errors are not demonstrated stopping behaviour.

The adapter copies raw input, invalidates every cell when freshness is zero,
and zeros every invalid canonical height. It never changes an invalid cell into
a valid observation. It distinguishes stale input, fresh partial input and fresh
complete input. A fresh, fully valid empty crop is healthy ground observation,
not sensor failure.

The new supervisor requires all 25 cells fresh/valid with age at most 0.2 seconds.
Any unusable sample immediately engages conventional speed feedback and zero
joint rates. There is no grace interval. The PI gains, integral limit, frozen
phase, paused task clock and stable-recovery requirement are retained from the
earlier prototype. It reads no true grade, load or obstacle state. Raw input,
canonical input, neural proposal and applied synthetic action are all separate.

Requiring the full grid is a conservative availability choice. It does not prove
all cells are physically necessary. Persistent partial coverage now holds the
machine rather than permitting delivery, including cases a more capable policy
could use. This method is not qualified for useful operation under the native
random impaired-sensing family. No learned perception or spatial imputation was
added.

## Bounded spatial diagnostic

The diagnostic uses the middle decision of each phase in the three retained
healthy practice traces: 15 snapshots. Each snapshot receives eight regional
masks with two encodings, retaining invalid height values or zeroing them.
Fifteen baseline queries match the retained actions exactly. The 240 intervention
queries hold phase fixed and execute no dynamics, teacher or phase updates.

| Phase | Largest absolute action change | Action component | Mask | Encoding |
| --- | ---: | --- | --- | --- |
| Approach | 0.806 | Bucket rate | Centre 3x3 | Retained height |
| Fill | 0.805 | Bucket rate | All cells | Zeroed height |
| Lift | 0.969 | Boom rate | Far three rows | Retained height |
| Carry | 0.857 | Drive | Right column | Retained height |
| Tip | 0.634 | Drive | Left column | Retained height |

These maxima span three neural seeds and the declared masks. They use the
normalised [-1,1] command scale, not physical action units. Changing only the
height encoding under the same mask produces up to 0.506 action difference.
Approach, carry and tip snapshots have zero height everywhere, yet changing
validity alone can change output. Height and mask are separate neural inputs.

The result demonstrates local input sensitivity. One snapshot per phase cannot
establish regional necessity, sufficiency or the cause of an entire failed
trajectory. No smaller required region is selected or qualified from these
consumed inputs. The diagnostic takes 0.25 seconds under its 45-second cap,
using 255 neural forward calls on one CPU thread and no physics or training.
Its original code snapshot is preserved separately from the later scalar-type
serialization correction.

## Partial coverage and moving loaded stops

Both partial encodings invalidate the near two rows of the 5x5 crop. The retained
variant keeps their raw height values. The zeroed variant also clears hidden
heights, matching native occlusion's mask/height semantics. Its fixed geometry
is not the native random visibility sampler. The canonical input makes invalid
heights zero for both variants; neither is silently treated as complete coverage.

All 27 full-task stopping cases detect loss immediately and satisfy the declared
ten-second physical hold. Maximum stopping path is 0.263 m. Moving-carry loss
now begins at observed reverse speed at least 0.5 m/s, rather than at carry entry
while stationary. Physical onset speeds are about -0.55 to -0.57 m/s, with about
2.49–2.51 tonnes onboard. Recovery trials actually override, stop and resume
before completing the original empty-start delivery target.

Stopping cases end after a nonterminal observation window. They are not
successful deliveries, emergency-brake qualification or safe real-machine
operation. No browser, machine interface or existing runtime uses this wrapper.

## Why the loaded-grade gate fails

The component fixtures start with 2,500 kg onboard, speed +/-0.8 m/s and grade
/-0.06 rad. They use the unchanged kernel and a declared nonempty initial state:
2,500 kg is transferred uniformly from pile cells into payload, conserving
material. They are component stopping probes, never empty-start deliveries.

| Grade rad | Initial speed m/s | Stop path m | Ten-second hold path m | Hold peak speed m/s | Result per neural seed |
| ---: | ---: | ---: | ---: | ---: | --- |
| -0.06 | -0.8 | 0.218 | 0.280 | 0.119 | Fail |
| -0.06 | +0.8 | 0.322 | 0.069 | 0.053 | Pass |
| +0.06 | -0.8 | 0.322 | 0.069 | 0.053 | Pass |
| +0.06 | +0.8 | 0.218 | 0.280 | 0.119 | Fail |

Both failures initially travel uphill, reach the three-low-speed-sample criterion
after about 0.7 seconds, then roll downhill before speed feedback catches up.
The hold exceeds both limits: 0.10 m/s peak speed and 0.25 m path. The evaluator
keeps the first settling event and checks the whole following window; it does
not restart the window until a favourable result appears. No collision or
simulator termination hides the adverse physical motion.

The applied conventional stopping controls are independent of neural proposals,
so each of these four fixture trajectories repeats identically across the three
weight sets. Six failed records therefore represent two failed distinct physical
conditions, not six independent machines. Every seed fails its own gate.

The next control experiment should address grade-disturbance compensation and
the transition from braking into holding, using observed motion only. Keep these
failed conditions as consumed diagnostics; freeze any revised law and its pilot
before new execution. Do not claim that successful braking establishes stable
holding or weaken the holding gate. Wider speeds, grip, longer loss and real
sensor faults remain separate, unqualified conditions.

## Aborted attempt and resource accounting

The first attempt fails while serialising its first case because `health.usable`
is a NumPy boolean. No trajectory or exact query ledger is written before the
exception. The available plan, exact sources, empty trace archive and error are
[retained](spatial-range-evidence/aborted-attempt/abort.json). Its costs are bounded
as at most 600 environment decisions and 600 neural queries, with zero replay.
The approximately 1.80-second archive timestamp span is not measured active time.
No outcome from that attempt is counted as a completed trial.

ADR-0067 freezes one serialization-only correction and restart. Casting that
flag to Python `bool` changes neither health decisions nor applied actions.
The verifier compares the two controller sources to enforce that correction's
scope. Corrected execution has a reduced 150-second cap and 30,000 evaluation-
decision cap, leaving the aborted attempt's 600-decision allowance within the
original 30,600 total. No control rule or adverse criterion is retuned.

The corrected pilot completes in 114.77 seconds on one CPU thread, with no GPU:

- 11,462 evaluation decisions and 11,462 neural queries;
- 10,313 additional physical replay decisions across all 48 supervised cases;
- 11,462 additional actor queries across all 51 cases;
- zero state, action or observation replay error;
- zero teacher queries, optimiser updates or held-out cases;
- 3,453,854-byte trace archive, below the 16 MiB cap.

Including the aborted allowance gives at most 12,062 evaluation decisions and
queries, not an exact measured total. The separate diagnostic adds 255 neural
queries. Replay costs are additional as listed above. Every corrected case,
failure and nonterminal hold remains retained, with weights unchanged and exact
source/checkpoint identity. Outcomes are sealed before independent replay.

Verify retained files without executing controllers, a browser or a service:

```sh
python3 scripts/verify-spatial-range.py
```

The fresh-test, runtime, human visual-review and publication boundaries remain
unchanged. This is a conventional synthetic-control experiment, not a new RL,
learned-world-model or field-safety result.
