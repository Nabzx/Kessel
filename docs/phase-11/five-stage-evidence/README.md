# Five-stage reference evidence

Reference feasibility only, from consumed validation seeds 108000 to 108015.
No learned training, no final-test use. See [the report](../five-stage-contract.md).

- `report.json`: all 80 case outcomes, source identity and counted costs.
- `traces.json.gz`: all actions, pre/post states and rewards.
- `source.zip`: exact package and locked dependencies.
- `files.json`: SHA-256 manifest, excluding itself.

Each retained trace was independently action-replayed during collection.
Reference and replay each use 9,712 decisions. All replay state/reward errors
are zero. Prepared starts and phase-initialised references are identified.
