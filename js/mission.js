import * as THREE from "three";

const canvas = document.getElementById("space-canvas");
const experience = document.getElementById("mission");
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const mobile = matchMedia("(max-width: 760px)").matches;
const renderer = new THREE.WebGLRenderer({ canvas, antialias: !mobile, alpha: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, mobile ? 1.5 : 1.8));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.12;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x03070d);
const Y_AXIS = new THREE.Vector3(0, 1, 0);
const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
camera.position.set(0, 0, 8.4);
camera.lookAt(0, 0, 0);

const earthRoot = new THREE.Group();
earthRoot.rotation.z = THREE.MathUtils.degToRad(23.44);
earthRoot.position.x = innerWidth <= 760 ? 0 : 1.55;
scene.add(earthRoot);
const surfaceRoot = new THREE.Group();
surfaceRoot.visible = false;
scene.add(surfaceRoot);

const earthGeometry = new THREE.SphereGeometry(2.38, mobile ? 72 : 112, mobile ? 48 : 80);
const earthMaterial = new THREE.MeshStandardMaterial({
  roughness: 1,
  metalness: 0,
  color: 0xffffff,
});
const earth = new THREE.Mesh(earthGeometry, earthMaterial);
earth.rotation.y = 0;
earthRoot.add(earth);

const nightUniforms = {
  nightMap: { value: null },
  sunDirection: { value: new THREE.Vector3(-5.5, 3.8, 7.5).normalize() },
};
const nightMaterial = new THREE.ShaderMaterial({
  uniforms: nightUniforms,
  vertexShader: `
    varying vec2 vUv;
    varying vec3 vNormalWorld;
    void main() {
      vUv = uv;
      vNormalWorld = normalize(mat3(modelMatrix) * normal);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D nightMap;
    uniform vec3 sunDirection;
    varying vec2 vUv;
    varying vec3 vNormalWorld;
    void main() {
      float daylight = dot(normalize(vNormalWorld), normalize(sunDirection));
      float night = 1.0 - smoothstep(-0.13, 0.12, daylight);
      float cityLight = dot(texture2D(nightMap, vUv).rgb, vec3(0.299, 0.587, 0.114));
      vec3 glow = vec3(1.0, 0.56, 0.24) * cityLight * night * 1.8;
      gl_FragColor = vec4(glow, cityLight * night);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }
  `,
  transparent: true,
  blending: THREE.AdditiveBlending,
  depthWrite: false,
});
const nightEarth = new THREE.Mesh(new THREE.SphereGeometry(2.386, mobile ? 72 : 112, mobile ? 48 : 80), nightMaterial);
nightEarth.rotation.y = earth.rotation.y;
nightEarth.visible = false;
nightEarth.renderOrder = 1;
earthRoot.add(nightEarth);

const cloudMaterial = new THREE.MeshBasicMaterial({
  color: 0xc2e5ef,
  transparent: true,
  opacity: 0.23,
  alphaTest: 0.025,
  depthWrite: false,
});
const cloudEarth = new THREE.Mesh(new THREE.SphereGeometry(2.405, mobile ? 72 : 112, mobile ? 48 : 80), cloudMaterial);
cloudEarth.rotation.y = earth.rotation.y;
cloudEarth.renderOrder = 2;
earthRoot.add(cloudEarth);

const surfaceMarkers = new THREE.Group();
earthRoot.add(surfaceMarkers);

const atmosphereMaterial = new THREE.ShaderMaterial({
  vertexShader: `
    varying vec3 vNormalWorld;
    varying vec3 vPositionWorld;
    void main() {
      vec4 worldPosition = modelMatrix * vec4(position, 1.0);
      vPositionWorld = worldPosition.xyz;
      vNormalWorld = normalize(mat3(modelMatrix) * normal);
      gl_Position = projectionMatrix * viewMatrix * worldPosition;
    }
  `,
  fragmentShader: `
    varying vec3 vNormalWorld;
    varying vec3 vPositionWorld;
    void main() {
      vec3 viewDirection = normalize(cameraPosition - vPositionWorld);
      float rim = pow(1.0 - max(dot(normalize(vNormalWorld), viewDirection), 0.0), 3.2);
      float daylight = max(dot(normalize(vNormalWorld), normalize(vec3(-0.5, 0.35, 0.8))), 0.0);
      vec3 hue = mix(vec3(0.06, 0.25, 0.5), vec3(0.16, 0.62, 0.84), daylight);
      gl_FragColor = vec4(hue, rim * 0.42);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }
  `,
  side: THREE.BackSide,
  transparent: true,
  blending: THREE.AdditiveBlending,
  depthWrite: false,
});
const atmosphere = new THREE.Mesh(new THREE.SphereGeometry(2.49, mobile ? 72 : 112, mobile ? 48 : 80), atmosphereMaterial);
atmosphere.renderOrder = 3;
earthRoot.add(atmosphere);

