# Recorded sensor-only forecasts

The strict numeric recording importer and observation-only forecasting experiment
are implemented. The [completed study](sensor-forecast-v2-evidence/report.json)
does **not** qualify the predictor. Validation selected an uncertainty threshold
without final-row tuning. On 29,786 accepted fresh rows, 21.97% exceed the declared
position/speed/load/height limits, against a maximum of 10%. Speed MAE is
0.03085 m/s versus persistence's 0.02335 m/s; valid-height MAE is 0.01302 m versus
0.00719 m on the same rows. The persistence-benefit gate also fails. Raw results,
failed family support and weights are retained. No control assistance is enabled.

The model sees the current 65 observed numeric channels, applied action and one
previous observation/action. No global pile, friction, density, obstacles,
privileged simulator state or future observation enters inference. Absolute
position/time are removed from encoded context; position residuals and a declared
clock prior produce the output. It predicts local observations, not a global map,
material conservation, delivery events or raw perception. Output bounds and unit
heading are declared priors.

The 196 hashed recordings contain 26 training, 18 validation and 152 evaluation
episodes from disjoint base seeds. They yield 6,298 / 4,303 / 32,140 causal pairs.
The first import rejected inconsistent reconstructed terminal clocks before any
optimisation. Its [failed capsule](sensor-forecast-evidence/report.json) remains.
ADR-0089 excludes 99 partial terminal snapshots from conversion, retaining them
in the original source archives. No full 0.1-second target is removed or clock
repaired. The second attempt used 2,250 updates and 19.70 seconds on one CPU,
zero new physics queries, within its 240-second/64-MiB cap.

## Import a numeric recording

    PYTHONPATH=training training/.venv/bin/python -m kessel_lab.sensor_records path/inside/repo.jsonl.gz

The strict schema is `kessel.sensor-recording-1`; examples are in the study's
`recordings.zip`. A header declares source SHA, source identity, source kind,
clock, calibration, frame and three sensor IDs. Each JSONL sample contains use
time, the versioned observation packet and historical normalised action, or null
when absent. Channels declare units, capture/delivery times and numeric values.
Proprioception has 15 fields; local height and binary validity are 5 by 5.
Unknown/duplicate fields, non-finite values, calibration/identity drift, future or
reordered timestamps and stale proprioception are rejected. Stale/invalid range
is masked. Sequence/time gaps break pairs and history. Historical commands are
never executed. Input is bounded to 16 MiB and must resolve inside the repository.
The tool does not open provenance paths or connect to machinery.

No actual machine recording was supplied. `claimed_field_recording` records can
use the same numeric validator, but that label is an assertion of provenance,
not authenticated hardware, a CAN/LiDAR decoder or field validation.

## Verification

    python3 scripts/verify-sensor-forecast.py
    PYTHONPATH=training training/.venv/bin/python -m pytest training/tests_lab/test_sensor_records.py training/tests_lab/test_sensor_checkpoint.py -q

The standard-library verifier reconstructs every converted observation and causal
pair from original hashed episodes, checks split lineage, training-only scales,
validation selection, fresh errors, persistence and family support. Checkpoint
tests replay saved predictions with simulator transition/state access disabled.
Neither numerical verification nor this experiment closes visual reviews.
