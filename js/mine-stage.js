import { authoredAsset } from "./authored-assets.js";
import * as THREE from "three";
import { texture, box, lightRig, seeded, line, varyTexture } from "./scene-utils.js";
import { rockMaterial, rockBody } from "./geology.js";
import { createMaterialTransfer } from "./material-transfer.js";
import { createServices, createContactDust } from "./mine-services.js";
import { createFleet } from "./fleet.js";
import { createRouteRibbons } from "./underground.js";
import { createLoadingMachine } from "./loading-machine.js";
export async function createMine(config) {
  const root = new THREE.Group();
  root.name = "sliced-rock-mine";
  const data = config.mine;
  const [floor, ore, floorNormal, oreNormal, vehicleModel, rockMat] = await Promise.all([
    texture(config.assets.floor, 22), texture(config.assets.ore),
    texture(config.assets.floor_normal, 22, false), texture(config.assets.ore_normal, 1, false),
    fetch(config.assets.truck, { cache: "no-store" }).then((r) => r.json()), rockMaterial(config.visuals.rock),
  ]);
  const geologyRoot=new THREE.Group();root.add(geologyRoot);
  let rockIndex = config.visuals.geology_seed;
  rockBody(data.base, rockMat, geologyRoot, rockIndex++, 1.8);
  for (const spec of [...data.pillars, ...data.rims])
    rockBody(spec, rockMat, geologyRoot, rockIndex++, config.visuals.pillar_relief_m);
  try {
    const authored=await authoredAsset(config.visuals.authored?.geology);
    if(authored){authored.traverse(o=>{if(o.isMesh)o.material=o.material.name.includes("Section")?rockMat.userData.sectionMaterial:rockMat;});geologyRoot.visible=false;root.add(authored);}
  } catch(error){console.warn("Authored geology unavailable",error);}
  const floorShape=new THREE.Shape();
  for(let i=0;i<64;i++){const a=i*Math.PI/32,c=Math.cos(a),q=Math.sin(a),x=Math.sign(c)*Math.abs(c)**.20*data.floor_size[0]*.475,z=Math.sign(q)*Math.abs(q)**.20*data.floor_size[1]*.475;i?floorShape.lineTo(x,z):floorShape.moveTo(x,z);}
  floorShape.closePath();const floorGeometry=new THREE.ShapeGeometry(floorShape);
  const uv=floorGeometry.attributes.uv,pos=floorGeometry.attributes.position;
  for(let i=0;i<uv.count;i++)uv.setXY(i,pos.getX(i)/data.floor_size[0]+.5,pos.getY(i)/data.floor_size[1]+.5);
  const ground = new THREE.Mesh(
    floorGeometry,
    new THREE.MeshStandardMaterial({
      map: floor,
      normalMap: floorNormal,
      color: 0x85877f,
      roughness: 0.88,
    }),
  );
  varyTexture(ground.material);
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = data.floor_y + 0.12;
  ground.receiveShadow = true;
  root.add(ground);
  const wearMat = new THREE.MeshStandardMaterial({ color: 0x3a3c36, roughness: 0.56, transparent: true, opacity: 0.18, depthWrite: false });
  for (const segment of data.network.segments) {
    const points = segment.centerline_m;
    for (let i = 1; i < points.length; i++) {
      const from = new THREE.Vector3(...points[i - 1]), to = new THREE.Vector3(...points[i]);
      const strip = new THREE.Mesh(new THREE.PlaneGeometry(4.6, from.distanceTo(to)), wearMat);
      strip.rotation.set(-Math.PI / 2, 0, -Math.atan2(to.x - from.x, to.z - from.z));
      strip.position.copy(from).lerp(to, .5); strip.position.y += .15;
      root.add(strip);
    }
  }
  const routes = createRouteRibbons(data.network, data.routes);
  routes.traverse((object) => {
    if (object.isMesh) {
      object.material.color.set(0xe66f60);
      object.material.opacity = 0.62;
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
    { oreMap: ore, oreNormal, authoredHauler:config.visuals.authored?.hauler, authoredOverview:config.visuals.authored?.hauler_overview },
  );
  await Promise.all(fleet.entries.map(v=>v.ready));
  root.add(fleet.group);
  for (const entry of fleet.entries) {
    entry.detail.visible = true;
    entry.overview.visible = false;
    entry.truck.traverse((object) => {
      if (object.isMesh && object.name!=="contact-shadow") object.castShadow = true;
    });
  }
  const excavatorConfig = data.excavator;
  const loading = await createLoadingMachine(
    excavatorConfig,
    data.network.nodes.find((node) => node.id === "draw"),
  );
  root.add(loading.root);
  const transfer = createMaterialTransfer(config.visuals.transfer,
    new THREE.MeshStandardMaterial({map:ore,normalMap:oreNormal,roughness:1,color:0xa3977e}),
    fleet.entries, loading.bucketPosition);
  root.add(transfer.root);
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
  try {
    const [authored,normal,ao]=await Promise.all([authoredAsset(config.visuals.authored?.ore),texture(config.visuals.authored.ore.normal_path,1,false),texture(config.visuals.authored.ore.ao_path,1,false)]);
    if(authored){const colour=ore.clone();colour.flipY=normal.flipY=ao.flipY=false;colour.needsUpdate=true;const oreMaterial=new THREE.MeshStandardMaterial({map:colour,normalMap:normal,aoMap:ao,roughness:1,color:0xb0a48e});ao.channel=0;
      authored.traverse(o=>{if(o.isMesh)o.material=oreMaterial;});
      for(const point of data.ore_piles){const pile=authored.clone(true);pile.position.fromArray(point);pile.scale.set(1.35,1.1,1.35);root.add(pile);}rocks.visible=false;
    }
  } catch(error){console.warn('Authored ore unavailable',error);}

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
  createServices(config.visuals.services, root);
  const dust = createContactDust(config.visuals.dust, matchMedia("(prefers-reduced-motion: reduce)").matches);
  root.add(dust.root);
  lightRig(root, 95, "mine");
  for (const [x, y, z] of data.lamps.slice(0, 2)) {
    const lamp = new THREE.PointLight(0xffd6a0, 80, 28, 2);
    lamp.position.set(x, y - 2, z); root.add(lamp);
  }
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
    for (const entry of fleet.entries) { entry.detail.visible = true; entry.overview.visible = false; }
    fleet.group.children
      .filter((object) => object.userData.routeId)
      .forEach((object) => {
        object.material.color.set(value ? 0x8fcaa5 : 0xe66f60);
        object.material.depthTest = true;
        object.material.toneMapped = true;
        object.material.opacity = 0.62;
      });
    elapsed = 0;
  }
  const scanUniforms = {
    kesselScanX: { value: -90 },
    kesselScanStrength: { value: 0 },
  };
  for (const material of [rockMat, ground.material]) {
    material.customProgramCacheKey = () => "kessel-mine-scan-" + (material === rockMat ? "rock" : "floor");
    const prepare = material.onBeforeCompile;
    material.onBeforeCompile = (shader) => {
      prepare.call(material, shader);
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
    const opacity = 1 - strength * 0.08;
    for (const entry of fleet.entries) entry.truck.visible = true;
    loading.root.visible = true;
    routes.children.forEach((object) => {
      object.material.opacity = 0.62 * opacity;
    });
    fleet.group.children
      .filter((object) => object.userData.routeId)
      .forEach((object) => {
        object.material.opacity = 0.62 * opacity;
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
    loading.update(fleet.entries[0], delta);
    dust.update(delta, fleet.entries);
    root.updateMatrixWorld(true);
    transfer.update();
    if (scan === 0)
      for (const entry of fleet.entries) entry.truck.visible = true;
  }
  return {
    root,
    fleet,
    setTrained,
    setScan,
    update,
    setEffects(value) { dust.root.visible = value; },
    get trained() {
      return trained;
    },
  };
}
