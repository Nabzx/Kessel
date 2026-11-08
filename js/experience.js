import * as THREE from "three";
import { createGlobe } from "./globe-stage.js";
import { createEnvironmentScenes } from "./environment-scenes.js";
import { studioEnvironment } from "./scene-utils.js";

const $ = (id) => document.getElementById(id);
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const canvas = $("world-canvas");
let renderer;
try {
  renderer = new THREE.WebGLRenderer({
    canvas,
    alpha: true,
    antialias: true,
    powerPreference: "high-performance",
  });
} catch (error) {
  $("start-experience").textContent = "This experience requires WebGL";
  throw error;
}
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.04;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
scene.background = new THREE.Color("#030506");
const camera = new THREE.PerspectiveCamera(
  34,
  innerWidth / innerHeight,
  0.01,
  100,
);
camera.position.set(0, 0, 17);
camera.lookAt(0, 0, 0);
const lookTarget = new THREE.Vector3();
let data, globe, surface, mine, learning, kit, environmentScenes;
let homeHandoff=null, selectorRect=null;
let stage = "welcome",
  comparison = false,
  environment = 0,
  transition = null,
  cameraMove = null;
let surfacePromise,
  minePromise,
  kitPromise,
  kitEnvironment,
  earthGoal = null,
  entryContext = null;
let lastTime = 0,
  globalTime = 0,
  quality = Math.min(devicePixelRatio || 1, 1.5),
  frameTimes = [],
  qualityFrames = [],
  hudTime = 0,
  kitActive = false,
  kitExploded = 1,
  mineNeedsReload = false;
const baseOpacity = new WeakMap(),
  baseLight = new WeakMap();
const panels = [
  "welcome",
  "selector",
  "surface-panel",
  "operations",
  "model-transition",
];
function showOnly(id) {
  for (const name of panels) $(name).hidden = name !== id;
}
function duration(seconds) {
  return reduced ? Math.min(0.35, seconds) : seconds;
}
function setStage(next) {
  stage = next;
  $("experience").dataset.stage = next;
  environmentScenes?.visible(["select","preparing"].includes(next));
  if(next === "select") { scene.background=null;globe?.mode("select"); }
  if(!renderer.shadowMap.autoUpdate)renderer.shadowMap.needsUpdate=true;
  frameTimes = [];
  const ordered=["select","surface","mine","trained","learning"];
  const active=ordered.indexOf(({flight:"surface",preparing:"surface",entering:"mine",comparing:"trained"})[next]||next);
  $("journey").hidden=active<0;
  for(const [i,item] of [...$("journey").children].entries()) {
    if(i===active)item.setAttribute("aria-current","step");else item.removeAttribute("aria-current");
    item.toggleAttribute("data-complete",i<active);
  }
}
function cameraTo(position, target, seconds, fov = camera.fov) {
  cameraMove = {
    start: performance.now(),
    duration: duration(seconds) * 1000,
    from: camera.position.clone(),
    to: new THREE.Vector3(...position),
    fromTarget: lookTarget.clone(),
    target: new THREE.Vector3(...target),
    fromFov: camera.fov,
    fov,
  };
}
function updateCamera(now) {
  if (!cameraMove) return;
  const p = Math.min(1, (now - cameraMove.start) / cameraMove.duration),
    t = p * p * (3 - 2 * p);
  camera.position.lerpVectors(cameraMove.from, cameraMove.to, t);
  lookTarget.lerpVectors(cameraMove.fromTarget, cameraMove.target, t);
  camera.fov = THREE.MathUtils.lerp(cameraMove.fromFov, cameraMove.fov, t);
  camera.updateProjectionMatrix();
  camera.lookAt(lookTarget);
  if (p === 1) cameraMove = null;
}
function viewport(mode = stage) {
  camera.aspect=innerWidth/innerHeight;
  camera.clearViewOffset();
  if (
    innerWidth > 700 &&
    ["mine", "trained", "comparing", "learning"].includes(mode)
  )
    camera.setViewOffset(
      innerWidth,
      innerHeight,
      innerWidth * 0.14,
      0,
      innerWidth,
      innerHeight,
    );
  else if (innerWidth <= 700 && ["mine", "trained", "learning"].includes(mode))
    camera.setViewOffset(
      innerWidth,
      innerHeight,
      0,
      innerHeight * 0.18,
      innerWidth,
      innerHeight,
    );
  camera.updateProjectionMatrix();
}
function fade(root, alpha) {
  root.visible = alpha > 0.001;
  root.traverse((object) => {
    if (object.isLight) {
      if (!baseLight.has(object)) baseLight.set(object, object.intensity);
      object.intensity = baseLight.get(object) * alpha;
    }
    if (object.isMesh || object.isPoints)
      for (const material of Array.isArray(object.material)
        ? object.material
        : [object.material])
        if (material) {
          if (!baseOpacity.has(material))
            baseOpacity.set(material, material.opacity);
          material.transparent =
            !!material.userData.scanTransparent ||
            alpha < 1 ||
            baseOpacity.get(material) < 1;
          material.opacity = baseOpacity.get(material) * alpha;
        }
  });
}
function globeFade(alpha) {
  globe.visible(alpha > 0.015);
  fade(globe.root, alpha);
  globe.sun.intensity = data.visuals.home.sun_intensity * alpha;
  globe.stars.material.opacity = 0.78 * alpha;
}
const glyphs = {
  glacier:
    '<path d="M12 73L50 18L68 39L91 7L148 73M12 73H148M50 18L44 49L61 41L68 39M91 7L96 34L113 30M44 49L61 73M96 34L84 73"/>',
  desert:
    '<path d="M4 65Q45 17 100 61T166 63M4 65Q54 30 101 61M23 70Q89 43 156 71"/><circle cx="129" cy="19" r="12"/>',
  space:
    '<ellipse cx="84" cy="43" rx="74" ry="18" transform="rotate(-20 84 43)"/><circle cx="84" cy="43" r="29"/><path d="M58 30Q84 21 107 30M57 52Q84 64 109 49M84 14Q66 43 84 72M84 14Q102 43 84 72"/>',
  mine: '<path d="M10 24L84 5L154 25L83 48Z M10 24V62L83 85L154 62V25M83 48V85M29 44L60 53V66L105 51L105 37M60 53L111 38M111 38V59L135 51"/>',
  sea: '<path d="M4 24Q22 9 42 24T82 24T122 24T162 24M4 41Q22 26 42 41T82 41T122 41T162 41M4 58Q22 43 42 58T82 58T122 58T162 58M4 75Q22 60 42 75T82 75T122 75T162 75"/>',
};
function chooseEnvironment(index) {
  environment = (index + data.environments.length) % data.environments.length;
  const item = data.environments[environment];
  $("environment-name").textContent = item.label;
  $("environment-description").textContent = item.description;
  $("environment-place").textContent = item.place;
  $("environment-image").alt=item.preview.alt;
  $("environment-image").src=item.preview.path;
  $("environment-credit").textContent=item.preview.caption;
  environmentScenes.select(item);
  environmentScenes.warm(environment);
  $("orbit-location").textContent=item.id === "space" ? "Lunar surface · preview" : `${Math.abs(item.latitude).toFixed(2)}° ${item.latitude<0?"S":"N"} / ${Math.abs(item.longitude).toFixed(2)}° ${item.longitude<0?"W":"E"}`;
  $("environment-status").textContent = item.available
    ? "Available"
    : "Planned";
  $("environment-count").textContent =
    `${String(environment + 1).padStart(2, "0")} / ${String(data.environments.length).padStart(2, "0")}`;
  $("environment-icon").innerHTML =
    `<svg viewBox="0 0 170 94">${glyphs[item.glyph]}</svg>`;
  $("selector").style.setProperty("--theme", item.colour);
  $("deploy-underground").hidden = !item.available;
  $("globe-label-name").textContent = item.place;
  globe.highlight(item.id);
  globe.sun.color.set(data.visuals.home.sun_colour);
  const target = item.id === "space" ? globe.earth.rotation.y : -THREE.MathUtils.degToRad(item.longitude + 90);
  earthGoal =
    target +
    Math.round((globe.earth.rotation.y - target) / (Math.PI * 2)) * Math.PI * 2;
  if(reduced){globe.earth.rotation.y=earthGoal;earthGoal=null;globe.update(0,0,false);}
}
function start() {
  if (!data || stage !== "welcome") return;
  const fromPosition=globe.root.position.clone();cameraMove=null;
  $("welcome").classList.add("leaving");
  setTimeout(()=>{if(stage!=="welcome")$("welcome").hidden=true;},reduced?0:650);
  $("selector").hidden=false;$("navigation").classList.add("started");
  setStage("select");
  if(!reduced){homeHandoff={start:performance.now(),fromPosition,duration:900};globe.root.position.copy(fromPosition);}
  cameraTo([0,0,12.8],[0,0,0],reduced?.01:.9,34);
  chooseEnvironment(0);
  $("deploy-underground").focus({preventScroll:true});
  setTimeout(()=>{
    if(stage!=="select")return;
    const warm=()=>{if(stage==="select")getSurface().then(()=>getMine()).catch(()=>{});};
    if("requestIdleCallback" in window)requestIdleCallback(warm,{timeout:1200});else warm();
  },reduced?100:data.visuals.home.prefetch_delay_seconds*1000);
}

