import * as THREE from "three";
import { createLoadingMachine } from "../../../js/loading-machine.js";
import { seeded, studioEnvironment } from "../../../js/scene-utils.js";

const $ = (id) => document.getElementById(id);
const reduced = matchMedia("(prefers-reduced-motion: reduce)");
const renderer = new THREE.WebGLRenderer({ canvas: $("study-canvas"), antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.localClippingEnabled = true;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 160);
camera.position.set(-17, 19, 22);
const target = new THREE.Vector3(0, 0.7, -1);
const cutaway = new THREE.Group();
cutaway.name = "synthetic-geological-reference";
scene.add(cutaway);
const frameTimes = [];
const materials = new Map();
const rockMeshes = [];
let activeMaterial = "rock_face_03", view = "cutaway", lighting = "studio";
let paused = reduced.matches, elapsed = 0, transition = null, scan = null, scanPromise = null;
let machine, manifest, lastTime = null, lastHud = 0, inspection = false;
const hemi = new THREE.HemisphereLight(0xc9dbdf, 0x302b24, 1.2);
const key = new THREE.DirectionalLight(0xf1ece2, 3.0);
key.position.set(-9, 17, 12);
key.castShadow = true;
key.shadow.mapSize.set(1024, 1024);
Object.assign(key.shadow.camera, { left: -16, right: 16, top: 16, bottom: -16, near: 1, far: 60 });
key.shadow.bias = -0.0004;
key.shadow.normalBias = 0.04;
scene.add(hemi, key);
const fill = new THREE.DirectionalLight(0xabc5d0, 0.65);
fill.position.set(8, 5, -12);
scene.add(fill);
const workLights = [];

async function readJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Reference unavailable: ${url}`);
  return response.json();
}

async function map(url, colour = false) {
  const result = await new THREE.TextureLoader().loadAsync(url);
  result.wrapS = result.wrapT = THREE.RepeatWrapping;
  result.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy());
  result.colorSpace = colour ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  return result;
}

async function material(spec) {
  const maps = Object.fromEntries(await Promise.all(spec.maps.map(async (entry) =>
    [entry.role, await map(entry.path, entry.role === "Diffuse")])));
  for (const entry of Object.values(maps))
    if (entry.image.width !== spec.resolution[0] || entry.image.height !== spec.resolution[1])
      throw new Error(`Unexpected material resolution: ${spec.id}`);
  const result = new THREE.MeshStandardMaterial({
    map: maps.Diffuse, normalMap: maps.nor_gl, roughnessMap: maps.Rough,
    aoMap: maps.AO, aoMapIntensity: 0.7, roughness: 1, metalness: 0,
    normalScale: new THREE.Vector2(0.65, 0.65), envMapIntensity: 0.45,
  });
  materials.set(spec.id, result);
}

function box(size, position, material, parent = cutaway) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), material);
  mesh.position.fromArray(position);
  mesh.castShadow = mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function projectRockUV(geometry) {
  // Match all candidates at one world-space repeat; avoid stretched side walls.
  const position = geometry.attributes.position, normal = geometry.attributes.normal;
  const uv = new Float32Array(position.count * 2);
  for (let i = 0; i < position.count; i++) {
    const x = Math.abs(normal.getX(i)), y = Math.abs(normal.getY(i)), z = Math.abs(normal.getZ(i));
    const u = x > y && x > z ? position.getZ(i) : position.getX(i);
    const v = y >= x && y >= z ? position.getZ(i) : position.getY(i);
    uv[i * 2] = u / 2.7;
    uv[i * 2 + 1] = v / 2.7;
  }
  geometry.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  geometry.setAttribute("uv1", geometry.attributes.uv.clone());
}

function bank(points, height) {
  const shape = new THREE.Shape(points.map(([x, z]) => new THREE.Vector2(x, -z)));
  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth: height, bevelEnabled: true, bevelThickness: 0.14,
    bevelSize: 0.13, bevelSegments: 2, steps: 1,
  });
  geometry.rotateX(-Math.PI / 2);
  projectRockUV(geometry);
  const mesh = new THREE.Mesh(geometry, materials.get(activeMaterial));
  mesh.castShadow = mesh.receiveShadow = true;
  rockMeshes.push(mesh);
  cutaway.add(mesh);
}

function buildGeology(floorMap, floorNormal, oreMap) {
  const base = new THREE.MeshStandardMaterial({ color: 0x23282a, roughness: 0.98 });
  box([20, 0.65, 19.5], [0, -0.5, 0], base);
  floorMap.repeat.set(20 / 2.7, 19.5 / 2.7);
  floorNormal.repeat.copy(floorMap.repeat);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(20, 19.5),
    new THREE.MeshStandardMaterial({ map: floorMap, normalMap: floorNormal,
      color: 0xaaa59b, normalScale: new THREE.Vector2(0.35, 0.35), roughness: 0.96 }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.07;
  floor.receiveShadow = true;
  cutaway.add(floor);
  bank([[-9,-8],[-2.7,-8],[-2.5,-5.4],[-3.1,-2],[-2.35,1.1],[-2.8,7.3],[-8.6,8],[-9.2,4.2],[-8.5,0.6],[-9.6,-4]], 3.2);
  bank([[2.6,-7.9],[8.7,-8.4],[9.3,-4],[8.4,0.2],[9,5.1],[8.1,7.4],[3.2,7.8],[2.5,5],[3,2.6],[2.2,-0.9],[3.1,-3]], 3.5);
  const rockMaterial = new THREE.MeshStandardMaterial({ map: oreMap, roughness: 1, color: 0xb2ada3 });
  const pile = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 1), rockMaterial, 54);
  const random = seeded(6311), pose = new THREE.Object3D();
  for (let i = 0; i < 54; i++) {
    const radius = 0.17 + random() * 0.28;
    pose.position.set((random()-0.5)*3.0, radius + random()*0.35, -5.7+(random()-0.5)*2.0);
    pose.scale.set(radius, radius*(0.7+random()*0.4), radius);
    pose.rotation.set(random()*3, random()*6, random()*3);
    pose.updateMatrix(); pile.setMatrixAt(i, pose.matrix);
  }
  pile.castShadow = pile.receiveShadow = true;
  cutaway.add(pile);
  const metal = new THREE.MeshStandardMaterial({ color: 0x455154, roughness: 0.68, metalness: 0.65 });
  for (const z of [-6, 0, 6]) {
    box([0.07, 2.7, 0.07], [2.55, 1.35, z], metal);
    const light = new THREE.PointLight(0xd5e2df, 0.7, 10, 2);
    light.position.set(2.3, 2.65, z);
    cutaway.add(light); workLights.push(light);
    const bulb = box([0.32,0.07,0.14], [2.3,2.7,z], new THREE.MeshBasicMaterial({color:0xd6e2dd}));
    bulb.castShadow = false;
  }
  // A small one-metre datum makes authored scale inspectable without a HUD grid.
  const marks = [];
  for (let i = -5; i <= 5; i++) marks.push(i, -0.045, 9, i, -0.045, 9.22);
  marks.push(-5,-0.045,9,5,-0.045,9);
  const datum = new THREE.LineSegments(new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(marks,3)),
    new THREE.LineBasicMaterial({color:0xd5ac6c,transparent:true,opacity:0.5}));
  cutaway.add(datum);
}

async function getScan() {
  if (scan) return scan;
  if (!scanPromise) scanPromise = (async () => {
    const meta = await readJson("assets/slovenia-tunnel.json");
    const response = await fetch("assets/slovenia-tunnel.bin");
    if (!response.ok) throw new Error("Scan reference unavailable");
    const bytes = await response.arrayBuffer();
    if (bytes.byteLength !== meta.bytes || bytes.byteLength !== meta.triangles * 9 * 4)
      throw new Error("Invalid scan reference length");
    const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)))
      .map((v) => v.toString(16).padStart(2,"0")).join("");
    if (hash !== meta.derived_sha256 || meta.physical_units !== null || !meta.reference_only)
      throw new Error("Invalid scan provenance");
    const values = new Float32Array(bytes);
    if (values.some((v) => !Number.isFinite(v))) throw new Error("Non-finite scan geometry");
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(values,3));
    geometry.computeVertexNormals();
    const reference = new THREE.Group();
    reference.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({
      color:0x949e96,roughness:1,side:THREE.DoubleSide,transparent:true,opacity:0.55,depthWrite:false,
    })));
    reference.add(new THREE.LineSegments(new THREE.WireframeGeometry(geometry),
      new THREE.LineBasicMaterial({color:0xb1c9bf,transparent:true,opacity:0.18,depthWrite:false})));
    reference.name = "credited-unitless-slovenian-reference";
    reference.userData.provenance = meta;
    reference.visible = false;
    scene.add(reference); scan = reference;
    return reference;
  })().catch((error) => { scanPromise = null; throw error; });
  return scanPromise;
}

function moveCamera(position, lookAt) {
  transition = { start:performance.now(), from:camera.position.clone(), targetFrom:target.clone(),
    to:new THREE.Vector3(...position), targetTo:new THREE.Vector3(...lookAt) };
}

function press(attribute, value) {
  for (const button of document.querySelectorAll(`[${attribute}]`))
    button.setAttribute("aria-pressed", String(button.getAttribute(attribute) === value));
}

function selectMaterial(id) {
  if (!materials.has(id)) return;
  activeMaterial = id;
  for (const mesh of rockMeshes) mesh.material = materials.get(id);
  press("data-material", id);
  $("resolution").textContent = `${materials.get(id).map.image.width / 1024 < 1 ? "512 px" : "1K"}`;
}

let viewRequest = 0;
async function selectView(next) {
  const request = ++viewRequest;
  try {
    if (next === "scan") await getScan();
    if (request !== viewRequest) return;
    view = next; cutaway.visible = next === "cutaway";
    if (scan) scan.visible = next === "scan";
    $("scene-caption").textContent = next === "scan" ? "Slovenia · CC BY 4.0 · source units" : "Synthetic scene · metres";
    $("repeat").textContent = next === "scan" ? "Untextured" : "2.7 m";
    $("resolution").textContent = next === "scan" ? "—" : (materials.get(activeMaterial).map.image.width < 1024 ? "512 px" : "1K");
    document.querySelectorAll("[data-material]").forEach((button) => { button.disabled = next === "scan"; });
    $("study-canvas").setAttribute("aria-label", next === "scan" ? "Cropped Slovenian tunnel reference; unknown units and CRS" : "Synthetic cutaway with retained excavator");
    press("data-view", next);
    inspection = false; $("inspect").textContent = "Inspect surface";
    if (next === "scan") moveCamera([12,14,18], [0,0,0]);
    else moveCamera([-17,19,22], [0,0.7,-1]);
    $("status").hidden = true;
  } catch (error) { $("status").textContent = error.message; $("status").hidden = false; }
}

function setLighting(next) {
  lighting = next;
  hemi.intensity = next === "mine" ? 0.48 : 1.2;
  key.intensity = next === "mine" ? 0.85 : 3;
  fill.intensity = next === "mine" ? 0.35 : 0.65;
  workLights.forEach((light) => { light.intensity = next === "mine" ? 5 : 0.7; });
  press("data-light", next);
}

function resize() {
  const rect = $("scene").getBoundingClientRect();
  renderer.setSize(rect.width, rect.height, false);
  camera.aspect = rect.width / Math.max(rect.height,1);
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe($("scene"));

function frame(now) {
  const dt = lastTime === null ? 0 : Math.min((now-lastTime)/1000,0.1);
  if (!document.hidden && lastTime !== null) {
    frameTimes.push(now-lastTime);
    if (frameTimes.length > 240) frameTimes.shift();
  }
  lastTime = now;
  if (!paused && !document.hidden) {
    elapsed += dt;
    machine?.update({phase:"loading",load:(elapsed/16)%1});
  }
  if (transition) {
    const t = reduced.matches ? 1 : Math.min((now-transition.start)/1600,1);
    const ease = t*t*t*(t*(t*6-15)+10);
    camera.position.lerpVectors(transition.from,transition.to,ease);
    target.lerpVectors(transition.targetFrom,transition.targetTo,ease);
    if (t === 1) transition = null;
  }
  camera.lookAt(target);
  if (!document.hidden) renderer.render(scene,camera);
  if (now-lastHud > 500) {
    const sorted = [...frameTimes].sort((a,b) => a-b);
    $("frame-ms").textContent = sorted.length ? `${sorted[Math.floor(sorted.length*0.95)].toFixed(1)} ms` : "—";
    $("triangles").textContent = renderer.info.render.triangles.toLocaleString("en-GB");
    lastHud = now;
  }
}

$("sources-open").addEventListener("click", () => $("sources-dialog").showModal());
document.addEventListener("visibilitychange", () => { lastTime = null; frameTimes.length = 0; });
reduced.addEventListener("change", () => {
  if (reduced.matches) {
    paused = true; $("pause").setAttribute("aria-pressed","true"); $("pause").textContent = "Resume";
  }
});
window.addEventListener("pagehide", (event) => { if (!event.persisted) renderer.dispose(); });

window.studyDiagnostics = () => {
  const sorted = [...frameTimes].sort((a,b) => a-b);
  const ext = renderer.getContext().getExtension("WEBGL_debug_renderer_info");
  return { view, material:activeMaterial, lighting, paused, sourceMode:"visual_reference",
    physicalUnits:view === "scan" ? null : "metres", renderer:ext ? renderer.getContext().getParameter(ext.UNMASKED_RENDERER_WEBGL) : "unavailable",
    drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,textures:renderer.info.memory.textures,
    p95FrameMs:sorted.length ? sorted[Math.floor(sorted.length*0.95)] : null,
    meanFps:sorted.length ? 1000/(frameTimes.reduce((a,b)=>a+b,0)/frameTimes.length) : null,
    pixelRatio:renderer.getPixelRatio(),transition:!!transition,
  };
};

async function boot() {
  manifest = await readJson("manifest.json");
  await Promise.all(manifest.materials.map(material));
  const baseline = new THREE.MeshStandardMaterial({
    map:await map(manifest.baseline.maps.Diffuse,true),
    normalMap:await map(manifest.baseline.maps.nor_gl),roughness:0.95,
    normalScale:new THREE.Vector2(0.65,0.65),metalness:0,
  });
  materials.set("baseline",baseline);
  const [floorMap,floorNormal,oreMap,environment] = await Promise.all([
    map("../../../assets/textures/brown_mud_dry_diff.jpg",true),
    map("../../../assets/textures/brown_mud_dry_nor_gl.jpg"),
    map("../../../assets/textures/aerial_rocks_02_diff.jpg",true),
    studioEnvironment({path:"../../../assets/lighting/kit-studio.bin",width:384,height:512}),
  ]);
  scene.environment = environment;
  buildGeology(floorMap,floorNormal,oreMap);
  machine = await createLoadingMachine({model:"../../../assets/models/excavator/excavator.gltf",length_m:6.2,
    boom_bone_index:1,bucket_bone_index:5,offset_m:[0,0,-0.4],target_offset_m:[0,0,-6]}, {position_m:[0,0,0]});
  machine.root.traverse((object) => { if (object.isMesh) { object.castShadow = true; object.receiveShadow = true; } });
  cutaway.add(machine.root);
  document.querySelectorAll("[data-material]").forEach((b) => b.addEventListener("click", () => selectMaterial(b.dataset.material)));
  document.querySelectorAll("[data-view]").forEach((b) => b.addEventListener("click", () => selectView(b.dataset.view)));
  document.querySelectorAll("[data-light]").forEach((b) => b.addEventListener("click", () => setLighting(b.dataset.light)));
  $("inspect").addEventListener("click", () => {
    inspection = !inspection;
    $("inspect").textContent = inspection ? "Overhead" : "Inspect surface";
    if (view === "scan") moveCamera(inspection ? [7,8,13] : [12,14,18], [0,0,0]);
    else moveCamera(inspection ? [1.2,7.3,13.5] : [-17,19,22], inspection ? [0,0.8,-1.8] : [0,0.7,-1]);
  });
  $("pause").setAttribute("aria-pressed",String(paused));
  $("pause").textContent = paused ? "Resume" : "Pause";
  $("pause").addEventListener("click", () => {
    paused = !paused; $("pause").setAttribute("aria-pressed",String(paused));
    $("pause").textContent = paused ? "Resume" : "Pause";
  });
  $("status").hidden = true;
  document.body.classList.add("ready");
  resize(); renderer.setAnimationLoop(frame);
}
boot().catch((error) => { $("status").textContent = error.message; $("status").setAttribute("role","alert"); console.error(error); });
