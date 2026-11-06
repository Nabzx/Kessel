# Public assets and Phase 11 planning

Research date: 4 November 2026. This shortlist precedes the Phase 11 visual
tickets. Source pages and published notices were inspected. Assets have not
been downloaded, benchmarked or accepted for inclusion by this investigation.
The existing Phase 10 baseline and learning captures were also inspected.

## Direction

Keep the approved Earth-to-Rwanda journey, overhead mine and optional learning
viewer. Retain black, off-white and mineral amber, with red/green reserved for
comparison state. Improve geology, proportions, material response, lighting
and machine motion before adding effects. The current rectangular rock masses
and masonry-like wall texture are the largest visual weaknesses. Technical
overlays should expose recorded state, actions, predictions and errors. Avoid
decorative terminals, random code, fake neural activity and paragraphs of copy.

The target is native M1 Chrome. Keep the shipped site static and data-driven.
Python training and asset processing are development tools, not a browser
build requirement. No paid assets, cloud GPU, Jetson or operator data are
assumed. Manual override, chase cameras and pricing remain excluded.

## Asset shortlist

| Source | Proposed use | Licence and status | Required preparation |
| --- | --- | --- | --- |
| [Poly Haven Rock Face 03](https://polyhaven.com/a/rock_face_03) | Natural exposed tunnel rock | CC0; first material candidate | Compare 1K/2K maps, set metre scale, inspect tiling and normal orientation. |
| [ambientCG Rock 030](https://ambientcg.com/view?id=Rock030) | Secondary cliff/rock variation | CC0; alternative candidate | Compare against Rock Face 03 under the same lighting. |
| [ambientCG Gravel 022](https://ambientcg.com/view?id=Gravel022) | Haul-road aggregate and pile fines | CC0; candidate | Mix with retained mud and ore maps; avoid a uniformly gravelled mine. |
| [ambientCG Metal 036](https://ambientcg.com/view?id=Metal036) | Smooth metal components and proposed kit | CC0; candidate | Apply only where metal response is appropriate; paint remains dielectric. |
| [ambientCG Rubber 004](https://ambientcg.com/view?id=Rubber004) | Small rubber components | CC0; conditional candidate | This is a gym-floor material, not a tyre scan. Inspect suitability; retain actual tread geometry. |
| [Poly Haven Modular Industrial Pipes 01](https://polyhaven.com/a/modular_industrial_pipes_01) | Sparse service infrastructure | CC0; candidate model set | Select relevant pieces, simplify and instance; not every pipe belongs in this mine. |
| [Poly Haven Coast Rocks 01](https://polyhaven.com/a/coast_rocks_01) | Scanned silhouette and surface reference | CC0; conditional geometry candidate | Source is about one million triangles and coastal in appearance. Decimate and assess geological suitability before use. |
| [Poly Haven Quarry 01](https://polyhaven.com/a/quarry_01) | Surface reflection/light reference | CC0; candidate HDRI | Prefilter offline and harmonise sun direction. Not a photograph of Rutongo. |
| [Existing excavator](../../assets/models/excavator/README.md) | Retained loading machine | Existing CC BY 4.0 asset and attribution | Preserve documented rig joints and improve shading and physical timing. |
| [Arahan: Free Old Mine Dump Truck](https://sketchfab.com/3d-models/free-old-mine-dump-truck-8ee438c24e994d9ca6c6afb5add305ca) | Surface-truck reference | Page advertises download and CC Attribution; conditional | Surface mining geometry, not an accepted underground hauler. Verify exact licence, download access, scale and rig. Do not substitute without an underground fit check. |
| [NASA ISS model](https://science.nasa.gov/resource/international-space-station-3d-model/) and [3D resources](https://science.nasa.gov/3d-resources/) | A small number of orbital silhouettes | NASA media guidance and asset-specific notices | Check notices; simplify and convert as needed. No endorsement or claim of a live orbital catalogue. |
| [Slovenian mine tunnel mesh and LiDAR](https://zenodo.org/records/18835599) | Geometric reference or separately labelled scan excerpt | CC BY 4.0 stated; 645.5 MB source archive | Crop and decimate offline; keep source coordinates and credit. Not Rutongo geometry. |
| [ETH Bedretto tunnel TLS and meshes](https://www.research-collection.ethz.ch/items/65adf5ab-b96b-4d46-afa1-6bf96417e568) | Alternative tunnel scan reference | Search-indexed publisher metadata reports CC BY 4.0; direct read returned 403 | Confirm downloadable metadata/licence before adoption. Large source files must not ship raw. |

[Poly Haven's asset licence](https://polyhaven.com/license) and
[ambientCG's licence](https://docs.ambientcg.com/license/) permit commercial
reuse and redistribution of their CC0 assets. Use official downloads or the
documented API within its terms. Third-party preview pages, branding and API
terms are distinct from the asset licence. Keep a provenance manifest even
where attribution is optional.

Existing NASA Earth and Copernicus surface assets remain useful. Sentinel-2's
10 m imagery cannot provide detailed machinery or portal geometry. Blend into
authored foreground terrain and industrial props as the camera approaches;
do not suggest invented high-resolution imagery is an acquired survey.
Do not bundle scraped Google tiles or use screenshots as terrain textures.

## Animation and rendering references

- [Three.js r160 source and MIT licence](https://github.com/mrdoob/three.js/tree/r160): inspect the matching-version animation examples and `webgl_clipping_stencil` for rig blending and capped cutaway sections. Newer examples may require APIs absent from the pinned renderer. Example model licences remain separate.
- [Three.js animation APIs](https://threejs.org/docs/): use explicit articulation or AnimationMixer for appropriate clips, driven by recorded motion and a common clock. Existing excavator joints have no baked source clip.
- [glTF Transform](https://gltf-transform.dev/): MIT tooling for repeatable simplification, texture processing and animation resampling. Keep tooling outside the static shipping path. Test decoder cost before adopting compressed formats.

Prefer authored camera curves with continuous position/velocity, grounded
wheel motion, hydraulic articulation, observable load transfer and restrained
light scattering. A scan transition should reveal existing geometry smoothly;
it should not replace physical continuity with a full-screen flash.

## Learning references and reuse

[Selene 3.1](https://github.com/Nabzx/selene3.1/tree/647ce1e8acf665435815576db30d38ca522240e1)
has MIT-licensed NumPy vector environments, real PyTorch PPO updates, a small
five-network dynamics ensemble and short uncertainty-gated imagined rollouts.
Its documented quick run reports 51,200 environment steps in 7.04 seconds;
this investigation did not reproduce the benchmark. Lunar decision dynamics
do not establish loader contact fidelity or Kessel training speed.

Reuse the separation of simulation, training, logging and playback. Replace
lunar actions with documented loader controls and mass-conserving simplified
pile interaction. Begin with a model-free policy and a reference controller.
Evaluate the learned dynamics before adding model-generated training data.

Two exporter details must change: the demo-bundle exporter authors its own
action sequence while accepting a learned-source label from checkpoint
presence, and the actor exporter fabricates position offsets for its visual
world-model errors. Kessel must record actual policy actions and model outputs.
Log raw validation error separately from a best-so-far series, actual episode
counts separately from environment steps, and training time separately from
accelerated playback time.

- [World Modeling for Autonomous Wheel Loaders](https://arxiv.org/abs/2309.12016): supports a pile-heightmap/action representation and load-outcome prediction as research direction. Its reported accuracy and timing are not Kessel measurements.
- [Continuous control of an underground loader using deep reinforcement learning](https://arxiv.org/abs/2103.01283): task-specific observations, continuous actuation, traction and effort matter.
- [Gymnasium vector environments](https://gymnasium.farama.org/api/vector/): batch semantics and termination handling need explicit tests.
- [ONNX Runtime quantisation](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html): evaluate numerical and closed-loop changes on CPU. TensorRT and Jetson latency remain hardware-dependent future work.

## Ticketing constraints

Raised [Phase 11 map #197](https://github.com/Nabzx/Kessel/issues/197) and 84
bounded child tickets (#198–#281). All 85 tickets are authored by Nabzx. The
84 native sub-issue links and 142 native blocking edges were read back and
verified against the plan. Every child has source links and measurable
completion criteria. Record
ADRs before changing the concept-only or authored-data invariants. Preserve
the existing presentation until logged evidence passes validation. Optional
scan adoption must not block a synthetic simulator or a viable visual fallback.
Research/prototype outputs become decisions before dependent build work starts.

The five follow-up layout/HUD tickets (#277–#281) use the existing design
tokens and architecture, with the public
[USWDS typography](https://designsystem.digital.gov/components/typography/)
and [data-visualisation guidance](https://designsystem.digital.gov/components/data-visualizations/)
as legibility references. They cover shared composition, the mine instrument
panel, technical charts, progressive HUD disclosure and interaction finish.
The references do not replace Kessel's visual identity or add a UI framework.
The native M1 verification ticket now waits for their completed integration.
