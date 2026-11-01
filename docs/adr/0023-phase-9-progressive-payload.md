# ADR-0023: Phase 9 progressive scene payload

Status: Accepted

Supersedes [ADR-0002](0002-mobile-payload-budget.md) for the Phase 9 mission
demo.

## Context

The old ~2.9 MB raw ceiling covers one rollout. Phase 9 adds globe imagery,
surface context, a tunnel network, and a fleet. Loading all of these before
the first frame would delay the initial view and hold unused scene assets in
memory on mobile.

## Decision

Load the experience progressively: the first interactive globe is the initial
stage; load Rwanda surface assets during descent; load underground geometry,
vehicles, and mission data before entering the fleet view. Keep only the
current and next stage resident during a transition, then dispose of the
departing stage's textures, geometry, and materials when it is no longer
needed. Shared renderer resources may remain resident.

Set transfer targets for Kessel-owned static assets, measured after gzip or
Brotli: no more than 3 MiB before the first interactive globe, no more than
3 MiB additional for the surface stage, and no more than 4 MiB additional for
the underground stage. Keep structured mission data at or below ADR-0002's
2.9 MB raw ceiling. Compress textures for web delivery where supported and
provide a compatible fallback. These are acceptance targets to measure in
the verification ticket; reduce optional cloud, night-light, and surface
detail layers before increasing them. Third-party CDN libraries are reported
separately, not hidden in the Kessel asset totals.

## Consequences

The full interactive route is budgeted at 10 MiB of Kessel-owned transfer,
while the first view stays within the existing quick-load intent. The descent
must handle loading and failure states. Asset totals need to be recorded per
stage during verification, including compressed transfer size and decoded
texture memory. An optional visual layer can be omitted on constrained
devices without blocking the mission.

## Final Phase 9 verification

The [verification report](../demo/phase-9-verification.md) records the final
stage transfers, decoded texture estimates, frame samples, mobile CPU profile
and slow-network timing, including the retained excavator asset. The mission
passes the 3/3/4 MiB stage transfer targets and the 10 MiB total. Optional
globe layers loaded after first interaction are reported separately. Libraries
and fonts are vendored locally and listed separately from mission assets.

The software-rendered browser samples do not meet a 30 fps smoothness target.
They are disclosed as a shortfall, not substituted for physical-phone results.
A real mid-range phone measurement remains outstanding. The core flow runs
without external requests using `?offline=1`; Google satellite reconnaissance
is optional online content with its own service attribution.
