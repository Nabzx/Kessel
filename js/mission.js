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
const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
camera.position.set(0, 0, 8.4);

const earthRoot = new THREE.Group();
earthRoot.rotation.z = THREE.MathUtils.degToRad(23.44);
earthRoot.position.x = innerWidth < 760 ? 0 : 1.55;
scene.add(earthRoot);

const earthGeometry = new THREE.SphereGeometry(2.38, mobile ? 72 : 112, mobile ? 48 : 80);
const earthMaterial = new THREE.MeshStandardMaterial({
  roughness: 1,
  metalness: 0,
  color: 0xffffff,
});
const earth = new THREE.Mesh(earthGeometry, earthMaterial);
earth.rotation.y = -THREE.MathUtils.degToRad(30.058333);
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
textureLoader.load("assets/earth-blue-marble-july.jpg", (texture) => {
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = Math.min(renderer.capabilities.getMaxAnisotropy(), 8);
  earthMaterial.map = texture;
  earthMaterial.needsUpdate = true;
  experience.classList.add("ready");
  const warp = document.getElementById("warp");
  if (!reducedMotion) warp.classList.add("active");
}, undefined, () => {
  document.getElementById("loading-status").textContent = "EARTH TEXTURE UNAVAILABLE";
});

textureLoader.load("assets/earth-black-marble-2016.jpg", (texture) => {
  nightUniforms.nightMap.value = texture;
  nightEarth.visible = true;
});
textureLoader.load("assets/earth-clouds.jpg", (texture) => {
  cloudMaterial.alphaMap = texture;
  cloudMaterial.needsUpdate = true;
});

const picker = document.getElementById("environment-options");
const pickerStatus = document.getElementById("picker-status");
const targetCoordinates = document.getElementById("target-coordinates");
const targetName = document.getElementById("target-name");
let missionState = "biome-select";

async function loadMission() {
  try {
    const response = await fetch("data/mission.json");
    if (!response.ok) throw new Error(`Mission data request failed: ${response.status}`);
    const mission = await response.json();
    const location = mission.location;
    const latitude = Math.abs(location.latitude).toFixed(2);
    const longitude = Math.abs(location.longitude).toFixed(2);
    targetCoordinates.innerHTML = `${latitude}° ${location.latitude < 0 ? "S" : "N"}<br />${longitude}° ${location.longitude < 0 ? "W" : "E"}`;
    targetName.textContent = `TARGET / ${location.name}, ${location.country}`;
    earth.rotation.y = -THREE.MathUtils.degToRad(location.longitude);
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
      picker.append(button);
    }
    pickerStatus.textContent = "Underground is available. Other environments are planned.";
  } catch (error) {
    pickerStatus.textContent = "Mission information is unavailable.";
    console.error(error);
  }
}
loadMission();

function resize() {
  const width = innerWidth;
  const height = innerHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.position.z = width < 760 ? 9.8 : 8.4;
  earthRoot.position.x = width < 760 ? 0 : 1.55;
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
  if (!reducedMotion) earth.rotation.y += delta * 0.025;
  nightEarth.rotation.y = earth.rotation.y;
  cloudEarth.rotation.y = earth.rotation.y + (reducedMotion ? 0 : Math.sin(time * 0.000012) * 0.012);
  earthRoot.getWorldPosition(earthWorldPosition);
  nightUniforms.sunDirection.value.copy(sun.position).sub(earthWorldPosition).normalize();
  renderer.render(scene, camera);
}
requestAnimationFrame(render);
