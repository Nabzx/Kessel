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
const undergroundRoot = new THREE.Group();
undergroundRoot.visible = false;
scene.add(undergroundRoot);

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
const enterUndergroundButton = document.getElementById("enter-underground");
const undergroundConsole = document.getElementById("underground-console");
let chooseUnderground = null;
let missionState = "biome-select";
let missionLocation = null;
let missionManifest = null;
let cameraTransition = null;
let portalTransition = null;
let undergroundStagePromise = null;
const targetWorldPosition = new THREE.Vector3();
const targetWorldNormal = new THREE.Vector3();
const projectedTarget = new THREE.Vector3();
const cameraToTarget = new THREE.Vector3();
const flightLookTarget = new THREE.Vector3();
let surfaceTerrainPromise = null;
let surfacePortal = null;
const surfaceLookTarget = new THREE.Vector3(-700, 370, 500);

function prepareSurfaceTerrain(surfaceAssets) {
  if (surfaceTerrainPromise) return surfaceTerrainPromise;
  const width = surfaceAssets.width_m;
  const elevationRange = surfaceAssets.elevation_max_m - surfaceAssets.elevation_min_m;
  surfaceTerrainPromise = new Promise((resolve, reject) => {
  const image = new Image();
  const heightImage = new Image();
  const loaded = Promise.all([
    new Promise((imageReady, imageError) => { image.onload = imageReady; image.onerror = imageError; }),
    new Promise((imageReady, imageError) => { heightImage.onload = imageReady; heightImage.onerror = imageError; }),
  ]);
  image.src = surfaceAssets.satellite_image;
  heightImage.src = surfaceAssets.elevation_heightmap;
  loaded.then(() => {
    const heightCanvas = document.createElement("canvas");
    heightCanvas.width = heightImage.naturalWidth;
    heightCanvas.height = heightImage.naturalHeight;
    const context = heightCanvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(heightImage, 0, 0);
    const samples = context.getImageData(0, 0, heightCanvas.width, heightCanvas.height).data;
    const elevationAt = (x, z) => {
      const px = Math.round(((x + width / 2) / width) * (heightCanvas.width - 1));
      const py = Math.round(((z + width / 2) / width) * (heightCanvas.height - 1));
      return surfaceAssets.elevation_min_m + (samples[(py * heightCanvas.width + px) * 4] / 255) * elevationRange;
    };
    const segments = heightCanvas.width - 1;
    const geometry = new THREE.PlaneGeometry(width, width, segments, heightCanvas.height - 1);
    geometry.rotateX(-Math.PI / 2);
    const positions = geometry.attributes.position;
    for (let i = 0; i < positions.count; i += 1) {
      positions.setY(i, surfaceAssets.elevation_min_m + (samples[i * 4] / 255) * elevationRange);
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

    const road = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-820, 0, 1900), new THREE.Vector3(-1030, 0, 1430),
      new THREE.Vector3(-900, 0, 1100), new THREE.Vector3(-820, 0, 760),
      new THREE.Vector3(-800, 0, 715),
    ]);
    const roadVertices = [];
    const roadIndices = [];
    const roadSteps = 64;
    for (let i = 0; i <= roadSteps; i += 1) {
      const t = i / roadSteps;
      const point = road.getPoint(t);
      const tangent = road.getTangent(t);
      const side = new THREE.Vector3(-tangent.z, 0, tangent.x).normalize().multiplyScalar(8);
      const y = elevationAt(point.x, point.z) + 0.8;
      roadVertices.push(point.x + side.x, y, point.z + side.z, point.x - side.x, y, point.z - side.z);
      if (i < roadSteps) {
        const start = i * 2;
        roadIndices.push(start, start + 2, start + 1, start + 1, start + 2, start + 3);
      }
    }
    const roadGeometry = new THREE.BufferGeometry();
    roadGeometry.setAttribute("position", new THREE.Float32BufferAttribute(roadVertices, 3));
    roadGeometry.setIndex(roadIndices);
    roadGeometry.computeVertexNormals();
    surfaceRoot.add(new THREE.Mesh(roadGeometry, new THREE.MeshStandardMaterial({ color: 0x4e4c43, roughness: 1 })));

    const portalConfig = surfaceAssets.portal;
    const portalX = portalConfig.x_m;
    const portalZ = portalConfig.z_m;
    const portal = new THREE.Group();
    portal.name = "illustrative-mine-portal";
    portal.userData.isMineEntrance = true;
    portal.position.set(portalX, elevationAt(portalX, portalZ), portalZ);
    surfacePortal = portal;
    surfaceRoot.add(portal);
    const apron = new THREE.Mesh(new THREE.BoxGeometry(38, 1.2, 34), new THREE.MeshStandardMaterial({ color: 0x635f53, roughness: 1 }));
    apron.position.set(0, 0.2, 2);
    portal.add(apron);

    const openingShape = new THREE.Shape();
    const halfAperture = portalConfig.aperture_width_m / 2;
    const apertureHeight = portalConfig.aperture_height_m;
    openingShape.moveTo(-halfAperture, 0);
    openingShape.lineTo(-halfAperture, apertureHeight / 2);
    openingShape.quadraticCurveTo(-halfAperture, apertureHeight, 0, apertureHeight);
    openingShape.quadraticCurveTo(halfAperture, apertureHeight, halfAperture, apertureHeight / 2);
    openingShape.lineTo(halfAperture, 0);
    openingShape.closePath();
    const opening = new THREE.Mesh(new THREE.ShapeGeometry(openingShape), new THREE.MeshBasicMaterial({ color: 0x030405, side: THREE.DoubleSide }));
    opening.position.set(0, 0, 0.5);
    portal.add(opening);
    const arch = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-1.9, 0.1, 0.75), new THREE.Vector3(-1.9, 1.5, 0.75),
      new THREE.Vector3(-1.65, 2.45, 0.75), new THREE.Vector3(-0.8, 3.35, 0.75),
      new THREE.Vector3(0, 3.55, 0.75), new THREE.Vector3(0.8, 3.35, 0.75),
      new THREE.Vector3(1.65, 2.45, 0.75), new THREE.Vector3(1.9, 1.5, 0.75),
      new THREE.Vector3(1.9, 0.1, 0.75),
    ]);
    portal.add(new THREE.Mesh(new THREE.TubeGeometry(arch, 40, 0.18, 8, false), new THREE.MeshStandardMaterial({ color: 0x9a8060, metalness: 0.5, roughness: 0.62 })));
    for (const side of [-1, 1]) {
      const lamp = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.75, 0.2), new THREE.MeshBasicMaterial({ color: 0xffbd68 }));
      lamp.position.set(side * 2.3, 2.8, 1);
      portal.add(lamp);
    }
    const portalMarker = new THREE.Mesh(
      new THREE.RingGeometry(portalConfig.marker_radius_m - 1, portalConfig.marker_radius_m, 64),
      new THREE.MeshBasicMaterial({ color: 0xffbd68, transparent: true, opacity: 0.68, side: THREE.DoubleSide, depthWrite: false }),
    );
    portalMarker.rotation.x = -Math.PI / 2;
    portalMarker.position.y = 1.4;
    portalMarker.name = "illustrative-portal-marker";
    portal.add(portalMarker);

    const addServiceShed = (x, z, width, height, depth) => {
      const shed = new THREE.Group();
      shed.position.set(x, elevationAt(x, z), z);
      surfaceRoot.add(shed);
      const building = new THREE.Mesh(new THREE.BoxGeometry(width, height, depth), new THREE.MeshStandardMaterial({ color: 0x77776d, roughness: 0.92 }));
      building.position.y = height / 2;
      shed.add(building);
      const roof = new THREE.Mesh(new THREE.BoxGeometry(width + 2, 1, depth + 2), new THREE.MeshStandardMaterial({ color: 0x343b3c, roughness: 0.88 }));
      roof.position.y = height + 0.5;
      shed.add(roof);
    };
    addServiceShed(-525, 420, 24, 9, 18);
    addServiceShed(-485, 460, 16, 6, 12);
    const stockpile = new THREE.Mesh(new THREE.ConeGeometry(10, 6, 12), new THREE.MeshStandardMaterial({ color: 0x625b4d, roughness: 1 }));
    stockpile.position.set(-510, elevationAt(-510, 380) + 3, 380);
    surfaceRoot.add(stockpile);
    resolve();
  }).catch(reject);
  });
}

