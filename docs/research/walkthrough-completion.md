# Surface and hardware brief

Research and implementation for #359, #372 and ADR-0053. Checked 8 November 2026.

The source shortlist and geographic delivery decision are retained in ADR-0051.
The shipped Sentinel-2 scene is regional 10 m imagery. The 30 m elevation grid
covers 4,096 m. Neither resolves portal collars, kerbs, vehicles or buildings.
At the authored yard camera (about 85 m from the portal), foreground geometry and
metre-scaled scanned materials must carry the shot. Regional data remains a
horizon/context layer. No surveyed mine plan is available. The current public
Rwanda mineral account supplies context, not vehicle or tunnel geometry.

Google/Cesium imagery remains excluded for the documented key, local-delivery,
licence and unverified rural coverage reasons in ADR-0051. No account, billing or
additional permission is required for the existing cleared local assets. Scanned
rock and ground maps are the retained Poly Haven CC0 assets, not unlicensed
operator photographs. Native 3D models are original repository-owned Blender work.

The surface subject is an eight-metre portal with concrete collar, steel sets,
ventilation duct, drainage and road clearance. The closed hill contains a boolean
horizontal cavity; an axial roof shell, floor and dark backstop provide depth.
Two 1.75 m authored workers and one slowly moving hauler establish scale. They do
not depict observed Rutongo activity. Cut-out procedural foliage replaces solid
canopy blobs; haze and key retain the same daylight direction.

## Proposed kit

Reference: NVIDIA's [carrier layout](https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/hardware_layout.html),
which distinguishes compute-module, carrier, storage and physical I/O roles.
This is an original assembly, not a copy or claim to be an NVIDIA-certified kit.

| Part | Proposed envelope / arrangement |
|---|---|
| Case | 340 × 260 mm footprint; split shell and finned removable lid |
| Carrier / compute | 170 × 140 mm board envelope, central package and thermal spreader |
| Power | Separate 120 × 100 mm board; input conditioning and service access |
| Vehicle I/O | 70 × 140 mm board; segregated from compute and power |
| Mounting | External feet on a machine bracket; removable fasteners |
| Interfaces | Circular connector collars, insulators and contacts; proposed wiring |
| Sensors | External stereo and range/pose housings, brackets and cable glands |

Browser scale is explicitly ten times physical source metres. Gasket land,
fasteners, supports, connector orientation, headers, spreader and fins carry the
mechanical detail. Sensing lifts first, followed by lid and interior boards. The
base and mounting plate stay in place. No ingress, thermal, vibration, safety or
field-deployment capability is certified by this render. Routing to an existing
machine is conceptual; final interfaces require a machine partner.

The technical chapters show recorded synthetic crops, actual retained raw
forecasts and charged PPO counters. CPU export sizes are copied with a source
checksum into data/engineering.json. The offline and fleet loops are locally
labelled authored architecture. No real fleet or validated Jetson latency is used.