scene.add(new THREE.AmbientLight(0x263746, 0.44));
const sun = new THREE.DirectionalLight(0xfff2da, 3.0);
sun.position.set(-5.5, 3.8, 7.5);
scene.add(sun);

const starsGeometry = new THREE.BufferGeometry();
const starPositions = new Float32Array(1100 * 3);
let seed = 741;
function random() {
  seed = (seed * 16807) % 2147483647;
  return (seed - 1) / 2147483646;
}
for (let i = 0; i < starPositions.length; i += 3) {
  const radius = 13 + random() * 35;
  const theta = random() * Math.PI * 2;
  const y = random() * 2 - 1;
  const ring = Math.sqrt(1 - y * y);
  starPositions[i] = Math.cos(theta) * ring * radius;
  starPositions[i + 1] = y * radius;
  starPositions[i + 2] = Math.sin(theta) * ring * radius;
}
starsGeometry.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
const stars = new THREE.Points(starsGeometry, new THREE.PointsMaterial({ color: 0xa8cfe2, size: 0.055, sizeAttenuation: true, transparent: true, opacity: 0.78 }));
scene.add(stars);

const textureLoader = new THREE.TextureLoader();
const picker = document.getElementById("environment-options");
const pickerStatus = document.getElementById("picker-status");
const targetCoordinates = document.getElementById("target-coordinates");
const targetName = document.getElementById("target-name");
const targetButton = document.getElementById("rutongo-marker");
const skipFlightButton = document.getElementById("skip-flight");
const flightStatus = document.getElementById("flight-status");
const surfaceConsole = document.getElementById("surface-console");
const surfaceCredit = document.getElementById("surface-credit");
let chooseUnderground = null;
let missionState = "biome-select";
let missionLocation = null;
let cameraTransition = null;
const targetWorldPosition = new THREE.Vector3();
const targetWorldNormal = new THREE.Vector3();
const projectedTarget = new THREE.Vector3();
const cameraToTarget = new THREE.Vector3();
const flightLookTarget = new THREE.Vector3();
let surfaceTerrainPromise = null;

function prepareSurfaceTerrain() {
  if (surfaceTerrainPromise) return surfaceTerrainPromise;
  surfaceTerrainPromise = new Promise((resolve, reject) => {
  const image = new Image();
  const heightImage = new Image();
  const loaded = Promise.all([
    new Promise((imageReady, imageError) => { image.onload = imageReady; image.onerror = imageError; }),
    new Promise((imageReady, imageError) => { heightImage.onload = imageReady; heightImage.onerror = imageError; }),
  ]);
  image.src = "assets/rutongo/satellite-2026-08-14.webp";
  heightImage.src = "assets/rutongo/elevation-30m-4km.png";
  loaded.then(() => {
    const heightCanvas = document.createElement("canvas");
    heightCanvas.width = heightImage.naturalWidth;
    heightCanvas.height = heightImage.naturalHeight;
    const context = heightCanvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(heightImage, 0, 0);
    const samples = context.getImageData(0, 0, heightCanvas.width, heightCanvas.height).data;
    const segments = heightCanvas.width - 1;
    const geometry = new THREE.PlaneGeometry(4096, 4096, segments, heightCanvas.height - 1);
    geometry.rotateX(-Math.PI / 2);
    const positions = geometry.attributes.position;
    for (let i = 0; i < positions.count; i += 1) {
      positions.setY(i, (samples[i * 4] / 255) * 429);
    }
    positions.needsUpdate = true;
    geometry.computeVertexNormals();
    const texture = new THREE.Texture(image);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.needsUpdate = true;
    const terrain = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ map: texture, roughness: 1, metalness: 0 }));
    terrain.receiveShadow = false;
    surfaceRoot.add(terrain);
    const base = new THREE.Mesh(new THREE.PlaneGeometry(30000, 30000), new THREE.MeshStandardMaterial({ color: 0x625d48, roughness: 1 }));
    base.rotation.x = -Math.PI / 2;
    base.position.y = -4;
    surfaceRoot.add(base);
    surfaceRoot.add(new THREE.HemisphereLight(0xd5e6ef, 0x5c4e3a, 1.6));
    const sun = new THREE.DirectionalLight(0xffe4bc, 2.2);
    sun.position.set(-1800, 2600, 1200);
    surfaceRoot.add(sun);
    resolve();
  }).catch(reject);
  });
}

