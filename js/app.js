import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";

/* ------------------------------------------------------------------ *
 * Kessel concept demo — data-driven renderer.
 *
 * Everything this file draws comes from data/rollout.json. There is
 * no model, no sim, no RL loop running in the browser: this is a
 * player for a pre-baked rollout. Swap rollout.json for a logged
 * episode from the real policy + world model and nothing here needs
 * to change — see docs/ARCHITECTURE.md.
 * ------------------------------------------------------------------ */

const LOOP_VEIL_WINDOW_S = 0.3; // ADR-0012: crossfade window either side of the loop seam
const WHEEL_SPIN_AXIS = new THREE.Vector3(0, 1, 0);
const GLINT_STRIDE = 7;
const GLINT_COUNT = Math.ceil(64 / GLINT_STRIDE); // #82: every 7th rock doubles as a mineral glint

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
  horizonTransition: null,
  scrubbing: false,
  boulderUntil: 0,
  boulderJumpT: null,
};

// ADR-0013: a restrained, edge-only chromatic aberration for the
// world-model panel -- near zero at screen centre, 1-2px of RGB channel
// split at the frame edges. A ShaderPass in the composer chain, not a
// CSS/SVG filter (an SVG feColorMatrix/feBlend attempt badly corrupted
// the canvas's actual pixel output -- this is the correct technique).
const CHROMA_SHADER = {
  uniforms: { tDiffuse: { value: null }, amount: { value: 0.0025 } },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float amount;
    varying vec2 vUv;
    void main() {
      vec2 centered = vUv - 0.5;
      float edge = clamp(length(centered) * 1.6, 0.0, 1.0);
      vec2 dir = normalize(centered + 1e-6) * amount * edge;
      float r = texture2D(tDiffuse, vUv - dir).r;
      float g = texture2D(tDiffuse, vUv).g;
      float b = texture2D(tDiffuse, vUv + dir).b;
      float a = texture2D(tDiffuse, vUv).a;
      gl_FragColor = vec4(r, g, b, a);
    }
  `,
};

// ADR-0012: crossfade the loop seam. A ShaderPass in both composer
// chains, not a DOM overlay -- a CSS class toggle on a div positioned
// over the WebGL canvases was found to corrupt their compositing in
// this environment (reproduced by isolating that exact call).
const FADE_SHADER = {
  uniforms: { tDiffuse: { value: null }, amount: { value: 0.0 } },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float amount;
    varying vec2 vUv;
    void main() {
      vec4 c = texture2D(tDiffuse, vUv);
      gl_FragColor = vec4(c.rgb * (1.0 - amount), c.a);
    }
  `,
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

function frameAt(t, out) {
  const frames = state.frames;
  const n = frames.length;
  const fIdx = (t / state.duration) * n;
  const i0 = ((Math.floor(fIdx) % n) + n) % n;
  const i1 = (i0 + 1) % n;
  out.f0 = frames[i0];
  out.f1 = frames[i1];
  out.a = fIdx - Math.floor(fIdx);
  return out;
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

  // ---- dust (#83: soft circular sprite, not the default square point) ----
  // Textured + additively-blended point sprites measured as real cost on
  // mobile (#95): recovered most of a 21fps -> 13fps regression by
  // dropping the texture there specifically, more than size alone did.
  // Desktop keeps the soft sprite; mobile keeps the original flat dot.
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
    map: IS_MOBILE ? null : dustSpriteTexture(),
    size: IS_MOBILE ? 0.022 : 0.04,
    transparent: true,
    opacity: 0.4,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const dust = new THREE.Points(dustGeo, dustMat);
  scene.add(dust);

  // ---- falling debris (#84): a sparser, gravity-biased sibling of the
  // dust system, trickling down near the pile rather than drifting up.
  // #95's throttled measurement found the cumulative cost of Phase 6's
  // additions (not any single one) added up to a real regression on
  // mobile -- zero debris there rather than trimming every item a
  // little, per ADR-0014's fallback. ----
  const debrisCount = IS_MOBILE ? 0 : 36;
  const debrisGeo = new THREE.BufferGeometry();
  const debrisPos = new Float32Array(debrisCount * 3);
  const debrisSeed = new Float32Array(debrisCount);
  for (let i = 0; i < debrisCount; i++) {
    debrisPos[i * 3 + 0] = THREE.MathUtils.randFloat(0.4, 2.6);
    debrisPos[i * 3 + 1] = THREE.MathUtils.randFloat(0.3, 1.6);
    debrisPos[i * 3 + 2] = THREE.MathUtils.randFloat(-1.6, 0.4);
    debrisSeed[i] = Math.random() * Math.PI * 2;
  }
  debrisGeo.setAttribute("position", new THREE.BufferAttribute(debrisPos, 3));
  const debrisMat = new THREE.PointsMaterial({
    color: 0x9c8a74,
    map: IS_MOBILE ? null : dustSpriteTexture(),
    size: IS_MOBILE ? 0.022 : 0.035,
    transparent: true,
    opacity: 0.55,
    depthWrite: false,
  });
  const debris = new THREE.Points(debrisGeo, debrisMat);
  scene.add(debris);

  // ---- tunnel support beams, rail track, contact shadows (#75-77) ----
  // Desktop-only: see the debris comment above -- #95 found the combined
  // cost of this detail pass regressed the mobile frame budget even
  // though each item alone looked cheap.
  let shadowMat = null;
  if (!IS_MOBILE) {
    const beamGeo = new THREE.BoxGeometry(4.6, 0.14, 0.16);
    const beamMat = new THREE.MeshStandardMaterial({ color: 0x241f18, roughness: 0.95 });
    const beamCount = 6;
    const beamMesh = new THREE.InstancedMesh(beamGeo, beamMat, beamCount);
    const beamDummy = new THREE.Object3D();
    for (let i = 0; i < beamCount; i++) {
      beamDummy.position.set(1.2, 3.85, -9 + i * 3.1);
      beamDummy.updateMatrix();
      beamMesh.setMatrixAt(i, beamDummy.matrix);
    }
    scene.add(beamMesh);

    const railMat = new THREE.MeshStandardMaterial({ color: 0x1c1a17, roughness: 0.6, metalness: 0.4 });
    for (const zOff of [-0.95, -0.25]) {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(7.5, 0.04, 0.06), railMat);
      rail.position.set(-1.6, 0.02, -0.6 + zOff);
      scene.add(rail);
    }

    shadowMat = new THREE.MeshBasicMaterial({
      map: shadowDecalTexture(),
      transparent: true,
      depthWrite: false,
    });
    const pileShadow = new THREE.Mesh(new THREE.CircleGeometry(1.5, 24), shadowMat);
    pileShadow.rotation.x = -Math.PI / 2;
    pileShadow.position.set(2.0, 0.015, -0.6);
    scene.add(pileShadow);
  }

  // ---- loader ----
  const loader = buildLoader(wireframePile);
  scene.add(loader.group);

  if (!wireframePile) {
    if (shadowMat) {
      const loaderShadow = new THREE.Mesh(new THREE.CircleGeometry(1.3, 20), shadowMat.clone());
      loaderShadow.rotation.x = -Math.PI / 2;
      loaderShadow.position.y = 0.015;
      loader.group.add(loaderShadow);
    }

    // ---- volumetric headlamp beam (#72): additive cone, not a real
    // volumetric pass -- reads as a light shaft once bloom picks it up
    // (ADR-0010). DoubleSide transparency overdraw measured as real cost
    // on the Phase 5 throttled profile (#95) -- desktop-only. ----
    if (!IS_MOBILE) {
      const beamTex = lightBeamTexture();
      const beamConeMat = new THREE.MeshBasicMaterial({
        map: beamTex,
        transparent: true,
        opacity: 0.5,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        side: THREE.DoubleSide,
      });
      const lightShaft = new THREE.Mesh(new THREE.ConeGeometry(0.9, 2.6, 16, 1, true), beamConeMat);
      lightShaft.rotation.z = Math.PI / 2;
      lightShaft.position.set(1.5, 1.15, 0.42);
      loader.group.add(lightShaft);
    }
  }

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
    // #74: a procedural noise bump map so the pile reads as textured
    // stone rather than flat-shaded polyhedra. Per-fragment bump
    // sampling across 64 lit instances measured as real cost on the
    // Phase 5 throttled profile (#95) -- desktop-only, same fallback as
    // the shader passes above.
    rockMat = new THREE.MeshStandardMaterial({
      color: 0x8a7b68,
      roughness: 0.9,
      metalness: 0.08,
      ...(IS_MOBILE ? {} : { bumpMap: makeNoiseBumpTexture(), bumpScale: 0.05 }),
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

  // ---- mineral glint (#82): a handful of rock positions double as tiny
  // emissive specks, catching the headlamp light. Sim panel only -- the
  // wireframe panel's own glow already reads as "lit." ----
  let glintMesh = null;
  if (!wireframePile && !IS_MOBILE) {
    const glintGeo = new THREE.SphereGeometry(0.035, 6, 6);
    const glintMat = new THREE.MeshBasicMaterial({ color: 0xfff1cf });
    glintMesh = new THREE.InstancedMesh(glintGeo, glintMat, GLINT_COUNT);
    glintMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    scene.add(glintMesh);
  }

  return { scene, camera, tunnel, dust, dustSeed, debris, debrisSeed, loader, rockMesh, rockGeo, glintMesh };
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

  const wheelRadius = 0.34;
  const wheelGeo = new THREE.CylinderGeometry(wheelRadius, wheelRadius, 0.26, 14);
  const wheelOffsets = [
    [0.62, 0.34, 0.62], [0.62, 0.34, -0.62],
    [-0.62, 0.34, 0.62], [-0.62, 0.34, -0.62],
  ];
  // #81: kept separately so applyLoaderPose can spin them with travel speed
  const wheels = [];
  for (const [x, y, z] of wheelOffsets) {
    const w = new THREE.Mesh(wheelGeo, wheelMat);
    w.rotation.x = Math.PI / 2;
    w.position.set(x, y, z);
    group.add(w);
    wheels.push(w);
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

  // #80: the Kessel retrofit kit -- a rugged sensor pod bolted onto the
  // cab roof, visually distinct (dark, matte) from the loader's own
  // bodywork, with a small status LED. Ties the visual directly back to
  // the product: this is a retrofit, not an OEM part.
  if (!ghost) {
    const podMat = new THREE.MeshStandardMaterial({ color: 0x18191b, roughness: 0.5, metalness: 0.6 });
    const pod = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.14, 0.2), podMat);
    pod.position.set(0.1, 1.68, -0.1);
    group.add(pod);
    const antenna = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.22, 6), podMat);
    antenna.position.set(0.02, 1.86, -0.15);
    group.add(antenna);
    const led = new THREE.Mesh(
      new THREE.SphereGeometry(0.018, 6, 6),
      new THREE.MeshBasicMaterial({ color: 0x4fd6e6 })
    );
    led.position.set(0.1, 1.68, 0.01);
    group.add(led);
  }

  return { group, boomPivot, bucketPivot, body, wheels, wheelRadius, prevWorldX: null };
}

