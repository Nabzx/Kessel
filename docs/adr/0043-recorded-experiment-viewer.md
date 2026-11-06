# ADR-0043: Recorded experiment viewer

Status: Accepted

Implements ADR-0031's separate recorded-data adapter. The authored mine,
comparison figures and proposed hardware remain illustrative.

## Decision

On explicit world-model entry, progressively fetch a small catalogue and a
hash-checked version-1.0 recorded-synthetic bundle. Validate source, units,
finite values, timestamps, checkpoint/model identities, terminal boundaries
and actual prediction/reference residuals before displaying it. No backend,
model weights or browser inference is required. On failure show an error and
an explicit concept-replay choice, never a provenance-changing silent fallback.

Present initial/intermediate/final checkpoints from the first declared RL seed,
executed in the same fixed reference scenario. Keep failed outcomes and no
successful learned full cycle. Training counts/curves come from that run's
unmodified log, not a drawn improvement curve. Preserve every decision/contact/
terminal record; interpolate pose only, hold decisions and material state at
recorded boundaries. State the measured training wall time, simulated time and
playback acceleration separately. A single animation-frame clock owns playback,
pause, pacing, inspection and return; reduced motion starts paused.

Physical x-forward/y-left/z-up maps to Three.js (x,z,-y). Chassis yaw never flips
on reversal. Articulation, joints, wheel angles, pile heights and material
counters come from records. The machinery mesh is a visual proxy, not a twin.

Inspect actual model forecasts at recorded anchors and supported reference
horizons. Keep observed local sensor crop, independent reference future and raw
learned future visually distinct. Use actual ensemble member endpoint spread in
metres for a labelled disagreement envelope, not a calibrated confidence region.
Show dimensionless model disagreement separately from position residual metres.
Absent/invalid forecasts stay absent or visibly flagged, never smoothed away.

Maintain the permanent concept caption and illustrative business labels. The
recorded viewer has its own short source label, run id and optional provenance
details. Preserve mine comparison, entry camera, scroll position and focus on
return. Keep the authored viewer accessible as an explicitly labelled concept
mode. This integration makes evidence inspectable, not successful deployment.

Refs: #243, #244, #245, #246, #247, #248, #249, #250.

Sources: [pinned Three.js r160 attributes](https://github.com/mrdoob/three.js/blob/r160/src/core/BufferAttribute.js),
[browser digests](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest),
and the contracts in ADR-0033. Prototype results: ADR-0042.
