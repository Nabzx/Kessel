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