function applyLoaderPose(loaderRig, loaderData) {
  const { group, boomPivot, bucketPivot, wheels, wheelRadius } = loaderRig;
  group.position.set(loaderData.pos[0], loaderData.pos[1], loaderData.pos[2]);
  group.rotation.y = loaderData.heading;
  boomPivot.rotation.z = loaderData.boom;
  bucketPivot.rotation.z = -loaderData.bucket * 1.4;

  // #81: spin the wheels with actual travel speed rather than leaving
  // them static while the loader moves.
  if (wheels && loaderRig.prevWorldX !== null) {
    const dx = loaderData.pos[0] - loaderRig.prevWorldX;
    const spin = dx / wheelRadius;
    // rotateOnAxis spins about the wheel's own current local axis,
    // independent of Euler composition order -- safer than touching
    // .rotation.y directly given the wheel already carries a fixed
    // 90-degree lie-flat rotation on X.
    for (const w of wheels) w.rotateOnAxis(WHEEL_SPIN_AXIS, spin);
  }
  loaderRig.prevWorldX = loaderData.pos[0];
}

function errorColor(e, maxE) {
  const t = THREE.MathUtils.clamp(e / maxE, 0, 1);
  // cyan (low error) -> amber -> red (high error)
  if (t < 0.5) return new THREE.Color().lerpColors(
    new THREE.Color(0x4fd6e6), new THREE.Color(0xf0a340), t / 0.5);
  return new THREE.Color().lerpColors(
    new THREE.Color(0xf0a340), new THREE.Color(0xff4d3d), (t - 0.5) / 0.5);
}

