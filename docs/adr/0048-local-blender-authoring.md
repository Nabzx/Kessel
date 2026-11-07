# ADR-0048: Local Blender authoring

Status: Accepted

## Decision

Use the maintainer's Blender 5.2.3 LTS in a separate factory-default authoring
instance. Pin ahujasid/mcp-for-blender to
2e4b0bc294694b1570d76ed01be657c22e6d02a0 (package 2.2.7, MCP SDK 1.30.0).
Use a local MCP stdio client and the add-on's loopback socket on 127.0.0.1:9877.
Keep safe mode enabled and telemetry disabled. No hosted generation provider,
API key, external upload or persistent change to the maintainer's working scene
is needed. Inspect/create/render/save/glTF round-trip proof precedes authoring.

Store repeatable metre-scale source scripts and editable .blend scenes under
tools/blender, outside the static package allowlist. Web derivatives belong in
assets/authored with source hashes, object/pivot contracts, licences, LODs and
texture budgets. Preserve the licensed excavator original. A derivative rig
mapping does not create a new licence or calibrated machine model.

Author geology, portal/yard, hauler, original reference loader, ore and proposed
kit with controlled silhouettes and separate glTF-compatible materials. Reuse
individually cleared CC0 maps. Bake static normal/AO detail where useful; never
bake conflicting dynamic sun or independent material-transfer animation.
Browser playback owns the logged clock, joint poses, wheel travel and ore ledger.

Compare Blender render colour management and browser ACES exposure using matched
cameras and swatches. Validate GLBs, skinning, materials, external resources,
bounds and native first-use/steady frame budgets before adopting them. Keep
geology and product assembly explicitly synthetic/proposed. Blender and MCP
remain offline authoring tools and never enter the published runtime.

Refs #306, #331–#342.
