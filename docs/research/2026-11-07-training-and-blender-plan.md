# Training, replay and Blender follow-up

7 November 2026. Planning backlog, not implementation evidence.

## Training and replay

Parent [#305](https://github.com/Nabzx/Kessel/issues/305) holds 24 tasks,
[#307–#330](https://github.com/Nabzx/Kessel/issues/307). Including the research
parent, this is 25 issues. The machine-readable
[manifest](2026-11-07-training-and-blender-backlog.json) records every issue,
acceptance criterion and dependency. Native sub-issues and blocker edges are
also present on GitHub.

The retained CPU studies demonstrate no learned complete delivery cycle; raw
world-model branches fail the physical checks. More training is not evidence
that the task works. Eight reference/RL tasks start with visual/collision
alignment, a reproducible full-cycle reference controller, integration steps,
material accounting and reproducible resets. Curriculum and memory ablations
follow those checks.

Eight world-model tasks address contact-event coverage, observable versus
privileged state, sensor degradation, conservation, multi-step drift, event
prediction, uncertainty and an equal-budget model-assisted comparison. Eight
replay tasks address the shared episode clock, contact poses, ore transfer,
event timelines, forecast comparisons, auditable checkpoint selection, material
presentation and exported end-to-end evidence. Existing partial transfer issue
#261 is referenced rather than presented as complete.

The [PPO paper](https://arxiv.org/abs/1707.06347) and
[DreamerV3 paper](https://arxiv.org/abs/2301.04104) inform the experiment questions.
They do not establish that Kessel's synthetic dynamics or fitted models are
valid. See the retained local reports in `docs/phase-11/rl-experiments.md` and
`docs/phase-11/world-model-experiments.md` for the actual current results.
Research must resolve into ADRs before dependent build tasks become ready.

## Blender authoring

Parent [#306](https://github.com/Nabzx/Kessel/issues/306) holds 12 tasks,
[#331–#342](https://github.com/Nabzx/Kessel/issues/331), making 13 issues including
the parent. The first task verifies a local Blender installation and MCP
connection. No Blender executable or exposed Blender MCP tool was available
in this session. Nothing was installed or connected.

The inspected upstream [mcp-for-blender README](https://github.com/ahujasid/mcp-for-blender)
describes an add-on, local socket connection, Python execution and a safe mode.
Connection and capability checks must precede authoring. Retain reproducible
scene scripts and bounded local operations rather than depending on an opaque
interactive session.

Subsequent tasks cover geology, the surface mine, a hauler, the existing licensed
excavator, ore piles, proposed retrofit hardware, a cleared material library,
lighting calibration, motion and validated glTF export. Keep exact source
credits, metres, pivots, normals, animation clips and triangle/texture budgets.
Use Blender offline to author assets; the shipped page remains a static Three.js
site. Visual improvement cannot validate physical dynamics or deployed autonomy.

## Immediate home work

The separately authorised home tickets #298–#303 use retained NASA Earth/ISS
assets and five individually checked government reference photographs. Exact
original URLs, notices, credits and hashes are in
[`assets/environments/manifest.json`](../../assets/environments/manifest.json).
The CDC mine photograph is Pennsylvania, not Rutongo. The five local WebP
previews total 277,482 bytes. These changes require neither a Blender connection
nor new training results. The home decision is [ADR-0046](../adr/0046-home-environment-presentation.md).
