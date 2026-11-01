import * as THREE from "three";

const canvas = document.getElementById("space-canvas");
const experience = document.getElementById("mission");
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
let mobile = matchMedia("(max-width: 760px)").matches;
const renderer = new THREE.WebGLRenderer({ canvas, antialias: !mobile, alpha: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, mobile ? 1.25 : 1.5));
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
cloudEarth.visible = false;
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
const fleetMode = document.getElementById("fleet-mode");
const fleetCaption = document.getElementById("fleet-caption");
const runOptimiserButton = document.getElementById("run-optimiser");
const returnFleetButton = document.getElementById("return-fleet");
const simulationStatus = document.getElementById("simulation-status");
const worldModelNote = document.getElementById("world-model-note");
const metricThroughput = document.getElementById("metric-throughput");
const metricCycle = document.getElementById("metric-cycle");
const metricUtilisation = document.getElementById("metric-utilisation");
const metricQueue = document.getElementById("metric-queue");
const cycleReference = document.getElementById("cycle-reference");
const cycleReferenceLink = document.getElementById("cycle-reference-link");
const surfaceMap=document.getElementById("surface-map");
const satelliteMap=document.getElementById("satellite-map");
const viewSatellite=document.getElementById("view-satellite");
const viewSite=document.getElementById("view-site");
const onlineMapAllowed=!new URLSearchParams(location.search).has("offline");
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
let simTimeouts = [];
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const roster = document.getElementById("fleet-roster");
const labels = document.getElementById("truck-labels");
const insight = document.getElementById("mission-insight");
const steps = document.getElementById("mission-steps");
const simulationProgress = document.getElementById("simulation-progress");
const horizonSlider = document.getElementById("prediction-horizon");
const tagElements = new Map();
const rosterElements = new Map();
const followPosition = new THREE.Vector3();
const followTarget = new THREE.Vector3();
const labelPosition = new THREE.Vector3();
let hudUpdated = 0;
let visiblePage = true;
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
  loaded.then(async () => {
    const groundDetail=await textureLoader.loadAsync(surfaceAssets.site.ground_detail);
    groundDetail.wrapS=groundDetail.wrapT=THREE.RepeatWrapping;
    groundDetail.colorSpace=THREE.SRGBColorSpace;
    groundDetail.anisotropy=4;
    const heightCanvas = document.createElement("canvas");
    heightCanvas.width = heightImage.naturalWidth;
    heightCanvas.height = heightImage.naturalHeight;
    const context = heightCanvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(heightImage, 0, 0);
    const samples = context.getImageData(0, 0, heightCanvas.width, heightCanvas.height).data;
    const rawElevationAt = (x, z) => {
      const fx = THREE.MathUtils.clamp(((x+width/2)/width)*(heightCanvas.width-1),0,heightCanvas.width-1);
      const fy = THREE.MathUtils.clamp(((z+width/2)/width)*(heightCanvas.height-1),0,heightCanvas.height-1);
      const x0=Math.floor(fx), y0=Math.floor(fy), x1=Math.min(x0+1,heightCanvas.width-1), y1=Math.min(y0+1,heightCanvas.height-1);
      const sample=(px,py)=>samples[(py*heightCanvas.width+px)*4]/255;
      const value=THREE.MathUtils.lerp(THREE.MathUtils.lerp(sample(x0,y0),sample(x1,y0),fx-x0),THREE.MathUtils.lerp(sample(x0,y1),sample(x1,y1),fx-x0),fy-y0);
      return surfaceAssets.elevation_min_m+value*elevationRange;
    };
    const portalGround = rawElevationAt(surfaceAssets.portal.x_m, surfaceAssets.portal.z_m);
    const elevationAt = (x,z) => {
      const distance = Math.hypot(x-surfaceAssets.portal.x_m,z-surfaceAssets.portal.z_m);
      return THREE.MathUtils.lerp(portalGround,rawElevationAt(x,z),THREE.MathUtils.smoothstep(distance,110,170));
    };
    const segments = heightCanvas.width - 1;
    const geometry = new THREE.PlaneGeometry(width, width, segments, heightCanvas.height - 1);
    geometry.rotateX(-Math.PI / 2);
    const positions = geometry.attributes.position;
    for (let i = 0; i < positions.count; i += 1) {
      positions.setY(i, elevationAt(positions.getX(i), positions.getZ(i)));
    }
    positions.needsUpdate = true;
    geometry.computeVertexNormals();
    const texture = new THREE.Texture(image);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.needsUpdate = true;
    const terrain = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ map: texture, roughness: 1, metalness: 0 }));
    terrain.material.userData.detailMap=groundDetail;
    terrain.material.onBeforeCompile=shader=>{
      shader.uniforms.detailMap={value:groundDetail};
      shader.fragmentShader="uniform sampler2D detailMap;\n"+shader.fragmentShader.replace("#include <map_fragment>","#include <map_fragment>\ndiffuseColor.rgb *= mix(vec3(1.0), texture2D(detailMap, vMapUv * 420.0).rgb * 2.0, 0.5);");
    };
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

    const site=surfaceAssets.site;
    const road = new THREE.CatmullRomCurve3(site.access_road_m.map(point=>new THREE.Vector3(...point)));
    const roadVertices = [];
    const roadIndices = [];
    const roadSteps = 256;
    for (let i = 0; i <= roadSteps; i += 1) {
      const t = i / roadSteps;
      const point = road.getPoint(t);
      const tangent = road.getTangent(t);
      const side = new THREE.Vector3(-tangent.z, 0, tangent.x).normalize().multiplyScalar(site.road_half_width_m);
      const y = elevationAt(point.x, point.z) + 0.8;
      roadVertices.push(point.x + side.x, elevationAt(point.x+side.x,point.z+side.z)+.55, point.z + side.z, point.x - side.x, elevationAt(point.x-side.x,point.z-side.z)+.55, point.z - side.z);
      if (i < roadSteps) {
        const start = i * 2;
        roadIndices.push(start, start + 2, start + 1, start + 1, start + 2, start + 3);
      }
    }
    const roadGeometry = new THREE.BufferGeometry();
    roadGeometry.setAttribute("position", new THREE.Float32BufferAttribute(roadVertices, 3));
    roadGeometry.setIndex(roadIndices);
    roadGeometry.computeVertexNormals();
    surfaceRoot.add(new THREE.Mesh(roadGeometry, new THREE.MeshStandardMaterial({ color: 0x746b58, roughness: 1, side: THREE.DoubleSide })));

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
      const ridges=new THREE.InstancedMesh(new THREE.BoxGeometry(.12,.16,depth+2),roof.material,12);
      const ridgePose=new THREE.Object3D();
      for(let i=0;i<12;i++){ridgePose.position.set((i/11-.5)*width,height+1.04,0);ridgePose.updateMatrix();ridges.setMatrixAt(i,ridgePose.matrix);} shed.add(ridges);
      const door=new THREE.Mesh(new THREE.PlaneGeometry(width*.35,height*.7),new THREE.MeshStandardMaterial({color:0x394b50,roughness:.8,side:THREE.DoubleSide}));
      door.position.set(0,height*.35,depth/2+.02);shed.add(door);
    };
    for(const shed of site.sheds) addServiceShed(portalX+shed.offset_m[0],portalZ+shed.offset_m[1],...shed.size_m);
    const tankMaterial = new THREE.MeshStandardMaterial({color:0xa5a89a,roughness:.65,metalness:.3});
    for (const spec of site.tanks) {
      const tank = new THREE.Mesh(new THREE.CylinderGeometry(spec.radius_m,spec.radius_m,spec.height_m,16),tankMaterial);
      const x=portalX+spec.offset_m[0], z=portalZ+spec.offset_m[1];
      tank.position.set(x,elevationAt(x,z)+spec.height_m/2,z); surfaceRoot.add(tank);
    }
    const yard = new THREE.Mesh(new THREE.PlaneGeometry(...site.yard_size_m),new THREE.MeshStandardMaterial({color:0x8b8372,roughness:1,side:THREE.DoubleSide}));
    const yardMap=groundDetail.clone(); yardMap.repeat.set(14,12); yard.material.map=yardMap;
    yard.rotation.x=-Math.PI/2; yard.position.set(portalX+site.yard_offset_m[0],portal.position.y+.2,portalZ+site.yard_offset_m[1]); surfaceRoot.add(yard);
    const stockpile = new THREE.Mesh(new THREE.ConeGeometry(site.stockpile.radius_m, site.stockpile.height_m, 12), new THREE.MeshStandardMaterial({ color: 0x625b4d, roughness: 1 }));
    stockpile.position.set(portalX + site.stockpile.offset_m[0], portal.position.y + site.stockpile.height_m/2, portalZ + site.stockpile.offset_m[1]);
    surfaceRoot.add(stockpile);
    resolve();
  }).catch(reject);
  });
  return surfaceTerrainPromise;
}

