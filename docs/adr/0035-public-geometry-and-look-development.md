# ADR-0035: Public geometry and look development

Status: Accepted. The prototype-only restriction for cleared material maps is
superseded by [ADR-0045](0045-cinematic-visual-materials.md). The scan provenance
and unknown-units boundary remains in force.

## Decision

Keep the mine layout synthetic and explicitly illustrative. The public
Slovenian mine dataset supplies a separately labelled geometric reference,
not a Rutongo survey, machine record or training environment. Its licence is
CC BY 4.0. The archive contains a 39,403-triangle simplified binary STL that
can be inspected through bounded HTTP range reads without fetching 645 MB.

The STL does not declare units, CRS or a certified axis convention. Its bounds
also do not establish the scale of the roughly 58 m segment described in the
radio-propagation notes. Preserve those uncertainties. Centre and rotate a
small excerpt for viewing only, keep `physical_units: null`, and identify the
assumed source +Z viewing-up axis. Do not place it on the Earth, infer portals
from it or use its dimensions to train/control a machine.

Use an isolated static look-development page under `docs/phase-11/lookdev/`
to compare the existing wall material with verified natural rock maps under
the same lighting, geometry, camera and display texel scale. Keep the existing
excavator and retained mud/ore assets. Research assets are not loaded by the
main cinematic experience. All prototype requests are local; no account, API
key or runtime asset API is needed.

Rock Face 03 is cleared for this comparison from its official CC0 source.
Keep attribution and source/derivative hashes in the manifest. Record blocked
or unverifiable candidates as deferred, not approved. No new vehicle or
orbital geometry is adopted merely because its preview is public.

## Consequences

The comparison can establish a material/lighting direction before a full mine
rebuild. Raw scans and source archives stay outside the repository. A compact
derived excerpt is reference-only and carries its source credit. Retain a
synthetic shell fallback, preserve the current demo and measure the prototype
on native M1 Chrome before recommending integration. The scene is a visual
prototype, not learned output. Refs: #201, #202, #203.

Sources: [dataset and licence](https://zenodo.org/records/18835599),
[Rock Face 03](https://polyhaven.com/a/rock_face_03),
[Poly Haven licence](https://polyhaven.com/license).
