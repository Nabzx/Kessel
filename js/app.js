import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";

/* ------------------------------------------------------------------ *
 * Kessel concept demo — data-driven renderer.
 *
 * Everything this file draws comes from data/rollout.json. There is
 * no model, no sim, no RL loop running in the browser: this is a
 * player for a pre-baked rollout. Swap rollout.json for a logged
 * episode from the real policy + world model and nothing here needs
 * to change — see docs/ARCHITECTURE.md.
 * ------------------------------------------------------------------ */

const IS_MOBILE = matchMedia("(max-width: 720px)").matches ||
  /iPhone|iPad|Android/i.test(navigator.userAgent);
const DPR_CAP = IS_MOBILE ? 1.6 : 2;

const state = {
  rollout: null,
  frames: null,
  fps: 20,
  duration: 0,
  virtualT: 0,
  lastRAF: 0,
  horizonIdx: 0,
  scrubbing: false,
  boulderUntil: 0,
  boulderJumpT: null,
};

const els = {
  intro: document.getElementById("intro"),
  skip: document.getElementById("skip-intro"),
  stage: document.getElementById("stage"),
  loading: document.getElementById("loading"),
  hudDecision: document.getElementById("hud-decision"),
  hudError: document.getElementById("hud-error"),
  hudEpisode: document.getElementById("hud-episode"),
  hudState: document.getElementById("hud-state"),
  boulderBtn: document.getElementById("drop-boulder"),
  scrubber: document.getElementById("scrubber"),
  scrubberReadout: document.getElementById("scrubber-readout"),
};

/* ------------------------------ data ------------------------------ */

async function loadRollout() {
  const res = await fetch("data/rollout.json", { cache: "no-store" });
  const json = await res.json();
  state.rollout = json;
  state.frames = json.frames;
  state.fps = json.meta.fps;
  state.duration = json.meta.duration_s;
  els.loading.classList.add("hidden");
}

function frameAt(t) {
  const frames = state.frames;
  const n = frames.length;
  const fIdx = (t / state.duration) * n;
  const i0 = Math.floor(fIdx) % n;
  const i1 = (i0 + 1) % n;
  const a = fIdx - Math.floor(fIdx);
  return { f0: frames[i0], f1: frames[i1], a };
}

function lerp(a, b, t) { return a + (b - a) * t; }
function lerpVec(out, a, b, t) {
  out[0] = lerp(a[0], b[0], t);
  out[1] = lerp(a[1], b[1], t);
  out[2] = lerp(a[2], b[2], t);
  return out;
}

/* --------------------------- intro cards --------------------------- */

function runIntro(onDone) {
  const cards = [...document.querySelectorAll(".intro-card")];
  let i = -1;
  let done = false;

  function next() {
    if (done) return;
    if (i >= 0) cards[i].classList.remove("active");
    i += 1;
    if (i >= cards.length) {
      finish();
      return;
    }
    cards[i].classList.add("active");
    setTimeout(next, 1900);
  }

  function finish() {
    if (done) return;
    done = true;
    els.intro.classList.add("fade-out");
    setTimeout(() => {
      els.intro.style.display = "none";
      onDone();
    }, 520);
  }

  els.skip.addEventListener("click", finish);
  next();
}

/* ------------------------------ scene ------------------------------ */

