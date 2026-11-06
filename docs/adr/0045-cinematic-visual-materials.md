# ADR-0045: Cinematic visual materials and geometry

Status: Accepted

## Decision

Supersede ADR-0035's restriction of the cleared rock maps to the isolated
look-development page. The maintainer has requested the visual realism work,
including the Earth hero and surface site. Adopt Rock Face 03 for exposed
geology and retain Dark Rock 02 for comparison. Both are verified CC0 maps.
Retain the licensed excavator, existing mud and ore maps, and original hauler.

Prepare local, hashed WebP derivatives outside the published runtime. Preserve
sRGB colour and linear OpenGL normal, roughness and AO data. Record compression
comparisons, source notices and physical repeat scale in a visual manifest.
Keep runtime dependencies compatible with the pinned Three.js r160.

Generate a closed, irregular synthetic cutaway from the authored scene bounds.
Keep route clearance by displacing pillar contours inwards. Public scan units
remain unknown; do not substitute a scan for Rutongo survey geometry. Site
services, material parameters and presentation budgets belong in the authored
experience contract. Sentinel imagery and elevation remain regional context;
portal details, surface structures and underground workings are illustrative.

A simplified NASA ISS model may provide a credited decorative silhouette.
Its presentation orbit is not an orbital catalogue or a scale model. Strip
source textures and markings; keep an original satellite as the fallback.

Use restrained stage lighting, shared materials, instanced fixtures and bounded
contact effects. Keep the existing baked kit environment. No runtime HDRI
prefilter, remote asset service, training or inference is introduced. Recorded
viewer behaviour is deferred at the maintainer's request; its evidence labels
and actual values remain intact while visual composition may be refined.

## Consequences

Natural geology replaces the masonry material in the current experience.
The synthetic shell remains data driven, capped and separate from training
geometry. Visual acceptance needs native M1 Chrome captures and performance
measurements, including reduced motion. Merge does not constitute final human
release acceptance. Refs #253–#270, #277–#281.

Sources: [Poly Haven licence](https://polyhaven.com/license),
[Rock Face 03](https://polyhaven.com/a/rock_face_03),
[NASA ISS](https://science.nasa.gov/resource/international-space-station-3d-model/),
[NASA media guidance](https://www.nasa.gov/nasa-brand-center/images-and-media/).
