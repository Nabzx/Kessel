import * as THREE from "three";
import { texture, box, lightRig, seeded, line } from "./scene-utils.js";
export async function createSurface(config) {
  const root = new THREE.Group();
  root.name = "rutongo-surface";
  const data = config.assets.surface;
  const [satellite, heightMap, soil, rock, soilNormal] = await Promise.all([
    texture(data.satellite_image),
    new THREE.TextureLoader().loadAsync(data.elevation_heightmap),
    texture(data.detail_map),
    texture(config.assets.wall),
    texture(config.assets.floor_normal, 17, false),
  ]);
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
  terrainMaterial.userData.detailMap = soil;
  terrainMaterial.onBeforeCompile = (shader) => {
    shader.uniforms.detailMap = { value: soil };
    shader.vertexShader =
      "varying vec3 terrainPosition;\n" +
      shader.vertexShader.replace(
        "#include <begin_vertex>",
        "#include <begin_vertex>\nterrainPosition=position;",
      );
    shader.fragmentShader =
      "uniform sampler2D detailMap;\nvarying vec3 terrainPosition;\n" +
      shader.fragmentShader.replace(
        "#include <map_fragment>",
        `#include <map_fragment>
 vec2 groundUV=terrainPosition.xz/7.0;
 vec3 detail=texture2D(detailMap,groundUV).rgb;
 float terrainPatch=sin(terrainPosition.x*.018+sin(terrainPosition.z*.025)*3.0)*sin(terrainPosition.z*.034);
 vec3 localGround=mix(vec3(.14,.19,.105),vec3(.27,.25,.15),smoothstep(-.45,.7,terrainPatch))*mix(vec3(.7),detail*2.4,.65);
 diffuseColor.rgb=mix(localGround,diffuseColor.rgb,smoothstep(180.0,850.0,length(terrainPosition.xz)));
 `,
      );
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
    color: 0xa3a18d,
    roughness: 1,
  });
  box(
    [data.yard_size_m[0], 0.35, data.yard_size_m[1]],
    [0, -0.1, 0],
    yardMat,
    root,
  );
  const buildingMat = new THREE.MeshStandardMaterial({
    color: 0xb2b3a6,
    roughness: 0.8,
  });
  const metal = new THREE.MeshStandardMaterial({
    color: 0x5c6664,
    roughness: 0.57,
    metalness: 0.4,
  });
  const dark = new THREE.MeshStandardMaterial({
    color: 0x293b41,
    roughness: 0.5,
  });
  for (const spec of data.buildings) {
    const [x, , z] = spec.position,
      [w, h, d] = spec.size;
    box([w, h, d], [x, h / 2, z], buildingMat, root);
    box([w + 1.5, 0.4, d + 1.5], [x, h + 0.2, z], metal, root);
    for (let i = 0; i < 8; i++)
      box(
        [0.12, 0.18, d + 1.5],
        [x + (i / 7 - 0.5) * w, h + 0.45, z],
        metal,
        root,
      );
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
  box(
    [22, 10, 9],
    [0, 4, -2],
    new THREE.MeshStandardMaterial({ map: rock, roughness: 0.95 }),
    portal,
  );
  const mouth = new THREE.Shape();
  mouth.moveTo(-4, 0);
  mouth.lineTo(-4, 3);
  mouth.quadraticCurveTo(-4, 7, 0, 7);
  mouth.quadraticCurveTo(4, 7, 4, 3);
  mouth.lineTo(4, 0);
  mouth.closePath();
  const opening = new THREE.Mesh(
    new THREE.ShapeGeometry(mouth),
    new THREE.MeshBasicMaterial({ color: 0x020304 }),
  );
  opening.position.set(0, 0, 2.56);
  portal.add(opening);
  for (const side of [-1, 1]) {
    box([0.2, 4.6, 0.2], [side * 4.4, 2.3, 2.8], metal, portal);
    box(
      [0.13, 1, 0.1],
      [side * 4.6, 3.8, 2.95],
      new THREE.MeshBasicMaterial({ color: 0xf6dba7 }),
      portal,
    );
  }
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
    new THREE.MeshStandardMaterial({
      map: roadMap,
      roughness: 1,
      color: 0x989078,
    }),
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
    pose.position.set(x, y + 2, z);
    pose.scale.set(1, 1, 1);
    pose.updateMatrix();
    trunk.setMatrixAt(i, pose.matrix);
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
        new THREE.Color().setHSL(
          0.21 + rand() * 0.08,
          0.2 + rand() * 0.15,
          0.22 + rand() * 0.1,
        ),
      );
    }
  }
  trunk.castShadow = true;
  canopy.castShadow = true;
  root.add(trunk, canopy);
  for (const x of [-60, -46]) {
    const tank = new THREE.Mesh(
      new THREE.CylinderGeometry(4, 4, 10, 24),
      metal,
    );
    tank.position.set(x, 5, 34);
    tank.castShadow = true;
    root.add(tank);
  }
  for (const [x, z] of [
    [21, 43],
    [28, 43],
    [35, 43],
  ]) {
    const pile = new THREE.Mesh(
      new THREE.ConeGeometry(5, 4, 9),
      new THREE.MeshStandardMaterial({ map: rock, roughness: 1 }),
    );
    pile.position.set(x, 2, z);
    root.add(pile);
  }
  lightRig(root, 650);
  heightMap.dispose();
  return { root, portal: portal.position.clone(), elevation };
}
