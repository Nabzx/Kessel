# Kessel realism and robot-learning research

Research date: 4 November 2026. Recommendations for discussion, not an adopted
architecture. No implementation or GitHub tickets are included in this note.

## Maintainer decisions

The maintainer wants all three outcomes: visual improvements, a genuine
training prototype, and an investor experience that presents its results.
No NVIDIA training GPU, Jetson, mine scans/CAD, machine telemetry or operator
partner is currently available. Use synthetic data. Local language-model
tooling is excluded from this milestone. Use Dependabot for dependency
maintenance and the existing Wayfinder process for research and decisions.

Start with a CPU-first loading experiment sized for the existing Mac. Its
initial pile and machine dynamics can be simplified, with the approximation
and source recorded. Benchmark feasibility before choosing model size, run
length or acceleration. Genuine learned results from that environment remain
simulation results. CUDA-based Isaac Lab/Newton work and Jetson measurements
depend on resources becoming available; they are not prerequisites for the
first learning experiment. No paid compute is assumed.

## Recommendation

Develop the presentation into a viewer for reproducible loader-learning
experiments. Upgrade the materials, geometry, lighting and physical motion in
parallel with a small Python training system. Start with one loader, one pile
and a measurable scoop task, then extend to retracting, hauling and delivery.
Retain the approved Earth-to-mine story and the black/off-white identity.

The current repository is a Three.js concept visualisation. Its training
keyframes, rewards, represented episode count and operating comparison are
authored. They are not an existing learning backend. Three.js is vendored at
0.160.0. Existing material maps were reduced to 512 px. Herdr and production
inference integrations were not established by the application files inspected;
development tooling may be configured elsewhere.

## Visual findings

