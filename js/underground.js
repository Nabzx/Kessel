import * as THREE from "three";

function centrelinePoints(segment) {
  const points = segment.centerline_m.map((coordinates) => new THREE.Vector3(...coordinates));
  const curve = new THREE.CatmullRomCurve3(points, false, "centripetal");
  const steps = Math.max(2, Math.ceil(curve.getLength() / 6));
  return { curve, points: curve.getSpacedPoints(steps) };
}

function makeTunnelShell(segment, width, height, material) {
  const { curve, points } = centrelinePoints(segment);
  const radius = width / 2;
  const profile = [
    [-radius, -height / 2],
    [radius, -height / 2],
    [radius, 0],
  ];
  for (let step = 1; step <= 12; step += 1) {
    const angle = Math.PI * step / 12;
    profile.push([radius * Math.cos(angle), radius * Math.sin(angle)]);
  }

  const positions = [];
  const uvs = [];
  const indices = [];
  const up = new THREE.Vector3(0, 1, 0);
  const totalLength = curve.getLength();
  for (let ring = 0; ring < points.length; ring += 1) {
    const tangent = curve.getTangentAt(ring / (points.length - 1)).normalize();
    const lateral = tangent.clone().cross(up).normalize();
    const origin = points[ring].clone().addScaledVector(up, height / 2);
    for (let edge = 0; edge < profile.length; edge += 1) {
      const [x, y] = profile[edge];
      const vertex = origin.clone().addScaledVector(lateral, x).addScaledVector(up, y);
      positions.push(vertex.x, vertex.y, vertex.z);
      uvs.push((ring / (points.length - 1)) * totalLength / 8, edge / profile.length * 3);
    }
  }
  for (let ring = 0; ring < points.length - 1; ring += 1) {
    for (let edge = 0; edge < profile.length; edge += 1) {
      const nextEdge = (edge + 1) % profile.length;
      const a = ring * profile.length + edge;
      const b = (ring + 1) * profile.length + edge;
      const c = ring * profile.length + nextEdge;
      const d = (ring + 1) * profile.length + nextEdge;
      indices.push(a, b, c, c, b, d);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return new THREE.Mesh(geometry, material);
}

function makeFloor(segment, material) {
  const { curve, points } = centrelinePoints(segment);
  const width = segment.width_m || 3;
  const halfWidth = width / 2;
  const positions = [];
  const uvs = [];
  const indices = [];
  const up = new THREE.Vector3(0, 1, 0);
  const totalLength = curve.getLength();
  for (let i = 0; i < points.length; i += 1) {
    const tangent = curve.getTangentAt(i / (points.length - 1)).normalize();
    const lateral = tangent.clone().cross(up).normalize();
    const centre = points[i].clone().addScaledVector(up, 0.05);
    const edgeA = centre.clone().addScaledVector(lateral, halfWidth);
    const edgeB = centre.clone().addScaledVector(lateral, -halfWidth);
    positions.push(edgeA.x, edgeA.y, edgeA.z, edgeB.x, edgeB.y, edgeB.z);
    uvs.push(0, i / (points.length - 1) * totalLength / 8, 1, i / (points.length - 1) * totalLength / 8);
    if (i < points.length - 1) {
      const start = i * 2;
      indices.push(start, start + 2, start + 1, start + 1, start + 2, start + 3);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return new THREE.Mesh(geometry, material);
}

async function loadTexture(loader, path, mobile) {
  const texture = await loader.loadAsync(path);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.colorSpace = THREE.SRGBColorSpace;
  if (mobile) texture.anisotropy = 1;
  return texture;
}

export async function createUndergroundStage(network, { mobile = false } = {}) {
  const root = new THREE.Group();
  root.name = "illustrative-underground-network";
  const loader = new THREE.TextureLoader();
  const [rockMap, floorMap, rockNormal, floorNormal] = await Promise.all([
    loadTexture(loader, "assets/textures/rock_wall_09_diff.jpg", mobile),
    loadTexture(loader, "assets/textures/brown_mud_dry_diff.jpg", mobile),
    mobile ? Promise.resolve(null) : loader.loadAsync("assets/textures/rock_wall_09_nor_gl.jpg"),
    mobile ? Promise.resolve(null) : loader.loadAsync("assets/textures/brown_mud_dry_nor_gl.jpg"),
  ]);
  const rockMaterial = new THREE.MeshStandardMaterial({ map: rockMap, normalMap: rockNormal, roughness: 0.95, metalness: 0.02, side: THREE.DoubleSide });
  const floorMaterial = new THREE.MeshStandardMaterial({ map: floorMap, normalMap: floorNormal, roughness: 1, side: THREE.DoubleSide });
  if (rockNormal) rockNormal.wrapS = rockNormal.wrapT = THREE.RepeatWrapping;
  if (floorNormal) floorNormal.wrapS = floorNormal.wrapT = THREE.RepeatWrapping;
  const baseWidth = network.design.cross_section.width_m;
  const baseHeight = network.design.cross_section.height_m;

  root.add(new THREE.AmbientLight(0x8c97a1, 0.42));
  const fill = new THREE.DirectionalLight(0xb9c5cc, 0.36);
  fill.position.set(-80, 110, 140);
  root.add(fill);

  for (const segment of network.segments) {
    const width = segment.width_m || baseWidth;
    const height = segment.height_m || baseHeight;
    if (segment.kind !== "surface_tipping_bay") {
      const shell = makeTunnelShell(segment, width, height, rockMaterial);
      shell.name = `tunnel-${segment.id}`;
      shell.userData.segmentId = segment.id;
      root.add(shell);
    }
    root.add(makeFloor(segment, floorMaterial));
  }

  for (const node of network.nodes) {
    if (node.kind !== "draw_point" && node.kind !== "tipping_point") continue;
    const marker = new THREE.Mesh(
      new THREE.SphereGeometry(0.7, 12, 8),
      new THREE.MeshBasicMaterial({ color: node.kind === "draw_point" ? 0xffae59 : 0x76ddba }),
    );
    marker.position.fromArray(node.position_m).y += 1;
    marker.name = node.id;
    marker.userData.nodeId = node.id;
    root.add(marker);
  }

  const lightNodes = network.nodes.filter((node) => node.kind === "junction" && node.id.startsWith("ramp-"));
  lightNodes.push(network.nodes.find((node) => node.id === "portal"));
  for (const node of lightNodes.filter(Boolean)) {
    const light = new THREE.PointLight(0xffd7a2, 64, 42, 2);
    light.position.fromArray(node.position_m).y += 2.2;
    root.add(light);
  }
  root.userData.networkId = network.meta.id;
  root.userData.seed = network.meta.seed;
  return root;
}

export function disposeUndergroundStage(root) {
  const geometries = new Set();
  const materials = new Set();
  const textures = new Set();
  root.traverse((object) => {
    if (object.geometry) geometries.add(object.geometry);
    const objectMaterials = Array.isArray(object.material) ? object.material : [object.material];
    for (const material of objectMaterials) {
      if (!material) continue;
      materials.add(material);
      for (const value of Object.values(material)) {
        if (value && value.isTexture) textures.add(value);
      }
    }
  });
  geometries.forEach((geometry) => geometry.dispose());
  materials.forEach((material) => material.dispose());
  textures.forEach((texture) => texture.dispose());
}