const preparationMs={};
async function prepareTransition(root,name) {
  const started=performance.now(),parent=root.parent,materials=new Map();
  root.removeFromParent();root.traverse(o=>{for(const m of Array.isArray(o.material)?o.material:[o.material])if(m)materials.set(m,m.transparent);});
  try {
    root.updateMatrixWorld(true);
    for(const m of materials.keys())m.transparent=true;
    const fog=scene.fog;scene.fog=null;root.visible=true;
    let ready;
    try {ready=renderer.compileAsync(root,camera,scene);} finally {scene.fog=fog;root.visible=false;}
    await ready;
  } finally {for(const [m,transparent] of materials)m.transparent=transparent;root.visible=false;parent?.add(root);preparationMs[name]=performance.now()-started;}
}
async function prepareStage(root,name,fog=null) {
  const started=performance.now(),holder=new THREE.Scene();holder.fog=fog;holder.add(root);root.visible=true;
  try {
    const textures=new Set();root.traverse(object=>{for(const material of Array.isArray(object.material)?object.material:[object.material])if(material)for(const value of [...Object.values(material),...Object.values(material.userData||{})])if(value?.isTexture)textures.add(value);});
    let count=0;
    for(const texture of textures){renderer.initTexture(texture);if(++count%2===0)await new Promise(requestAnimationFrame);}
    holder.updateMatrixWorld(true);
    const materials=new Map();root.traverse(o=>{for(const m of Array.isArray(o.material)?o.material:[o.material])if(m)materials.set(m,m.transparent);});
    try {
      for(const stageFog of fog?[null,fog]:[null]){
        holder.fog=stageFog;
        for(const [m,transparent] of materials)m.transparent=transparent;
        await renderer.compileAsync(holder,camera);
        for(const m of materials.keys())m.transparent=true;
        await renderer.compileAsync(holder,camera);
      }
    } finally {for(const [m,transparent] of materials)m.transparent=transparent;}
  } finally {holder.remove(root);root.visible=false;preparationMs[name]=performance.now()-started;}
}
async function getSurface() {
  if (!surfacePromise)
    surfacePromise = import("./surface-stage.js")
      .then((module) => module.createSurface(data))
      .then(async(value) => {
        await prepareStage(value.root,"surface",new THREE.Fog("#778c8c",420,1800));
        await prepareTransition(value.root,"flight");
        surface = value;
        surface.root.visible = false;
        scene.add(surface.root);
        return value;
      })
      .catch((error) => {
        surfacePromise = null;
        throw error;
      });
  return surfacePromise;
}
async function getMine() {
  if (!minePromise)
    minePromise = import("./mine-stage.js")
      .then((module) => module.createMine(data))
      .then(async(value) => {
        await prepareStage(value.root,"mine");
        mine = value;
        mine.root.visible = false;
        scene.add(mine.root);
        return value;
      })
      .catch((error) => {
        minePromise = null;
        throw error;
      });
  return minePromise;
}
const learningCache = new Map(), learningLoads = new Map();
let learningRequest = 0, learningEntryTrigger = null;
async function getLearning(sourceMode = "recorded_synthetic") {
  if (learningCache.has(sourceMode)) return learningCache.get(sourceMode);
  if (!learningLoads.has(sourceMode)) {
    const promise = (sourceMode === "authored"
      ? import("./learning-stage.js").then((module) => module.createLearning(data))
      : Promise.all([import("./recorded-stage.js"), import("./recorded-data.js")])
          .then(async ([module, adapter]) => module.createRecorded(data, await adapter.loadExperiment(undefined, fetch, sourceMode === "reference" ? "reference-cycle-v1" : sourceMode === "curriculum" ? "curriculum-followup-v1" : null))))
      .then(async (value) => {
        await prepareStage(value.root,`learning-${sourceMode}`,new THREE.Fog("#061014",35,110));
        value.sourceMode = sourceMode;
        value.root.visible = false; scene.add(value.root);
        learningCache.set(sourceMode, value); return value;
      })
      .catch((error) => { learningLoads.delete(sourceMode); throw error; });
    learningLoads.set(sourceMode, promise);
  }
  return learningLoads.get(sourceMode);
}
function showInstruments(name, focus = false) {
  const recorded = document.body.dataset.learningSource !== "authored";
  const forecast = recorded && name === "forecast";
  learning?.forecast?.(forecast);
  $("policy-instruments").hidden = forecast;
  $("forecast-instruments").hidden = !forecast;
  for (const id of ["policy", "forecast"]) {
    const selected = (id === "forecast") === forecast, button = $(id + "-tab");
    button.setAttribute("aria-selected", String(selected));
    button.tabIndex = selected ? 0 : -1;
    if (selected && focus) button.focus();
  }
  $("learning-section-label").textContent = forecast ? "World model" : document.body.dataset.learningSource === "reference" ? "Reference simulator" : "Reinforcement learning";
  $("learning-title").textContent = forecast ? "Raw dynamics" : document.body.dataset.learningSource === "reference" ? "Reference cycle" : document.body.dataset.learningSource === "curriculum" ? "Partial pickup" : recorded ? "Policy checkpoints" : "Scoop and haul";
}
function configureLearningUI(sourceMode) {
  const recorded = sourceMode !== "authored";
  document.body.dataset.learningSource = sourceMode;
  $("learning-source").value = sourceMode;
  $("policy-tab").textContent=sourceMode === "reference" ? "Controller" : "Policy";
  $("replay-training").textContent=sourceMode === "reference" ? "Replay cycle" : sourceMode === "curriculum" ? "Replay study" : "Replay training";
  document.querySelectorAll("[data-recorded]").forEach((element) => { element.hidden = !recorded; });
  $("learning-source-label").textContent = recorded ? "Recorded synthetic · full-7" : "Illustrative training replay";
  $("reward-curve-label").textContent = recorded ? "Training mean reward" : "Reward";
  $("curve-y-axis").removeAttribute("title"); $("curve-y-axis").removeAttribute("aria-label");
  $("curve-y-axis").textContent=recorded?"Mean step reward":"Reward / relative";
  $("curve-x-axis").textContent=recorded?"Environment decisions":"Represented episodes";
  $("reward-heading").textContent = recorded ? "Step reward" : "Reward";
  $("episode-caption").textContent = recorded ? "completed training episodes" : "represented episodes";
  showInstruments("policy");
  $("caption-detail").textContent = recorded ? "Recorded synthetic experiment. Mine figures illustrative." : "Illustrative training replay.";
  document.querySelectorAll("[data-checkpoint]").forEach((button, index) => {
    button.textContent = recorded ? ["Initial", "Intermediate", "Final"][index] : ["Early", "Learning", "Trained"][index];
  });
  if (recorded) learning.mount();
  else {
    $("observation-value").textContent = "Geometry + machine pose";
    $("reward-explanation").textContent = "Ore − spillage − delay";
    $("reward-chart").setAttribute("aria-label", "Illustrative reward improvement over training");
    $("reward-point").style.visibility = "visible";
    $("reward-path").setAttribute("d", rewardPoints.map((p, i) => `${i ? "L" : "M"}${p[0]} ${p[1]}`).join(" "));
  }
}
function errorStatus(message) {
  $("flight-label").hidden = false;
  $("flight-label").textContent = message;
}
async function beginFlight() {
  if(stage!=="select" || !data.environments[environment].available)return;
  setStage("preparing");homeHandoff=null;cameraMove=null;
  showOnly(null);$("globe-label").hidden=true;errorStatus("Preparing Rwanda");
  const curtain=$("scene-curtain");curtain.classList.add("covered");
  try{
    await Promise.all([getSurface(),new Promise(resolve=>setTimeout(resolve,reduced?0:460))]);
    if(stage!=="preparing")return;
    arrive();
    requestAnimationFrame(()=>requestAnimationFrame(()=>curtain.classList.remove("covered")));
  }catch(error){
    setStage("select");showOnly("selector");globe.visible(true);curtain.classList.remove("covered");
    errorStatus("Terrain unavailable. Please try again.");$("deploy-underground").focus({preventScroll:true});
    console.warn("Surface preparation failed",error.message);
  }
}