async function finishGlobeFlight() {
  if (!cameraTransition) return;
  const completedTransition = cameraTransition;
  cameraTransition = null;
  try {
    await prepareSurfaceTerrain();
  } catch (error) {
    skipFlightButton.hidden = true;
    flightStatus.textContent = "SURFACE DATA UNAVAILABLE";
    console.error("Rutongo surface data could not be loaded", error);
    return;
  }
  experience.classList.add("surface-transition");
  await new Promise((resolve) => setTimeout(resolve, 680));
  earth.rotation.y = completedTransition.toEarthRotation;
  earthRoot.visible = false;
  surfaceMarkers.visible = false;
  stars.visible = false;
  surfaceRoot.visible = true;
  scene.background.set(0x7c8982);
  scene.fog = new THREE.Fog(0x7c8982, 3800, 11500);
  camera.near = 1;
  camera.far = 40000;
  camera.position.set(0, 2600, 2500);
  camera.fov = 47;
  camera.updateProjectionMatrix();
  camera.lookAt(0, 100, 0);
  cameraTransition = null;
  skipFlightButton.hidden = true;
  flightStatus.textContent = `ARRIVED / ${missionLocation.name.toUpperCase()}`;
  experience.classList.remove("descending");
  experience.classList.add("surface-arrived");
  surfaceConsole.hidden = false;
  surfaceCredit.hidden = false;
  await new Promise((resolve) => setTimeout(resolve, 820));
  experience.classList.remove("surface-transition");
  window.dispatchEvent(new CustomEvent("kessel:descentcomplete", { detail: { location: missionLocation } }));
}

function beginGlobeFlight(location) {
  if (cameraTransition) return;
  prepareSurfaceTerrain().catch((error) => {
    flightStatus.textContent = "SURFACE DATA UNAVAILABLE";
    console.error("Rutongo surface data could not be loaded", error);
  });
  const baseRotation = -THREE.MathUtils.degToRad(location.longitude + 90);
  const fullTurn = Math.PI * 2;
  const nearestTurn = Math.round((earth.rotation.y - baseRotation) / fullTurn);
  const toEarthRotation = baseRotation + nearestTurn * fullTurn;
  const targetNormal = geographicNormal(location.latitude, location.longitude)
    .applyAxisAngle(Y_AXIS, toEarthRotation)
    .applyQuaternion(earthRoot.quaternion)
    .normalize();
  const earthCentre = earthRoot.getWorldPosition(new THREE.Vector3());
  const toLookTarget = earthCentre.clone().addScaledVector(targetNormal, 2.38);
  const toCameraPosition = earthCentre.clone().addScaledVector(targetNormal, 3.85);
  const duration = reducedMotion ? 240 : 6200;
  cameraTransition = {
    start: performance.now(),
    duration,
    fromEarthRotation: earth.rotation.y,
    toEarthRotation,
    fromCameraPosition: camera.position.clone(),
    toCameraPosition,
    fromLookTarget: new THREE.Vector3(0, 0, 0),
    toLookTarget,
    fromFov: camera.fov,
    toFov: reducedMotion ? camera.fov : 24,
  };
  experience.classList.add("descending");
  targetButton.hidden = true;
  skipFlightButton.hidden = false;
  flightStatus.hidden = false;
  flightStatus.textContent = `DESCENDING / ${location.name.toUpperCase()}`;
}

function updateCameraTransition(now) {
  if (!cameraTransition) return;
  const progress = Math.min((now - cameraTransition.start) / cameraTransition.duration, 1);
  const eased = progress < 0.5
    ? 4 * progress * progress * progress
    : 1 - Math.pow(-2 * progress + 2, 3) / 2;
  earth.rotation.y = THREE.MathUtils.lerp(cameraTransition.fromEarthRotation, cameraTransition.toEarthRotation, eased);
  camera.position.lerpVectors(cameraTransition.fromCameraPosition, cameraTransition.toCameraPosition, eased);
  flightLookTarget.lerpVectors(cameraTransition.fromLookTarget, cameraTransition.toLookTarget, eased);
  camera.fov = THREE.MathUtils.lerp(cameraTransition.fromFov, cameraTransition.toFov, eased);
  camera.updateProjectionMatrix();
  camera.lookAt(flightLookTarget);
  if (progress >= 1) finishGlobeFlight();
}