function buildCommonScene({ wireframePile }) {
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x05060a, 0.045);

  const camera = new THREE.PerspectiveCamera(58, 1, 0.1, 100);
  camera.position.set(0.5, 1.95, 5.2);
  camera.lookAt(1.0, 0.9, -1.4);

  // ---- tunnel shell ----
  const tunnelMat = new THREE.MeshStandardMaterial({
    color: 0x6b5f4d,
    roughness: 0.92,
    metalness: 0.05,
    side: THREE.BackSide,
  });
  const tunnelGeo = new THREE.CylinderGeometry(3.1, 3.1, 24, 20, 1, true,
    THREE.MathUtils.degToRad(162), THREE.MathUtils.degToRad(216));
  // perturb the tunnel wall vertices for a hand-hewn look
  const posAttr = tunnelGeo.attributes.position;
  for (let i = 0; i < posAttr.count; i++) {
    const x = posAttr.getX(i), y = posAttr.getY(i), z = posAttr.getZ(i);
    const n = Math.sin(x * 1.7 + y * 0.6) * 0.18 + Math.sin(z * 0.9) * 0.12;
    const r = Math.hypot(x, z) || 1;
    posAttr.setX(i, x + (x / r) * n);
    posAttr.setZ(i, z + (z / r) * n);
  }
  tunnelGeo.computeVertexNormals();
  const tunnel = new THREE.Mesh(tunnelGeo, tunnelMat);
  tunnel.rotation.x = Math.PI / 2;
  tunnel.position.set(1.2, 1.9, -2);
  scene.add(tunnel);

  const floorGeo = new THREE.PlaneGeometry(10, 24, 24, 24);
  const floorPos = floorGeo.attributes.position;
  for (let i = 0; i < floorPos.count; i++) {
    const x = floorPos.getX(i), y = floorPos.getY(i);
    floorPos.setZ(i, Math.sin(x * 0.8 + y * 0.3) * 0.05 + Math.sin(y * 1.3) * 0.04);
  }
  floorGeo.computeVertexNormals();
  const floorMat = new THREE.MeshStandardMaterial({ color: 0x4a4136, roughness: 1, metalness: 0 });
  const floor = new THREE.Mesh(floorGeo, floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(1.2, 0, -2);
  scene.add(floor);

  // ---- lighting ----
  scene.add(new THREE.AmbientLight(0x3a4a5e, 1.6));
  scene.add(new THREE.HemisphereLight(0x55697e, 0x0a0806, 0.9));

  const headlamp = new THREE.PointLight(0xffc07a, 7, 11, 2);
  headlamp.position.set(-1.6, 2.2, 3);
  scene.add(headlamp);

  const keyFill = new THREE.PointLight(0xffd9a8, 4.5, 8, 2);
  keyFill.position.set(0.6, 2.6, 2.4);
  scene.add(keyFill);

  const farGlow = new THREE.PointLight(0x4fd6e6, 2.2, 12, 2);
  farGlow.position.set(3.4, 2.2, -5.6);
  scene.add(farGlow);

  const rim = new THREE.DirectionalLight(0x9fb3cc, 0.7);
  rim.position.set(-3, 4, 4);
  scene.add(rim);

  // ---- dust ----
  const dustCount = IS_MOBILE ? 140 : 320;
  const dustGeo = new THREE.BufferGeometry();
  const dustPos = new Float32Array(dustCount * 3);
  const dustSeed = new Float32Array(dustCount);
  for (let i = 0; i < dustCount; i++) {
    dustPos[i * 3 + 0] = THREE.MathUtils.randFloat(-4, 6);
    dustPos[i * 3 + 1] = THREE.MathUtils.randFloat(0.05, 3.2);
    dustPos[i * 3 + 2] = THREE.MathUtils.randFloat(-6, 3);
    dustSeed[i] = Math.random() * Math.PI * 2;
  }
  dustGeo.setAttribute("position", new THREE.BufferAttribute(dustPos, 3));
  const dustMat = new THREE.PointsMaterial({
    color: 0xd8b98a,
    size: IS_MOBILE ? 0.028 : 0.022,
    transparent: true,
    opacity: 0.35,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const dust = new THREE.Points(dustGeo, dustMat);
  scene.add(dust);

  // ---- loader ----
  const loader = buildLoader(wireframePile);
  scene.add(loader.group);

  // ---- rock pile ----
  const rockGeo = new THREE.IcosahedronGeometry(0.22, 0);
  let rockMat, rockMesh, rockColors;
  if (wireframePile) {
    rockMat = new THREE.MeshBasicMaterial({
      color: 0x4fd6e6,
      wireframe: true,
      transparent: true,
      opacity: 0.9,
      vertexColors: true,
    });
  } else {
    rockMat = new THREE.MeshStandardMaterial({
      color: 0x8a7b68,
      roughness: 0.9,
      metalness: 0.08,
    });
  }
  const n = 64;
  rockMesh = new THREE.InstancedMesh(rockGeo, rockMat, n);
  rockMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  if (wireframePile) {
    rockColors = new THREE.InstancedBufferAttribute(new Float32Array(n * 3), 3);
    rockMesh.instanceColor = rockColors;
  }
  scene.add(rockMesh);

  return { scene, camera, tunnel, dust, dustSeed, loader, rockMesh, rockGeo };
}

function buildLoader(ghost) {
  const group = new THREE.Group();

  const baseMat = ghost
    ? new THREE.MeshBasicMaterial({ color: 0x4fd6e6, wireframe: true, transparent: true, opacity: 0.25 })
    : new THREE.MeshStandardMaterial({ color: 0xcf7a2b, roughness: 0.55, metalness: 0.35 });
  const darkMat = ghost
    ? baseMat
    : new THREE.MeshStandardMaterial({ color: 0x5a5244, roughness: 0.75, metalness: 0.25 });
  const wheelMat = ghost
    ? baseMat
    : new THREE.MeshStandardMaterial({ color: 0x2e2c29, roughness: 0.85 });

  const body = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.7, 1.1), baseMat);
  body.position.set(0, 0.75, 0);
  group.add(body);

  const cab = new THREE.Mesh(new THREE.BoxGeometry(0.75, 0.55, 0.95), darkMat);
  cab.position.set(0.25, 1.33, 0);
  group.add(cab);

  const wheelGeo = new THREE.CylinderGeometry(0.34, 0.34, 0.26, 14);
  const wheelOffsets = [
    [0.62, 0.34, 0.62], [0.62, 0.34, -0.62],
    [-0.62, 0.34, 0.62], [-0.62, 0.34, -0.62],
  ];
  for (const [x, y, z] of wheelOffsets) {
    const w = new THREE.Mesh(wheelGeo, wheelMat);
    w.rotation.x = Math.PI / 2;
    w.position.set(x, y, z);
    group.add(w);
  }

  // articulated boom + bucket, pivoted at the front of the body
  const boomPivot = new THREE.Group();
  boomPivot.position.set(0.95, 0.85, 0);
  group.add(boomPivot);

  const boom = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.22, 0.28), darkMat);
  boom.position.set(0.75, 0, 0);
  boomPivot.add(boom);

  const bucketPivot = new THREE.Group();
  bucketPivot.position.set(1.5, 0, 0);
  boomPivot.add(bucketPivot);

  const bucket = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.42, 0.95), baseMat);
  bucket.position.set(0.3, -0.18, 0);
  bucketPivot.add(bucket);

  const headlampMesh = new THREE.Mesh(
    new THREE.SphereGeometry(0.06, 8, 8),
    new THREE.MeshBasicMaterial({ color: 0xffdca0 })
  );
  headlampMesh.position.set(0.78, 1.15, 0.42);
  if (!ghost) group.add(headlampMesh);

  return { group, boomPivot, bucketPivot, body };
}

function applyLoaderPose(loaderRig, loaderData) {
  const { group, boomPivot, bucketPivot } = loaderRig;
  group.position.set(loaderData.pos[0], loaderData.pos[1], loaderData.pos[2]);
  group.rotation.y = loaderData.heading;
  boomPivot.rotation.z = loaderData.boom;
  bucketPivot.rotation.z = -loaderData.bucket * 1.4;
}

function errorColor(e, maxE) {
  const t = THREE.MathUtils.clamp(e / maxE, 0, 1);
  // cyan (low error) -> amber -> red (high error)
  if (t < 0.5) return new THREE.Color().lerpColors(
    new THREE.Color(0x4fd6e6), new THREE.Color(0xf0a340), t / 0.5);
  return new THREE.Color().lerpColors(
    new THREE.Color(0xf0a340), new THREE.Color(0xff4d3d), (t - 0.5) / 0.5);
}