/* ---------------------------- textures ---------------------------- */
// Small canvas-generated textures -- no external assets, consistent with
// the "no build step" invariant. Each is built once and reused across
// both scenes.

function makeRadialGradientTexture({ size = 64, inner = "rgba(255,255,255,1)", outer = "rgba(255,255,255,0)" }) {
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  g.addColorStop(0, inner);
  g.addColorStop(1, outer);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function makeNoiseBumpTexture(size = 128) {
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d");
  const img = ctx.createImageData(size, size);
  for (let i = 0; i < size * size; i++) {
    const v = 90 + Math.random() * 110;
    img.data[i * 4] = img.data[i * 4 + 1] = img.data[i * 4 + 2] = v;
    img.data[i * 4 + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(4, 4);
  return tex;
}

let _dustSpriteTex = null;
function dustSpriteTexture() {
  if (!_dustSpriteTex) {
    _dustSpriteTex = makeRadialGradientTexture({
      size: 32,
      inner: "rgba(255,245,225,0.9)",
      outer: "rgba(255,245,225,0)",
    });
  }
  return _dustSpriteTex;
}

let _shadowDecalTex = null;
function shadowDecalTexture() {
  if (!_shadowDecalTex) {
    _shadowDecalTex = makeRadialGradientTexture({
      size: 64,
      inner: "rgba(0,0,0,0.55)",
      outer: "rgba(0,0,0,0)",
    });
  }
  return _shadowDecalTex;
}

let _beamTex = null;
function lightBeamTexture() {
  if (!_beamTex) {
    _beamTex = makeRadialGradientTexture({
      size: 64,
      inner: "rgba(255,210,150,0.5)",
      outer: "rgba(255,210,150,0)",
    });
  }
  return _beamTex;
}

/* ------------------------------ main ------------------------------ */

const rolloutPromise = loadRollout();

async function main() {
  await rolloutPromise;

  const canvasSim = document.getElementById("canvas-sim");
  const canvasPred = document.getElementById("canvas-pred");

  const sim = buildCommonScene({ wireframePile: false });
  const pred = buildCommonScene({ wireframePile: true });
  pred.loader.group.visible = true;

  // #73: a slow, small, looping positional drift so the scene doesn't
  // read as a frozen diorama. Base positions captured once; tick() adds
  // a bounded offset on top rather than accumulating drift.
  const simBasePos = sim.camera.position.clone();
  const predBasePos = pred.camera.position.clone();

  const rendererOpts = { antialias: !IS_MOBILE, powerPreference: "high-performance" };
  const rendererSim = new THREE.WebGLRenderer({ canvas: canvasSim, ...rendererOpts });
  const rendererPred = new THREE.WebGLRenderer({ canvas: canvasPred, ...rendererOpts });
  rendererSim.setPixelRatio(Math.min(window.devicePixelRatio, DPR_CAP));
  rendererPred.setPixelRatio(Math.min(window.devicePixelRatio, DPR_CAP));
  rendererSim.toneMapping = THREE.ACESFilmicToneMapping;
  rendererPred.toneMapping = THREE.ACESFilmicToneMapping;
  rendererSim.toneMappingExposure = 1.05;
  rendererPred.toneMappingExposure = 1.05;

  // ADR-0014's stated fallback, exercised for real: #95's throttled
  // measurement showed a serious regression (~21fps -> ~8fps on the
  // Phase 5 Pixel-5/4x-throttle profile) once the extra ShaderPass per
  // composer were added. Mesh-based detail (Phase 6's environment props)
  // stays on everywhere; these two full-screen passes become
  // desktop-only rather than being cut outright.
  const composerSim = new EffectComposer(rendererSim);
  composerSim.addPass(new RenderPass(sim.scene, sim.camera));
  const bloomSim = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.65, 0.5, 0.18);
  composerSim.addPass(bloomSim);
  const fadeSim = new ShaderPass(FADE_SHADER);
  if (!IS_MOBILE) composerSim.addPass(fadeSim);

  const composerPred = new EffectComposer(rendererPred);
  composerPred.addPass(new RenderPass(pred.scene, pred.camera));
  const bloomPred = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.95, 0.55, 0.1);
  composerPred.addPass(bloomPred);
  const chromaPass = new ShaderPass(CHROMA_SHADER);
  if (!IS_MOBILE) composerPred.addPass(chromaPass);
  const fadePred = new ShaderPass(FADE_SHADER);
  if (!IS_MOBILE) composerPred.addPass(fadePred);

  function resize() {
    for (const { canvas, camera, composer, bloom, renderer } of [
      { canvas: canvasSim, camera: sim.camera, composer: composerSim, bloom: bloomSim, renderer: rendererSim },
      { canvas: canvasPred, camera: pred.camera, composer: composerPred, bloom: bloomPred, renderer: rendererPred },
    ]) {
      const w = canvas.clientWidth, h = canvas.clientHeight;
      camera.aspect = w / Math.max(h, 1);
      camera.updateProjectionMatrix();
      composer.setSize(w, h);
      bloom.setSize(w, h);
    }
  }
  window.addEventListener("resize", resize);
  window.addEventListener("orientationchange", () => setTimeout(resize, 200));

  const maxErrorSeen = { v: 0.3 };
  const dummy = new THREE.Object3D();

  function updateRocksSim(frame) {
    const scales = state.rollout.rock_scale;
    for (let i = 0; i < frame.rocks.length; i++) {
      const [x, y, z] = frame.rocks[i];
      dummy.position.set(x, y, z);
      dummy.rotation.set(i * 0.7, i * 1.3, i * 0.4);
      dummy.scale.setScalar(0.22 * scales[i]);
      dummy.updateMatrix();
      sim.rockMesh.setMatrixAt(i, dummy.matrix);
      if (sim.glintMesh && i % GLINT_STRIDE === 0) {
        const gi = i / GLINT_STRIDE;
        dummy.scale.setScalar(1); // glint geometry is already sized; don't inherit the rock's scale
        dummy.position.set(x, y + 0.05, z);
        dummy.updateMatrix();
        sim.glintMesh.setMatrixAt(gi, dummy.matrix);
      }
    }
    sim.rockMesh.instanceMatrix.needsUpdate = true;
    if (sim.glintMesh) sim.glintMesh.instanceMatrix.needsUpdate = true;
  }

  // #91: scrubbing the horizon tweens between the previous and new
  // predicted state over ~250ms instead of popping instantly.
  const HORIZON_TWEEN_MS = 250;

  function updateRocksPred(frame, horizonIdx, now) {
    const scales = state.rollout.rock_scale;
    const target = frame.predicted_horizon[horizonIdx];

    let from = null, tweenT = 1;
    const tr = state.horizonTransition;
    if (tr && tr.to === horizonIdx) {
      tweenT = Math.min(1, (now - tr.t0) / HORIZON_TWEEN_MS);
      if (tweenT < 1) from = frame.predicted_horizon[tr.from];
      else state.horizonTransition = null;
    }

    for (let i = 0; i < target.rocks.length; i++) {
      let x, y, z, e;
      if (from) {
        const fx = from.rocks[i], tx = target.rocks[i];
        x = lerp(fx[0], tx[0], tweenT);
        y = lerp(fx[1], tx[1], tweenT);
        z = lerp(fx[2], tx[2], tweenT);
        e = lerp(from.error[i], target.error[i], tweenT);
      } else {
        [x, y, z] = target.rocks[i];
        e = target.error[i];
      }
      dummy.position.set(x, y, z);
      dummy.rotation.set(i * 0.7, i * 1.3, i * 0.4);
      dummy.scale.setScalar(0.22 * scales[i]);
      dummy.updateMatrix();
      pred.rockMesh.setMatrixAt(i, dummy.matrix);
      maxErrorSeen.v = Math.max(maxErrorSeen.v * 0.998, e, 0.25);
      const c = errorColor(e, maxErrorSeen.v);
      pred.rockMesh.setColorAt(i, c);
    }
    pred.rockMesh.instanceMatrix.needsUpdate = true;
    pred.rockMesh.instanceColor.needsUpdate = true;
  }

  // #88: HUD numbers ease toward their target each frame rather than
  // snapping, reading as a live-ticking instrument. A brief "ticking"
  // colour cue shows while a value is still catching up to its target.
  const hudDisplay = { decision_ms: 0, prediction_error: 0 };

  function updateHud(frame, horizonIdx) {
    const hud = frame.hud;
    const h = frame.predicted_horizon[horizonIdx];
    const meanErr = h.error.reduce((a, b) => a + b, 0) / h.error.length;

    hudDisplay.decision_ms += (hud.decision_ms - hudDisplay.decision_ms) * 0.18;
    hudDisplay.prediction_error += (meanErr - hudDisplay.prediction_error) * 0.18;

    const decisionSettled = Math.abs(hud.decision_ms - hudDisplay.decision_ms) < 0.3;
    const errorSettled = Math.abs(meanErr - hudDisplay.prediction_error) < 0.003;

    els.hudDecision.textContent = `${hudDisplay.decision_ms.toFixed(0)} ms`;
    els.hudDecision.classList.toggle("ticking", !decisionSettled);
    els.hudError.textContent = `${hudDisplay.prediction_error.toFixed(2)} m`;
    els.hudError.classList.toggle("ticking", !errorSettled);
    els.hudEpisode.textContent = `#${hud.episode}`;
    els.hudState.textContent = hud.state;
    els.hudState.className = hud.state;
  }

  function updateDust(dust, seed, t) {
    const pos = dust.geometry.attributes.position;
    for (let i = 0; i < seed.length; i++) {
      const s = seed[i];
      pos.array[i * 3 + 1] += 0.0022;
      pos.array[i * 3 + 0] += Math.sin(t * 0.6 + s) * 0.0007;
      if (pos.array[i * 3 + 1] > 3.3) pos.array[i * 3 + 1] = 0.05;
    }
    pos.needsUpdate = true;
  }

  // #84: debris trickles DOWN from near the pile and recycles to the
  // top, the inverse of the dust system's slow upward drift.
  function updateDebris(debris, seed, t) {
    const pos = debris.geometry.attributes.position;
    for (let i = 0; i < seed.length; i++) {
      const s = seed[i];
      pos.array[i * 3 + 1] -= 0.006 + 0.003 * Math.sin(t * 2 + s);
      pos.array[i * 3 + 0] += Math.sin(t * 1.3 + s) * 0.0015;
      if (pos.array[i * 3 + 1] < 0.02) {
        pos.array[i * 3 + 1] = THREE.MathUtils.randFloat(1.1, 1.6);
        pos.array[i * 3 + 0] = THREE.MathUtils.randFloat(0.4, 2.6);
        pos.array[i * 3 + 2] = THREE.MathUtils.randFloat(-1.6, 0.4);
      }
    }
    pos.needsUpdate = true;
  }

  els.boulderBtn.addEventListener("click", () => {
    const boulderFrame = state.rollout.boulder_event_frame;
    const boulderT = (boulderFrame / state.frames.length) * state.duration;
    state.virtualT = boulderT;
    els.boulderBtn.disabled = true;
    setTimeout(() => { els.boulderBtn.disabled = false; }, 3600);
  });

  els.scrubber.addEventListener("input", () => {
    const newIdx = Number(els.scrubber.value);
    if (newIdx !== state.horizonIdx) {
      state.horizonTransition = { from: state.horizonIdx, to: newIdx, t0: performance.now() };
    }
    state.horizonIdx = newIdx;
    state.scrubbing = true;
    const dt = state.rollout.meta.horizon_steps_s[state.horizonIdx];
    els.scrubberReadout.textContent = `+${dt.toFixed(1)}s`;
    clearTimeout(state._scrubTimer);
    state._scrubTimer = setTimeout(() => { state.scrubbing = false; }, 2200);
  });

  resize();

  // Scratch objects reused every tick instead of allocated per frame --
  // this loop runs at display refresh rate for the life of the page.
  const _frame = { f0: null, f1: null, a: 0 };
  const _loaderPos = [0, 0, 0];
  const _loaderData = { pos: _loaderPos, heading: 0, boom: 0, bucket: 0 };

  let last = performance.now();
  function tick(now) {
    const dt = Math.max(0, Math.min((now - last) / 1000, 0.08));
    last = now;
    state.virtualT = (state.virtualT + dt) % state.duration;

    const { f0, f1, a } = frameAt(state.virtualT, _frame);

    lerpVec(_loaderPos, f0.loader.pos, f1.loader.pos, a);
    _loaderData.heading = lerp(f0.loader.heading, f1.loader.heading, a);
    _loaderData.boom = lerp(f0.loader.boom, f1.loader.boom, a);
    _loaderData.bucket = lerp(f0.loader.bucket, f1.loader.bucket, a);
    applyLoaderPose(sim.loader, _loaderData);
    applyLoaderPose(pred.loader, _loaderData);

    updateRocksSim(f0);
    updateRocksPred(f0, state.horizonIdx, now);
    updateHud(f0, state.horizonIdx);

    updateDust(sim.dust, sim.dustSeed, state.virtualT);
    updateDust(pred.dust, pred.dustSeed, state.virtualT);
    updateDebris(sim.debris, sim.debrisSeed, state.virtualT);
    updateDebris(pred.debris, pred.debrisSeed, state.virtualT);

    // #73: camera parallax, phased off wall-clock time (not virtualT) so
    // Drop boulder's playback jump doesn't also jump the camera drift.
    const pt = now / 1000;
    sim.camera.position.set(
      simBasePos.x + Math.sin(pt * 0.11) * 0.05,
      simBasePos.y + Math.sin(pt * 0.07 + 1.3) * 0.03,
      simBasePos.z
    );
    pred.camera.position.set(
      predBasePos.x + Math.sin(pt * 0.11) * 0.05,
      predBasePos.y + Math.sin(pt * 0.07 + 1.3) * 0.03,
      predBasePos.z
    );

    // ADR-0012: crossfade the loop seam instead of a visible pose snap.
    // distToSeam is 0 at the very start/end of the loop and
    // LOOP_VEIL_WINDOW_S away from it; smoothstep turns that into a
    // 0-1 fade amount for the FADE_SHADER uniform on both composers.
    const distToSeam = Math.min(state.virtualT, state.duration - state.virtualT);
    const veilAmount = 1 - THREE.MathUtils.smoothstep(distToSeam, 0, LOOP_VEIL_WINDOW_S);
    fadeSim.uniforms.amount.value = veilAmount;
    fadePred.uniforms.amount.value = veilAmount;

    composerSim.render();
    composerPred.render();
    requestAnimationFrame(tick);
  }

  els.stage.classList.add("visible");
  els.stage.setAttribute("aria-hidden", "false");
  requestAnimationFrame(tick);
}

runIntro(() => { main(); });