function arrive() {
  transition = null;
  cameraMove = null;
  globe.visible(false);
  globe.sun.intensity = 0;
  surface.root.position.set(0, 0, 0);
  surface.root.quaternion.identity();
  surface.root.scale.setScalar(1);
  fade(surface.root, 1);
  camera.position.fromArray(data.assets.surface.camera);
  lookTarget.fromArray(data.assets.surface.target);
  camera.fov = 43;
  camera.near = 0.5;
  camera.far = 9000;
  viewport("surface");
  camera.updateProjectionMatrix();
  camera.lookAt(lookTarget);
  scene.background=new THREE.Color("#778c8c");
  scene.fog = new THREE.Fog("#778c8c", 420, 1800);
  setStage("surface");
  showOnly("surface-panel");
  $("skip-transition").hidden = true;
  $("flight-label").hidden = true;
  $("nav-location").textContent = "Rutongo / Rwanda";
  getMine().catch(() => {});
}
function mineView() {
  surface.root.visible = false;
  globe.visible(false);
  mine.root.visible = true;
}
async function enterMine() {
  if (stage !== "surface") return;
  if (mineNeedsReload) { location.reload(); return; }
  const button = $("enter-mine");
  button.disabled = true;
  button.textContent = "Preparing the mine";
  let nextTransition;
  try {
    const entrance = data.visuals?.entrance;
    const alignment = data.mine.network.nodes.find(node => node.id === entrance?.portal_alignment_node);
    const vector = value => Array.isArray(value) && value.length === 3 && value.every(Number.isFinite);
    if (!entrance || !vector(entrance.approach_offset_m) || !vector(entrance.approach_target_offset_m) || !vector(alignment?.position_m)) {
      mineNeedsReload = true;
      throw new Error("Mine entrance settings are unavailable");
    }
    await getMine();
    await prepareTransition(mine.root,"entrance");
    // Complete preparation before hiding the surface or committing a new stage.
    const portal = surface.portal.clone();
    nextTransition = {
      type: "entrance",
      background: scene.background.clone(),
      sectionOffset: new THREE.Vector3(portal.x - alignment.position_m[0], 0, portal.z - alignment.position_m[2]),
      approachPosition: portal.clone().add(new THREE.Vector3(...entrance.approach_offset_m)),
      approachTarget: portal.clone().add(new THREE.Vector3(...entrance.approach_target_offset_m)),
      start: performance.now(),
      duration: duration(data.timing.entrance_seconds) * 1000,
      fromPosition: camera.position.clone(),
      fromTarget: lookTarget.clone(),
    };
  } catch (error) {
    button.disabled = false;
    button.textContent = mineNeedsReload ? "Reload experience" : "Try again";
    errorStatus(mineNeedsReload
      ? "Mine view unavailable. Reload the experience to try again."
      : "Mine assets unavailable. Please try again.");
    console.warn("Mine transition preparation failed:", error);
    return;
  }
  $("surface-panel").hidden = true;
  $("flight-label").hidden = true;
  fade(mine.root, 0);
  mine.root.position.copy(nextTransition.sectionOffset);
  transition = nextTransition;
  scene.fog = null;
  setStage("entering");
  viewport("mine");
}
function mineArrived() {
  transition = null;
  fade(surface.root, 0);
  mineView();
  fade(mine.root, 1);
  mine.root.position.set(0,0,0);
  mine.setTrained(false);
  mine.setScan(0);
  scene.background.set("#030506");
  camera.near = 2;
  camera.far = 2000;
  camera.updateProjectionMatrix();
  setStage("mine");
  viewport();
  showOnly("operations");
  setMetrics(false);
  $("enter-mine").disabled = false;
  $("enter-mine").textContent = "Enter the mine";
  $("flight-label").hidden = true;
}
function operationValues(trained) {
  const o = data.operations,
    v = trained ? o.after : o.before;
  const throughput =
    ((o.fleet_size * o.payload_t * 60) / v.cycle_minutes) * v.utilisation;
  const hours = o.batch_t / throughput;
  const hourly = o.fleet_size * v.machine_cost_hour + o.overhead_gbp_hour;
  const baselineRate =
    ((o.fleet_size * o.payload_t * 60) / o.before.cycle_minutes) *
    o.before.utilisation;
  const baseHours = o.batch_t / baselineRate;
  const baseCost =
    baseHours *
    (o.fleet_size * o.before.machine_cost_hour + o.overhead_gbp_hour);
  return {
    throughput,
    hours,
    hourly,
    cost: hourly / throughput,
    schedule: (o.planned_batch_hours - hours) * 60,
    idle: v.idle_percent,
    savedMoney: trained ? baseCost - hours * hourly : 0,
    savedMinutes: trained ? (baseHours - hours) * 60 : 0,
  };
}
const money = (value) =>
  new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    maximumFractionDigits: 0,
  }).format(value);
