# ADR-0088: Recorded sensor-only forecasts and log import

Status: Accepted for the request to remove privileged forecast inputs and validate
against recordings. Available recordings are synthetic unless actual field data
is supplied. Do not label synthetic recordings as field evidence.

Add a strict read-only recording schema with clock, frame, calibration and sensor
identities, SI units, ordered capture/delivery/use times, monotonically increasing
sequence and normalised historical actions. Reject unknown/privileged fields,
non-finite values, reordered packets, calibration drift and stale proprioception.
Mask invalid/stale range without inventing observations. Gaps break training
pairs/history; never interpolate absent packets or execute imported commands.
Support externally supplied recordings through the same numeric validator while
keeping provenance assertions distinct from verified hardware authenticity.

Convert retained complete harvest episodes into independently hashed sensor-only
recordings. Read only their observation/action fields, never their physical state
as model input or target. Train on bases 19020/19021; validation uses learned
practice 19025; evaluation uses the fixed fresh learned qualification recordings,
including source/pattern identity. Keep complete split/recording lineage and reject
recording/base overlap. Partial terminal intervals and sequence/time gaps remain
in the raw recording but do not become 0.1-second prediction targets.

Fit three seeded 128-unit residual MLP members with current local observation,
applied action and one previous observation/action. Inputs contain no global pile,
density, friction, grade, obstacle boxes, privileged state or future observations.
Remove absolute position/time from encoded context; predict position residuals
and advance the declared decision clock explicitly. Predict proprioception, local
height and range-validity probability only. Nonnegative height, unit heading and
clock advancement are known output priors, not learned global physics or sensing.
Train-only normalisation, 750 updates/member (2250 total), one CPU thread, 240 s,
no new physical queries and 64 MiB evidence. No final-driven refit or broad sweep.

Retain persistence comparison, raw next-observation errors and failed support
families. Train heights only where target range is fresh and valid. Future dropout
is stochastic; report validity Brier/calibration rather than promising its exact
mask. Forecast use requires current fresh range with >=5 valid cells. Choose the
highest validation coverage uncertainty percentile with >=100 accepted rows and
<=10% high-error rows. High error means position >0.05 m, speed >0.05 m/s, carried
mass >50 kg or mean target-valid height error >0.05 m. Final accepted errors must
meet that unchanged rule and beat persistence by >=10% in speed or valid height
MAE. Never transfer privileged-state qualification to this new predictor.

The live viewer may show sensor-only predictions only with their measured support
and source identity; a failed gate stays experimental/unavailable for qualified
use. Keep privileged hybrid forecasts separately selectable and honestly labelled.
No global map, conservation, delivery prediction, policy-benefit or field claim
follows from local sensor forecasts. Add leakage tests, saved-weight replay,
malformed/gapped-recording tests and a no-simulator-oracle prediction test. Tests
and experiments stay in-process and inside the repository.
