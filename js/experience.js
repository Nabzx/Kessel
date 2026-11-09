import {createSurfaceFilm} from "./surface-film.js";
import {installChapters} from "./technical-chapters.js";
import * as THREE from "three";
import { createGlobe } from "./globe-stage.js";
import { createEnvironmentScenes } from "./environment-scenes.js";
import { studioEnvironment } from "./scene-utils.js";

const $ = (id) => document.getElementById(id);
const motionPreference=matchMedia("(prefers-reduced-motion: reduce)");
let reduced=motionPreference.matches;
motionPreference.addEventListener("change",event=>{reduced=event.matches;if(reduced&&transition)transition.start=performance.now()-transition.duration;});
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
let data, globe, surface, mine, learning, kit, environmentScenes,technicalChapters;
const surfaceFilm=createSurfaceFilm(()=>{if(surface&&stage==="surface")surface.root.visible=true;});
const chapterIds=["earth","environments","surface","mine","training","inside","retrofit"];
let chapter="earth",chapterRequest=0,chapterBusy=false,mineVisited=false;
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
  kitExploded = 0,
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
  const mapped={welcome:"earth",select:"environments",surface:"surface",mine:"mine",trained:"mine",learning:"training",inside:"inside",retrofit:"retrofit"}[next];
  if(mapped){chapter=mapped;document.body.dataset.chapter=chapter;updateRail();}
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
function start(){if(data)navigateChapter("environments");}
function updateRail(){
 const buttons=[...$("chapter-rail").querySelectorAll("[data-scene]")];
 for(const b of buttons){if(b.dataset.scene===chapter)b.setAttribute("aria-current","step");else b.removeAttribute("aria-current");}
 $("rail-index").textContent=`${String(chapterIds.indexOf(chapter)+1).padStart(2,"0")} / 07`;
}
function navigationInert(value){for(const id of ["experience","product","learning-ui","navigation"])$(id).inert=value;}
async function navigateChapter(next){
 if(!data||!chapterIds.includes(next))return;
 if(next===chapter&&!chapterBusy)return;
 if(stage==="comparing"){mine.setTrained(comparison);comparisonDone(comparison);}
 const request=++chapterRequest;++handoffToken;++learningRequest;chapterBusy=true;navigationInert(true);
 transition=null;cameraMove=null;homeHandoff=null;
 const curtain=$("scene-curtain");curtain.classList.add("covered");
 $("chapter-rail").removeAttribute("data-error");$("chapter-rail").setAttribute("aria-busy","true");
 for(const b of $("chapter-rail").querySelectorAll("[data-scene]"))b.toggleAttribute("data-pending",b.dataset.scene===next);
 $("rail-state").textContent="Preparing chapter";
 try{
  const prepare=next==="surface"?Promise.all([getSurface(),surfaceFilm.prepare()]):next==="mine"?getMine():next==="training"?getLearning("authored"):next==="retrofit"?ensureKit():Promise.resolve();
  const [destination]=await Promise.all([prepare,presentationWait(reduced?0:300)]);
  if(request!==chapterRequest)return;
  surfaceFilm.hide();showOnly(null);globe.visible(false);
  for(const root of [surface?.root,mine?.root,learning?.root,kit?.root])if(root)root.visible=false;
  $("learning-ui").hidden=true;$("experience").style.visibility="";$("product").style.visibility="";
  $("product").hidden=!["inside","retrofit"].includes(next);$("navigation").hidden=false;
  $("globe-label").hidden=true;$("flight-label").hidden=true;$("skip-transition").hidden=true;$("model-transition").hidden=true;
  document.body.classList.add("story-locked");document.body.classList.remove("product-active");
  document.body.dataset.chapter=next;scene.environment=null;scene.fog=null;scene.background=new THREE.Color("#030506");kitActive=false;
  camera.near=.05;camera.far=2000;window.scrollTo(0,0);
  $("navigation").classList.toggle("started",next!=="earth");
  if(next==="earth"){
   setStage("welcome");globe.mode("welcome");globe.sun.intensity=data.visuals.home.sun_intensity;
   $("welcome").classList.remove("leaving");$("start-experience").disabled=false;showOnly("welcome");
   camera.position.fromArray(data.visuals.home.camera);lookTarget.set(0,0,0);camera.fov=34;viewport();$("nav-location").textContent="";
  }else if(next==="environments"){
   setStage("select");globe.mode("select");globe.sun.intensity=data.visuals.home.sun_intensity;
   showOnly("selector");chooseEnvironment(environment);camera.position.set(0,0,12.8);lookTarget.set(0,0,0);camera.fov=34;viewport();$("nav-location").textContent="Deployment environments";
   setTimeout(()=>{if(stage==="select")getSurface().catch(()=>{});},500);
  }else if(next==="surface"){
   arrive();surfaceFilm.show();surface.root.visible=document.body.classList.contains("surface-fallback");
  }else if(next==="mine"){
   if(!mineVisited){mine.setTrained(false);mine.setScan(0);mineVisited=true;}
   mine.root.visible=true;mine.root.position.set(0,0,0);setStage(comparison?"trained":"mine");showOnly("operations");setMetrics(comparison);
   camera.position.fromArray(data.mine.camera);lookTarget.fromArray(data.mine.target);camera.fov=40;camera.near=2;viewport();$("nav-location").textContent="Rutongo / underground";
   $("enter-mine").disabled=false;$("enter-mine").textContent="Enter the mine";
  }else if(next==="training"){
   learning=destination;learning.root.visible=true;setStage("learning");$("learning-ui").hidden=false;$("navigation").hidden=true;
   document.body.dataset.learningSource="authored";scene.background.set("#061014");scene.fog=new THREE.Fog("#061014",65,150);camera.fov=42;camera.far=300;viewport("learning");frameLearning();hudTime=0;updateLearning(0);
  }else if(next==="inside"){
   setStage("inside");$("nav-location").textContent="Inside Kessel";viewport();
  }else if(next==="retrofit"){
   setStage("retrofit");kitActive=true;kit.root.visible=true;scene.environment=kitEnvironment;$("nav-location").textContent="Proposed retrofit kit";updateProduct();
  }
  if(next!=="training")delete document.body.dataset.learningSource;
  camera.updateProjectionMatrix();camera.lookAt(lookTarget);lastTime=0;
  await new Promise(requestAnimationFrame);if(request!==chapterRequest)return;
  curtain.classList.remove("covered");chapterBusy=false;navigationInert(false);$("chapter-rail").removeAttribute("aria-busy");
  for(const b of $("chapter-rail").querySelectorAll("[data-scene]"))b.removeAttribute("data-pending");
  $("rail-state").textContent="Chapter ready";handoffState="settled";
 }catch(error){
  if(request!==chapterRequest)return;chapterBusy=false;navigationInert(false);curtain.classList.remove("covered");$("chapter-rail").removeAttribute("aria-busy");$("chapter-rail").setAttribute("data-error","");for(const b of $("chapter-rail").querySelectorAll("[data-scene]"))b.removeAttribute("data-pending");$("rail-state").textContent="Chapter unavailable. Select it to retry.";
  errorStatus("Chapter unavailable. Please try again.");console.warn("Chapter preparation failed:",error.message);
 }
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
async function prepareStage(root,name,fog=null,environment=null) {
  const started=performance.now(),holder=new THREE.Scene();holder.fog=fog;holder.environment=environment;holder.add(root);root.visible=true;
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
      ? import("./training-stage.js").then((module) => module.createLearning(data))
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
function errorStatus(message) {
  $("flight-label").hidden = false;
  $("flight-label").textContent = message;
}
let handoffToken=0, handoffState="settled";
const presentationWait=ms=>new Promise(resolve=>{const begin=performance.now();const tick=now=>now-begin>=ms?resolve():requestAnimationFrame(tick);requestAnimationFrame(tick);});
async function beginFlight(){if(data.environments[environment].available)return navigateChapter("surface");}

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
  // #391: fog colour now matches the sky dome's horizon band so distant ground
  // dissolves into haze instead of ending against a different flat grey, and it
  // starts far nearer so the mid-ground ridges actually recede.
  scene.background=new THREE.Color("#b3bcb7");
  scene.fog = new THREE.Fog("#b3bcb7", 150, 1350);
  setStage("surface");
  showOnly("surface-panel");
  $("skip-transition").hidden = true;
  $("flight-label").hidden = true;
  $("nav-location").textContent = "Rutongo / Rwanda";
  getMine().catch(() => {});
}
function mineView() {
  if(surface)surface.root.visible = false;
  globe.visible(false);
  mine.root.visible = true;
}
async function enterMine(){return navigateChapter("mine");}

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
  $("product").hidden = true;
  document.body.classList.add("story-locked");
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
async function openLearning(){return navigateChapter("training");}

function frameLearning() {
  if(stage!=="learning" || !learning?.fitCamera)return;
  const panel=document.querySelector(".learning-panel").getBoundingClientRect();
  lookTarget.copy(learning.fitCamera(camera,panel,document.querySelector(".learning-header").getBoundingClientRect().bottom));
}
function closeLearning(){return navigateChapter("mine");}
function updateLearning(delta){
 renderer.shadowMap.needsUpdate=true;
 const state=learning.update(delta);
 if(globalTime-hudTime<70&&delta>0)return;hudTime=globalTime;
 $("episode-count").textContent=state.episodes.toLocaleString("en-GB");
 $("reward-value").textContent=state.reward.toFixed(2);
 $("task-phase").textContent=state.action;
 $("training-order").textContent=state.trial.name;
 $("training-jobs").textContent=`${state.jobs} / 3 jobs`;
 $("task-payload").textContent=`${(state.payloadKg/1000).toFixed(2)} t`;
 const prior=learning.trace.trials.slice(0,state.index).reduce((s,t)=>s+t.rows.at(-1)[10],0);
 $("task-delivered").textContent=`${((prior+state.deliveredKg)/1000).toFixed(2)} t`;
 $("task-time").textContent=`${state.time.toFixed(1)} s`;
 $("action-value").textContent=({1:"Hold · missed engagement",2:"Hold · bucket curl",3:"Lift · curl",4:"Reverse · steer hold",5:"Brake · replan route",6:"Throttle · articulated steer",8:"Brake · raise bucket",9:"Hold · bucket tip",10:"Brake · task complete",11:"Brake · evaluate pickup"})[state.phase]||"Throttle · steer · lift";
 $("checkpoint-outcome").textContent=state.complete?"Three work orders complete. 6.00 t delivered.":state.index===0?"Bucket too high. The pickup fails.":state.index===1?"Partial pickup. Below the 2 t target.":state.index===4?"Obstacle detected. A clear route to the receiver.":"Scoop. Reverse clear. Haul. Tip into the receiver.";
 $("training-status").textContent=state.complete?"EVALUATION COMPLETE":state.playing?"POLICY EVALUATION / 6×":"REPLAY PAUSED";
 $("training-indicator").textContent=state.complete?"COMPLETE":state.playing?"TRAINING":"PAUSED";
 $("payload-readout").textContent=state.index<2?"PICKUP EVALUATION":`WORK ORDER ${String(state.index-1).padStart(2,"0")} / 03`;
 $("pause-training").disabled=state.complete;$("pause-training").textContent=state.complete?"Finished":state.playing?"Pause":"Play";
 const progress=Math.min(1,state.elapsed/state.duration);$("training-progress").setAttribute("aria-valuenow",Math.round(progress*100));$("training-progress").firstElementChild.style.width=`${progress*100}%`;
 const points=learning.trace.trials.map((t,i)=>[i*75,62-(t.reward+.41)/1.37*55]);
 $("reward-path").setAttribute("d",points.map((p,i)=>`${i?"L":"M"}${p.join(" ")}`).join(" "));
 $("reward-point").setAttribute("cx",state.index*75);$("reward-point").setAttribute("cy",points[state.index][1]);
 $("training-reset").hidden=!state.reset;$("training-reset").style.opacity=state.reset?Math.sin(state.reset*Math.PI):0;
}

async function ensureKit() {
  if (kit) return kit;
  if (kitPromise) return kitPromise;
  kitPromise = Promise.all([
    import("./retrofit-stage.js"),
    studioEnvironment(data.kit.lighting),
  ])
    .then(async ([module, environment]) => {
      const value = await module.createRetrofit(data);
      await prepareStage(value.root,"kit",null,environment);
      kitEnvironment = environment;kit=value;
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
function updateProduct(){
 if(stage!=="retrofit"||!kit)return;
 const rect=$("kit-window").getBoundingClientRect();kitActive=true;kit.root.visible=true;scene.environment=kitEnvironment;
 camera.position.fromArray(data.kit.camera);lookTarget.set(0,kitExploded?2:.7,0);
 const distance=camera.position.distanceTo(lookTarget);
 camera.fov=THREE.MathUtils.radToDeg(2*Math.atan(((4.1/distance)*innerHeight)/Math.max(300,rect.height)));
 camera.near=.05;camera.far=120;camera.clearViewOffset();camera.setViewOffset(innerWidth,innerHeight,innerWidth/2-(rect.left+rect.width/2),innerHeight/2-(rect.top+rect.height/2),innerWidth,innerHeight);camera.updateProjectionMatrix();camera.lookAt(lookTarget);
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
  frameLearning();
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
    technicalChapters=installChapters();
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
    document.body.classList.add("ready");
    $("start-experience").disabled = false;
    $("start-experience").textContent = "Enter experience ↗";
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
  if (document.hidden || $("technical-dialog").open) return;
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
  if(stage==="surface"&&surface?.root.visible)surface?.update?.(delta,reduced);
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
$("exit-world-model").addEventListener("click",closeLearning);
$("task-continue").addEventListener("click",()=>navigateChapter("inside"));
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
$("kit-next").addEventListener("click",()=>{if(kit){kitExploded=kit.step(1)>0;updateProduct();}});
$("kit-prev").addEventListener("click",()=>{if(kit){kitExploded=kit.step(-1)>0;updateProduct();}});
$("kit-pause").addEventListener("click",()=>{if(kit)$("kit-pause").textContent=kit.pause()?"Pause":"Play";});
$("assemble-kit").addEventListener("click", () => {
  if (!kit) return;
  kitExploded = kit.toggle();
  $("assemble-kit").textContent = kitExploded
    ? "Assemble the kit"
    : "Open the assembly";
  updateProduct();
});
$("scroll-product").addEventListener("click",()=>navigateChapter("inside"));
$("restart").addEventListener("click",()=>navigateChapter("earth"));
$("replay-experience").addEventListener("click",()=>location.reload());
const railButtons=[...$("chapter-rail").querySelectorAll("[data-scene]")];
for(const [index,button] of railButtons.entries()){
 button.addEventListener("click",()=>navigateChapter(button.dataset.scene));
 button.addEventListener("keydown",event=>{
  if(!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;event.preventDefault();event.stopPropagation();
  const next=event.key==="Home"?0:event.key==="End"?railButtons.length-1:(index+(event.key==="ArrowRight"?1:-1)+railButtons.length)%railButtons.length;railButtons[next].focus();
 });
}
for (const id of ["sources-open", "caption-sources"])
  $(id)?.addEventListener("click", () => $("sources-dialog").showModal());
$("sources-close").addEventListener("click", () => $("sources-dialog").close());
document.addEventListener("keydown", (event) => {
  if ($("sources-dialog").open) return;
  if(event.key==="Escape"&&chapterBusy){++chapterRequest;++handoffToken;chapterBusy=false;navigationInert(false);$("scene-curtain").classList.remove("covered");$("chapter-rail").removeAttribute("aria-busy");for(const b of $("chapter-rail").querySelectorAll("[data-scene]"))b.removeAttribute("data-pending");$("flight-label").hidden=true;if(stage==="comparing")comparisonDone(comparison);return;}
  if (event.key === "Escape" && stage === "learning") closeLearning();
  if (stage === "select" && event.key === "ArrowRight")
    chooseEnvironment(environment + 1);
  if (stage === "select" && event.key === "ArrowLeft")
    chooseEnvironment(environment - 1);
});
window.addEventListener("resize", resize, { passive: true });
let hiddenAt=0;
document.addEventListener("visibilitychange",()=>{
  if(document.hidden){hiddenAt=performance.now();surfaceFilm.hide();return;}
  const paused=hiddenAt?performance.now()-hiddenAt:0;
  for(const movement of [transition,cameraMove,homeHandoff])if(movement)movement.start+=paused;
  hiddenAt=0;lastTime=0;if(stage==="surface")surfaceFilm.show();
});
document.addEventListener("keydown",event=>{
  if(event.key!=="Escape" || !(["preparing","entering"].includes(stage)||(stage==="surface"&&handoffState==="preparing")))return;
  ++handoffToken;handoffState="cancelled";$("scene-curtain").classList.remove("covered");$("flight-label").hidden=true;
  if(stage==="preparing"){setStage("select");showOnly("selector");globe.visible(true);$("deploy-underground").focus();}
  else {surface.root.visible=true;if(mine)mine.root.visible=false;arrive();$("enter-mine").disabled=false;$("enter-mine").textContent="Enter the mine";$("enter-mine").focus();}
});
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
    chapter,chapterBusy,chapterRequest,surfaceFilm:surfaceFilm.diagnostics(),technical:technicalChapters?.diagnostics(),
    camera: {position:camera.position.toArray(),fov:camera.fov,moving:cameraMove!==null},
    earthSettling:earthGoal!==null,
    globe: globe?.diagnostics?.() ?? null,
    environmentBackground:environmentScenes?.diagnostics() || null,
    handoffState,
    homeHandoff:homeHandoff!==null,
    selectorViewport:selectorRect,
    presentation: document.querySelector('meta[name="kessel-presentation"]')?.content || "unversioned",
    scenes: {earth:globe?.root.visible ?? false,surface:surface?.root.visible ?? false,mine:mine?.root.visible ?? false,kit:kit?.root.visible ?? false},
    environment: data?.environments[environment].id,
    comparison,
    scrollY,
    kitActive,
    kit:kit?.diagnostics?.() ?? null,
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
  renderer.shadowMap.autoUpdate = tier !== "low" || stage === "learning";
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