function timeValue(minutes) {
  const m = Math.round(Math.abs(minutes)),
    h = Math.floor(m / 60);
  return h ? `${h}h${m % 60 ? String(m % 60).padStart(2, "0") : ""}` : `${m}`;
}
function setMetrics(trained) {
  const v = operationValues(trained),
    b = operationValues(false);
  $("value-throughput").innerHTML =
    `${Math.round(v.throughput)} <small>t/h</small>`;
  $("value-schedule").innerHTML =
    `${timeValue(v.schedule)} <small>${v.schedule >= 0 ? "ahead" : "late"}</small>`;
  $("value-idle").innerHTML = `${v.idle}<small>%</small>`;
  $("value-cost").innerHTML = `£${v.cost.toFixed(2)}<small>/t</small>`;
  $("value-money").textContent = money(v.savedMoney);
  $("value-time").innerHTML =
    `${timeValue(v.savedMinutes)}<small>${v.savedMinutes >= 60 ? "" : "min"}</small>`;
  $("delta-throughput").textContent = trained
    ? `From ${Math.round(b.throughput)} t/h`
    : "Below shift plan";
  $("delta-schedule").textContent = trained
    ? "Same target"
    : "Ore movement delayed";
  $("delta-idle").textContent = trained
    ? `${b.idle - v.idle} pp less`
    : "Machines waiting";
  $("delta-cost").textContent = trained
    ? `£${(b.cost - v.cost).toFixed(2)} less per tonne`
    : "Illustrative machine costs";
  $("comparison-state").textContent = trained ? "Trained site" : "Baseline";
  $("operations").classList.toggle("trained", trained);
  $("local-status").textContent = trained ? "No GPS · onboard" : "No GPS";
  $("show-before").setAttribute("aria-pressed", String(!trained));
  $("show-after").setAttribute("aria-pressed", String(trained));
}
function compare(trained = true) {
  if (!["mine", "trained"].includes(stage) || trained === comparison) return;
  mineView();
  setStage("comparing");
  $("operations").classList.add("comparing");
  $("compare-trained").disabled = true;
  $("show-before").disabled = true;
  $("show-after").disabled = true;
  transition = {
    type: "compare",
    start: performance.now(),
    duration:
      duration(trained ? data.timing.model_glimpse_seconds : 1.0) * 1000,
    trained,
    switched: false,
  };
  if (trained) $("model-transition").hidden = false;
  viewport("comparing");
}
function comparisonDone(trained) {
  mineView();
  transition = null;
  comparison = trained;
  mine.setScan(0);
  $("operations").classList.remove("comparing");
  setMetrics(trained);
  $("model-transition").hidden = true;
  setStage(trained ? "trained" : "mine");
  viewport();
  $("comparison-switch").hidden = false;
  $("compare-trained").hidden = true;
  $("show-before").disabled = false;
  $("show-after").disabled = false;
  $("explore-world-model").hidden = false;
  $("scroll-product").hidden = false;
  $("product").hidden = false;
  document.body.classList.remove("story-locked");
}
function updateTransition(now) {
  if (!transition) return;
  const tr = transition,
    p = THREE.MathUtils.clamp((now - tr.start) / tr.duration, 0, 1),
    ease = p * p * (3 - 2 * p);
  if (tr.type === "flight") {
    const split = 0.55;
    if (p < split) {
      const t = p / split,
        e = t * t * (3 - 2 * t);
      globe.earth.rotation.y = THREE.MathUtils.lerp(
        tr.earthFrom,
        tr.earthAngle,
        e,
      );
      camera.position.lerpVectors(tr.fromPosition, tr.mountCamera, e);
      lookTarget.lerpVectors(tr.fromTarget, tr.mountPosition, e);
      camera.fov = THREE.MathUtils.lerp(34, 42, e);
    } else {
      const t = (p - split) / (1 - split),
        e = t * t * (3 - 2 * t),
        scale = Math.exp(THREE.MathUtils.lerp(Math.log(tr.scale), 0, e));
      fade(surface.root, THREE.MathUtils.smoothstep(t, 0, 0.45));
      surface.root.position.copy(tr.mountPosition).multiplyScalar(1 - e);
      surface.root.quaternion
        .copy(tr.mountRotation)
        .slerp(new THREE.Quaternion(), e);
      surface.root.scale.setScalar(scale);
      const local = tr.far
        .clone()
        .lerp(new THREE.Vector3(...data.assets.surface.camera), e);
      camera.position
        .copy(local)
        .multiplyScalar(scale)
        .applyQuaternion(surface.root.quaternion)
        .add(surface.root.position);
      lookTarget.copy(
        new THREE.Vector3(...data.assets.surface.target)
          .multiplyScalar(scale)
          .applyQuaternion(surface.root.quaternion)
          .add(surface.root.position),
      );
      globeFade(1 - THREE.MathUtils.smoothstep(t, 0, 0.28));
      camera.near = Math.max(0.00005, scale * 0.15);
      scene.background.lerp(new THREE.Color("#778c8c"), Math.min(1, t * 0.12));
    }
    camera.updateProjectionMatrix();
    camera.lookAt(lookTarget);
    if (p === 1) arrive();
  } else if (tr.type === "entrance") {
    const pullback=THREE.MathUtils.smoothstep(p,.16,1);
    const approach=THREE.MathUtils.smoothstep(p,0,.52);
    camera.position.lerpVectors(tr.fromPosition,tr.approachPosition,approach)
      .lerp(new THREE.Vector3(...data.mine.camera),pullback);
    lookTarget.lerpVectors(tr.fromTarget,tr.approachTarget,approach)
      .lerp(new THREE.Vector3(...data.mine.target),pullback);
    mine.root.position.copy(tr.sectionOffset).multiplyScalar(1-pullback);
    camera.fov = THREE.MathUtils.lerp(43, 40, ease);
    camera.updateProjectionMatrix();
    camera.lookAt(lookTarget);
    const reveal = THREE.MathUtils.smoothstep(p, .18, .8);
    fade(surface.root, 1 - reveal);
    fade(mine.root, reveal);
    scene.background.copy(tr.background).lerp(new THREE.Color("#030506"), ease);
    if (p === 1) mineArrived();
  } else if (tr.type === "compare") {
    mine.setScan(ease);
    if (!tr.switched && p > 0.55) {
      tr.switched = true;
      mine.setTrained(tr.trained);
      setMetrics(tr.trained);
    }
    if (p === 1) comparisonDone(tr.trained);
  }
}
async function openLearning(requestedMode = "recorded_synthetic") {
  if (!mine) return;
  const sourceMode = typeof requestedMode === "string" ? requestedMode : "recorded_synthetic";
  if (!["recorded_synthetic", "reference", "curriculum", "authored"].includes(sourceMode)) return;
  const request = ++learningRequest, alreadyOpen = stage === "learning", button = document.activeElement;
  if (!alreadyOpen && ["explore-world-model", "product-world-model"].includes(button?.id)) learningEntryTrigger = button;
  if (button?.tagName === "BUTTON") button.disabled = true;
  let value;
  try { value = await getLearning(sourceMode); }
  catch (error) {
    if (button) button.disabled = false;
    if (request !== learningRequest) return;
    $("experiment-error-message").textContent = `${error.message}. Retry or choose the labelled concept replay.`;
    $("experiment-error").hidden = false;
    $("retry-recorded").dataset.source=sourceMode;
    if (learning) $("learning-source").value = learning.sourceMode;
    if (button) button.disabled = false;
    return;
  }
  if (button) button.disabled = false;
  if (request !== learningRequest) return;
  $("experiment-error").hidden = true;
  if (!alreadyOpen) entryContext = {
    stage, scroll: scrollY, camera: camera.position.clone(), target: lookTarget.clone(),
    fov: camera.fov, kitActive, trigger: learningEntryTrigger || button,
  };
  if (learning) learning.root.visible = false;
  learning = value;
  setStage("learning");
  mine.root.visible = false;
  if (surface) surface.root.visible = false;
  if (kit) kit.root.visible = false;
  scene.environment = null; globe.visible(false);
  learning.root.visible = true;learning.replay();
  $("product").style.visibility = "hidden";$("experience").style.visibility = "hidden";
  $("navigation").hidden = true;$("learning-ui").hidden = false;
  configureLearningUI(sourceMode);
  document.body.classList.add("story-locked");
  scene.background.set("#061014");scene.fog = new THREE.Fog("#061014", 35, 110);
  camera.near = 0.05;camera.far = 300;camera.fov = 42;
  camera.position.fromArray(learning.camera || data.training.camera);
  lookTarget.fromArray(learning.target || data.training.target);
  viewport("learning");camera.lookAt(lookTarget);
  $("exit-world-model").textContent = entryContext.scroll > innerHeight * 0.5 ? "← Return to product" : "← Return to mine";
  cameraMove = null;hudTime = 0;updateLearning(0);
  if (!alreadyOpen) $("exit-world-model").focus({ preventScroll: true });
}
function closeLearning() {
  if (stage !== "learning") return;
  learningRequest++;
  learning.root.visible = false;
  $("experiment-error").hidden = true;
  $("learning-ui").hidden = true;
  $("product").style.visibility = "";
  $("experience").style.visibility = "";
  $("navigation").hidden = false;
  document.body.classList.remove("story-locked");
  $("caption-detail").textContent = "Public geography. Illustrative mission.";
  setStage(entryContext.stage);
  scene.fog = null;
  scene.background.set("#030506");
  camera.position.copy(entryContext.camera);
  lookTarget.copy(entryContext.target);
  camera.fov = entryContext.fov;
  camera.near = 2;
  camera.far = 2000;
  viewport(stage);
  camera.lookAt(lookTarget);
  window.scrollTo({ top: entryContext.scroll, behavior: "instant" });
  mine.root.visible = !entryContext.kitActive;
  updateProduct();
  entryContext.trigger?.focus({ preventScroll: true });
  learningEntryTrigger = null;
  delete document.body.dataset.learningSource;
}
let rewardPoints = [];
function updateLearning(delta) {
  if (learning.sourceMode !== "authored") { learning.update(delta); return; }
  const state = learning.update(delta),
    checkpoint = data.training.checkpoints[state.index];
  if (globalTime - hudTime < 95) return;
  hudTime = globalTime;
  $("episode-count").textContent = state.episodes.toLocaleString("en-GB");
  $("reward-value").textContent = checkpoint.reward.toFixed(2);
  $("action-value").textContent = state.action;
  $("policy-value").textContent = checkpoint.name;
  $("checkpoint-outcome").textContent = checkpoint.outcome;
  $("payload-readout").textContent =
    `Payload ${state.load_t.toFixed(1)} / ${data.training.capacity_t} t`;
  $("training-status").textContent = state.paused
    ? "Replay paused"
    : state.running
      ? "Accelerated imagined rollouts"
      : "Policy checkpoint replay";
  $("pause-training").textContent = learning.running ? "Pause" : "Play";
  document
    .querySelectorAll("[data-checkpoint]")
    .forEach((button, index) =>
      button.classList.toggle("active", index === state.index),
    );
  const index = Math.min(
      rewardPoints.length - 1,
      Math.floor(state.progress * (rewardPoints.length - 1)),
    ),
    point = rewardPoints[index];
  if (point) {
    $("reward-point").setAttribute("cx", point[0]);
    $("reward-point").setAttribute("cy", point[1]);
  }
}
async function ensureKit() {
  if (kit) return kit;
  if (kitPromise) return kitPromise;
  kitPromise = Promise.all([
    import("./retrofit-stage.js"),
    studioEnvironment(data.kit.lighting),
  ])
    .then(([module, environment]) => {
      kit = module.createRetrofit(data);
      kitEnvironment = environment;
      scene.add(kit.root);
      kit.root.visible = false;
      for (const component of data.kit.components) {
        const button = document.createElement("button");
        button.textContent = component.name;
        button.title = component.description;
        button.addEventListener("mouseenter", () => kit.focus(component.id));
        button.addEventListener("focus", () => kit.focus(component.id));
        button.addEventListener("mouseleave", () => kit.focus(null));
        button.addEventListener("blur", () => kit.focus(null));
        $("kit-components").append(button);
      }
      return kit;
    })
    .catch((error) => {
      kitPromise = null;
      throw error;
    });
  return kitPromise;
}
function updateProduct() {
  if (
    !mine ||
    stage === "learning" ||
    !["mine", "trained"].includes(stage) ||
    $("product").hidden
  )
    return;
  if (scrollY > innerHeight * 0.25 && !kit && !kitPromise)
    ensureKit().catch(() =>
      errorStatus("Kit assets unavailable. Please try again."),
    );
  const rect = $("kit-window").getBoundingClientRect();
  const visible =
    rect.top < innerHeight * 0.85 && rect.bottom > innerHeight * 0.15;
  if (visible && !kit) {
    ensureKit().then(updateProduct);
    return;
  }
  kitActive = visible && !!kit;
  $("journey").hidden = scrollY > innerHeight * .25;
  if (kitActive) {
    scene.environment = kitEnvironment;
    mine.root.visible = false;
    kit.root.visible = true;
    scene.background.set("#030506");
    scene.fog = null;
    camera.position.fromArray(data.kit.camera);
    lookTarget.set(0, kitExploded ? 2 : 0.7, 0);
    const distance = camera.position.distanceTo(lookTarget);
    camera.fov = THREE.MathUtils.radToDeg(
      2 *
        Math.atan(
          ((4.1 / distance) * innerHeight) / Math.max(300, rect.height),
        ),
    );
    camera.near = 0.05;
    camera.far = 120;
    camera.clearViewOffset();
    camera.setViewOffset(
      innerWidth,
      innerHeight,
      innerWidth / 2 - (rect.left + rect.width / 2),
      innerHeight / 2 - (rect.top + rect.height / 2),
      innerWidth,
      innerHeight,
    );
    camera.updateProjectionMatrix();
    camera.lookAt(lookTarget);
  } else {
    scene.environment = null;
    if (kit) kit.root.visible = false;
    if (scrollY < innerHeight * 0.95) {
      mine.root.visible = true;
      scene.background.set("#030506");
      scene.fog = null;
      camera.position.fromArray(data.mine.camera);
      lookTarget.fromArray(data.mine.target);
      camera.fov = 40;
      camera.near = 2;
      camera.far = 2000;
      viewport();
      camera.lookAt(lookTarget);
    } else mine.root.visible = false;
  }
}
function resize() {
  renderer.setSize(innerWidth, innerHeight, false);
  quality = Math.min(devicePixelRatio || 1, 1.5);
  renderer.setPixelRatio(quality);
  camera.aspect = innerWidth / innerHeight;
  viewport();
  if(stage === "welcome") {
    cameraMove=null;camera.position.fromArray(data?.visuals.home.camera || [0,0,12.8]);lookTarget.set(0,0,0);camera.lookAt(lookTarget);
  }
  if(stage === "select") {
    homeHandoff=null;cameraMove=null;globe?.mode("select");camera.position.set(0,0,12.8);lookTarget.set(0,0,0);camera.lookAt(lookTarget);
  }
  updateProduct();
}
function pinLabel() { $("globe-label").hidden=true; }
function drawScene(now) {
  renderer.setScissorTest(false);renderer.setViewport(0,0,innerWidth,innerHeight);
  if(["select","preparing"].includes(stage)) {
    scene.background=null;renderer.setClearColor(0x000000,0);renderer.clear();
    const frame=$("orbit-panel").querySelector(".orbit-frame").getBoundingClientRect();
    if(frame.width>0)selectorRect={left:frame.left,top:frame.top,width:frame.width,height:frame.height};
    let rect=selectorRect || {left:innerWidth-320,top:innerHeight*.3,width:260,height:260};
    if(homeHandoff){
      const t=Math.min(1,(now-homeHandoff.start)/homeHandoff.duration),q=t*t*(3-2*t);
      rect={left:rect.left*q,top:rect.top*q,width:THREE.MathUtils.lerp(innerWidth,rect.width,q),height:THREE.MathUtils.lerp(innerHeight,rect.height,q)};
      globe.root.position.copy(homeHandoff.fromPosition).multiplyScalar(1-q);
      if(t===1)homeHandoff=null;
    }
    const y=innerHeight-rect.top-rect.height;
    camera.aspect=rect.width/rect.height;camera.clearViewOffset();camera.updateProjectionMatrix();camera.lookAt(lookTarget);
    renderer.setViewport(rect.left,y,rect.width,rect.height);renderer.setScissor(rect.left,y,rect.width,rect.height);renderer.setScissorTest(true);
    globe.lod?.(camera);renderer.render(scene,camera);renderer.setScissorTest(false);renderer.setViewport(0,0,innerWidth,innerHeight);
  }else{renderer.setClearColor(0x030506,1);globe?.lod?.(camera);renderer.render(scene,camera);}
}