async function finishGlobeFlight() {
  if (!cameraTransition) return;
  const completedTransition = cameraTransition;
  cameraTransition = null;
  try {
    await prepareSurfaceTerrain(missionManifest.assets.surface);
  } catch (error) {
    cameraTransition = completedTransition;
    skipFlightButton.hidden = false;
    skipFlightButton.textContent = "RETRY DESCENT";
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
  camera.position.copy(surfacePortal.position).add(new THREE.Vector3(-100, 145, 210));
  camera.fov = 47;
  camera.updateProjectionMatrix();
  surfaceLookTarget.copy(surfacePortal.position).add(new THREE.Vector3(24, 0, -20));
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
  document.getElementById("restart-mission").hidden = false;
  document.querySelector(".mission-index").hidden = true;
  targetButton.innerHTML = 'MINE PORTAL <span>ENTER UNDERGROUND</span>';
  targetButton.hidden = false;
  disposeGlobeStage();
  if (onlineMapAllowed && navigator.onLine) setSurfaceView("satellite");
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
  if (cameraTransition.kind === "mission-view") {
    const progress = Math.min((now - cameraTransition.start) / cameraTransition.duration, 1);
    const eased = progress * progress * (3 - 2 * progress);
    camera.position.lerpVectors(cameraTransition.fromCameraPosition, cameraTransition.toCameraPosition, eased);
    flightLookTarget.lerpVectors(cameraTransition.fromLookTarget, cameraTransition.toLookTarget, eased);
    camera.fov = THREE.MathUtils.lerp(cameraTransition.fromFov, cameraTransition.toFov, eased);
    camera.updateProjectionMatrix();
    camera.lookAt(flightLookTarget);
    if (progress >= 1) cameraTransition = null;
    return;
  }
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
    horizonSlider.max = String(mission.prediction_preview.samples.length - 1);
    horizonSlider.value = String(Math.min(1, mission.prediction_preview.samples.length - 1));
    displayMetrics(mission.optimiser_trace.before);
    fleetMode.textContent = mission.routes[0]?.status.replaceAll("_", " ").toUpperCase() || "SCRIPTED";
    runOptimiserButton.textContent = `RUN ${mission.optimiser_trace.run_count.toLocaleString()} SIMULATIONS`;
    simulationStatus.textContent = `${mission.optimiser_trace.source.toUpperCase()} RESULT · ILLUSTRATIVE VALUES`;
    cycleReference.textContent = mission.optimiser_trace.citation_summary;
    cycleReferenceLink.href = mission.optimiser_trace.citation;
    cycleReferenceLink.textContent = mission.optimiser_trace.citation_label;
    const location = mission.location;
    missionLocation = location;
    const latitude = Math.abs(location.latitude).toFixed(2);
    const longitude = Math.abs(location.longitude).toFixed(2);
    targetCoordinates.innerHTML = `${latitude}° ${location.latitude < 0 ? "S" : "N"}<br />${longitude}° ${location.longitude < 0 ? "W" : "E"}`;
    targetName.textContent = `TARGET / ${location.name}, ${location.country}`;
    earth.rotation.y = -THREE.MathUtils.degToRad(location.longitude + 90);
    const globeAssets = mission.assets.globe;
    textureLoader.load(globeAssets.day_map, async (texture) => {
      if (typeof createImageBitmap === "function") {
        try { texture.image=await createImageBitmap(texture.image,{resizeWidth:mobile?2048:4096,resizeHeight:mobile?1024:2048,resizeQuality:"high"}); } catch { /* Retain the source if bitmap resizing is unavailable. */ }
      }
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.anisotropy = Math.min(renderer.capabilities.getMaxAnisotropy(), 8);
      earthMaterial.map = texture;
      earthMaterial.needsUpdate = true;
      experience.classList.add("ready");
      const warp = document.getElementById("warp");
      if (!reducedMotion) warp.classList.add("active");
      const defer = window.requestIdleCallback || ((callback) => setTimeout(callback, 1200));
      defer(() => {
        if(mobile || missionState !== "biome-select") return;
        textureLoader.load(globeAssets.night_lights,async texture=>{
          if(typeof createImageBitmap === "function") { try { texture.image=await createImageBitmap(texture.image,{resizeWidth:2048,resizeHeight:1024}); } catch {} }
          nightUniforms.nightMap.value=texture;nightEarth.visible=true;
        });
        textureLoader.load(globeAssets.clouds,texture=>{cloudMaterial.alphaMap=texture;cloudMaterial.needsUpdate=true;cloudEarth.visible=true;});
      },{timeout:2500});
      defer(() => loadDepositMarkers(mission.assets.deposit_markers, location), { timeout: 1800 });
    }, undefined, () => {
      document.getElementById("loading-status").textContent = "EARTH TEXTURE UNAVAILABLE";
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
    targetButton.addEventListener("click", () => missionState === "surface-arrived" ? beginPortalTransition() : chooseUnderground?.());
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
    const modelResponse = await fetch(missionManifest.assets.fleet_vehicle_model);
    if (!modelResponse.ok) throw new Error(`Fleet vehicle model request failed: ${modelResponse.status}`);
    const vehicleModel = await modelResponse.json();
    const rendererModule = await import(new URL(assets.renderer, document.baseURI));
    const root = await rendererModule.createUndergroundStage(network, {
      mobile,
      routes: missionManifest.routes,
      fleet: missionManifest.fleet,
      vehicleModel,
      predictionPreview: missionManifest.prediction_preview,
      loadingBay: assets.loading_bay,
      excavatorConfig: assets.excavator,
    });
    if (!surfacePortal) throw new Error("Mine entrance is not ready");
    undergroundRoot.position.copy(surfacePortal.position);
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

function fleetStage() {
  return undergroundRoot.userData.stage;
}

function moveMissionCamera(position, target, duration = 1500) {
  cameraTransition = {
    kind: "mission-view",
    start: performance.now(),
    duration,
    fromCameraPosition: camera.position.clone(),
    toCameraPosition: position.clone(),
    fromLookTarget: flightLookTarget.clone(),
    toLookTarget: target.clone(),
    fromFov: camera.fov,
    toFov: camera.fov,
  };
}

function displayMetrics(values) {
  metricThroughput.textContent = `${values.throughput_tph} t/h`;
  metricCycle.textContent = `${values.cycle_minutes} min`;
  metricUtilisation.textContent = `${values.utilisation_percent}%`;
  metricQueue.textContent = `${values.queue_delay_minutes} min`;
}

function setInsight(index, title, copy) {
  document.getElementById("insight-index").textContent = index;
  document.getElementById("insight-title").textContent = title;
  document.getElementById("insight-copy").textContent = copy;
}

function applyViewport() {
  camera.clearViewOffset();
  if (["fleet", "truck"].includes(missionState)) {
    // Reserve room for the console without distorting the vehicle or network.
    camera.setViewOffset(innerWidth, innerHeight, mobile ? 0 : -innerWidth * .15, mobile ? innerHeight * .16 : 0, innerWidth, innerHeight);
  }
}

function showFleetOverview(duration = 1700) {
  fleetStage()?.userData.setInspection(false);
  const network = fleetStage()?.userData.network;
  const bounds = new THREE.Box3();
  for (const node of network.nodes) bounds.expandByPoint(new THREE.Vector3(...node.position_m));
  const centre = bounds.getCenter(new THREE.Vector3()).add(undergroundRoot.position);
  const length = bounds.getSize(new THREE.Vector3()).z;
  const position = centre.clone().add(new THREE.Vector3(length * .73, length * .72, length * .42));
  if (mobile) position.add(new THREE.Vector3(length*.26,length*.24,length*.15));
  camera.fov = mobile ? 59 : 47;
  camera.near = .1; camera.far = 2500;
  scene.fog = new THREE.Fog(0x07111c,900,2300);
  scene.background.set(0x07111c);
  applyViewport(); camera.updateProjectionMatrix();
  const previousPosition=camera.position.clone(),previousQuaternion=camera.quaternion.clone();
  for(let attempt=0;attempt<24;attempt++) {
    camera.position.copy(position);camera.lookAt(centre);camera.updateMatrixWorld(true);
    const fits=network.nodes.every(node=>{
      const point=new THREE.Vector3(...node.position_m).add(undergroundRoot.position).project(camera);
      return point.x>(mobile?-.88:-.42)&&point.x<.9&&point.y>(mobile?.02:-.6)&&point.y<(mobile?.72:.67);
    });
    if(fits) break;
    position.sub(centre).multiplyScalar(1.1).add(centre);
  }
  camera.position.copy(previousPosition);camera.quaternion.copy(previousQuaternion);camera.updateMatrixWorld(true);
  moveMissionCamera(position, centre, reducedMotion ? 150 : duration);
}

function buildFleetControls() {
  const fleet = fleetStage().userData.fleet;
  for (const entry of fleet.entries) {
    const shortName = entry.id.replace("truck-", "HT-").toUpperCase();
    const button = document.createElement("button"); button.type="button";
    button.setAttribute("aria-label", `Inspect ${shortName}`); button.setAttribute("aria-pressed","false");
    button.innerHTML = `<i class="roster-dot"></i><span>${shortName}</span><span class="roster-phase">HAULING</span><span class="roster-arrow">↗</span>`;
    button.addEventListener("click",()=>selectTruck(entry.id)); roster.append(button); rosterElements.set(entry.id,button);
    const tag = document.createElement("span"); tag.className="truck-tag"; tag.innerHTML=`${shortName}<b>HAUL</b>`; labels.append(tag); tagElements.set(entry.id,tag);
  }
}

function startOptimisation() {
  const trace = missionManifest?.optimiser_trace;
  if (!trace || !fleetStage() || fleetStage().userData.fleet.optimised || simTimeouts.length) return;
  const fleet = fleetStage().userData.fleet;
  runOptimiserButton.disabled = true;
  for(const button of rosterElements.values()) button.disabled=true;
  experience.classList.add("simulation-running");
  setInsight("02 / TRAIN", "A world to learn in.", "Evaluate policies inside a model of the mine. Learn how the fleet can move together before deploying to a machine.");
  simulationStatus.textContent = `DISPLAYING PRE-COMPUTED TRACE · ${trace.run_count.toLocaleString()} ITERATIONS · ILLUSTRATIVE`;
  trace.steps.forEach((snapshot, index) => {
    simTimeouts.push(setTimeout(() => {
      const fraction=snapshot.iterations/trace.run_count;
      displayMetrics({throughput_tph:Math.round(THREE.MathUtils.lerp(trace.before.throughput_tph,trace.after.throughput_tph,fraction)),cycle_minutes:THREE.MathUtils.lerp(trace.before.cycle_minutes,trace.after.cycle_minutes,fraction).toFixed(1),utilisation_percent:Math.round(THREE.MathUtils.lerp(trace.before.utilisation_percent,trace.after.utilisation_percent,fraction)),queue_delay_minutes:THREE.MathUtils.lerp(trace.before.queue_delay_minutes,trace.after.queue_delay_minutes,fraction).toFixed(1)});
      const progress = Math.round(fraction * 100);
      simulationProgress.setAttribute("aria-valuenow", String(progress));
      simulationProgress.querySelector("i").style.width = `${progress}%`;
      simulationStatus.textContent = `ITERATIONS ${snapshot.iterations.toLocaleString()} / ${trace.run_count.toLocaleString()} · ROLL-OUTS ${snapshot.rollouts.toLocaleString()} · ${snapshot.elapsed_ms} ms REPORTED`;
      if (index === trace.steps.length - 1) {
        fleet.setOptimised(true);
        const ribbons = fleet.group;
        experience.classList.add("route-converging");
        const routeMeshes = ribbons ? ribbons.children.filter((object) => object.userData.routeId) : [];
        routeMeshes.forEach((object, routeIndex) => {
          simTimeouts.push(setTimeout(() => {
            object.material.color.setHex(0x65d79a);
            object.userData.status = "converged";
            if (routeIndex !== routeMeshes.length - 1) return;
            fleetMode.textContent = "CONVERGED";
            fleetCaption.textContent = "Coordinated routes. Less time waiting. Select a machine to see the policy at work.";
            setInsight("03 / DEPLOY", "Intelligence on the machine.", "Compress the trained policy onto rugged compute. Retrofit the existing fleet. Operate without GPS or a cloud connection.");
            metricThroughput.textContent = `${trace.after.throughput_tph} t/h`;
            metricCycle.textContent = `${trace.after.cycle_minutes} min`;
            metricUtilisation.textContent = `${trace.after.utilisation_percent}%`;
            metricQueue.textContent = `${trace.after.queue_delay_minutes} min`;
            simulationStatus.textContent = `+${Math.round((trace.after.throughput_tph / trace.before.throughput_tph - 1) * 100)}% THROUGHPUT · PRE-COMPUTED RESULT`;
            metricThroughput.dataset.change=`FROM ${trace.before.throughput_tph} t/h`;
            metricCycle.dataset.change=`FROM ${trace.before.cycle_minutes} min`;
            metricUtilisation.dataset.change=`FROM ${trace.before.utilisation_percent}%`;
            metricQueue.dataset.change=`FROM ${trace.before.queue_delay_minutes} min`;
            metricThroughput.title = `Before: ${trace.before.throughput_tph} t/h`;
            metricCycle.title = `Before: ${trace.before.cycle_minutes} min`;
            metricUtilisation.title = `Before: ${trace.before.utilisation_percent}%`;
            metricQueue.title = `Before: ${trace.before.queue_delay_minutes} min`;
            runOptimiserButton.textContent = "SIMULATION COMPLETE";
            runOptimiserButton.hidden = true;
            experience.classList.remove("simulation-running");
            for(const button of rosterElements.values()) button.disabled=false;
            simTimeouts = [];
          }, 320 * (routeIndex + 1)));
        });
      }
    }, 520 * (index + 1)));
  });
}

function selectTruck(id) {
  const stage = fleetStage(); const fleet = stage?.userData.fleet;
  if (!fleet || simTimeouts.length) return;
  const entry = fleet.select(id);
  if (!entry) return;
  missionState = "truck";
  simulationStatus.setAttribute("aria-live","off");
  stage.userData.setInspection(true);
  scene.background.set(0x10171b);
  scene.fog = new THREE.Fog(0x10171b,18,100);
  camera.fov = mobile ? 66 : 58;
  camera.far=500; applyViewport(); camera.updateProjectionMatrix();
  returnFleetButton.hidden=false; runOptimiserButton.hidden=true; worldModelNote.hidden=false;
  flightStatus.hidden=false; flightStatus.textContent=`${id.replace("truck-","HT-").toUpperCase()} / ONBOARD POLICY`;
  for (const [vehicleId,button] of rosterElements) button.setAttribute("aria-pressed",String(vehicleId===id));
  const offset = new THREE.Vector3(.25,2.65,-9).applyQuaternion(entry.truck.quaternion);
  const position=entry.truck.position.clone().add(offset).add(undergroundRoot.position);
  const target=entry.truck.position.clone().add(new THREE.Vector3(0,1.25,2).applyQuaternion(entry.truck.quaternion)).add(undergroundRoot.position);
  moveMissionCamera(position,target,reducedMotion?150:1400);
  undergroundConsole.classList.add("truck-selected");
  fleetMode.textContent="OFFLINE";
  setInsight("04 / AUTONOMY", "The mine goes offline. Work continues.", "The policy runs on the vehicle. Sensors inform the next action locally. Deployment data improves the world model when a connection returns.");
  steps.children[4].className="is-complete"; steps.children[6].className="is-active";
  updateHorizon();
}

function returnToFleet() {
  const fleet = fleetStage()?.userData.fleet;
  if (!fleet) return;
  missionState = "fleet";
  simulationStatus.setAttribute("aria-live","polite");
  fleet.select(null);
  fleetMode.textContent = fleet.optimised ? "CONVERGED" : "UNOPTIMISED";
  simulationStatus.textContent = fleet.optimised ? "PRE-COMPUTED RESULT · ILLUSTRATIVE VALUES" : "PRE-COMPUTED TRACE · ILLUSTRATIVE SCENARIO";
  if (fleet.optimised) setInsight("03 / DEPLOY", "Intelligence on the machine.", "Compress the trained policy onto rugged compute. Retrofit the existing fleet. Operate without GPS or a cloud connection.");
  else setInsight("01 / OBSERVE", "A shared bottleneck.", "Uncoordinated machines compete for the same decline. Queues build. Productive time falls.");
  for (const button of rosterElements.values()) button.setAttribute("aria-pressed","false");
  returnFleetButton.hidden = true;
  runOptimiserButton.hidden = fleet.optimised;
  worldModelNote.hidden = true;
  undergroundConsole.classList.remove("truck-selected");
  flightStatus.textContent = "ILLUSTRATIVE CUTAWAY / THREE LEVELS";
  showFleetOverview();
}

runOptimiserButton.addEventListener("click", startOptimisation);
returnFleetButton.addEventListener("click", returnToFleet);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && missionState === "truck" && !document.getElementById("sources-dialog").open) returnToFleet();
});
canvas.addEventListener("click", (event) => {
  if (!["fleet", "truck"].includes(missionState) || !undergroundRoot.visible) return;
  const rect = canvas.getBoundingClientRect();
  pointer.set(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  const fleet = fleetStage()?.userData.fleet;
  const hits = raycaster.intersectObjects(fleet?.group.children || [], true);
  if (missionState === "truck") return;
  const vehicle = hits.map((hit) => hit.object.userData.vehicleId || hit.object.parent?.userData.vehicleId).find(Boolean);
  if (vehicle) selectTruck(vehicle);
});

function disposeGlobeStage() {
  const geometries=new Set(), materials=new Set(), textures=new Set();
  for (const root of [earthRoot,stars]) root.traverse(object=>{
    if(object.geometry) geometries.add(object.geometry);
    if(object.material) {
      materials.add(object.material);
      for(const value of Object.values(object.material)) if(value?.isTexture) textures.add(value);
    }
  });
  if(nightUniforms.nightMap.value) textures.add(nightUniforms.nightMap.value);
  geometries.forEach(item=>item.dispose()); materials.forEach(item=>item.dispose()); textures.forEach(item=>item.dispose());
  scene.remove(earthRoot,stars);
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
      for (const value of [...Object.values(material), ...Object.values(material.userData || {})]) {
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
  surfaceMap.hidden=true;
  satelliteMap.removeAttribute("src");
  targetButton.hidden = true;
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
    scene.background.set(0x07111c);
    scene.fog = new THREE.Fog(0x07090a, 75, 310);
    camera.near = 0.1;
    camera.far = 600;
    camera.updateProjectionMatrix();
    disposeSurfaceStage();
  }
  if (progress >= 1) {
    portalTransition = null;
    missionState = "fleet";
    showFleetOverview(1900);
    buildFleetControls();
    insight.hidden = false; steps.hidden = false;
    document.querySelector(".topbar-readout").innerHTML = '<span class="status-light"></span> AUTONOMY / OFFLINE<br /><span class="readout-sub">ILLUSTRATIVE MISSION</span>';
    experience.classList.add("underground-active");
    returnFleetButton.hidden = true;
    runOptimiserButton.hidden = false;
    runOptimiserButton.disabled = false;
    simulationStatus.textContent = `${missionManifest.optimiser_trace.source.toUpperCase()} OPTIMISER · ILLUSTRATIVE VALUES`;
    experience.classList.remove("portal-entering");
    experience.classList.remove("surface-arrived");
    surfaceConsole.hidden = true;
    surfaceCredit.hidden = true;
    undergroundConsole.hidden = false;
    flightStatus.textContent = "ILLUSTRATIVE CUTAWAY / THREE LEVELS";
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
  mobile = width <= 760;
  adaptiveRatio = Math.min(devicePixelRatio || 1, mobile ? 1.25 : 1.5);
  renderer.setPixelRatio(adaptiveRatio);
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  if (portalTransition) {
    camera.updateProjectionMatrix();
  } else if (missionState === "surface-arrived") {
    if (surfacePortal) camera.position.copy(surfacePortal.position).add(new THREE.Vector3(-100, mobile ? 210 : 145, mobile ? 270 : 210));
    camera.lookAt(surfaceLookTarget);
  } else if (missionState !== "fleet" && missionState !== "truck") {
    camera.position.z = width <= 760 ? 9.8 : 8.4;
  }
  applyViewport();
  earthRoot.position.x = width <= 760 ? 0 : 1.55;
  camera.updateProjectionMatrix();
}
addEventListener("resize", resize, { passive: true });

let lastTime = 0;
let sampledState = "";
let frameTimes = [];
let qualitySample = [];
let adaptiveRatio = Math.min(devicePixelRatio || 1, mobile ? 1.25 : 1.5);
resize();
const earthWorldPosition = new THREE.Vector3();
function render(time) {
  requestAnimationFrame(render);
  const frameMs = lastTime ? time - lastTime : 0;
  if (sampledState !== missionState) { sampledState = missionState; frameTimes = []; qualitySample = []; }
  if(frameMs > 0 && visiblePage) {
    frameTimes.push(frameMs); if(frameTimes.length > 180) frameTimes.shift();
    qualitySample.push(frameMs);
    if(qualitySample.length >= 20) {
      const mean=qualitySample.reduce((sum,value)=>sum+value,0)/qualitySample.length;
      if(mean > 40 && adaptiveRatio > .76) { adaptiveRatio=Math.max(.75,adaptiveRatio*.8);renderer.setPixelRatio(adaptiveRatio); }
      else if(mean < 20) {
        const cap=Math.min(devicePixelRatio||1,mobile?1.25:1.5);
        if(adaptiveRatio < cap) { adaptiveRatio=Math.min(cap,adaptiveRatio*1.08);renderer.setPixelRatio(adaptiveRatio); }
      }
      qualitySample=[];
    }
  }
  const delta = lastTime ? Math.min((time - lastTime) / 1000, 0.2) : 0;
  lastTime = time;
  if (!reducedMotion && missionState === "biome-select") earth.rotation.y += delta * 0.025;
  if(missionState==="truck"&&cameraTransition?.kind==="mission-view") {
    const entry=fleetStage()?.userData.fleet.entries.find(item=>item.id===fleetStage().userData.fleet.selectedId);
    if(entry) {
      cameraTransition.toCameraPosition.set(.25,2.65,-9).applyQuaternion(entry.truck.quaternion).add(entry.truck.position).add(undergroundRoot.position);
      cameraTransition.toLookTarget.set(0,1.25,2).applyQuaternion(entry.truck.quaternion).add(entry.truck.position).add(undergroundRoot.position);
    }
  }
  updateCameraTransition(time);
  updatePortalTransition(time);
  if (!visiblePage) return;
  if (undergroundRoot.visible) {
    const stage=fleetStage(); const fleet=stage.userData.fleet;
    fleet.update(delta);
    const entry = fleet.entries.find(item=>item.id===fleet.selectedId);
    if (entry && missionState==="truck") {
      stage.userData.updateInspection(entry, delta);
      if (!cameraTransition) {
        followPosition.set(.25,2.65,-9).applyQuaternion(entry.truck.quaternion).add(entry.truck.position).add(undergroundRoot.position);
        followTarget.set(0,1.25,2).applyQuaternion(entry.truck.quaternion).add(entry.truck.position).add(undergroundRoot.position);
        camera.position.lerp(followPosition,1-Math.exp(-delta*5));
        flightLookTarget.copy(followTarget); camera.lookAt(flightLookTarget);
      }
      const phases={loading:"LOADING ORE",hauling:"HAULING",tipping:"TIPPING ORE",returning:"RETURNING EMPTY",queued:"WAITING AT DECLINE"};
      simulationStatus.textContent=`${entry.id.replace("truck-","HT-").toUpperCase()} · ${phases[entry.truck.userData.phase]} · ${Math.round(entry.load*100)}% PAYLOAD`;
    }
    if(time-hudUpdated>120) {
      hudUpdated=time;
      for(const [truckIndex,truck] of fleet.entries.entries()) {
        const phase=truck.truck.userData.phase;
        rosterElements.get(truck.id)?.querySelector(".roster-phase").replaceChildren(phase.toUpperCase());
        const tag=tagElements.get(truck.id);
        if(!tag) continue;
        labelPosition.copy(truck.truck.position).add(undergroundRoot.position).add(new THREE.Vector3(0,4,0)).project(camera);
        tag.hidden=missionState!=="fleet"||labelPosition.z>1||Math.abs(labelPosition.x)>1||Math.abs(labelPosition.y)>1;
        tag.style.left=`${(labelPosition.x*.5+.5)*innerWidth}px`; tag.style.top=`${(-labelPosition.y*.5+.5)*innerHeight-12-truckIndex*23}px`;
        tag.querySelector("b").textContent=phase==="queued"?"QUEUE":phase.toUpperCase();
      }
    }
  }
  nightEarth.rotation.y = earth.rotation.y;
  surfaceMarkers.rotation.y = earth.rotation.y;
  cloudEarth.rotation.y = earth.rotation.y + (reducedMotion ? 0 : Math.sin(time * 0.000012) * 0.012);
  earthRoot.getWorldPosition(earthWorldPosition);
  nightUniforms.sunDirection.value.copy(sun.position).sub(earthWorldPosition).normalize();
  if (missionLocation && ["biome-select","surface-arrived"].includes(missionState)) {
    if(missionState==="surface-arrived"&&surfacePortal) {
      projectedTarget.copy(surfacePortal.position).add(new THREE.Vector3(0,6,0)).project(camera);
      targetButton.hidden=!surfaceMap.hidden||projectedTarget.z>1;
    } else {
      targetWorldPosition.copy(geographicNormal(missionLocation.latitude,missionLocation.longitude)).multiplyScalar(2.44).applyAxisAngle(Y_AXIS,earth.rotation.y).applyQuaternion(earthRoot.quaternion).add(earthRoot.position);
      targetWorldNormal.copy(geographicNormal(missionLocation.latitude,missionLocation.longitude)).applyAxisAngle(Y_AXIS,earth.rotation.y).applyQuaternion(earthRoot.quaternion);
      projectedTarget.copy(targetWorldPosition).project(camera);
      cameraToTarget.copy(camera.position).sub(targetWorldPosition);
      targetButton.hidden=targetWorldNormal.dot(cameraToTarget)<=0||projectedTarget.z < -1||projectedTarget.z>1;
    }
    if(!targetButton.hidden) { targetButton.style.left=`${(projectedTarget.x*.5+.5)*innerWidth}px`; targetButton.style.top=`${(-projectedTarget.y*.5+.5)*innerHeight}px`; }
  }
  renderer.render(scene, camera);
}
requestAnimationFrame(render);

function updateHorizon() {
  const index=Number(horizonSlider.value);
  const sample=missionManifest?.prediction_preview.samples[index];
  if(!sample) return;
  document.getElementById("horizon-value").textContent=`+${sample.horizon_seconds} s`;
  document.getElementById("prediction-error").textContent=`${sample.error_m.toFixed(2)} m`;
  fleetStage()?.userData.fleet.setPredictionSample(index);
}
horizonSlider.addEventListener("input",updateHorizon);
document.getElementById("watch-cycle").addEventListener("click",()=>{
  fleetStage()?.userData.fleet.watchCycle();
  cameraTransition=null;
});
document.getElementById("restart-mission").addEventListener("click",()=>location.reload());
const sourcesDialog=document.getElementById("sources-dialog");
document.getElementById("open-sources").addEventListener("click",()=>sourcesDialog.showModal());
document.getElementById("close-sources").addEventListener("click",()=>sourcesDialog.close());
sourcesDialog.addEventListener("click",event=>{if(event.target===sourcesDialog){const box=sourcesDialog.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)sourcesDialog.close();}});
document.addEventListener("visibilitychange",()=>{visiblePage=!document.hidden;lastTime=0;});

// Read-only measurements for the release verification report.
export function getMissionDiagnostics() {
  const textures=new Set();
  scene.traverse(object=>{
    const materials=Array.isArray(object.material)?object.material:[object.material];
    for(const material of materials) if(material) {
      for(const value of [...Object.values(material),...Object.values(material.userData||{})]) if(value?.isTexture) textures.add(value);
      for(const uniform of Object.values(material.uniforms||{})) if(uniform.value?.isTexture) textures.add(uniform.value);
    }
  });
  const textureBytes=[...textures].reduce((sum,texture)=>sum+(texture.image?.width||0)*(texture.image?.height||0)*4*(texture.generateMipmaps?4/3:1),0);
  const sorted=[...frameTimes].sort((a,b)=>a-b);
  const gl=renderer.getContext(), debug=gl.getExtension("WEBGL_debug_renderer_info");
  const fleet=fleetStage()?.userData.fleet;
  return {state:missionState,pixelRatio:renderer.getPixelRatio(),drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,gpuTextures:renderer.info.memory.textures,estimatedTextureMiB:Number((textureBytes/1048576).toFixed(2)),frameSamples:sorted.length,meanFps:sorted.length?Number((1000/(sorted.reduce((a,b)=>a+b,0)/sorted.length)).toFixed(1)):null,p95FrameMs:sorted[Math.floor(sorted.length*.95)]||null,renderer:debug?gl.getParameter(debug.UNMASKED_RENDERER_WEBGL):"not exposed",selected:fleet?.selectedId,vehicles:fleet?.entries.map(entry=>({id:entry.id,phase:entry.phase,distance:entry.distance,load:entry.load,position:entry.truck.position.toArray(),up:new THREE.Vector3(0,1,0).applyQuaternion(entry.truck.quaternion).toArray()}))};
}

function setSurfaceView(view) {
  const satellite=view==="satellite";
  surfaceMap.hidden=!satellite;
  viewSatellite.setAttribute("aria-pressed",String(satellite));
  viewSite.setAttribute("aria-pressed",String(!satellite));
  document.getElementById("surface-view-description").textContent=satellite?"Satellite imagery of the Rutongo area. Explore the site from above.":"Local terrain model · illustrative mine portal and service yard";
  if(satellite && !satelliteMap.src) satelliteMap.src=missionManifest.assets.surface.satellite_embed.url;
  targetButton.hidden=satellite;
  if(!satellite) satelliteMap.removeAttribute("src");
}
viewSatellite.addEventListener("click",()=>setSurfaceView("satellite"));
viewSite.addEventListener("click",()=>setSurfaceView("site"));
