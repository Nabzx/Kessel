import * as THREE from "three";
import { texture, box, lightRig, seeded, line } from "./scene-utils.js";
import { createFleet } from "./fleet.js";
import { createRouteRibbons } from "./underground.js";
import { createLoadingMachine } from "./loading-machine.js";
export async function createMine(config) {
  const root = new THREE.Group();
  root.name = "sliced-rock-mine";
  const data = config.mine;
  const [wall, floor, ore, wallNormal, floorNormal, oreNormal, vehicleModel] =
    await Promise.all([
      texture(config.assets.wall),
      texture(config.assets.floor, 16),
      texture(config.assets.ore),
      texture(config.assets.wall_normal, 1, false),
      texture(config.assets.floor_normal, 16, false),
      texture(config.assets.ore_normal, 1, false),
      fetch(config.assets.truck).then((r) => r.json()),
    ]);
  const rockMat = new THREE.MeshStandardMaterial({
    map: wall,
    normalMap: wallNormal,
    normalScale: new THREE.Vector2(0.55, 0.55),
    color: 0xadb4b3,
    roughness: 0.96,
  });
  // Box UVs are scaled per face so rock texture remains at a consistent metre scale.
  function rockBox(spec) {
    const mesh = box(spec.size, spec.position, rockMat, root);
    const uv = mesh.geometry.attributes.uv;
    for (let i = 0; i < uv.count; i++)
      uv.setXY(
        i,
        (uv.getX(i) * Math.max(spec.size[0], spec.size[2])) / 7,
        (uv.getY(i) * spec.size[1]) / 4,
      );
    return mesh;
  }
  rockBox(data.base);
  for (const spec of data.pillars) rockBox(spec);
  for (const spec of data.rims) rockBox(spec);
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(...data.floor_size),
    new THREE.MeshStandardMaterial({
      map: floor,
      normalMap: floorNormal,
      color: 0xb9b4a3,
      roughness: 0.95,
    }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = data.floor_y + 0.12;
  ground.receiveShadow = true;
  root.add(ground);
  const routes = createRouteRibbons(data.network, data.routes);
  routes.traverse((object) => {
    if (object.isMesh) {
      object.material.color.set(0xe66f60);
      object.material.opacity = 0.72;
      object.material.depthTest = true;
      object.material.toneMapped = true;
    }
  });
  root.add(routes);
  const fleet = createFleet(
    data.network,
    data.routes,
    data.fleet,
    vehicleModel,
    routes,
    data.prediction_preview,
    { oreMap: ore, oreNormal },
  );
  root.add(fleet.group);
  for (const entry of fleet.entries) {
    entry.detail.visible = true;
    entry.overview.visible = false;
    entry.truck.traverse((object) => {
      if (object.isMesh) object.castShadow = true;
    });
  }
  const excavatorConfig = data.excavator;
  const loading = await createLoadingMachine(
    excavatorConfig,
    data.network.nodes.find((node) => node.id === "draw"),
  );
  root.add(loading.root);
  const rand = seeded(863),
    pose = new THREE.Object3D();
  const rocks = new THREE.InstancedMesh(
    new THREE.IcosahedronGeometry(1, 1),
    new THREE.MeshStandardMaterial({
      map: ore,
      normalMap: oreNormal,
      color: 0xc8c2b1,
      roughness: 1,
    }),
    90,
  );
  data.ore_piles.forEach((point, pile) => {
    for (let i = 0; i < 30; i++) {
      const angle = rand() * Math.PI * 2,
        r = rand() * 4;
      pose.position.set(
        point[0] + Math.cos(angle) * r,
        point[1] + 0.5 + (4 - r) * 0.35 + rand(),
        point[2] + Math.sin(angle) * r,
      );
      pose.rotation.set(rand() * 4, rand() * 4, rand() * 4);
      pose.scale.setScalar(0.6 + rand() * 0.7);
      pose.updateMatrix();
      rocks.setMatrixAt(pile * 30 + i, pose.matrix);
    }
  });
  rocks.castShadow = true;
  root.add(rocks);
  const structureMat = new THREE.MeshStandardMaterial({
    color: 0x737a74,
    roughness: 0.55,
    metalness: 0.5,
  });
  const stripeMat = new THREE.MeshBasicMaterial({ color: 0xd5ac6c });
  for (const [x, y, z] of data.lamps) {
    box([0.25, 15, 0.25], [x, y - 7.5, z], structureMat, root);
    box(
      [2.8, 0.2, 0.65],
      [x, y, z],
      new THREE.MeshBasicMaterial({ color: 0xf2e3c6 }),
      root,
    );
  }
  for (const tip of data.network.nodes.filter(
    (node) => node.kind === "tipping_point",
  )) {
    const [x, y, z] = tip.position_m;
    box([9, 1, 7], [x + 10, y + 0.5, z], structureMat, root);
    for (let i = 0; i < 5; i++)
      box([0.45, 0.12, 4.5], [x + 6 + i * 1.8, y + 1.1, z], stripeMat, root);
  }
  // Exposed services and support fixtures follow the working corridors.
  for (const z of [-48, 48]) {
    root.add(
      line(
        [
          [-60, data.floor_y + 0.2, z],
          [60, data.floor_y + 0.2, z],
        ],
        0x4f5550,
      ),
    );
    for (let x = -50; x <= 50; x += 20) {
      box(
        [0.16, 1.2, 0.16],
        [x, data.floor_y + 0.6, z + 2],
        structureMat,
        root,
      );
    }
  }
  lightRig(root, 150);
  let trained = false,
    elapsed = 0,
    scan = 0;
  const original = [];
  root.traverse((object) => {
    if (object.isMesh && object.material) {
      for (const material of Array.isArray(object.material)
        ? object.material
        : [object.material])
        if (!original.some((item) => item.material === material))
          original.push({
            material,
            wire: material.wireframe,
            opacity: material.opacity,
          });
    }
  });
  function setTrained(value) {
    trained = value;
    fleet.setOptimised(value);
    fleet.entries.forEach((entry, index) => {
      entry.distance =
        (value
          ? data.trained_offsets[index]
          : data.fleet.vehicles[index].phase_offset) * entry.path.length;
      entry.dwell = 0;
      entry.phase =
        entry.distance === 0
          ? "loading"
          : entry.distance > entry.path.tipDistance
            ? "returning"
            : "hauling";
      entry.detail.visible = true;
      entry.overview.visible = false;
    });
    fleet.group.children
      .filter((object) => object.userData.routeId)
      .forEach((object) => {
        object.material.color.set(value ? 0x8fcaa5 : 0xe66f60);
        object.material.depthTest = true;
        object.material.toneMapped = true;
        object.material.opacity = 0.8;
      });
    elapsed = 0;
  }
  const scanUniforms = {
    kesselScanX: { value: -90 },
    kesselScanStrength: { value: 0 },
  };
  for (const material of [rockMat, ground.material]) {
    material.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, scanUniforms);
      shader.vertexShader =
        "varying vec3 kesselPosition;\n" +
        shader.vertexShader.replace(
          "#include <project_vertex>",
          "#include <project_vertex>\nkesselPosition=(modelMatrix*vec4(transformed,1.0)).xyz;",
        );
      shader.fragmentShader =
        "varying vec3 kesselPosition;\nuniform float kesselScanX;\nuniform float kesselScanStrength;\n" +
        shader.fragmentShader.replace(
          "#include <tonemapping_fragment>",
          `float scanBand=exp(-pow((kesselPosition.x-kesselScanX)/7.0,2.0));
 float scanGrid=(1.0-smoothstep(.03,.09,abs(fract(kesselPosition.x*.25)-.5)))*(1.0-smoothstep(.03,.09,abs(fract(kesselPosition.z*.25)-.5)));
 gl_FragColor.rgb+=vec3(.34,.6,.53)*kesselScanStrength*(scanBand*.45+scanGrid*.09);
 #include <tonemapping_fragment>`,
        );
    };
  }
  function setScan(value) {
    scan = value;
    const strength = Math.sin(Math.PI * value);
    scanUniforms.kesselScanX.value = THREE.MathUtils.lerp(-88, 88, value);
    scanUniforms.kesselScanStrength.value = strength;
    const opacity =
      1 -
      THREE.MathUtils.smoothstep(value, 0.1, 0.38) +
      THREE.MathUtils.smoothstep(value, 0.62, 0.94);
    for (const entry of original) {
      if (entry.material.userData.machineMaterial) {
        entry.material.opacity = entry.opacity * opacity;
        entry.material.transparent = true;
      }
    }
    for (const entry of fleet.entries) entry.truck.visible = true;
    loading.root.visible = true;
    routes.children.forEach((object) => {
      object.material.opacity = 0.72 * opacity;
    });
    fleet.group.children
      .filter((object) => object.userData.routeId)
      .forEach((object) => {
        object.material.opacity = 0.8 * opacity;
      });
  }
  for (const machine of [
    ...fleet.entries.map((entry) => entry.truck),
    loading.root,
  ])
    machine.traverse((object) => {
      if (object.isMesh)
        for (const material of Array.isArray(object.material)
          ? object.material
          : [object.material]) {
          material.userData.machineMaterial = true;
          material.userData.scanTransparent = true;
          material.transparent = true;
        }
    });

  function update(delta) {
    elapsed += delta;
    for (const entry of fleet.entries) {
      const hold = data.baseline_holds.find(
        (item) => item.vehicle_id === entry.id,
      );
      entry.speed = trained
        ? data.fleet.speed_mps.converged
        : data.fleet.speed_mps.unoptimised;
      if (!trained && hold && elapsed % hold.period_seconds < hold.hold_seconds)
        entry.speed = 0;
    }
    fleet.update(delta);
    loading.update(fleet.entries[0]);
    if (scan === 0)
      for (const entry of fleet.entries) entry.truck.visible = true;
  }
  return {
    root,
    fleet,
    setTrained,
    setScan,
    update,
    get trained() {
      return trained;
    },
  };
}