async function init() {
  try {
    const response = await fetch("data/experience.json", { cache: "no-store" });
    if (!response.ok) throw new Error("Experience data unavailable");
    data = await response.json();
    const study=new URLSearchParams(location.search).get("home-study");
    if(study === "instrument"){document.body.dataset.homeDirection="instrument";data.visuals.home.earth_x=2.05;document.querySelector(".welcome-wordmark").src="assets/brand/kessel-instrument.svg";}
    globe = createGlobe(scene, data);
    environmentScenes=createEnvironmentScenes(data);
    globe.earth.rotation.y = -THREE.MathUtils.degToRad(
      data.location.longitude + 90,
    );
    await globe.load();
    environmentScenes.warm(0);
    await renderer.compileAsync(scene,camera);
    const images=await fetch("assets/environments/manifest.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("Environment references unavailable");return r.json();});
    for(const image of images.images){
      const li=document.createElement("li"),link=document.createElement("a");
      li.append(document.createTextNode(image.credit+". "+image.subject+". "));
      link.href=image.page;link.textContent="Free source";link.target="_blank";link.rel="noopener";li.append(link);$("environment-sources").append(li);
    }
    for (const [index, concept] of data.training.concepts.entries())
      document.querySelectorAll(".rl-readouts>div")[index].title =
        concept.description;
    document.body.classList.add("ready");
    $("start-experience").disabled = false;
    $("start-experience").textContent = "Enter experience ↗";
    const points = [];
    for (let i = 0; i < 90; i++) {
      const t = i / 89,
        y = THREE.MathUtils.clamp(
          0.07 +
            t * 0.88 +
            0.035 * Math.sin(i * 1.9) -
            0.03 * Math.sin(i * 0.36),
          0,
          1,
        );
      points.push([(i / 89) * 300, 68 - y * 62]);
    }
    rewardPoints = points;
    $("reward-path").setAttribute(
      "d",
      points
        .map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`)
        .join(" "),
    );
    resize();
    if(!reduced){camera.position.fromArray(data.visuals.home.arrival_camera);cameraTo(data.visuals.home.camera,[0,0,0],data.visuals.home.arrival_seconds,34);}
  } catch (error) {
    $("start-experience").textContent = "Reload to try again";
    $("start-experience").disabled = false;
    $("start-experience").onclick = () => location.reload();
    console.error(error);
  }
}
function render(now) {
  requestAnimationFrame(render);
  globalTime = now;
  const ms = lastTime ? now - lastTime : 0,
    delta = lastTime ? Math.min(ms / 1000, 0.1) : 0;
  lastTime = now;
  if (document.hidden) return;
  if (ms) {
    frameTimes.push(ms);
    if (frameTimes.length > 180) frameTimes.shift();
    qualityFrames.push(ms);
    if (qualityFrames.length >= 30) {
      const mean =
        qualityFrames.reduce((a, b) => a + b, 0) / qualityFrames.length;
      const cap = Math.min(devicePixelRatio || 1, 1.5);
      let next = quality;
      if (mean > 35) next = Math.max(0.75, quality * 0.85);
      else if (mean < 20) next = Math.min(cap, quality * 1.08);
      if (mean > 40 && next <= .85) setVisualQuality("low");
      if (next !== quality) {
        quality = next;
        renderer.setPixelRatio(next);
      }
      qualityFrames = [];
    }
  }
  if (globe && ["welcome", "select", "flight", "preparing"].includes(stage)) {
    if (stage === "select") {
      if (earthGoal !== null) {
        globe.earth.rotation.y = THREE.MathUtils.damp(globe.earth.rotation.y,earthGoal,3,delta);
        if(Math.abs(globe.earth.rotation.y-earthGoal)<.002){globe.earth.rotation.y=earthGoal;earthGoal=null;}
      }
    }
    globe.update(reduced?0:now,reduced?0:delta,!reduced&&(stage==="welcome"||(stage==="select"&&earthGoal===null)));
  }
  updateCamera(now);
  updateTransition(now);
  if (
    mine?.root.visible &&
    ["mine", "trained", "entering", "comparing"].includes(stage)
  )
    mine.update(delta);
  if (stage === "learning" && learning)
    updateLearning(learning.sourceMode !== "authored" ? ms / 1000 : delta);
  if (kitActive && kit) kit.update(delta);
  pinLabel();
  drawScene(now);
}
for (const name of ["policy", "forecast"]) {
  const button = $(name + "-tab");
  button.addEventListener("click", () => showInstruments(name));
  button.addEventListener("keydown", event => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    showInstruments(event.key === "Home" ? "policy" : event.key === "End" ? "forecast" : name === "policy" ? "forecast" : "policy", true);
  });
}
$("start-experience").addEventListener("click", start);
$("environment-prev").addEventListener("click", () =>
  chooseEnvironment(environment - 1),
);
$("environment-next").addEventListener("click", () =>
  chooseEnvironment(environment + 1),
);
$("deploy-underground").addEventListener("click", beginFlight);
$("skip-transition").addEventListener("click", () => {
  if (transition?.type === "flight") arrive();
});
$("enter-mine").addEventListener("click", enterMine);
$("compare-trained").addEventListener("click", () => compare(true));
$("show-before").addEventListener("click", () => compare(false));
$("show-after").addEventListener("click", () => compare(true));
$("explore-world-model").addEventListener("click", openLearning);
$("product-world-model").addEventListener("click", openLearning);
$("exit-world-model").addEventListener("click", closeLearning);
$("learning-source").addEventListener("change", (event) => openLearning(event.target.value));
$("retry-recorded").addEventListener("click", () => openLearning($("retry-recorded").dataset.source || "recorded_synthetic"));
$("use-concept-replay").addEventListener("click", () => openLearning("authored"));
$("replay-scrub").addEventListener("input", (event) => learning?.seek?.(Number(event.target.value)));
$("replay-pace").addEventListener("change", (event) => learning?.pace?.(Number(event.target.value)));
$("forecast-horizon").addEventListener("change", (event) => learning?.horizon?.(Number(event.target.value)));
$("previous-event").addEventListener("click", () => learning?.event?.(-1));
$("next-event").addEventListener("click", () => learning?.event?.(1));
$("inspect-forecast").addEventListener("click", () => learning?.inspect?.());
$("replay-training").addEventListener("click", () => {
  if (learning) {
    learning.replay();
    hudTime = 0;
    updateLearning(0);
  }
});
$("pause-training").addEventListener("click", () => {
  if (learning) {
    learning.pause();
    hudTime = 0;
    updateLearning(0);
  }
});
document.querySelectorAll("[data-checkpoint]").forEach((button) =>
  button.addEventListener("click", () => {
    if (learning) {
      learning.checkpoint(Number(button.dataset.checkpoint));
      hudTime = 0;
      updateLearning(0);
    }
  }),
);
$("assemble-kit").addEventListener("click", () => {
  if (!kit) return;
  kitExploded = kit.toggle();
  $("assemble-kit").textContent = kitExploded
    ? "Assemble the kit"
    : "Explode the kit";
  updateProduct();
});
$("scroll-product").addEventListener("click", () =>
  $("product-overview").scrollIntoView({
    behavior: reduced ? "instant" : "smooth",
  }),
);
for (const id of ["restart", "replay-experience"])
  $(id).addEventListener("click", () => location.reload());
for (const id of ["sources-open", "caption-sources"])
  $(id)?.addEventListener("click", () => $("sources-dialog").showModal());
$("sources-close").addEventListener("click", () => $("sources-dialog").close());
document.addEventListener("keydown", (event) => {
  if ($("sources-dialog").open) return;
  if (event.key === "Escape" && stage === "learning") closeLearning();
  if (stage === "select" && event.key === "ArrowRight")
    chooseEnvironment(environment + 1);
  if (stage === "select" && event.key === "ArrowLeft")
    chooseEnvironment(environment - 1);
});
document.addEventListener("visibilitychange", () => {
  lastTime = 0;
});
window.addEventListener("resize", resize, { passive: true });
window.addEventListener("scroll", updateProduct, { passive: true });
init();
resize();
requestAnimationFrame(render);
export function diagnostics() {
  const gl = renderer.getContext(),
    debug = gl.getExtension("WEBGL_debug_renderer_info");
  const authoredAssets=new Set();scene.traverse(o=>{const path=o.userData.authoredAsset||o.userData.assetPath;if(path)authoredAssets.add(path);});
  return {
    authoredAssets:[...authoredAssets],
    preparationMs:{...preparationMs},
    stage,
    camera: {position:camera.position.toArray(),fov:camera.fov,moving:cameraMove!==null},
    earthSettling:earthGoal!==null,
    globe: globe?.diagnostics?.() ?? null,
    environmentBackground:environmentScenes?.diagnostics() || null,
    homeHandoff:homeHandoff!==null,
    selectorViewport:selectorRect,
    presentation: document.querySelector('meta[name="kessel-presentation"]')?.content || "unversioned",
    scenes: {earth:globe?.root.visible ?? false,surface:surface?.root.visible ?? false,mine:mine?.root.visible ?? false,kit:kit?.root.visible ?? false},
    environment: data?.environments[environment].id,
    comparison,
    scrollY,
    kitActive,
    learning: stage === "learning" ? learning?.diagnostics?.() || { sourceMode: "authored" } : null,
    drawCalls: renderer.info.render.calls,
    triangles: renderer.info.render.triangles,
    textures: renderer.info.memory.textures,
    shadows: renderer.shadowMap.enabled,
    shadowUpdate: renderer.shadowMap.autoUpdate ? "dynamic" : "static",
    pixelRatio: renderer.getPixelRatio(),
    heapUsedBytes: performance.memory?.usedJSHeapSize ?? null,
    meanFps: frameTimes.length
      ? 1000 / (frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length)
      : null,
    p99FrameMs: [...frameTimes].sort((a,b)=>a-b)[Math.floor(frameTimes.length*.99)],
    p95FrameMs: [...frameTimes].sort((a, b) => a - b)[
      Math.floor(frameTimes.length * 0.95)
    ],
    renderer: debug
      ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL)
      : "not exposed",
  };
}

// Presentation-only quality control for repeatable native visual acceptance.
export function setVisualEffects(enabled) { mine?.setEffects(Boolean(enabled)); }
const shadowDefaults = new WeakMap();
export function setVisualQuality(tier = "standard") {
  // Keep a static geology shadow field in the cheaper tier. Existing contact
  // shadows ground vehicles without recompiling the lit material programmes.
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.autoUpdate = tier !== "low";
  renderer.shadowMap.needsUpdate = true;
  scene.traverse(object=>{
    if(!object.isMesh)return;
    let moving=Boolean(object.userData.vehicleId),parent=object.parent;
    while(parent&&!moving){moving=parent.name==="licensed-loading-excavator";parent=parent.parent;}
    if(!moving)return;
    if(!shadowDefaults.has(object))shadowDefaults.set(object,object.castShadow);
    object.castShadow=tier!=="low"&&shadowDefaults.get(object);
  });
  mine?.setEffects(tier !== "low");
}