function geographicNormal(latitude, longitude) {
  const lat = THREE.MathUtils.degToRad(latitude);
  const lon = THREE.MathUtils.degToRad(longitude);
  const cosLat = Math.cos(lat);
  return new THREE.Vector3(cosLat * Math.cos(lon), Math.sin(lat), -cosLat * Math.sin(lon));
}

async function loadDepositMarkers(path, location) {
  try {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`Deposit data request failed: ${response.status}`);
    const depositData = await response.json();
    const positions = new Float32Array(depositData.markers.length * 3);
    const colors = new Float32Array(depositData.markers.length * 3);
    depositData.markers.forEach((marker, index) => {
      const point = geographicNormal(marker.latitude, marker.longitude).multiplyScalar(2.425);
      positions.set([point.x, point.y, point.z], index * 3);
      const tin = marker.commodities.includes("tin");
      const tantalum = marker.commodities.includes("tantalum");
      const color = tin && tantalum ? [0.82, 0.9, 0.78] : tin ? [0.22, 0.74, 0.86] : [1, 0.54, 0.2];
      colors.set(color, index * 3);
    });
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    const material = new THREE.PointsMaterial({
      size: mobile ? 2.5 : 3.2,
      sizeAttenuation: false,
      vertexColors: true,
      transparent: true,
      opacity: 0.88,
      depthWrite: false,
    });
    surfaceMarkers.add(new THREE.Points(geometry, material));

    const targetNormal = geographicNormal(location.latitude, location.longitude);
    const target = new THREE.Group();
    target.position.copy(targetNormal).multiplyScalar(2.435);
    target.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), targetNormal);
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.025, 0.04, 40),
      new THREE.MeshBasicMaterial({ color: 0x74d7e8, side: THREE.DoubleSide, transparent: true, opacity: 0.9 }),
    );
    ring.position.z = 0.003;
    target.add(ring);
    const targetLight = new THREE.Mesh(
      new THREE.SphereGeometry(0.018, 12, 8),
      new THREE.MeshBasicMaterial({ color: 0xd7fbff }),
    );
    targetLight.position.z = 0.008;
    target.add(targetLight);
    surfaceMarkers.add(target);
    targetButton.hidden = false;
    if (missionState === "biome-select") {
      pickerStatus.textContent = `${depositData.markers.length.toLocaleString()} historical tin and tantalum locations loaded. Rutongo is the selected target.`;
    }
  } catch (error) {
    pickerStatus.textContent = "The globe is ready. Deposit markers could not be loaded.";
    console.error(error);
  }
}