async function finishGlobeFlight() {
  if (!cameraTransition) return;
  const completedTransition = cameraTransition;
  cameraTransition = null;
  try {
    await prepareSurfaceTerrain(missionManifest.assets.surface);
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
  camera.position.copy(surfacePortal.position).add(new THREE.Vector3(-400, 850, 900));
  camera.fov = 47;
  camera.updateProjectionMatrix();
  surfaceLookTarget.copy(surfacePortal.position);
  camera.lookAt(surfaceLookTarget);
  cameraTransition = null;
  skipFlightButton.hidden = true;
  flightStatus.textContent = `ARRIVED / ${missionLocation.name.toUpperCase()}`;
  experience.classList.remove("descending");
  experience.classList.add("surface-arrived");
  surfaceConsole.hidden = false;
  surfaceCredit.hidden = false;
  missionState = "surface-arrived";
  enterUndergroundButton.hidden = false;
  await new Promise((resolve) => setTimeout(resolve, 820));
  experience.classList.remove("surface-transition");
  window.dispatchEvent(new CustomEvent("kessel:surface-arrival", { detail: { location: missionLocation } }));
}

function beginGlobeFlight(location) {
  if (cameraTransition) return;
  prepareSurfaceTerrain(missionManifest.assets.surface).catch((error) => {
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
    missionManifest = mission;
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

async function prepareUndergroundStage() {
  if (undergroundStagePromise) return undergroundStagePromise;
  undergroundStagePromise = (async () => {
    const assets = missionManifest.assets.underground;
    const response = await fetch(assets.network_geometry);
    if (!response.ok) throw new Error(`Tunnel network request failed: ${response.status}`);
    const network = await response.json();
    const rendererModule = await import(new URL(assets.renderer, document.baseURI));
    const root = await rendererModule.createUndergroundStage(network, { mobile });
    if (!surfacePortal) throw new Error("Mine entrance is not ready");
    root.position.copy(surfacePortal.position);
    undergroundRoot.add(root);
    undergroundRoot.visible = false;
    undergroundRoot.userData.dispose = () => rendererModule.disposeUndergroundStage(root);
    undergroundRoot.userData.stage = root;
    return root;
  })();
  try {
    return await undergroundStagePromise;
  } catch (error) {
    undergroundStagePromise = null;
    throw error;
  }
}

function disposeSurfaceStage() {
  const geometries = new Set();
  const materials = new Set();
  const textures = new Set();
  surfaceRoot.traverse((object) => {
    if (object.geometry) geometries.add(object.geometry);
    const list = Array.isArray(object.material) ? object.material : [object.material];
    for (const material of list) {
      if (!material) continue;
      materials.add(material);
      for (const value of Object.values(material)) {
        if (value?.isTexture) textures.add(value);
      }
    }
  });
  for (const geometry of geometries) geometry.dispose();
  for (const texture of textures) texture.dispose();
  for (const material of materials) material.dispose();
  surfaceRoot.clear();
  scene.remove(surfaceRoot);
}

async function beginPortalTransition() {
  if (missionState !== "surface-arrived" || portalTransition) return;
  enterUndergroundButton.disabled = true;
  enterUndergroundButton.querySelector("span").textContent = "PREPARING";
  flightStatus.textContent = "PREPARING TUNNEL NETWORK";
  try {
    await prepareUndergroundStage();
  } catch (error) {
    enterUndergroundButton.disabled = false;
    enterUndergroundButton.querySelector("span").textContent = "DESCEND ›";
    flightStatus.textContent = "TUNNEL DATA UNAVAILABLE";
    console.error("Underground stage could not be loaded", error);
    return;
  }
  if (missionState !== "surface-arrived" || !surfacePortal) return;
  missionState = "surface-transition";
  const fromPosition = camera.position.clone();
  const fromLookTarget = surfaceLookTarget.clone();
  const targetPosition = surfacePortal.position.clone().add(new THREE.Vector3(0, 1.5, -5));
  const targetLook = surfacePortal.position.clone().add(new THREE.Vector3(0, 1.5, -34));
  const duration = reducedMotion ? 650 : 4200;
  portalTransition = {
    start: performance.now(),
    duration,
    fromPosition,
    fromLookTarget,
    targetPosition,
    targetLook,
    fromFov: camera.fov,
    switched: false,
  };
  experience.style.setProperty("--portal-duration", `${duration}ms`);
  experience.classList.add("portal-entering");
  enterUndergroundButton.hidden = true;
  flightStatus.textContent = "ENTERING / RUTONGO SCENARIO";
}

function updatePortalTransition(now) {
  if (!portalTransition) return;
  const progress = Math.min((now - portalTransition.start) / portalTransition.duration, 1);
  const eased = progress * progress * (3 - 2 * progress);
  camera.position.lerpVectors(portalTransition.fromPosition, portalTransition.targetPosition, eased);
  flightLookTarget.lerpVectors(portalTransition.fromLookTarget, portalTransition.targetLook, eased);
  camera.fov = THREE.MathUtils.lerp(portalTransition.fromFov, 56, eased);
  camera.updateProjectionMatrix();
  camera.lookAt(flightLookTarget);

  if (!portalTransition.switched && progress >= 0.9) {
    portalTransition.switched = true;
    surfaceRoot.visible = false;
    undergroundRoot.visible = true;
    scene.background.set(0x07090a);
    scene.fog = new THREE.Fog(0x07090a, 75, 310);
    camera.near = 0.1;
    camera.far = 600;
    camera.updateProjectionMatrix();
    disposeSurfaceStage();
  }
  if (progress >= 1) {
    portalTransition = null;
    missionState = "fleet";
    experience.classList.remove("portal-entering");
    experience.classList.remove("surface-arrived");
    surfaceConsole.hidden = true;
    surfaceCredit.hidden = true;
    undergroundConsole.hidden = false;
    flightStatus.textContent = "UNDERGROUND / LEVEL 01";
    window.dispatchEvent(new CustomEvent("kessel:descentcomplete", { detail: { location: missionLocation } }));
  }
}

loadMission();
window.addEventListener("kessel:statechange", (event) => {
  if (event.detail.to === "surface-descent") beginGlobeFlight(event.detail.location);
});
skipFlightButton.addEventListener("click", finishGlobeFlight);
enterUndergroundButton.addEventListener("click", beginPortalTransition);

function resize() {
  const width = innerWidth;
  const height = innerHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  if (portalTransition) {
    camera.updateProjectionMatrix();
  } else if (missionState === "surface-arrived") {
    if (surfacePortal) camera.position.copy(surfacePortal.position).add(new THREE.Vector3(-400, width <= 760 ? 1100 : 850, width <= 760 ? 1250 : 900));
    camera.lookAt(surfaceLookTarget);
  } else if (missionState !== "fleet" && missionState !== "truck" && missionState !== "override") {
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
  updatePortalTransition(time);
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
