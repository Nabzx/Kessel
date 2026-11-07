# ADR-0046: Home and environment presentation

Status: Accepted

## Decision

Refine the home globe and environment selector within the existing Three.js
renderer and static data contract. Keep the established geographic texture
basis, lower wordmark position, five environments and underground-only action.

Retain the cleared NASA globe layers and decorative unmarked ISS model. Use a
single directional sun vector for day, night, atmosphere and clouds even when
the globe's presentation root moves. Use authored visual parameters for the
short arrival, orbital composition and marker treatment. Keep one camera clock
and an immediate reduced-motion path. Defer mine prefetch until the selector
has settled, so initial texture work does not compete with the home arrival.

Replace line icons with compressed, locally served photographic previews.
Individual NASA, NOAA and CDC records identify source, credit and usage status;
retain original and derivative hashes, crop/resize operations and a total byte
budget. Treat all previews as environment references. The CDC research mine is
in Pennsylvania and is not a photograph of Rutongo. Preserve that distinction
in the figure caption and Sources. No image implies a deployment or endorsement.

Keep accurate geographic pins, hide occluded/out-of-bounds labels and derive
the selected label from the actual marker transform. Keep Earth's illumination
neutral while theming the surrounding UI and background. New presentation
parameters and image metadata belong in data/experience.json.

## Consequences

No Cesium, streaming imagery service, Blender runtime or third-party account
is added to the site. Blender MCP is a separately planned offline authoring
workflow, not a prerequisite for this home work. Native Chrome checks must
cover rapid selection, returning caches, first-use loading, geographic
alignment, reduced motion and the Earth-to-mine hand-off.

Refs #298, #299, #300, #301, #302, #303.
