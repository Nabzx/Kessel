# ADR-0018: Well-lit product-demo lighting, superseding the headlamp-only mood

Status: Accepted

## Context

The lighting rig since ADR-0005, tuned further in Phase 6b (#103) and
again in Phase 6c, was built around a single warm headlamp as the
dominant light source, with everything outside its pool falling toward
the fog colour. That was a deliberate choice for an "offline, no GPS,
underground" mood -- but direct maintainer feedback on the Phase 6d
realism work (#122/#123) is that it reads as too dark full stop, and
that the real CC0 textures and rock geometry just added are getting
lost in it rather than showing. The ask is a well-lit product-demo
look: legibility and showing off the work over atmosphere.

## Decision

Replace the headlamp-dominant rig with a broad, bright base light (a
soft overhead work-light directional, much stronger ambient/hemisphere)
so the scene reads clearly on its own, with the headlamp kept as a
narrative accent (the loader is still a mining vehicle with a working
headlamp) rather than the thing doing the actual illuminating. Fog
density drops sharply so geometry stays legible at distance instead of
fading to the fog colour. Tone-mapping exposure goes up to match.

## Consequences

This directly supersedes the "atmospheric, headlamp-only" mood ADR-0005
established and Phase 6b/6c iterated on -- not a tweak within that
direction, a reversal of it. The underground/offline premise is still
true in the HUD copy and narrative; it no longer needs the render
itself to look dim to read as underground. Tunnel/floor/rock materials
(#122/#123) are unchanged; they just become visible now that something
is actually lighting them across the whole scene, not only near the
loader.
