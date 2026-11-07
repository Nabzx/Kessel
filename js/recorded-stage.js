import * as THREE from "three";
import { createReferenceLoader } from "./loader-stage.js";
import { texture, box, lightRig, line } from "./scene-utils.js";
import { ReplayClock, sampleEpisode, curvePoints } from "./recorded-data.js";

export async function createRecorded(config, bundle) {
  const root = new THREE.Group(); root.name = "recorded-synthetic-experiment";
  const [ore, floor, asset] = await Promise.all([texture(config.assets.ore), texture(config.assets.floor, 5), fetch(config.assets.loader, { cache: "no-store" }).then((r) => { if (!r.ok) throw new Error("Loader asset unavailable"); return r.json(); })]);
  const indices = Object.fromEntries(bundle.state_names.map((name, i) => [name, i]));
  const initial = bundle.episodes[0].records[0].state, halfWidth = initial[indices.half_width_m];
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(29, halfWidth * 2), new THREE.MeshStandardMaterial({ map: floor, color: 0x72756c, roughness: 1 }));
  ground.rotation.x = -Math.PI / 2;ground.position.x = 3.5;ground.receiveShadow = true;root.add(ground);
  const edging = new THREE.MeshStandardMaterial({ color: 0x303c3b, roughness: 1, map: ore });
  for (const side of [-1, 1]) box([29, 0.65, 0.45], [3.5, 0.325, side * (halfWidth + 0.225)], edging, root);
  const grid = new THREE.GridHelper(30, 30, 0x4c625f, 0x293a3a);grid.position.set(3.5, 0.012, 0);grid.material.transparent = true;grid.material.opacity = 0.18;root.add(grid);
  const loader = createReferenceLoader(asset, ore);root.add(loader.root);
  document.getElementById("geometry-guide").addEventListener("change",event=>loader.guide(event.target.checked));
  const pile = new THREE.InstancedMesh(new THREE.BoxGeometry(0.49, 1, 0.49), new THREE.MeshStandardMaterial({ map: ore, color: 0xb6a792, roughness: 1 }), 64);
  pile.castShadow = true;pile.receiveShadow = true;root.add(pile);
  const receiver = new THREE.Group();const rx = initial[indices.receiver_x_m], ry = -initial[indices.receiver_y_m];
  const hx = initial[indices.receiver_half_x_m], hy = initial[indices.receiver_half_y_m];
  for (const side of [-1, 1]) box([2 * hx, 0.4, 0.12], [rx, 0.2, ry + side * hy], edging, receiver);
  box([0.12, 0.4, 2 * hy], [rx + hx, 0.2, ry], edging, receiver);root.add(receiver);
  const traces = bundle.episodes.map((episode) => {
    const path = line(episode.records.map((r) => [r.state[0], 0.025, -r.state[1]]), 0x728d89, 0.5);path.visible = false;root.add(path);return path;
  });
  const ghost = (colour) => {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(7.1, 1.9, 1.5), new THREE.MeshBasicMaterial({ color: colour, wireframe: true, transparent: true, opacity: 0.4, depthWrite: false }));root.add(mesh);return mesh;
  };
  const reference = ghost(0xe5e6d9), prediction = ghost(0xd5ac6c);
  const residual = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]), new THREE.LineBasicMaterial({ color: 0xd5ac6c, depthTest: false }));residual.renderOrder = 3;root.add(residual);
  const spread = new THREE.Mesh(new THREE.RingGeometry(0.96, 1, 48), new THREE.MeshBasicMaterial({ color: 0xd5ac6c, transparent: true, opacity: 0.7, side: THREE.DoubleSide, depthTest: false }));spread.rotation.x = -Math.PI / 2;root.add(spread);
  const sensors = new THREE.InstancedMesh(new THREE.SphereGeometry(0.035, 6, 4), new THREE.MeshBasicMaterial({ color: 0xa6c2ca, transparent: true, opacity: 0.8 }), 25);root.add(sensors);
  const forecastPile = new THREE.InstancedMesh(new THREE.SphereGeometry(0.035, 6, 4), new THREE.MeshBasicMaterial({ color: 0xffffff, depthTest: false }), 64);forecastPile.renderOrder = 2;root.add(forecastPile);
  lightRig(root, 35);
  const clock = new ReplayClock(bundle, matchMedia("(prefers-reduced-motion: reduce)").matches);
  const pose = new THREE.Object3D(), colour = new THREE.Color();
  const ui = Object.fromEntries(["episode-count", "reward-value", "action-value", "policy-value", "checkpoint-outcome", "payload-readout", "training-status", "pause-training", "reward-path", "reward-point", "training-status", "episode-caption", "reward-explanation", "observation-value", "recorded-time", "replay-scrub", "prediction-error", "prediction-score", "prediction-validity", "prediction-time", "member-spread", "run-provenance", "reward-chart", "observation-crop"].map((id) => [id, document.getElementById(id)]));
  const cells = Array.from({ length: 25 }, () => { const cell = document.createElement("span");ui["observation-crop"].append(cell);return cell; });
  const points = curvePoints(bundle.learning_curve);
  let horizon = 1, hudElapsed = 0, lastFrame = null, lastEpisode = -1, currentFuture = null;
  function place(mesh, state) { mesh.position.set(state[0] + 1.65 * Math.cos(state[2]), 0.95, -state[1] - 1.65 * Math.sin(state[2]));mesh.rotation.y = state[2]; }
  function renderForecast(frame, episode) {
    const future = frame.predictions.find((p) => p.horizon_decisions === horizon), exists = !!future?.prediction;
    for (const object of [reference, prediction, residual, spread, forecastPile]) object.visible = exists;
    if (!exists) return future;
    const p = future.prediction, ref = episode.records[future.reference_index].state;
    place(reference, ref);place(prediction, p);
    const positions = residual.geometry.attributes.position;
    positions.setXYZ(0, ref[0], 1, -ref[1]);positions.setXYZ(1, p[0], 1, -p[1]);positions.needsUpdate = true;
    residual.geometry.computeBoundingSphere();
    let xx = 0, yy = 0, xy = 0;
    const mx = future.members_xy_m.reduce((sum, m) => sum + m[0], 0) / 3, my = future.members_xy_m.reduce((sum, m) => sum + m[1], 0) / 3;
    for (const m of future.members_xy_m) { xx += (m[0] - mx) ** 2 / 3;yy += (m[1] - my) ** 2 / 3;xy += (m[0] - mx) * (m[1] - my) / 3; }
    const radius = Math.sqrt(((xx - yy) / 2) ** 2 + xy * xy), major = Math.sqrt(Math.max(0, (xx + yy) / 2 + radius)), minor = Math.sqrt(Math.max(0, (xx + yy) / 2 - radius));
    spread.position.set(p[0], 0.04, -p[1]);spread.rotation.set(-Math.PI / 2, 0, 0.5 * Math.atan2(2 * xy, xx - yy));spread.scale.set(major, minor, 1);
    for (let k = 0; k < 64; k++) {
      pose.position.set(p[indices.pile_origin_x_m] + (Math.floor(k / 8) + 0.5) * 0.5, p[15 + k], -(p[indices.pile_origin_y_m] + (k % 8 + 0.5) * 0.5));pose.scale.setScalar(1);pose.updateMatrix();forecastPile.setMatrixAt(k, pose.matrix);
      colour.set(0x708f94).lerp(new THREE.Color(0xd5ac6c), Math.min(1, Math.abs(p[15 + k] - ref[15 + k]) / 0.002));forecastPile.setColorAt(k, colour);
    }
    forecastPile.instanceMatrix.needsUpdate = true;forecastPile.instanceColor.needsUpdate = true;
    return { ...future, spread_m: major };
  }
  function paintHud(state, sampled, future) {
    const { episode, index } = state, frame = sampled.frame, counters = episode.policy.training_counters;
    ui["episode-count"].textContent = counters.completed_episodes.toLocaleString("en-GB");
    const measured = counters.rollouts > 0 ? bundle.learning_curve[counters.rollouts - 1] : null;
    ui["reward-value"].textContent = measured ? measured.mean_step_reward.toFixed(4) : "No update";
    ui["action-value"].title = "Acceleration, articulation rate, boom rate, bucket rate; normalised [-1,1]";
    ui["action-value"].setAttribute("aria-label", frame.action ? frame.action.map((v, i) => `${bundle.action_names[i]} ${v.toFixed(3)}`).join(", ") + "; normalised minus one to one" : "Terminal record, no next action");
    ui["action-value"].textContent = frame.action ? frame.action.map((v) => v.toFixed(2)).join(" · ") : "No next action";
    ui["policy-value"].textContent = `${episode.name} · ${episode.policy.checkpoint_sha256.slice(0, 8)}`;
    ui["observation-value"].textContent = `Local crop · ${frame.observation.slice(40).filter(Boolean).length}/25 valid`;
    const weighted = frame.reward_weighted ? Object.entries(frame.reward_weighted).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))[0] : null;
    const termNames = { elapsed_s: "time", effort_proxy_j: "effort", collision_count: "collision", delivered_kg: "delivery", spilled_kg: "spill", slip_s: "slip" };
    ui["reward-explanation"].textContent = weighted ? `${frame.reward.toFixed(4)} · ${termNames[weighted[0]]} ${weighted[1].toFixed(4)}` : "Episode ended";
    const outcome = { tunnel_wall: "Wall collision", time_limit: "Time limit", stuck: "Stuck", success: "Delivery complete" }[episode.outcome] || episode.outcome;
    ui["checkpoint-outcome"].textContent = `${outcome}. Delivered ${episode.metrics.delivered_kg.toFixed(0)} kg.`;
    ui["payload-readout"].textContent = `Payload ${frame.state[7].toFixed(0)} / 3,500 kg`;
    ui["training-status"].textContent = state.paused ? state.complete ? "Recorded episode ended" : "Recorded replay paused" : "Recorded policy decisions";
    ui["pause-training"].textContent = state.paused ? "Play" : "Pause";
    ui["recorded-time"].textContent = `Sim ${frame.t_s.toFixed(2)} s · ${state.holding ? "terminal hold" : `playback ${state.acceleration.toFixed(2)}×`}`;
    ui["replay-scrub"].max = episode.records.at(-1).t_s;ui["replay-scrub"].value = state.time;
    ui["replay-scrub"].setAttribute("aria-valuetext", `${frame.t_s.toFixed(2)} simulated seconds, ${episode.name} checkpoint`);
    document.querySelectorAll("[data-checkpoint]").forEach((button, i) => { button.classList.toggle("active", i === index);button.setAttribute("aria-pressed", String(i === index)); });
    for (let k = 0; k < 25; k++) {
      const h = frame.observation[15 + k], valid = frame.observation[40 + k] === 1;
      cells[k].style.background = valid ? `hsl(39 30% ${16 + Math.min(1, h / 1.5) * 60}%)` : "#1b2224";
      cells[k].title = valid ? `${h.toFixed(3)} m` : "No valid range return";
    }
    ui["observation-crop"].setAttribute("aria-label", `Recorded 5 by 5 height crop in metres: ${frame.observation.slice(15, 40).map((v) => v.toFixed(2)).join(", ")}. Validity mask ${frame.observation.slice(40).join(", ")}`);
    const curveIndex = Math.max(0, Math.min(points.length - 1, counters.rollouts - 1)), point = points[curveIndex];
    ui["reward-point"].style.visibility = counters.rollouts === 0 ? "hidden" : "visible";
    if (point) { ui["reward-point"].setAttribute("cx", point[0]);ui["reward-point"].setAttribute("cy", point[1]); }
    ui["prediction-error"].textContent = future?.prediction ? `${future.residual.position_m.toFixed(4)} m` : "Unavailable";
    ui["prediction-score"].textContent = future?.prediction ? future.disagreement.toFixed(3) : "No score";
    ui["prediction-time"].textContent = future?.prediction ? `Reference t=${future.target_t_s.toFixed(2)} s · +${horizon} decision${horizon > 1 ? "s" : ""}` : "Inspect a forecast anchor";
    ui["member-spread"].textContent = future?.prediction ? `Member spread σ ${future.spread_m.toFixed(4)} m` : "No member endpoints";
    const violations = future?.prediction ? Object.entries(future.violations).filter(([key, value]) => key === "mass_error_kg" ? Math.abs(value) > 1 : value).map(([key]) => key) : [];
    ui["prediction-validity"].textContent = !future?.prediction ? future?.missing_reason === "model_event_stop" ? "Model stopped this branch" : "No recorded forecast" : violations.length ? "Raw forecast: physical violations" : "Raw forecast";
    ui["prediction-validity"].title = violations.join(", ");
  }
  function update(delta) {
    const state = clock.update(delta), sampled = sampleEpisode(state.episode, state.time), s = sampled.frame.state, p = sampled.pose;
    loader.apply(p, sampled.wheelAngles, s[7]);
    const changed = lastFrame !== sampled.frame || lastEpisode !== state.index;
    if (changed) {
      for (let k = 0; k < 64; k++) { const h = s[15 + k];pose.position.set(s[indices.pile_origin_x_m] + (Math.floor(k / 8) + 0.5) * 0.5, h / 2, -(s[indices.pile_origin_y_m] + (k % 8 + 0.5) * 0.5));pose.scale.set(1, Math.max(0.0001, h), 1);pose.updateMatrix();pile.setMatrixAt(k, pose.matrix); }pile.instanceMatrix.needsUpdate = true;
      traces.forEach((trace, i) => { trace.visible = i === state.index; });
      const heading = s[2] + s[4], mx = s[0] + 1.8 * Math.cos(s[2]) + (1.6 + 1.2 * Math.cos(s[5])) * Math.cos(heading), my = s[1] + 1.8 * Math.sin(s[2]) + (1.6 + 1.2 * Math.cos(s[5])) * Math.sin(heading);
      for (let k = 0; k < 25; k++) { const along = (Math.floor(k / 5) - 1) * 0.75, across = (k % 5 - 2) * 0.75;pose.position.set(mx + along * Math.cos(heading) - across * Math.sin(heading), sampled.frame.observation[15 + k] + 0.02, -(my + along * Math.sin(heading) + across * Math.cos(heading)));pose.scale.setScalar(sampled.frame.observation[40 + k] ? 1 : 0);pose.updateMatrix();sensors.setMatrixAt(k, pose.matrix); }sensors.instanceMatrix.needsUpdate = true;
      lastFrame = sampled.frame;lastEpisode = state.index;
    }
    if (changed || delta === 0) currentFuture = renderForecast(sampled.frame, state.episode);
    const future = currentFuture;
    hudElapsed += delta;if (hudElapsed >= 0.09 || changed || delta === 0) { paintHud(state, sampled, future);hudElapsed = 0; }
    return { ...state, sourceMode: "recorded_synthetic", frameIndex: sampled.index };
  }
  function mount() {
    const rewards=bundle.learning_curve.map(row=>row.mean_step_reward);
    const axis=document.getElementById("curve-y-axis");
    axis.textContent="Mean step reward";
    axis.title=`Dimensionless; raw range ${Math.min(...rewards).toFixed(4)} to ${Math.max(...rewards).toFixed(4)}`;
    axis.setAttribute("aria-label",axis.title);
    document.getElementById("curve-x-axis").textContent=`0–${bundle.learning_curve.at(-1).environment_steps.toLocaleString("en-GB")} decisions`;
    ui["reward-path"].setAttribute("d", points.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(" "));
    ui["reward-chart"].setAttribute("aria-label", "Measured mean step reward at each recorded optimiser rollout. No smoothing; no full learned delivery cycle.");
    ui["run-provenance"].textContent = `${bundle.run_id}\nTraining: ${bundle.run.training_wall_s.toFixed(2)} s wall · ${bundle.run.counters.environment_steps.toLocaleString("en-GB")} decisions · ${bundle.run.counters.optimiser_updates.toLocaleString("en-GB")} optimiser steps\nNominal training simulation: ${bundle.run.counters.nominal_simulated_s.toFixed(1)} s\nTraining curve includes its recorded curriculum/shaping stage. Replay step rewards use delivery-v1.\nAction order: acceleration, articulation, boom, bucket; normalised [-1,1].\nPolicy and raw dynamics are separate networks. Model ${bundle.world_model.model_sha256}\nTraining source ${bundle.run.source.git_commit}\nExporter source ${bundle.export_source.git_commit}\nEnvelope: ${bundle.world_model.envelope_method}\n${bundle.presentation.limitations}`;
    lastFrame = null;update(0);
  }
  return { root, sourceMode: "recorded_synthetic", camera: [24, 21, 28], target: [3, 0.5, 0], mount, update,
    replay() { clock.replay();update(0); }, pause() { clock.toggle();update(0); }, checkpoint(index) { clock.checkpoint(index);update(0); },
    seek(time) { clock.seek(time);update(0); }, pace(value) { clock.setPace(value);update(0); },
    horizon(value) { if (![1, 2, 4, 8].includes(value)) return;horizon = value;this.inspect(); },
    inspect() { const state = clock.state(), anchors = state.episode.records.filter((r) => r.predictions.some((p) => p.horizon_decisions === horizon));if (!anchors.length) return;const anchor = anchors.reduce((a, b) => Math.abs(b.t_s - state.time) < Math.abs(a.t_s - state.time) ? b : a);clock.seek(anchor.t_s);update(0); },
    get running() { return !clock.paused; },
    diagnostics() { const state = clock.state(), sampled = sampleEpisode(state.episode, state.time), p = sampled.pose, heading = p[2] + p[4];
      loader.root.updateMatrixWorld(true);
      const actualMouth = loader.bucket.localToWorld(new THREE.Vector3(0, 0, 0.6));
      const expectedMouth = new THREE.Vector3(p[0] + 1.8 * Math.cos(p[2]) + (1.6 + 1.2 * Math.cos(p[5])) * Math.cos(heading), 0.35 + 2 * Math.sin(p[5]), -p[1] - 1.8 * Math.sin(p[2]) - (1.6 + 1.2 * Math.cos(p[5])) * Math.sin(heading));
      return { bucketMouthErrorM: actualMouth.distanceTo(expectedMouth), runId: bundle.run_id, sourceMode: "recorded_synthetic", checkpoint: state.index, simulatedTime: state.time, paused: state.paused, horizon, frame: sampleEpisode(state.episode, state.time).index, counters: state.episode.policy.training_counters }; },
  };
}