async function loadMission() {
  try {
    const response = await fetch("data/mission.json");
    if (!response.ok) throw new Error(`Mission data request failed: ${response.status}`);
    const mission = await response.json();
    const location = mission.location;
    missionLocation = location;
    const latitude = Math.abs(location.latitude).toFixed(2);
    const longitude = Math.abs(location.longitude).toFixed(2);
    targetCoordinates.innerHTML = `${latitude}° ${location.latitude < 0 ? "S" : "N"}<br />${longitude}° ${location.longitude < 0 ? "W" : "E"}`;
    targetName.textContent = `TARGET / ${location.name}, ${location.country}`;
    earth.rotation.y = -THREE.MathUtils.degToRad(location.longitude + 90);
    const globeAssets = mission.assets.globe;
    textureLoader.load(globeAssets.day_map, (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.anisotropy = Math.min(renderer.capabilities.getMaxAnisotropy(), 8);
      earthMaterial.map = texture;
      earthMaterial.needsUpdate = true;
      experience.classList.add("ready");
      const warp = document.getElementById("warp");
      if (!reducedMotion) warp.classList.add("active");
      const defer = window.requestIdleCallback || ((callback) => setTimeout(callback, 1200));
      defer(() => loadDepositMarkers(mission.assets.deposit_markers, location), { timeout: 1800 });
    }, undefined, () => {
      document.getElementById("loading-status").textContent = "EARTH TEXTURE UNAVAILABLE";
    });
    textureLoader.load(globeAssets.night_lights, (texture) => {
      nightUniforms.nightMap.value = texture;
      nightEarth.visible = true;
    });
    textureLoader.load(globeAssets.clouds, (texture) => {
      cloudMaterial.alphaMap = texture;
      cloudMaterial.needsUpdate = true;
    });
    for (const environment of mission.environments) {
      const live = environment.status === "available";
      const button = document.createElement("button");
      button.type = "button";
      button.className = `environment-option ${live ? "is-live" : "is-locked"}`;
      button.dataset.environment = environment.id;
      button.setAttribute("aria-disabled", String(!live));
      button.setAttribute("aria-pressed", "false");
      button.setAttribute("aria-describedby", "picker-status");
      button.title = live ? `${environment.label} is available` : `${environment.label} is planned and not available yet`;
      const stateLabel = live ? "AVAILABLE" : "PLANNED";
      button.innerHTML = `<span class="option-glyph" aria-hidden="true">${environment.glyph}</span><span class="option-label">${environment.label}<span class="option-state">${stateLabel}</span></span><span class="option-summary">${environment.summary}</span>`;
      button.addEventListener("click", () => {
        if (!live) {
          pickerStatus.textContent = `${environment.label} is planned. Underground is the only available environment.`;
          return;
        }
        if (missionState !== "biome-select") return;
        missionState = "surface-descent";
        pickerStatus.textContent = `Underground selected. Preparing descent to ${location.name}.`;
        for (const option of picker.children) option.setAttribute("aria-pressed", String(option === button));
        window.dispatchEvent(new CustomEvent("kessel:statechange", { detail: { from: "biome-select", to: missionState, location } }));
      });
      if (live) chooseUnderground = () => button.click();
      picker.append(button);
    }
    pickerStatus.textContent = "Underground is available. Other environments are planned.";
    targetButton.addEventListener("click", () => chooseUnderground?.());
  } catch (error) {
    pickerStatus.textContent = "Mission information is unavailable.";
    console.error(error);
  }
}
loadMission();
window.addEventListener("kessel:statechange", (event) => {
  if (event.detail.to === "surface-descent") beginGlobeFlight(event.detail.location);
});
skipFlightButton.addEventListener("click", finishGlobeFlight);

function resize() {
  const width = innerWidth;
  const height = innerHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  if (experience.classList.contains("surface-arrived")) {
    camera.position.set(0, width <= 760 ? 3100 : 2600, width <= 760 ? 3000 : 2500);
    camera.lookAt(0, 100, 0);
  } else {
    camera.position.z = width <= 760 ? 9.8 : 8.4;
  }
  earthRoot.position.x = width <= 760 ? 0 : 1.55;
  camera.updateProjectionMatrix();
}
addEventListener("resize", resize, { passive: true });
resize();

let lastTime = 0;
const earthWorldPosition = new THREE.Vector3();
function render(time) {
  requestAnimationFrame(render);
  const delta = lastTime ? Math.min((time - lastTime) / 1000, 0.05) : 0;
  lastTime = time;
  if (!reducedMotion && missionState === "biome-select") earth.rotation.y += delta * 0.025;
  updateCameraTransition(time);
  nightEarth.rotation.y = earth.rotation.y;
  surfaceMarkers.rotation.y = earth.rotation.y;
  cloudEarth.rotation.y = earth.rotation.y + (reducedMotion ? 0 : Math.sin(time * 0.000012) * 0.012);
  earthRoot.getWorldPosition(earthWorldPosition);
  nightUniforms.sunDirection.value.copy(sun.position).sub(earthWorldPosition).normalize();
  if (missionLocation && !targetButton.hidden) {
    targetWorldPosition.copy(geographicNormal(missionLocation.latitude, missionLocation.longitude)).multiplyScalar(2.44);
    targetWorldPosition.applyAxisAngle(Y_AXIS, earth.rotation.y).applyQuaternion(earthRoot.quaternion).add(earthRoot.position);
    targetWorldNormal.copy(geographicNormal(missionLocation.latitude, missionLocation.longitude));
    targetWorldNormal.applyAxisAngle(Y_AXIS, earth.rotation.y).applyQuaternion(earthRoot.quaternion);
    projectedTarget.copy(targetWorldPosition).project(camera);
    cameraToTarget.copy(camera.position).sub(targetWorldPosition);
    const visible = targetWorldNormal.dot(cameraToTarget) > 0 && projectedTarget.z >= -1 && projectedTarget.z <= 1;
    targetButton.hidden = !visible;
    if (visible) {
      targetButton.style.left = `${(projectedTarget.x * 0.5 + 0.5) * innerWidth}px`;
      targetButton.style.top = `${(-projectedTarget.y * 0.5 + 0.5) * innerHeight}px`;
    }
  }
  renderer.render(scene, camera);
}
requestAnimationFrame(render);
