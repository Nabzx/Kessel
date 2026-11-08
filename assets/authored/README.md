# Blender-authored web derivatives

Original Kessel geology, surface portal/yard, hauler LODs, ore, reference loader
and proposed retrofit assembly. Authored through the pinned MCP for Blender
connector using Blender 5.2.3 LTS. Synthetic visual geometry, not a Rutongo
survey or calibrated contact model. Kit source is approximately 340 x 260 mm;
the browser displays it enlarged by ten for inspection.

`excavator.glb` is a non-destructive rig round trip of the retained
[Excavator 3d Rigging](https://sketchfab.com/3d-models/excavator-3d-rigging-f82f787abd304dea89667e078ccf7052)
by [mohamed.salaah880](https://sketchfab.com/mohamed.salaah880),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The original in assets/models/excavator remains byte-for-byte intact. Source
node indices provide unique joint names in this derivative; no original credit
is removed. The two original ore maps are procedural normal/AO bakes, exported
as pixel-exact lossless WebP. The retained CC0 rock/ground maps have their own
individual notices and hashes in assets/materials and the look-development study.

`manifest.json` traces every web derivative to an editable .blend and source
script. Sources and raw bakes stay in tools/blender and are excluded by static
packaging. Playback owns joints, wheel travel, tipping and material state; no
independent Blender animation loop runs in the browser. See ADR-0048 and the
native report under docs/phase-11/blender-evidence.

The original `observation-satellite.glb` and its genuinely reduced overview LOD
were authored through the same pinned Blender MCP for ADR-0052. Solar cells,
interconnects, insulation quilts, radiators, optical baffles and dish supports are
geometry. The source has a approximately 10.6 m array span; its apparent size/orbit is
normalised for the hero. It is an illustrative spacecraft, not live tracking or
a replica of a particular mission. See the manifest and orbital-home report.
