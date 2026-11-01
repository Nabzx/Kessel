# ADR-0027: Phase 9 presentation and authored vehicle

Status: Accepted

Extends ADR-0022 and ADR-0024. Supersedes the temporary vehicle sourcing
approach in issue #154 and the override state in ADR-0024.

## Context

The agreed deliverable is a concept visualisation for an investor demo.
The fleet overview must expose routes and traffic; a closed tunnel roof hides
both. Truck inspection must follow the machine and explain offline autonomy.
A learned policy and surveyed Rutongo workings are outside this repository.
The maintainer authorised an original procedural vehicle when no truck asset
was present. An excavator is not an underground haul truck.

## Decision

Use a cutaway network in fleet overview and reveal the tunnel interior during
truck inspection. Derive camera framing and level labels from the network.
Provide both on-scene picking and keyboard-accessible fleet controls. Keep
one renderer, release departed stage assets, and stop playback in hidden tabs.

Finish the original, independently articulated vehicle described by
`assets/models/haul-truck.json`. Geometry is authored for Kessel and covered
by the repository copyright; no third-party model licence or authenticated
download is required. The TH315 specification supplies the reference envelope,
not a claim of manufacturer fidelity. Share or instance repeated geometry.

The mission may define `fleet.dwell_seconds`, `fleet.inspection_time_scale`,
and `prediction_preview` samples with horizon seconds and illustrative error
in metres. Loading and tipping occur at their route endpoints with the truck
stationary. Cargo fills during loading and clears during tipping. Direction
is taken from the directed route, including after a reversal.

Prediction ghosts are an explicitly scripted comparison at selectable future
horizons, coloured cyan through amber to red in accordance with ADR-0006.
The scale uses the current authored sample range with a 0.25 m floor. A real
learned-model run is not a prerequisite for this concept demonstration.

A permanent concept caption, an illustrative metric label and a sources
panel remain accessible at every stage. Explain the product sequence as
training in a world model, compression onto rugged compute and offline
operation. Scripted trace playback must not imply live training or inference.

## Consequences

Phase 9 can be completed within the agreed illustrative scope. The fleet and
truck views serve different viewing distances without hiding the story.
Physical-device measurements remain a separately disclosed evidence gap if
only browser emulation is available; emulator results cannot establish a
real-phone frame rate.

## References

- [Sandvik TH315](https://www.mining.sandvik/en/products/equipment/trucks/th315-underground-truck/)
- [Three.js instancing](https://threejs.org/docs/#api/en/objects/InstancedMesh)
- [Three.js shadow cost](https://threejs.org/manual/en/shadows.html)

## Surface imagery and retained assets

Following maintainer review, the surface stage opens an embedded Google Maps
satellite view with Google's own provider credits intact. It is an online
view, not an image copied into the terrain texture. The local Copernicus
terrain and authored site remain selectable; `?offline=1` starts with that
view and avoids the Google request. Google supports embedding maps through
its sharing interface. No Google imagery is cached or redistributed here.

Restore the existing Poly Haven wall, mud and ore maps, including desktop
normal maps. Load the CC BY 4.0 excavator from `assets/models/excavator` as a
stationary loading machine, using the bone indices established in ADR-0021.
The expanded loading chamber is an illustrative scene input, not a surveyed
Rutongo excavation. The model and adaptations are credited in the sources
panel and its asset README.

Serve pinned Three.js modules and the two OFL web fonts locally. The core 3D
mission therefore runs without external requests. Google satellite imagery
is the only optional online stage; its transfer and availability are reported
separately. Distant trucks use a silhouette with the same envelope; inspection
reveals the complete rig. Merge static floors and walls to reduce draw calls.

- [Google Maps sharing and embedding](https://support.google.com/maps/answer/7101463)
- [Google Map Tiles policies](https://developers.google.com/maps/documentation/tile/policies)
