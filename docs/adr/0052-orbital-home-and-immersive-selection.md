# ADR-0052: Orbital home and immersive selection

Status: Accepted

## Context

Implements the home sequence in #349: #351–#358 and #381, following ADR-0051.
The maintainer authorises completing this sequence without intermediate permission
requests. The local prototype/hero.html and wordmark-position edit are existing
maintainer work and remain untouched. Visual acceptance is recorded separately
from implementation and automated verification.

## Decision

Choose a photographic orbital opening: a large, correctly oriented Earth above
an original off-white vector wordmark, two detailed spacecraft, a restrained
star field and one start action. Use the existing high-resolution NASA sources;
new shading must preserve orientation, linear colour and one world-space sun.
Clouds, surface, night lights and limb share that sun. No dense nearby asteroids.
Author the new original satellite through the pinned local Blender MCP, with an
editable source scene, physically legible solar arrays/insulation/radiators and
bounded browser derivatives. Retain the NASA ISS as a distinct second spacecraft.
Orbits are illustrative and do not claim live tracking.

The selector becomes an immersive full-screen photographic scene. Underground is
first/default, followed by glacier, desert, space and deep sea. Only Underground
is deployable. A real rotating Earth renders inside a bounded right-hand context
panel using the same renderer and scene, with transparent canvas elsewhere.
The selected image and its credit remain distinct from actual Rwanda imagery.
A pair of decoded image layers crossfade with a latest-request token; invalid
or missing optional assets cannot overwrite a newer selection.

A short fade/exposure settle introduces the home. Start moves focus to the
selector and smoothly settles the globe into its smaller context view. The
subsequent Rwanda hand-off uses a controlled fade into the existing exterior
rather than magnifying a miniature globe through mismatched scene scales.
Preparing, cancellation and reduced motion keep a usable state. No iframe,
second WebGL renderer, live imagery key or runtime Blender service is shipped.

Use a new home stylesheet rather than editing the maintainer's local wordmark
position change. Version every local module/style together. Preserve source,
coordinate and pipeline disclosures; global footer treatment follows ADR-0051.
No pricing, manual control or release/publication work is introduced.

## Verification

Retain a browser direction study and animatic covering the full proposed route,
with old/new frames, both arrival alternatives and current downstream shots.
Do not claim that unrebuilt surface/kit frames are their final redesigns.
Measure normal/reduced-motion laptop layouts, geographic frames, actual asset
adoption/fallback, rapid input, complete mine hand-off, cold preparation and
settled p95/p99/max frames. Visual judgement remains for the maintainer; the
implemented route must be reviewable without interrupting its completion.
