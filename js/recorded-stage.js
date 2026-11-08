import { authoredAsset } from "./authored-assets.js";
import * as THREE from "three";
import { createReferenceLoader } from "./loader-stage.js";
import { texture, box, lightRig, line } from "./scene-utils.js";
import { ReplayClock, sampleEpisode, curvePoints, episodeEvents } from "./recorded-data.js";

import { heightField } from "./height-field.js";

export async function createRecorded(config, bundle) {
  const root = new THREE.Group(); root.name = "recorded-synthetic-experiment";
  const [ore, floor, asset, authored] = await Promise.all([texture(config.assets.ore), texture(config.assets.floor, 5), fetch(config.assets.loader, { cache: "no-store" }).then((r) => { if (!r.ok) throw new Error("Loader asset unavailable"); return r.json(); }), authoredAsset(config.visuals.authored?.reference_loader).catch(error=>{console.warn("Authored loader unavailable",error);return null;})]);
  const isReference=bundle.agent?.kind === "reference_controller";
  const [oreNormal,floorNormal]=await Promise.all([texture(config.assets.ore_normal,1,false),texture(config.assets.floor_normal,5,false)]);
  const indices = Object.fromEntries(bundle.state_names.map((name, i) => [name, i]));
  const initial = bundle.episodes[0].records[0].state, halfWidth = initial[indices.half_width_m];
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(29, halfWidth * 2), new THREE.MeshStandardMaterial({ map: floor, normalMap:floorNormal, normalScale:new THREE.Vector2(.55,.55), color: 0x72756c, roughness: 1 }));
  ground.rotation.x = -Math.PI / 2;ground.position.x = 3.5;ground.receiveShadow = true;root.add(ground);
  const edging = new THREE.MeshStandardMaterial({ color: 0x303c3b, roughness: 1, map: ore });
  for (const side of [-1, 1]) box([29, 0.65, 0.45], [3.5, 0.325, side * (halfWidth + 0.225)], edging, root);
  const grid = new THREE.GridHelper(30, 30, 0x4c625f, 0x293a3a);grid.position.set(3.5, 0.012, 0);grid.material.transparent = true;grid.material.opacity = 0.18;root.add(grid);
  const loader = createReferenceLoader(asset, ore, authored);root.add(loader.root);
  document.getElementById("geometry-guide").addEventListener("change",event=>loader.guide(event.target.checked));
  function materialSurface(colour) {
    const geometry=new THREE.BufferGeometry(), mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({map:ore,normalMap:oreNormal,normalScale:new THREE.Vector2(.6,.6),color:colour,roughness:.98}));mesh.castShadow=mesh.receiveShadow=true;root.add(mesh);
    function set(cells,originX,originY,dx=.5,dy=.5) {
      const field=heightField(cells,8,8,dx,dy), values=new Float32Array(field.positions);
      if(geometry.attributes.position?.array.length===values.length) { geometry.attributes.position.array.set(values);geometry.attributes.position.needsUpdate=true; }
      else { geometry.setAttribute("position",new THREE.BufferAttribute(values,3));const uv=new Float32Array(values.length/3*2);for(let i=0;i<values.length/3;i++){uv[i*2]=values[i*3];uv[i*2+1]=-values[i*3+2];}geometry.setAttribute("uv",new THREE.BufferAttribute(uv,2)); }
      geometry.computeVertexNormals();geometry.computeBoundingSphere();mesh.position.set(originX,.005,-originY);mesh.visible=field.volume>1e-12;return field;
    }
    return {mesh,set};
  }
  const pile=materialSurface(0xb6a792),deposition=materialSurface(0x9f927a),spill=materialSurface(0x897960);
  const heapWeights=Array.from({length:64},(_,k)=>Math.exp(-((Math.floor(k/8)-3.5)**2+(k%8-3.5)**2)/5));
  const heapTotal=heapWeights.reduce((a,b)=>a+b,0);
  const transferFragments=new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.045,0),new THREE.MeshStandardMaterial({map:ore,color:0xae9b7c,roughness:1}),16);transferFragments.castShadow=true;root.add(transferFragments);
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
  const reference=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(7.1,1.9,1.5)),new THREE.LineDashedMaterial({color:0xe5e6d9,dashSize:.2,gapSize:.12,transparent:true,opacity:.7,depthTest:false}));reference.computeLineDistances();reference.renderOrder=3;root.add(reference);
  const prediction = ghost(0x4ee29b);
  const residual = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]), new THREE.LineBasicMaterial({ color: 0x4ee29b, depthTest: false }));residual.renderOrder = 3;root.add(residual);
  const spread = new THREE.Mesh(new THREE.RingGeometry(0.96, 1, 48), new THREE.MeshBasicMaterial({ color: 0x4ee29b, transparent: true, opacity: 0.7, side: THREE.DoubleSide, depthTest: false }));spread.rotation.x = -Math.PI / 2;root.add(spread);
  const sensors = new THREE.InstancedMesh(new THREE.SphereGeometry(0.035, 6, 4), new THREE.MeshBasicMaterial({ color: 0xa6c2ca, transparent: true, opacity: 0.8 }), 25);root.add(sensors);
  const forecastPile = new THREE.InstancedMesh(new THREE.SphereGeometry(0.035, 6, 4), new THREE.MeshBasicMaterial({ color: 0xffffff, depthTest: false }), 64);forecastPile.renderOrder = 2;root.add(forecastPile);
  const key=lightRig(root,22,"mine");key.shadow.mapSize.set(2048,2048);key.shadow.camera.top=key.shadow.camera.right=18;key.shadow.camera.bottom=key.shadow.camera.left=-18;
  const rim=new THREE.DirectionalLight(0x9fbfc6,.8);rim.position.set(4,7,-8);root.add(rim);
  const service=new THREE.MeshStandardMaterial({color:0x88adb0,emissive:0x46767c,emissiveIntensity:.45,roughness:.45,metalness:.6});
  for(const side of [-1,1]){box([27,.045,.045],[3.5,.75,side*(halfWidth+.02)],service,root);for(let k=0;k<10;k++)box([.08,.15,.08],[-9+k*2.7,.5,side*(halfWidth-.01)],edging,root);}

  const clock = new ReplayClock(bundle, matchMedia("(prefers-reduced-motion: reduce)").matches);
  const pose = new THREE.Object3D(), colour = new THREE.Color();
  const ui = Object.fromEntries(["episode-count", "reward-value", "action-value", "policy-value", "checkpoint-outcome", "payload-readout", "training-status", "pause-training", "reward-path", "reward-point", "training-status", "episode-caption", "reward-explanation", "observation-value", "recorded-time", "replay-scrub", "prediction-error", "prediction-score", "prediction-validity", "prediction-time", "member-spread", "run-provenance", "reward-chart", "observation-crop"].map((id) => [id, document.getElementById(id)]));
  const cells = Array.from({ length: 25 }, () => { return document.createElement("span"); });
  let points = curvePoints(bundle.learning_curve), forecastVisible=false, materialAudit=null, eventButtons=[], activeEvents=[];
  let horizon = 1, hudElapsed = 0, lastFrame = null, lastEpisode = -1, currentFuture = null;
  function place(mesh, state) { mesh.position.set(state[0] + 1.65 * Math.cos(state[2]), 0.95, -state[1] - 1.65 * Math.sin(state[2]));mesh.rotation.y = state[2]; }
  function renderForecast(frame, episode) {
    const future = frame.predictions.find((p) => p.horizon_decisions === horizon), exists = !!future?.prediction;
    for (const object of [reference, prediction, residual, spread, forecastPile]) object.visible = exists && forecastVisible;
    sensors.visible=forecastVisible;
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
      colour.set(0x708f94).lerp(new THREE.Color(0x4ee29b), Math.min(1, Math.abs(p[15 + k] - ref[15 + k]) / 0.002));forecastPile.setColorAt(k, colour);
    }
    forecastPile.instanceMatrix.needsUpdate = true;forecastPile.instanceColor.needsUpdate = true;
    return { ...future, spread_m: major };
  }
  // #365/#366/#367: when the whole sequence finishes it used to rest on just
  // the last episode's outcome, so Reference ended on "Stuck. Delivered 0 kg."
  // despite two completed 2,000 kg cycles, and the bounded policy runs ended
  // on a bare wall collision with no statement of what the run as a whole
  // showed. Summarise every recorded episode instead. Nothing is reordered or
  // reclassified; failures stay failures.
  const sequenceSummary = (() => {
    const eps = bundle.episodes, delivered = eps.filter((e) => e.metrics.delivered_kg > 0);
    const noun = isReference ? "recorded cycles" : eps[0]?.training_seed ? "recorded seeds" : "recorded checkpoints";
    const head = `${eps.length} ${noun}`;
    if (delivered.length) {
      const kg = delivered.map((e) => `${e.metrics.delivered_kg.toFixed(0)} kg`).join(", ");
      const short = eps.length - delivered.length;
      return `${head} · ${delivered.length} delivered (${kg})${short ? ` · ${short} did not` : ""}.`;
    }
    const peaks = eps.map((e) => e.metrics.peak_load_kg).filter((v) => typeof v === "number" && v > 0);
    return `${head} · no delivery completed in this bounded run.`
      + (peaks.length > 1 ? ` Peak load ${Math.min(...peaks).toFixed(0)} → ${Math.max(...peaks).toFixed(0)} kg.` : "");
  })();
  function paintHud(state, sampled, future) {
    const { episode, index } = state, frame = sampled.frame, counters = episode.policy?.training_counters || {completed_episodes:0,rollouts:0};
    // #366: the hero used to show only the live delivered mass, so mid-cycle it
    // read "0" directly above "Delivery complete. Delivered 2027 kg." Show the
    // running total against this episode's recorded result instead, so the
    // number reads as progress rather than contradicting the outcome line.
    ui["episode-count"].textContent = isReference
      ? `${frame.state[8].toFixed(0)} / ${episode.metrics.delivered_kg.toFixed(0)}`
      : counters.completed_episodes.toLocaleString("en-GB");
    const measured = counters.rollouts > 0 ? (episode.learning_curve || bundle.learning_curve)[counters.rollouts - 1] : null;
    ui["reward-value"].textContent = isReference ? `${frame.state[8].toFixed(0)} kg` : measured ? measured.mean_step_reward.toFixed(4) : "No update";
    ui["action-value"].title = "Acceleration, articulation rate, boom rate, bucket rate; normalised [-1,1]";
    ui["action-value"].setAttribute("aria-label", frame.action ? frame.action.map((v, i) => `${bundle.action_names[i]} ${v.toFixed(3)}`).join(", ") + "; normalised minus one to one" : "Terminal record, no next action");
    ui["action-value"].textContent = frame.action ? frame.action.map((v) => v.toFixed(2)).join(" · ") : "No next action";
    ui["policy-value"].textContent = isReference ? `Reference · ${frame.phase || "Terminal"}` : `${episode.name} · ${episode.policy.checkpoint_sha256.slice(0, 8)}`;
    ui["observation-value"].textContent = `Local crop · ${frame.observation.slice(40).filter(Boolean).length}/25 valid`;
    const weighted = frame.reward_weighted ? Object.entries(frame.reward_weighted).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))[0] : null;
    const termNames = { elapsed_s: "time", effort_proxy_j: "effort", collision_count: "collision", delivered_kg: "delivery", spilled_kg: "spill", slip_s: "slip" };
    ui["reward-explanation"].textContent = weighted ? `${frame.reward.toFixed(4)} · ${termNames[weighted[0]]} ${weighted[1].toFixed(4)}` : "Episode ended";
    const outcome = { tunnel_wall: "Wall collision", time_limit: "Time limit", stuck: "Stuck", success: "Delivery complete" }[episode.outcome] || episode.outcome;
    const episodeOutcome = `${outcome}. Delivered ${episode.metrics.delivered_kg.toFixed(0)} kg.${episode.training_seed ? ` Peak load ${episode.metrics.peak_load_kg?.toFixed(0) || "0"} kg.` : ""}`;
    const finishedSequence = state.complete && clock.sequence;
    ui["checkpoint-outcome"].textContent = finishedSequence ? `${episodeOutcome} ${sequenceSummary}` : episodeOutcome;
    ui["payload-readout"].textContent = `Payload ${frame.state[7].toFixed(0)} / 3,500 kg`;
    ui["training-status"].textContent = state.paused ? state.complete ? finishedSequence ? "All recorded episodes shown" : "Recorded episode ended" : "Recorded replay paused" : isReference ? "Recorded reference control" : "Recorded policy decisions";
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
    const event=activeEvents.filter(e=>e.t_s<=frame.t_s+1e-9).at(-1);
    document.getElementById("event-readout").textContent=event ? `${event.kind.replaceAll("_"," ")} · ${event.t_s.toFixed(2)} s` : "No recorded event";
    eventButtons.forEach((button,i)=>button.setAttribute("aria-pressed",String(activeEvents[i]===event)));
    const curveIndex = Math.max(0, Math.min(points.length - 1, counters.rollouts - 1)), point = isReference ? [frame.t_s/episode.records.at(-1).t_s*300,66-frame.state[8]/Math.max(1,episode.metrics.delivered_kg)*60] : points[curveIndex];
    ui["reward-point"].style.visibility = !isReference && counters.rollouts === 0 ? "hidden" : "visible";
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
      const density=s[indices.density_kg_m3],source=pile.set(s.slice(15,79),s[indices.pile_origin_x_m],s[indices.pile_origin_y_m]);
      deposition.set(heapWeights.map(w=>w*s[8]/(density*(hx*hy/16)*heapTotal)),rx-hx,-ry-hy,hx/4,hy/4);
      // Spill location is a display centroid derived from recorded transfer poses.
      let spillX=0,spillY=0,spillKg=0;
      for(let i=1;i<=sampled.index;i++){const a=state.episode.records[i-1].state,b=state.episode.records[i].state,kg=Math.max(0,b[9]-a[9]);spillX+=kg*(b[0]+1.8*Math.cos(b[2])+(1.6+1.2*Math.cos(b[5]))*Math.cos(b[2]+b[4]));spillY+=kg*(b[1]+1.8*Math.sin(b[2])+(1.6+1.2*Math.cos(b[5]))*Math.sin(b[2]+b[4]));spillKg+=kg;}
      spill.set(heapWeights.map(w=>w*s[9]/(density*.0625*heapTotal)),spillKg?spillX/spillKg-1:0,spillKg?spillY/spillKg-1:0,.25,.25);
      materialAudit={sourceKg:source.volume*density,carriedKg:s[7],deliveredKg:s[8],spilledKg:s[9],residualKg:source.volume*density+s[7]+s[8]+s[9]-s[indices.initial_mass_kg]};
      if(lastEpisode!==state.index) mountEpisode(state.episode);
      traces.forEach((trace, i) => { trace.visible = i === state.index; });
      const heading = s[2] + s[4], mx = s[0] + 1.8 * Math.cos(s[2]) + (1.6 + 1.2 * Math.cos(s[5])) * Math.cos(heading), my = s[1] + 1.8 * Math.sin(s[2]) + (1.6 + 1.2 * Math.cos(s[5])) * Math.sin(heading);
      for (let k = 0; k < 25; k++) { const along = (Math.floor(k / 5) - 1) * 0.75, across = (k % 5 - 2) * 0.75;pose.position.set(mx + along * Math.cos(heading) - across * Math.sin(heading), sampled.frame.observation[15 + k] + 0.02, -(my + along * Math.sin(heading) + across * Math.cos(heading)));pose.scale.setScalar(sampled.frame.observation[40 + k] ? 1 : 0);pose.updateMatrix();sensors.setMatrixAt(k, pose.matrix); }sensors.instanceMatrix.needsUpdate = true;
      lastFrame = sampled.frame;lastEpisode = state.index;
    }
    const previous=state.episode.records[Math.max(0,sampled.index-1)],deliveredDelta=Math.max(0,s[8]-previous.state[8]),loadedDelta=Math.max(0,s[7]-previous.state[7]),spilledDelta=Math.max(0,s[9]-previous.state[9]);
    transferFragments.visible=sampled.index>0&&(deliveredDelta+loadedDelta+spilledDelta)>1e-6&&state.time-sampled.frame.t_s<.12;
    if(transferFragments.visible){const mouth=loader.geometry().mouth,t=Math.min(1,(state.time-sampled.frame.t_s)/.12);for(let i=0;i<16;i++){const angle=i*2.399,fall=(t+i/32)%1;pose.position.set(mouth.x+Math.cos(angle)*.18,mouth.y-(deliveredDelta+spilledDelta>0?fall*fall*.7:-fall*.15),mouth.z+Math.sin(angle)*.18);pose.scale.setScalar(.65+i%3*.18);pose.rotation.set(i,t+i,i*.4);pose.updateMatrix();transferFragments.setMatrixAt(i,pose.matrix);}transferFragments.instanceMatrix.needsUpdate=true;}
    if (changed || delta === 0) currentFuture = renderForecast(sampled.frame, state.episode);
    const future = currentFuture;
    hudElapsed += delta;if (hudElapsed >= 0.09 || changed || delta === 0) { paintHud(state, sampled, future);hudElapsed = 0; }
    return { ...state, sourceMode: "recorded_synthetic", frameIndex: sampled.index };
  }
  function mountEpisode(episode) {
    activeEvents=episodeEvents(episode);const markers=document.getElementById("event-markers");markers.replaceChildren();
    eventButtons=activeEvents.map(event=>{const button=document.createElement("button");button.type="button";button.title=`${event.kind} · ${event.t_s.toFixed(2)} s`;button.setAttribute("aria-label",button.title);button.style.left=`${event.t_s/episode.records.at(-1).t_s*100}%`;button.addEventListener("click",()=>{clock.seek(event.t_s);update(0);});markers.append(button);return button;});
    if(episode.learning_curve){points=curvePoints(episode.learning_curve);ui["reward-path"].setAttribute("d",points.map((p,i)=>`${i?"L":"M"}${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(" "));}
    if(isReference){const rows=episode.records,maxKg=Math.max(1,episode.metrics.delivered_kg),duration=rows.at(-1).t_s;ui["reward-path"].setAttribute("d",rows.map((r,i)=>`${i?"L":"M"}${(r.t_s/duration*300).toFixed(2)} ${(66-r.state[8]/maxKg*60).toFixed(2)}`).join(" "));document.getElementById("curve-x-axis").textContent=`0–${duration.toFixed(1)} simulated seconds`;}
  }
  function mount() {
    ui["observation-crop"].replaceChildren(...cells);
    const rewards=bundle.learning_curve.map(row=>row.mean_step_reward);
    if(!rewards.length) rewards.push(0);
    const axis=document.getElementById("curve-y-axis");
    axis.textContent="Mean step reward";
    axis.title=`Dimensionless; raw range ${Math.min(...rewards).toFixed(4)} to ${Math.max(...rewards).toFixed(4)}`;
    axis.setAttribute("aria-label",axis.title);
    document.getElementById("curve-x-axis").textContent=`0–${(bundle.learning_curve.at(-1)?.environment_steps || 0).toLocaleString("en-GB")} decisions`;
    ui["reward-path"].setAttribute("d", points.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(" "));
    ui["reward-chart"].setAttribute("aria-label", "Measured mean step reward at each recorded optimiser rollout. No smoothing; no full learned delivery cycle.");
    if(!isReference) ui["run-provenance"].textContent = `${bundle.run_id}\nTraining: ${bundle.run.training_wall_s.toFixed(2)} s wall · ${bundle.run.counters.environment_steps.toLocaleString("en-GB")} decisions · ${bundle.run.counters.optimiser_updates.toLocaleString("en-GB")} optimiser steps\nNominal training simulation: ${bundle.run.counters.nominal_simulated_s.toFixed(1)} s\nTraining curve includes its recorded curriculum/shaping stage. Replay step rewards use delivery-v1.\nAction order: acceleration, articulation, boom, bucket; normalised [-1,1].\nPolicy and raw dynamics are separate networks. Model ${bundle.world_model.model_sha256}\nTraining source ${bundle.run.source.git_commit}\nExporter source ${bundle.export_source.git_commit}\nEnvelope: ${bundle.world_model.envelope_method}\n${bundle.presentation.limitations}`;
    if(bundle.run_id==="curriculum-followup-v1"){
      document.getElementById("learning-source-label").textContent="Recorded synthetic · curriculum study";
      document.getElementById("learning-title").textContent="Partial pickup";
      document.querySelectorAll("[data-checkpoint]").forEach((button,i)=>{button.textContent=bundle.episodes[i].name;});
      ui["run-provenance"].textContent=`${bundle.run_id}\n${bundle.presentation.selection}\n${bundle.episodes.map(e=>`Seed ${e.training_seed}: ${e.policy.checkpoint_sha256}`).join("\n")}\nEach seed: 4,096 charged reference decisions; no invented online training.\n${bundle.presentation.limitations}`;
    }
    if(isReference){
      document.getElementById("learning-source-label").textContent="Synthetic reference · conventional controller";
      document.getElementById("learning-title").textContent="Reference cycle";document.getElementById("episode-caption").textContent="kg delivered this cycle";
      document.getElementById("learning-section-label").textContent="Reference simulator";document.getElementById("reward-curve-label").textContent="Delivered ore";
      document.getElementById("curve-y-axis").textContent="Delivered / kg";document.getElementById("curve-y-axis").removeAttribute("title");
      ui["reward-chart"].setAttribute("aria-label","Recorded delivered mass over simulated time, conventional reference controller");
      document.querySelectorAll("[data-checkpoint]").forEach((button,i)=>{button.textContent=bundle.episodes[i]?.name || "";button.hidden=!bundle.episodes[i];});
      document.getElementById("caption-detail").textContent="Conventional reference, not a learned policy. Mine figures illustrative.";
      ui["run-provenance"].textContent=`${bundle.run_id}\nController ${bundle.agent.configuration_sha256}\n${bundle.presentation.selection}\nModel ${bundle.world_model.model_sha256}\n${bundle.world_model.selection}\n${bundle.presentation.limitations}\nCargo, transfer fragments and spill centroid are visual proxies; height-field source and destination volumes follow the recorded ledger.`;
    }
    lastFrame = null;lastEpisode=-1;update(0);
  }
  // #368: frame the recorded task from the data instead of a fixed camera.
  // The previous [24,21,28] -> [3,0.5,0] pair sat ~40 m from a task about 11 m
  // across, so the loading-and-delivery work occupied roughly 19% of the frame
  // width and read as a toy adrift on an empty floor (see #364's measurements).
  // Keep the same three-quarter view direction; solve distance and lateral
  // placement from the recorded receiver, pile and machine path.
  const framing = (() => {
    const DIRECTION = new THREE.Vector3(21, 20.5, 28).normalize();  // old camera - old target
    const FOV = 42, HALF = Math.tan((FOV / 2) * Math.PI / 180);
    // experience.js viewport() already calls setViewOffset with an x offset of
    // innerWidth * 0.14 for the learning stage, which pans rendered content
    // left by 0.28 NDC to clear the instrument panel. Do not shift the look
    // target as well -- that double-corrects and pushes the work off to the
    // left. Only the fit has to respect the remaining usable half-width.
    const VIEW_SHIFT = 0.28, PANEL_NDC = 0.507;
    const USABLE = Math.min(1 - VIEW_SHIFT, PANEL_NDC + VIEW_SHIFT), FILL = 0.88;
    const min = new THREE.Vector3(Infinity, 0, Infinity), max = new THREE.Vector3(-Infinity, 2.5, -Infinity);
    const include = (x, z) => { min.x = Math.min(min.x, x); max.x = Math.max(max.x, x); min.z = Math.min(min.z, z); max.z = Math.max(max.z, z); };
    include(rx - hx, ry - hy); include(rx + hx, ry + hy);               // receiver
    const px = initial[indices.pile_origin_x_m], py = initial[indices.pile_origin_y_m];
    include(px, -py); include(px + 4, -(py + 4));                        // 8x8 pile cells at 0.5 m
    for (const episode of bundle.episodes)
      for (const record of episode.records) include(record.state[0], -record.state[1]);
    const centre = new THREE.Vector3((min.x + max.x) / 2, 1, (min.z + max.z) / 2);
    const aspect = Math.max(1, innerWidth / Math.max(1, innerHeight));
    // Fit the task's screen-space extent inside the usable half-width.
    const right = new THREE.Vector3(0, 1, 0).cross(DIRECTION).normalize();
    const spanRight = Math.abs((max.x - min.x) * right.x) + Math.abs((max.z - min.z) * right.z);
    const spanUp = Math.abs(max.x - min.x) * 0.35 + (max.y - min.y);
    const distance = Math.max(
      spanRight / (2 * HALF * aspect * USABLE * FILL),
      spanUp / (2 * HALF * FILL),
      14,
    );
    return { camera: centre.clone().addScaledVector(DIRECTION, distance).toArray(), target: centre.toArray() };
  })();

  return { root, sourceMode: "recorded_synthetic", camera: framing.camera, target: framing.target, mount, update,
    replay() { clock.replay();update(0); }, pause() { clock.toggle();update(0); }, checkpoint(index) { clock.checkpoint(index);update(0); },
    seek(time) { clock.seek(time);update(0); }, pace(value) { clock.setPace(value);update(0); },
    forecast(value) { forecastVisible=!!value;update(0); },
    event(direction) { const time=clock.state().time,events=episodeEvents(clock.state().episode);const event=direction>0?events.find(e=>e.t_s>time+1e-7):events.filter(e=>e.t_s<time-1e-7).at(-1);if(event){clock.seek(event.t_s);update(0);} },
    horizon(value) { if (![1, 2, 4, 8].includes(value)) return;horizon = value;this.inspect(); },
    inspect() { const state = clock.state(), anchors = state.episode.records.filter((r) => r.predictions.some((p) => p.horizon_decisions === horizon));if (!anchors.length) return;const anchor = anchors.reduce((a, b) => Math.abs(b.t_s - state.time) < Math.abs(a.t_s - state.time) ? b : a);clock.seek(anchor.t_s);update(0); },
    get running() { return !clock.paused; },
    diagnostics() { const state = clock.state(), sampled = sampleEpisode(state.episode, state.time), p = sampled.pose, heading = p[2] + p[4];
      loader.root.updateMatrixWorld(true);
      const actualMouth = loader.bucket.localToWorld(new THREE.Vector3(0, 0, 0.6));
      const expectedMouth = new THREE.Vector3(p[0] + 1.8 * Math.cos(p[2]) + (1.6 + 1.2 * Math.cos(p[5])) * Math.cos(heading), 0.35 + 2 * Math.sin(p[5]), -p[1] - 1.8 * Math.sin(p[2]) - (1.6 + 1.2 * Math.cos(p[5])) * Math.sin(heading));
      return { bucketMouthErrorM: actualMouth.distanceTo(expectedMouth), runId: bundle.run_id, sourceMode: "recorded_synthetic", checkpoint: state.index, simulatedTime: state.time, paused: state.paused, horizon, frame: sampleEpisode(state.episode, state.time).index, counters: state.episode.policy?.training_counters || null, material:materialAudit, forecastVisible, agentKind:isReference?"reference_controller":"learned_policy", eventCount:activeEvents.length }; },
  };
}
