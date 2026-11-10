# Retrofit engineering references

The final chapter is a proposed engineering study. The geometry is original
Kessel work, not an NVIDIA product model or a selected bill of materials.

[NVIDIA's hardware layout](https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/hardware_layout.html)
separates the compute module, carrier interfaces, camera transport and storage.
This informs the distinction between compute, perception inputs and vehicle I/O
in the illustration. It does not make the depicted housing an Orin developer kit.

[NVIDIA's CAN documentation](https://docs.nvidia.com/jetson/archives/r36.4.4/DeveloperGuide/HR/ControllerAreaNetworkCan.html)
distinguishes the SoC controller, pins and external bus interfacing. The proposed
vehicle interface therefore remains separate from the actor compute. Bus
transceivers, isolation, command supervision and machine integration require their
own hardware and validation; the demo does not claim qualification.

[The robot_localization state-estimation documentation](https://github.com/cra-ros-pkg/robot_localization/blob/rolling-devel/doc/state_estimation_nodes.rst)
describes combining configured sensor observations into a local state estimate.
The four-stage signal view separates sensing, estimation, policy inference and
actuation. It is an authored architecture explanation, not output from a running
robot. GPS is not shown as a required input.

The housing footprint follows the existing 340 × 260 mm Blender study. Component
roles and target interfaces live in `data/retrofit-showcase.json`. CPU export
measurements remain in the existing retained engineering chapter. No Jetson
latency, ingress rating, thermal rating or certified stopping behaviour is claimed.

For the surface correction, the retained Blender scene confirmed quaternion mode
on the imported truck. Euler animation keys did not turn that rigid root. The
replacement explicitly selects XYZ mode, keys a single directed trajectory and
checks the evaluated world forward vector and tyre-ground contact at every source
frame. The browser fallback reads the same trace, with its ground datum translated
to the surface yard mesh.
