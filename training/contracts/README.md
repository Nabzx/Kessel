# Loader and experiment contract, version 1.0

See [ADR-0033](../../docs/adr/0033-loader-and-experiment-contracts.md).
These unit and episode semantics are implemented by the curated recorded
viewer bundle under [ADR-0043](../../docs/adr/0043-recorded-experiment-viewer.md).
Its compact browser layout and evidence are documented in the integration
report. The CPU benchmark writes a separate report format.

## State and actions

Physical positions are metres in x-forward/y-left/z-up. Yaw, articulation,
boom and bucket angles are radians. Speed is signed metres/second, all mass
fields kilograms. Piles store height in metres, cell area in square metres
and bulk density in kg/m³. The mass ledger includes pile, bucket, spilled and
delivered mass. Do not let rendering particles change this ledger.

`actions` has shape `(num_envs, 4)`: acceleration, articulation rate, boom rate
and bucket rate, each normalised to [-1, 1]. A final record has `action: null`.
Default limits and finite/bounds assertions are in `contracts.py`. Convert
physical points to Three.js `(x, z, -y)`. Never flip the chassis heading to
represent reversing.

## Manifest example

The executable example below is a schema illustration, not a measured run:

```json
{
  "schema_version": "1.0",
  "run_id": "example-only",
  "source_mode": "authored",
  "started_at_utc": "2026-11-05T00:00:00Z",
  "source": {"commit": "<git-sha>", "dirty": true},
  "simulator": {"id": "synthetic-loader", "version": "0.1"},
  "configuration": {"seed": 42, "decision_s": 0.1, "substeps": 5},
  "configuration_sha256": "<canonical-configuration-hash>",
  "dataset": {"split_id": "synthetic-v1", "seed": 42},
  "controller": {"type": "reference", "checkpoint_sha256": null},
  "software": {"python": "<version>", "numpy": "<version>"},
  "hardware": {"cpu": "<measured-identity>", "device": "cpu"},
  "counters": {
    "completed_episodes": 0, "environment_steps": 0,
    "agent_decisions": 0, "optimiser_updates": 0,
    "imagined_transitions": 0, "simulated_seconds": 0,
    "training_wall_seconds": 0
  }
}
```

## Episode records

Each episode has `episode_id`, `seed`, `terminated`, `truncated`, `outcome`,
`metrics` and `records`. The flags cannot both be true. Terminated means a
task-defined success/failure; truncated means an external time limit.
Records have increasing `t_s`, `state`, `observation`, `action`, `reward_terms`
and optional `predictions`. Privileged `state` must not leak into observations.

Every prediction identifies `model_sha256`, `horizon_s`, `prediction`,
`reference`, `residual` with units, and an uncertainty score/method. A variance
score is not a metre error or confidence probability. Missing or unsupported
predictions are absent/null. Learned actions require an executed checkpoint
hash. Recorded synthetic bundles require concrete versions and finite values;
example placeholders above are invalid in such a bundle.

Major schema changes need a new version and ADR. The future adapter must
validate before switching source modes and leave the authored experience
available under its own label. Never combine recorded learning data with
authored business measures under one measured-results label.