Rock Wall 09, currently applied to mine rock, is classified as man-made
fortress masonry. It is a poor choice for exposed geological surfaces.
[Official asset](https://polyhaven.com/a/rock_wall_09).

Candidate assets, subject to checking colour and scale against mine references:

| Purpose | Candidate | Use |
| --- | --- | --- |
| Main exposed rock | [Rock Face 03](https://polyhaven.com/a/rock_face_03) | Cracks, chipped surfaces and uneven natural rock. |
| Secondary strata | [Dark Rock 02](https://polyhaven.com/a/dark_rock_02) | Layered, fractured rock for variation. |
| Alternative strata | [Rock 06](https://polyhaven.com/a/rock_06) | Striated rock; assess its warm colour before using it underground. |
| Detailed portal rock | [Rock Face 02 model](https://polyhaven.com/a/rock_face_02) | Scanned geometry for a small number of prominent surfaces; simplify the source mesh. |
| Surface terrain | [Rocky Terrain 02](https://polyhaven.com/a/rocky_terrain_02) | Broad ground variation around the site, not a replacement for geographic imagery. |
| Machine walkways | [Metal Plate](https://polyhaven.com/a/metal_plate) | Worn industrial tread plate on appropriate small components. |

These Poly Haven assets have CC0 notices on their source pages. ambientCG is
another source of painted metal, rubber, concrete and ground materials; its
[licence](https://docs.ambientcg.com/license/) permits commercial use and
redistribution of its asset files. This does not establish permission for
unrelated manufacturer models or commercial asset stores.

Use 1K or 2K material sets selectively, with base colour, OpenGL normal and
packed occlusion/roughness/metalness maps. Add geological colour variation,
wetness, tyre tracks and blast marks with masks. Use triplanar projection where
UV stretching is visible. Large silhouette changes need geometry, not a
normal map. Keep the existing mud and ore sets where they remain appropriate.

Replace rectangular rock pillars with irregular excavated masses and model
selected ribs, supports, mesh, services and drainage. A more detailed original
or properly licensed low-profile loader should have articulated steering,
bucket linkage, hydraulic rods, tyres and convincing load transfer. A visual
mesh also needs separate collision, inertia and actuator definitions to become
a training asset.

Add local industrial lighting, restrained airborne dust, contact shadows and
roughness variation. Tie dust and vibration to movement, contact or slip.
Match wheel rotation, steering, bucket penetration, pile change and delivery to
the same simulation state. These are proposed visual improvements, not a claim
that the current scene supplies validated mine physics.

[KTX2Loader](https://threejs.org/docs/pages/KTX2Loader.html) supports compressed
GPU textures through Basis transcoding. Evaluate it for the higher-resolution
sets while retaining measured M1 Chrome budgets. New loaders and shaders must
match the pinned Three.js version or follow a deliberate upgrade. Prepare
lighting and warm shaders before the relevant transition.

## Transitions and technical presentation

Suggested presentation sequence:

1. Keep the geographically fixed location during the Earth approach; reveal
   progressively finer terrain detail before entering the mine.
2. Use an animated section plane and an illuminated geological cut edge to
   expose the workings. Keep the camera position continuous.
3. Enter the world model through the same loader pose and pile shape. Reveal
   observation points, local occupancy and predicted trajectories around it.
4. Show candidate actions, then the chosen action and its measured outcome.
   Compare a prediction with simulation reference at the same timestamp.
5. Display early and later policies against identical held-out pile conditions.
   Animate real checkpoint results and restore the same mine context on exit.
6. Carry the selected policy identifier into the exploded compute module,
   linking training to deployment visually.

Keep technical information attached to the process: sensor observations,
state estimates, bucket angle, load, slip, chosen controls, reward terms and
prediction residuals. An uncertainty display must come from an evaluated
estimator or remain explicitly illustrative. Avoid treating arbitrary latent
coordinates as physical distances or displaying invented confidence levels.

## Research most relevant to the product

**Wheel-loader world models.** Aoshima and colleagues predict pile evolution,
loaded mass, cycle time and work from pile heightmaps and loading actions,
using data generated by multibody simulation. This is directly relevant to a
compact first model of loader interactions. Its reported results are research
results on its own setup, not Kessel results or Jetson benchmarks.
[Author project](https://umit.cs.umu.se/wl-predictor/),
[paper](https://arxiv.org/abs/2309.12016).

**Underground loader RL.** Backman and colleagues study dig-point selection
and continuous bucket-filling control using soft actor-critic in simulation,
with camera, lidar, motion and force observations. Rewards include energy
considerations alongside loading performance. This establishes relevant prior
work, not an existing production capability in our repository.
[Author project](https://www.algoryx.se/papers/drl-loader/),
[paper](https://arxiv.org/abs/2103.01283).

**Latent control learning.** DreamerV3 learns predictive latent dynamics and
an actor/critic using imagined trajectories. TD-MPC2 optimises candidate
trajectories inside a learned latent model. They are useful experimental
references; model-predictive planning has different deployment requirements
from executing a distilled observation-to-action policy.
[DreamerV3](https://www.nature.com/articles/s41586-025-08744-2),
[TD-MPC2](https://www.tdmpc2.com/).

**Frontier world models.** Dreamer 4 studies offline imagination training and
complex interactions. NVIDIA Cosmos 3 provides broader world-model and action
generation capabilities. These deserve evaluation as research/data tools;
neither project establishes calibrated underground digging performance for
Kessel. Evaluate contact forces, mass, slip and task outcomes on our own data.
[Dreamer 4](https://danijar.com/project/dreamer4/),
[Cosmos](https://www.nvidia.com/en-us/ai/cosmos/),
[NVIDIA physics evaluation research](https://research.nvidia.com/labs/cosmos-lab/phyworldbench/).

Prior work means the investment case should identify a concrete advantage in
machine integration, transfer across sites, deployment data, reliability or
operating results. The broad combination of RL, simulation and underground
loaders is established research.

## Proposed component boundaries

| Component | Initial recommendation | Qualification |
| --- | --- | --- |
| Investor experience | Existing Three.js front end | Render logged experiments; measure added material and animation costs on the M1. |
| Geographic context | Existing local imagery initially; assess CesiumJS when needed | Streaming imagery, terrain and georeferencing are its contribution. Verify provider coverage and access. |
| Training environment | First establish a small CPU-first synthetic loading benchmark; assess Isaac Lab/Newton and AGX when resources permit | Validate loader/material interaction before choosing a production simulator. |
| Learning | Python/PyTorch, a model-free control baseline and a compact action-conditioned dynamics model | Baseline first, then measure whether model-based training improves sample efficiency or performance. |
| Deployment policy | Observation/history-conditioned student policy | The student must use inputs available on the deployed machine. |
| Export/inference | ONNX export; benchmark TensorRT directly or via ONNX Runtime | Pin compatible JetPack, CUDA, TensorRT and runtime versions. |
| Mapping/control | Sensor fusion and local mapping, bounded motion controls, machine interface | These are required product components beyond a neural policy. |
| Coding workflow | Existing tools, Wayfinder research/decisions and Dependabot maintenance | No local language-model tooling in this milestone. |

[CesiumJS](https://cesium.com/platform/cesiumjs/) is a geospatial visualisation
library. Combining it with Three.js requires deliberate coordinate, camera and
renderer ownership. It does not supply subterranean scans or a digging engine.
The current single-renderer journey should be retained until an integration
experiment demonstrates a visual or data benefit.

An alternative geospatial experiment is
[NASA-AMMOS 3DTilesRendererJS](https://github.com/NASA-AMMOS/3DTilesRendererJS),
which renders 3D Tiles through Three.js. It could preserve a single renderer
while adding streamed context. Evaluate coverage, provider access and local
detail before selecting either integration. The open renderer's licence does
not provide rights to every imagery service it can connect to.

Isaac Lab 3.0 adds Newton and multiple physics backends.
[Release notes](https://github.com/isaac-sim/IsaacLab/releases/tag/v3.0.0).
Its [supported training platforms](https://isaac-sim.github.io/IsaacLab/main/source/isaaclab/installation.html)
use NVIDIA CUDA hardware. The M1 remains suitable for the web experience and
some small learning experiments; plan a separate NVIDIA training machine for
this proposed backend.

Newton's MPM supports granular materials, but articulated machine dynamics
and reaction forces require the appropriate rigid/material coupling. The
documented two-way path is experimental, so test penetration resistance,
reaction force, mass conservation, wheel slip, resets and parallel throughput.
Moving a kinematic bucket through particles alone does not validate a loading
controller.
[MPM documentation](https://isaac-sim.github.io/IsaacLab/v3.0.0/source/concepts/using_mpm.html),
[coupling documentation](https://isaac-sim.github.io/IsaacLab/main/source/concepts/coupled_solvers.html).

AGX is a serious comparator because its simulator was used in underground
loader research. Its terrain, drivetrain and tyre examples provide a useful
reference. Check commercial access and integration cost before adopting it.
[Published loader project](https://www.algoryx.se/groundbreaking-ai-project-for-autonomous-machines/),
[wheel-loader examples](https://us.download.algoryx.se/AGXUnity/documentation/current/examples.html).

Use representations appropriate to the task. A pile heightmap is a useful
initial candidate; a local occupancy or distance field can support navigation.
A dense voxel model of the entire mine is not a prerequisite for every
controller. [Nvblox](https://nvidia-isaac-ros.github.io/repositories_and_packages/isaac_ros_nvblox/index.html)
is one mapping option to investigate against actual sensor and compute needs.

## Distillation, quantisation and edge hardware

The proposed stack description combines separate steps. Knowledge distillation
trains a smaller student to reproduce useful teacher behaviour. Quantisation
changes numerical precision. TensorRT optimises inference; ONNX Runtime runs
models through execution providers. Neither runtime automatically transfers
the capabilities of a large world model into a small robot controller.
[NVIDIA Model Optimizer](https://github.com/NVIDIA/Model-Optimizer),
[ONNX Runtime TensorRT provider](https://onnxruntime.ai/docs/execution-providers/TensorRT-ExecutionProvider.html).

Initially distil the useful policy, with its required observation processing
and history. A separate lightweight world model could run onboard if the
selected planning architecture needs it. Its role and budget must be explicit.
Start with a floating-point reference, then FP16 and calibrated INT8 where
supported. Compare closed-loop success, loads, constraint violations and
latency after export, rather than accepting file-size reduction alone.

Jetson Orin is a plausible candidate, including industrial module options.
Select memory, power, carrier and enclosure after measuring the complete
sensor-to-command pipeline. An industrial compute module is one component of
a ruggedised system. The current family also includes Thor; newer hardware
does not by itself justify its larger power envelope for our first policy.
[NVIDIA module lineup](https://developer.nvidia.com/embedded/jetson-modules).

Add a machine-interface/control layer with deterministic limits and stop
behaviour. This is distinct from adding manual override to the demo.
[ros2_control controller manager](https://control.ros.org/kilted/doc/ros2_control/controller_manager/doc/userdoc.html)
is a framework to evaluate, not a substitute for machine integration.

## First reproducible learning experiment

1. Define the machine articulation, pile representation, observations,
   controls and success criteria. Give the environment deterministic seeds.
2. Establish a scripted or conventional controller baseline. Measure fill,
   cycle time, effort, spillage, collisions and slip.
3. Train one RL policy for bucket filling. Extend its curriculum to retract,
   haul and deliver once the loading interaction is credible.
4. Record state/action/next-state transitions. Train a compact dynamics model
   to predict pile change and task outcomes. Evaluate held-out conditions and
   rollout error before using the model for imagination training or planning.
5. Compare models and policies on identical unseen piles, dynamics and sensor
   noise, across multiple seeds. Record uncertainty and failure cases.
6. Export real trajectories, reward terms, prediction/reference pairs and
   checkpoint metadata into the demo's data contract. Use actual episode and
   environment-step counts from those runs.
7. Evaluate a student policy and its exported/quantised variants with the same
   task tests. Measure edge latency on the selected hardware when available.

This can produce real learned results in simulation. Real-machine performance
requires calibration, machine data and validation beyond that milestone.
Avoid assigning target accuracy, savings or inference latency before measuring
them. A successful single task is the starting evidence for the broader stack.

The browser can first replay logged results while preserving honest source
labels. Later, a compatible small exported policy could run locally using
[ONNX Runtime Web](https://onnxruntime.ai/docs/tutorials/web/ep-webgpu.html),
with WASM or WebGPU chosen by measured workload. GPU training and a complete
granular simulator do not have to run inside the investor page.

## Development workflow and research

Use the repository's existing Wayfinder map, research, prototype and task
structure. Resolve technical investigations into evidence and ADRs before
dependent implementation. See docs/agents/issue-tracker.md. Continue targeted
primary-source research as each component is built; this note does not create
a running research service or background agent.

[Dependabot](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
monitors supported dependency manifests and proposes updates. Plan coverage for
GitHub Actions and the future Python training dependencies. Vendored JavaScript
files also need explicit version tracking and an update procedure. Dependency
maintenance and scientific research are separate jobs.

Track dataset versions, configurations, seeds, metrics and checkpoints for
every experiment. Local coding/research language models are out of scope.
Offline inference by the trained vehicle policy remains the product goal.

## Next planning step

Prepare a joined visual/training/demonstration plan using the confirmed
synthetic-data and existing-compute constraints. Raise GitHub tickets when the
maintainer requests ticketing. Hardware selection and real-machine validation
remain later decisions supported by measured model and interface needs.
