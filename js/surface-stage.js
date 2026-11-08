import { authoredAsset } from "./authored-assets.js";
import * as THREE from "three";
import { texture, box, lightRig, seeded, line, varyTexture } from "./scene-utils.js";
import { createVehicle } from "./vehicle.js";
import { rockMaterial, rockBody } from "./geology.js";
export async function createSurface(config) {
  const root = new THREE.Group();
  root.name = "rutongo-surface";
  const data = config.assets.surface;
  const design = config.visuals.surface;
  const [satellite, heightMap, soil, rockMat, soilNormal, aggregate, vehicleModel, grass, grassNormal, grassRough] = await Promise.all([
    texture(data.satellite_image),
    new THREE.TextureLoader().loadAsync(data.elevation_heightmap),
    texture(data.detail_map),
    rockMaterial(config.visuals.rock),
    texture(config.assets.floor_normal, 17, false),
    texture(config.assets.ore),
    fetch(config.assets.truck, { cache: "no-store" }).then(r => r.json()),
    texture(design.ground.diff), texture(design.ground.normal,1,false), texture(design.ground.roughness,1,false),
  ]);
  rockMat.userData.vegetationMap=grass;
  const prepareRock=rockMat.onBeforeCompile;
  rockMat.onBeforeCompile=shader=>{
    prepareRock.call(rockMat,shader);shader.uniforms.vegetationMap={value:grass};
    shader.fragmentShader="uniform sampler2D vegetationMap;\n"+shader.fragmentShader.replace("float strata=",`float vegetation=smoothstep(.58,.85,rockN.y)*smoothstep(4.0,12.0,rockPosition.y);
      vec3 plants=texture2D(vegetationMap,rockPosition.xz/15.0).rgb*vec3(.7,.9,.6);
      rockTex=mix(rockTex,plants,vegetation*.85);
      float strata=`);
  };
  rockMat.customProgramCacheKey=()=>"kessel-surface-geology-v2";
  const image = heightMap.image,
    canvas = document.createElement("canvas");
  canvas.width = image.width;
  canvas.height = image.height;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  context.drawImage(image, 0, 0);
  const values = context.getImageData(0, 0, image.width, image.height).data;
  const [originX, , originZ] = data.site_origin_m;
  function raw(x, z) {
    const fx = THREE.MathUtils.clamp(
        ((x + originX + data.width_m / 2) / data.width_m) * (image.width - 1),
        0,
        image.width - 1,
      ),
      fy = THREE.MathUtils.clamp(
        ((z + originZ + data.width_m / 2) / data.width_m) * (image.height - 1),
        0,
        image.height - 1,
      );
    const x0 = Math.floor(fx),
      y0 = Math.floor(fy),
      x1 = Math.min(x0 + 1, image.width - 1),
      y1 = Math.min(y0 + 1, image.height - 1);
    const sample = (a, b) => values[(b * image.width + a) * 4] / 255;
    return (
      THREE.MathUtils.lerp(
        THREE.MathUtils.lerp(sample(x0, y0), sample(x1, y0), fx - x0),
        THREE.MathUtils.lerp(sample(x0, y1), sample(x1, y1), fx - x0),
        fy - y0,
      ) *
      (data.elevation_max_m - data.elevation_min_m)
    );
  }
  const zero = raw(0, 0);
  const elevation = (x, z) =>
    THREE.MathUtils.lerp(
      0,
      raw(x, z) - zero,
      THREE.MathUtils.smoothstep(Math.hypot(x, z), 115, 240),
    );
  const geometry = new THREE.PlaneGeometry(
    data.width_m,
    data.width_m,
    128,
    128,
  );
  geometry.rotateX(-Math.PI / 2);
  const positions = geometry.attributes.position;
  for (let i = 0; i < positions.count; i++) {
    const x = positions.getX(i) - originX,
      z = positions.getZ(i) - originZ;
    positions.setXYZ(i, x, elevation(x, z), z);
  }
  geometry.computeVertexNormals();
  const terrainMaterial = new THREE.MeshStandardMaterial({
    map: satellite,
    roughness: 1,
  });
  Object.assign(terrainMaterial.userData,{detailMap:grass,detailNormal:grassNormal,detailRough:grassRough});
  terrainMaterial.onBeforeCompile = (shader) => {
    shader.uniforms.detailMap = { value: grass };
    shader.uniforms.detailNormal = {value:grassNormal};
    shader.uniforms.detailRough = {value:grassRough};
    shader.vertexShader =
      "varying vec3 terrainPosition;\n" +
      shader.vertexShader.replace(
        "#include <begin_vertex>",
        "#include <begin_vertex>\nterrainPosition=position;",
      );
    shader.fragmentShader =
      "uniform sampler2D detailMap,detailNormal,detailRough;\nvarying vec3 terrainPosition;\n" +
      shader.fragmentShader.replace(
        "#include <map_fragment>",
        `#include <map_fragment>
 vec2 groundUV=terrainPosition.xz/15.0;
 vec3 detail=mix(texture2D(detailMap,groundUV).rgb,texture2D(detailMap,groundUV*.73+vec2(.37,.62)).rgb,.4);
 float terrainPatch=sin(terrainPosition.x*.018+sin(terrainPosition.z*.025)*3.0)*sin(terrainPosition.z*.034);
 vec3 localGround=detail*mix(vec3(.58,.8,.48),vec3(.7,.88,.61),smoothstep(-.45,.7,terrainPatch));
 diffuseColor.rgb=mix(localGround,diffuseColor.rgb,smoothstep(180.0,850.0,length(terrainPosition.xz)));
 `,
      );
    shader.fragmentShader=shader.fragmentShader.replace("#include <roughnessmap_fragment>",`#include <roughnessmap_fragment>
      roughnessFactor=mix(texture2D(detailRough,terrainPosition.xz/15.0).r,1.0,smoothstep(180.0,850.0,length(terrainPosition.xz)));`);
    shader.fragmentShader=shader.fragmentShader.replace("#include <normal_fragment_maps>",`#include <normal_fragment_maps>
      vec3 n=texture2D(detailNormal,terrainPosition.xz/15.0).xyz*2.0-1.0;
      normal=normalize(normal+mat3(viewMatrix)*vec3(n.x,n.z-1.0,n.y)*.35*(1.0-smoothstep(180.0,850.0,length(terrainPosition.xz))));
    `);
  };
  const terrain = new THREE.Mesh(geometry, terrainMaterial);
  terrain.receiveShadow = true;
  root.add(terrain);
  const yardMap = soil.clone();
  yardMap.repeat.set(17, 14);
  const yardMat = new THREE.MeshStandardMaterial({
    map: yardMap,
    normalMap: soilNormal,
    normalScale: new THREE.Vector2(0.3, 0.3),
    color: 0xa2a799,
    roughness: 1,
  });
  const yardShape = new THREE.Shape(design.yard_outline.map(([x, z]) => new THREE.Vector2(x, -z)));
  const yardGeometry = new THREE.ShapeGeometry(yardShape, 1);
  yardGeometry.rotateX(-Math.PI / 2);
  const uv = yardGeometry.attributes.uv, yardPositions = yardGeometry.attributes.position;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, yardPositions.getX(i) / 5, yardPositions.getZ(i) / 5);
  yardMap.repeat.set(1, 1); soilNormal.repeat.set(1, 1);
  yardMat.transparent = true;
  yardMat.onBeforeCompile = (shader) => {
    shader.uniforms.yardOutline = { value: design.yard_outline.map(p => new THREE.Vector2(...p)) };
    shader.vertexShader = "varying vec2 yardPoint;\n" + shader.vertexShader.replace("#include <begin_vertex>", "#include <begin_vertex>\nyardPoint=position.xz;");
    shader.fragmentShader = "uniform vec2 yardOutline[10]; varying vec2 yardPoint;\n" + shader.fragmentShader.replace("#include <alphatest_fragment>", `
      float edgeDistance=1000.0;
      for(int i=0;i<10;i++){vec2 a=yardOutline[i],b=yardOutline[(i+1)%10],v=b-a;
        float t=clamp(dot(yardPoint-a,v)/dot(v,v),0.0,1.0);edgeDistance=min(edgeDistance,length(yardPoint-a-v*t));}
      diffuseColor.a*=smoothstep(0.0,4.0,edgeDistance);
      #include <alphatest_fragment>`);
  };
  varyTexture(yardMat);
  yardMat.customProgramCacheKey=()=>"kessel-authored-yard-edge-v1";
  const yard = new THREE.Mesh(yardGeometry, yardMat);
  yard.position.y = .14; yard.receiveShadow = true; root.add(yard);
  const buildingMat = new THREE.MeshStandardMaterial({
    color: 0x81877d,
    roughness: 0.75,
  });
  const metal = new THREE.MeshStandardMaterial({
    color: 0x626e70,
    roughness: 0.57,
    metalness: 0.75,
  });
  const dark = new THREE.MeshStandardMaterial({
    color: 0x293b41,
    roughness: 0.5,
  });
  for (const spec of data.buildings) {
    const [x, , z] = spec.position,
      [w, h, d] = spec.size;
    box([w, h, d], [x, h / 2, z], buildingMat, root);
    const roof = box([w + 1.8, .25, d + 1.8], [x, h + .4, z], metal, root);
    roof.rotation.z = .045;
    const ribCount = Math.ceil(w / .75);
    const ribs = new THREE.InstancedMesh(new THREE.BoxGeometry(.055, .1, d + 1.8), metal, ribCount);
    const ribPose = new THREE.Object3D();
    for (let i = 0; i < ribCount; i++) {
      const offset = (i / (ribCount - 1) - .5) * (w + 1.8);
      ribPose.position.set(x + offset, h + .58 + offset * .045, z); ribPose.updateMatrix(); ribs.setMatrixAt(i, ribPose.matrix);
    }
    root.add(ribs);
    const cladding = new THREE.InstancedMesh(new THREE.BoxGeometry(.045, h - .3, .08), metal, Math.ceil(w / 1.2));
    for (let i = 0; i < cladding.count; i++) {
      ribPose.position.set(x - w / 2 + i * 1.2, h / 2, z + d / 2 + .06); ribPose.updateMatrix(); cladding.setMatrixAt(i, ribPose.matrix);
    }
    root.add(cladding);
    for (const side of [-1, 1]) {
      box([.16, h, .16], [x + side * (w / 2 - .4), h / 2, z + d / 2 + .15], metal, root);
      box([w * .32, .2, 1.5], [x + side * w * .3, h * .77, z + d / 2 + .7], metal, root);
    }
    box(
      [w * 0.35, h * 0.75, 0.1],
      [x, h * 0.375, z + d / 2 + 0.08],
      dark,
      root,
    );
    for (const side of [-1, 1])
      box(
        [2.8, 1.5, 0.12],
        [x + side * w * 0.32, h * 0.6, z + d / 2 + 0.1],
        dark,
        root,
      );
  }
  const portal = new THREE.Group();
  portal.position.fromArray(data.portal_position);
  root.add(portal);
  // An open, extruded collar and recessed tunnel, rather than a black decal on a box.
  const half = design.portal_width_m / 2, height = design.portal_height_m;
  const outline = new THREE.Shape();
  outline.moveTo(-half - 1.4, 0); outline.lineTo(-half - 1.4, height * .55);
  outline.quadraticCurveTo(-half - 1.4, height + 1.3, 0, height + 1.3);
  outline.quadraticCurveTo(half + 1.4, height + 1.3, half + 1.4, height * .55);
  outline.lineTo(half + 1.4, 0); outline.closePath();
  const mouth = new THREE.Path();
  mouth.moveTo(-half, 0); mouth.lineTo(half, 0); mouth.lineTo(half, height * .5);
  mouth.quadraticCurveTo(half, height, 0, height); mouth.quadraticCurveTo(-half, height, -half, height * .5); mouth.closePath();
  outline.holes.push(mouth);
  const concrete = new THREE.MeshStandardMaterial({ color: 0x8c8c7d, roughness: .96 });
  const collar = new THREE.Mesh(new THREE.ExtrudeGeometry(outline, { depth: 10, bevelEnabled: true, bevelThickness: .18, bevelSize: .15, bevelSegments: 2, curveSegments: 16 }), concrete);
  collar.position.z = -8; collar.castShadow = collar.receiveShadow = true; portal.add(collar);
  const tunnel = new THREE.Mesh(new THREE.CylinderGeometry(half, half, 22, 24, 1, true, 0, Math.PI), rockMat);
  tunnel.rotation.set(Math.PI / 2, 0, Math.PI / 2); tunnel.position.set(0, 3, -12);
  tunnel.material.side = THREE.DoubleSide; portal.add(tunnel);
  box([half * 2, .2, 24], [0, .12, -10], yardMat, portal);
  box([half * 2, height, .2], [0, height / 2, -22], new THREE.MeshBasicMaterial({ color: 0x040605 }), portal);
  for (const side of [-1, 1]) {
    const rubble=rockBody({size:[15, 10, 18],position:[side * 12, 3, -6]},rockMat,portal,design.rock_seed+(side+1),1.1); rubble.material=rockMat;
    box([.3, 4.5, .3], [side * (half + .45), 2.25, 2.5], metal, portal);
    const stripes = new THREE.InstancedMesh(new THREE.BoxGeometry(.36,.35,.36),new THREE.MeshStandardMaterial({color:0xc3a057,roughness:.8}),4);
    const pose = new THREE.Object3D();
    for(let i=0;i<4;i++){pose.position.set(side*(half+.45),.7+i*.9,2.5);pose.updateMatrix();stripes.setMatrixAt(i,pose.matrix);}portal.add(stripes);
    box([.45,.15,1.2],[side*3.5,4.6,1],new THREE.MeshBasicMaterial({color:0xffe6bc}),portal);
  }
  try {
    const authored=await authoredAsset(config.visuals.authored?.portal);
    if(authored){for(const child of portal.children)if(child.isMesh&&child!==tunnel)child.visible=false;authored.traverse(o=>{if(o.isMesh&&o.material.name.includes("Rock"))o.material=rockMat;});portal.add(authored);}
  } catch(error){console.warn("Authored portal unavailable",error);}
  const portalLight = new THREE.PointLight(0xffd9a4, 80, 18, 2); portalLight.position.set(0,4,-4);portal.add(portalLight);
  const hillSpec=design.portal_hill, hillGeometry=new THREE.PlaneGeometry(hillSpec.size[0],hillSpec.size[2],40,40);
  hillGeometry.rotateX(-Math.PI/2);hillGeometry.translate(...hillSpec.position);
  const hp=hillGeometry.attributes.position;
  for(let i=0;i<hp.count;i++){
    const x=hp.getX(i),z=hp.getZ(i),r=Math.pow(x/(hillSpec.size[0]/2),2)+Math.pow((z-hillSpec.position[2])/(hillSpec.size[2]/2),2);
    const shape=Math.max(0,1-r),front=THREE.MathUtils.smoothstep(-z,66,95);
    hp.setY(i,hillSpec.size[1]*shape*front*(.9+.08*Math.sin(x*.041)+.06*Math.cos(z*.031)));
  }
  const hillIndices=[];
  for(let i=0;i<hillGeometry.index.count;i+=3){
    const tri=[0,1,2].map(j=>hillGeometry.index.getX(i+j));
    const x=tri.reduce((v,j)=>v+hp.getX(j),0)/3,z=tri.reduce((v,j)=>v+hp.getZ(j),0)/3;
    if(Math.abs(x)<hillSpec.aperture_half_width_m&&z>hillSpec.aperture_end_z)continue;
    hillIndices.push(...tri);
  }
  hillGeometry.setIndex(hillIndices);hillGeometry.computeVertexNormals();
  const hill=new THREE.Mesh(hillGeometry,rockMat);hill.castShadow=hill.receiveShadow=true;root.add(hill);
  const roadGeometry = new THREE.PlaneGeometry(12, 750, 2, 80);
  roadGeometry.rotateX(-Math.PI / 2);
  roadGeometry.translate(0, 0, 300);
  const roadVertices = roadGeometry.attributes.position;
  for (let i = 0; i < roadVertices.count; i++)
    roadVertices.setY(
      i,
      elevation(roadVertices.getX(i), roadVertices.getZ(i)) + 0.3,
    );
  roadGeometry.computeVertexNormals();
  const roadMap = soil.clone();
  roadMap.repeat.set(2, 100);
  const road = new THREE.Mesh(
    roadGeometry,
    varyTexture(new THREE.MeshStandardMaterial({
      map: roadMap,
      roughness: 1,
      color: 0x989078,
    })),
  );
  road.receiveShadow = true;
  root.add(road);
  const rand = seeded(data.tree_seed),
    count = data.tree_count;
  const trunk = new THREE.InstancedMesh(
    new THREE.CylinderGeometry(0.3, 0.55, 4, 5),
    new THREE.MeshStandardMaterial({ color: 0x544a36, roughness: 1 }),
    count,
  );
  const canopy = new THREE.InstancedMesh(
    new THREE.IcosahedronGeometry(1, 2),
    new THREE.MeshStandardMaterial({ color: 0x415a34, roughness: 1 }),
    count * 3,
  );
  const pose = new THREE.Object3D();
  for (let i = 0; i < count; i++) {
    let x = (rand() - 0.5) * 1100,
      z = (rand() - 0.5) * 1000;
    if (Math.abs(x) < 110 && Math.abs(z) < 130) x += x < 0 ? -140 : 140;
    const y = elevation(x, z),
      scale = 2 + rand() * 3;
    // The trunk used to be left at scale 1 whatever the canopy did, so a
    // five-metre crown sat on a one-metre stem and the tree read as a blob
    // floating above a stick. Scale it with the crown, with a little
    // independent slenderness so the stand is not uniform.
    pose.position.set(x, y + scale * 0.9, z);
    pose.scale.set(scale * (0.3 + rand() * 0.12), scale * 0.62, scale * (0.3 + rand() * 0.12));
    pose.rotation.set(0, rand() * Math.PI, 0);
    pose.updateMatrix();
    trunk.setMatrixAt(i, pose.matrix);
    pose.rotation.set(0, 0, 0);
    for (let lobe = 0; lobe < 3; lobe++) {
      pose.position.set(
        x + (lobe - 1) * scale * 0.55,
        y + 3 + scale * (lobe === 1 ? 1 : 0.5),
        z + (rand() - 0.5) * scale,
      );
      pose.scale.set(scale * 0.85, scale * (0.65 + rand() * 0.4), scale * 0.85);
      pose.rotation.set(rand(), rand(), rand());
      pose.updateMatrix();
      canopy.setMatrixAt(i * 3 + lobe, pose.matrix);
      canopy.setColorAt(
        i * 3 + lobe,
        // Lightness used to top out at 0.32, which rendered sunlit hillside
        // foliage as near-black silhouettes. Opened up and given a wider hue
        // and saturation spread so the stand reads as varied species.
        new THREE.Color().setHSL(
          0.19 + rand() * 0.13,
          0.26 + rand() * 0.22,
          0.3 + rand() * 0.2,
        ),
      );
    }
  }
  trunk.castShadow = true;
  canopy.castShadow = true;
  root.add(trunk, canopy);
  for (const [x, z] of design.tank_positions) {
    const tank = new THREE.Mesh(
      new THREE.CylinderGeometry(4, 4, 10, 24),
      metal,
    );
    tank.position.set(x, 5, z);
    tank.castShadow = true;
    root.add(tank);
  }
  for (const [index, [x, z]] of design.stockpiles.entries()) {
    const pileGeometry = new THREE.SphereGeometry(1, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2);
    const pp = pileGeometry.attributes.position;
    for(let i=0;i<pp.count;i++){const k=1+.13*Math.sin(i*2.71+index);pp.setXYZ(i,pp.getX(i)*k,pp.getY(i),pp.getZ(i)*k);}pileGeometry.computeVertexNormals();
    const pile = new THREE.Mesh(pileGeometry, rockMat);pile.position.set(x,.15,z);pile.scale.set(6,4,5);pile.castShadow=pile.receiveShadow=true;root.add(pile);
  }
  // Lightweight original service-yard details. Placements are authored, not survey data.
  const fencePoints=design.fence.map(p=>new THREE.Vector3(p[0],1.8,p[1]));
  const fenceMat=new THREE.MeshStandardMaterial({color:0x68716c,roughness:.7,metalness:.65});
  for(let i=1;i<fencePoints.length;i++) {
    const a=fencePoints[i-1],b=fencePoints[i],n=Math.ceil(a.distanceTo(b)/4),pose=new THREE.Object3D();
    const posts=new THREE.InstancedMesh(new THREE.CylinderGeometry(.075,.075,3.6,6),fenceMat,n+1);
    for(let j=0;j<=n;j++){pose.position.copy(a).lerp(b,j/n);pose.updateMatrix();posts.setMatrixAt(j,pose.matrix);}root.add(posts);
    for(const y of [.5,2,3.3])root.add(line([[a.x,y,a.z],[b.x,y,b.z]],0x6c756c,.65));
  }
  const conveyor = new THREE.Group();conveyor.position.set(33,0,47);conveyor.rotation.z=-.15;root.add(conveyor);
  box([25,.5,2.5],[0,4,0],dark,conveyor);box([25,.12,.2],[0,4.6,1.3],metal,conveyor);box([25,.12,.2],[0,4.6,-1.3],metal,conveyor);
  for(const x of [-10,0,10]){box([.25,4,.25],[x,2,-1],metal,conveyor);box([.25,4,.25],[x,2,1],metal,conveyor);}
  for(const x of [-76,-68,62,70]){box([1.8,.8,.7],[x,.4,8],concrete,root);}
  for(const x of [-7,7]){
    const drain=box([.35,.08,102],[x,.16,11],metal,root);drain.receiveShadow=true;
  }
  for (const spec of design.parked_vehicles) {
    const vehicle=createVehicle(spec.id,vehicleModel,{oreMap:aggregate,authoredHauler:config.visuals.authored?.hauler,authoredOverview:config.visuals.authored?.hauler_overview});vehicle.root.position.fromArray(spec.position);
    vehicle.root.rotation.y=spec.heading;vehicle.detail.visible=true;vehicle.overview.visible=false;vehicle.cargo.visible=false;
    vehicle.root.traverse(o=>{if(o.isMesh)o.castShadow=o.receiveShadow=true;});root.add(vehicle.root);
  }
  lightRig(root, 120);
  heightMap.dispose();
  return { root, portal: portal.position.clone(), elevation };
}
