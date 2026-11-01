import * as THREE from "three";
import { createFleet } from "./fleet.js";
import { createLoadingMachine } from "./loading-machine.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

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
    profile.push([radius * Math.cos(angle), height / 2 * Math.sin(angle)]);
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

export function createRouteRibbons(network, routes = []) {
  const routeRoot = new THREE.Group();
  routeRoot.name = "scripted-route-ribbons";
  if (!routes.length) return routeRoot;

  const segments = new Map(network.segments.map((segment) => [segment.id, segment]));
  const edges = new Map(network.graph.edges.map((edge) => [edge.id, edge]));
  const narrowestHeading = Math.min(...network.graph.edges.map((edge) => edge.width_m));
  const laneSpacing = Math.max(0.04, Math.min(0.8, (narrowestHeading - 0.4) / routes.length));
  const ribbonWidth = Math.min(1.1, laneSpacing * 1.35);

  routes.forEach((route, routeIndex) => {
    if (route.node_ids.length !== route.edge_ids.length + 1) {
      throw new Error(`Route ${route.id} must have one more node than edge`);
    }
    const points = [];
    route.edge_ids.forEach((edgeId, index) => {
      const edge = edges.get(edgeId);
      const segment = edge && segments.get(edge.segment_id);
      const startNode = route.node_ids[index];
      const endNode = route.node_ids[index + 1];
      if (!edge || !segment) throw new Error(`Route ${route.id} refers to missing edge ${edgeId}`);
      const forward = edge.from === startNode && edge.to === endNode;
      const reverse = edge.to === startNode && edge.from === endNode;
      if (!forward && (!reverse || edge.one_way)) {
        throw new Error(`Route ${route.id} has an invalid direction on ${edgeId}`);
      }
      const centreline = forward ? segment.centerline_m : [...segment.centerline_m].reverse();
      for (const coordinate of centreline) {
        const point = new THREE.Vector3(...coordinate);
        if (!points.length || points[points.length - 1].distanceToSquared(point) > 1e-6) points.push(point);
      }
    });
    if (points.length < 2) throw new Error(`Route ${route.id} has no drawable centreline`);

    const laneOffset = (routeIndex - (routes.length - 1) / 2) * laneSpacing;
    const positions = [];
    const indices = [];
    for (let pointIndex = 0; pointIndex < points.length; pointIndex += 1) {
      const previous = points[Math.max(0, pointIndex - 1)];
      const next = points[Math.min(points.length - 1, pointIndex + 1)];
      const tangent = next.clone().sub(previous);
      tangent.y = 0;
      if (tangent.lengthSq() < 1e-8) tangent.set(0, 0, -1);
      tangent.normalize();
      const lateral = new THREE.Vector3(-tangent.z, 0, tangent.x);
      const centre = points[pointIndex].clone().addScaledVector(lateral, laneOffset);
      centre.y += 0.18;
      const halfWidth = ribbonWidth / 2;
      const left = centre.clone().addScaledVector(lateral, halfWidth);
      const right = centre.clone().addScaledVector(lateral, -halfWidth);
      positions.push(left.x, left.y, left.z, right.x, right.y, right.z);
      if (pointIndex < points.length - 1) {
        const vertex = pointIndex * 2;
        indices.push(vertex, vertex + 2, vertex + 1, vertex + 1, vertex + 2, vertex + 3);
      }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geometry.setIndex(indices);
    geometry.computeBoundingSphere();
    const colour = route.status === "converged" ? 0x65d79a : route.status === "operator_override" ? 0x69d9e8 : 0xff4038;
    const material = new THREE.MeshBasicMaterial({
      color: colour,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.94,
      depthWrite: false,
      depthTest: false,
      polygonOffset: true,
      polygonOffsetFactor: -1,
      toneMapped: false,
    });
    const ribbon = new THREE.Mesh(geometry, material);
    ribbon.renderOrder = 5;
    ribbon.name = `route-ribbon-${route.id}`;
    ribbon.userData.routeId = route.id;
    ribbon.userData.vehicleId = route.vehicle_id;
    ribbon.userData.status = route.status;
    routeRoot.add(ribbon);
  });
  return routeRoot;
}

export function setRouteStatus(root, status) {
  root.traverse((object) => {
    if (!object.userData?.routeId || !object.material?.color) return;
    const colour = status === "converged" ? 0x65d79a : 0xff4038;
    object.material.color.setHex(colour);
    object.userData.status = status;
  });
}

function makeLabel(text, colour = "#8eb6c9") {
  const canvas = document.createElement("canvas"); canvas.width = 512; canvas.height = 96;
  const context = canvas.getContext("2d");
  context.font = "500 27px monospace"; context.fillStyle = colour; context.fillText(text, 14, 56);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true, depthTest: false, opacity: .85 }));
  sprite.scale.set(92, 17, 1); return sprite;
}

function makeLowWalls(segment, material) {
  const { points } = centrelinePoints(segment);
  const half = segment.width_m / 2;
  const vertices = [];
  for (const sign of [-1, 1]) {
    for (let i = 1; i < points.length; i++) {
      const a = points[i - 1], b = points[i];
      const lateral = new THREE.Vector3(-(b.z-a.z), 0, b.x-a.x).normalize().multiplyScalar(sign * half);
      const p = a.clone().add(lateral), q = b.clone().add(lateral);
      vertices.push(p.x,p.y,p.z, q.x,q.y,q.z, p.x,p.y+.6,p.z, p.x,p.y+.6,p.z, q.x,q.y,q.z, q.x,q.y+.6,q.z);
    }
  }
  const geometry = new THREE.BufferGeometry(); geometry.setAttribute("position",new THREE.Float32BufferAttribute(vertices,3)); geometry.computeVertexNormals();
  return new THREE.Mesh(geometry, material);
}

export async function createUndergroundStage(network, { mobile = false, routes = [], fleet: fleetConfig, vehicleModel, predictionPreview, loadingBay, excavatorConfig } = {}) {
  const root = new THREE.Group(); root.name = "illustrative-underground-network";
  const loader = new THREE.TextureLoader();
  const [rockMap, floorMap, rockNormal, floorNormal, oreMap, oreNormal] = await Promise.all([
    loadTexture(loader, "assets/textures/rock_wall_09_diff.jpg", mobile),
    loadTexture(loader, "assets/textures/brown_mud_dry_diff.jpg", mobile),
    mobile ? null : loader.loadAsync("assets/textures/rock_wall_09_nor_gl.jpg"),
    mobile ? null : loader.loadAsync("assets/textures/brown_mud_dry_nor_gl.jpg"),
    loadTexture(loader,"assets/textures/aerial_rocks_02_diff.jpg",mobile),
    mobile ? null : loader.loadAsync("assets/textures/aerial_rocks_02_nor_gl.jpg"),
  ]);
  for(const texture of [rockNormal,floorNormal,oreNormal].filter(Boolean)) texture.wrapS=texture.wrapT=THREE.RepeatWrapping;
  rockMap.anisotropy = floorMap.anisotropy = mobile ? 1 : 4;
  const rockMaterial = new THREE.MeshStandardMaterial({ map: rockMap, normalMap: rockNormal, normalScale: new THREE.Vector2(.65,.65), roughness: .94, side: THREE.DoubleSide });
  const floorMaterial = new THREE.MeshStandardMaterial({ map: floorMap, normalMap: floorNormal, normalScale: new THREE.Vector2(.6,.6), color: 0xc3bdab, roughness: .92, side: THREE.DoubleSide });
  const wallMaterial = new THREE.MeshStandardMaterial({ color: 0x71848a, roughness: .9, side: THREE.DoubleSide });
  const interiors = new THREE.Group(); interiors.visible = false;
  const cutaway = new THREE.Group();
  const annotations = new THREE.Group();
  const floorGeometries=[],wallGeometries=[],centrelinePositions=[];
  root.add(interiors, cutaway, annotations);
  root.add(new THREE.HemisphereLight(0xc0e0f2, 0x3a332c, 2.0));
  const fill = new THREE.DirectionalLight(0xffe6bb, 2.0); fill.position.set(-80, 150, 80); root.add(fill);
  for (const segment of network.segments) {
    if (segment.kind !== "surface_tipping_bay") {
      const shell = makeTunnelShell(segment, segment.width_m, segment.height_m, rockMaterial);
      shell.geometry.computeBoundingSphere(); shell.name = `tunnel-${segment.id}`; interiors.add(shell);
    }
    floorGeometries.push(makeFloor(segment, floorMaterial).geometry);
    wallGeometries.push(makeLowWalls(segment, wallMaterial).geometry);
    for(let index=1;index<segment.centerline_m.length;index++) {
      for(const point of [segment.centerline_m[index-1],segment.centerline_m[index]]) centrelinePositions.push(point[0],point[1]+.17,point[2]);
    }
  }
  const grid = new THREE.GridHelper(1100, 44, 0x173242, 0x101f2b); grid.position.set(0,-88,-400); grid.material.transparent = true; grid.material.opacity = .5; annotations.add(grid);
  for (const node of network.nodes.filter(node => /^ramp-L/.test(node.id))) {
    const label = makeLabel(`LEVEL ${node.level.slice(1).padStart(2,"0")} / ${Math.abs(node.position_m[1])} M`);
    label.position.set(132, node.position_m[1] + 3, node.position_m[2]); annotations.add(label);
    const plate = new THREE.Mesh(new THREE.PlaneGeometry(245,160),new THREE.MeshBasicMaterial({color:0x132632,transparent:true,opacity:.22,side:THREE.DoubleSide,depthWrite:false}));
    plate.rotation.x = -Math.PI/2; plate.position.set(0,node.position_m[1]-3,node.position_m[2]); annotations.add(plate);
    const outline = new THREE.LineSegments(new THREE.EdgesGeometry(plate.geometry),new THREE.LineBasicMaterial({color:0x28495b,transparent:true,opacity:.4})); outline.rotation.copy(plate.rotation); outline.position.copy(plate.position); annotations.add(outline);
  }
  for (const route of routes) {
    const node=network.nodes.find(item=>item.id===route.node_ids[0]);
    const next=network.nodes.find(item=>item.id===route.node_ids[1]);
    const direction=new THREE.Vector3(...next.position_m).sub(new THREE.Vector3(...node.position_m)).normalize();
    const centre=new THREE.Vector3(...node.position_m);
    const bay={width_m:loadingBay.width_m,height_m:loadingBay.height_m,centerline_m:[centre.clone().addScaledVector(direction,-loadingBay.length_behind_m).toArray(),centre.clone().addScaledVector(direction,loadingBay.length_ahead_m).toArray()]};
    floorGeometries.push(makeFloor(bay,floorMaterial).geometry);
    const capShape=new THREE.Shape();
    capShape.moveTo(-bay.width_m/2,0);capShape.lineTo(bay.width_m/2,0);capShape.lineTo(bay.width_m/2,bay.height_m);capShape.lineTo(-bay.width_m/2,bay.height_m);capShape.closePath();
    const hole=new THREE.Path();const aperture=network.design.cross_section;
    hole.moveTo(-aperture.width_m/2,0);hole.lineTo(-aperture.width_m/2,aperture.height_m/2);
    for(let i=0;i<=16;i++){const angle=Math.PI-Math.PI*i/16;hole.lineTo(aperture.width_m/2*Math.cos(angle),aperture.height_m/2+aperture.height_m/2*Math.sin(angle));}
    hole.lineTo(aperture.width_m/2,0);hole.closePath();capShape.holes.push(hole);
    const bulkhead=new THREE.Mesh(new THREE.ShapeGeometry(capShape),rockMaterial);bulkhead.position.copy(centre).addScaledVector(direction,loadingBay.length_ahead_m-.1);bulkhead.rotation.y=Math.atan2(direction.x,direction.z);bulkhead.geometry.computeBoundingSphere();
    // The cap's vertices are local, so retain its centre in network coordinates for culling.
    bulkhead.userData.localCap=true;interiors.add(bulkhead);

    const shell=makeTunnelShell(bay,bay.width_m,bay.height_m,rockMaterial);shell.geometry.computeBoundingSphere();interiors.add(shell);
  }
  const floorGeometry=mergeGeometries(floorGeometries);floorGeometries.forEach(geometry=>geometry.dispose());
  const overviewFloorMaterial=new THREE.MeshBasicMaterial({map:floorMap,color:0x879a9b,side:THREE.DoubleSide});
  const floors=new THREE.Mesh(floorGeometry,overviewFloorMaterial);root.add(floors);
  const wallGeometry=mergeGeometries(wallGeometries);wallGeometries.forEach(geometry=>geometry.dispose());
  cutaway.add(new THREE.Mesh(wallGeometry,new THREE.MeshBasicMaterial({color:0x38515d,side:THREE.DoubleSide})));
  const routeBaseGeometry=new THREE.BufferGeometry();routeBaseGeometry.setAttribute("position",new THREE.Float32BufferAttribute(centrelinePositions,3));
  annotations.add(new THREE.LineSegments(routeBaseGeometry,new THREE.LineBasicMaterial({color:0x527d8a,transparent:true,opacity:.55})));
  const fixtures=new THREE.Group(); fixtures.visible=false; root.add(fixtures);
  const lampPoses=[],cablePositions=[];
  const pose=new THREE.Object3D();
  for(const segment of network.segments) {
    const {curve}=centrelinePoints(segment);
    const count=Math.max(1,Math.floor(curve.getLength()/18));
    const cable=[];
    for(let i=0;i<=count;i++) {
      const t=i/count, point=curve.getPointAt(t), tangent=curve.getTangentAt(t);
      const lateral=new THREE.Vector3(-tangent.z,0,tangent.x).normalize();
      point.addScaledVector(lateral,segment.width_m/2-.2);point.y+=segment.height_m*.65;
      pose.position.copy(point);pose.rotation.set(0,Math.atan2(tangent.x,tangent.z),0);pose.updateMatrix();lampPoses.push(pose.matrix.clone());
      cable.push(point);
    }
    for(let i=1;i<cable.length;i++) cablePositions.push(...cable[i-1].toArray(),...cable[i].toArray());
  }
  const lamps=new THREE.InstancedMesh(new THREE.BoxGeometry(.12,.09,.85),new THREE.MeshBasicMaterial({color:0xc4e5ec,toneMapped:false}),lampPoses.length);
  lampPoses.forEach((matrix,index)=>lamps.setMatrixAt(index,matrix)); fixtures.add(lamps);
  const cableGeometry=new THREE.BufferGeometry(); cableGeometry.setAttribute("position",new THREE.Float32BufferAttribute(cablePositions,3));
  fixtures.add(new THREE.LineSegments(cableGeometry,new THREE.LineBasicMaterial({color:0x273a40})));
  const routeRibbons = createRouteRibbons(network, routes); root.add(routeRibbons);
  const fleet = createFleet(network, routes, fleetConfig, vehicleModel, routeRibbons, predictionPreview, {oreMap,oreNormal}); root.add(fleet.group);
  const rockGeometry = new THREE.IcosahedronGeometry(1,1);
  const oreMaterial = new THREE.MeshStandardMaterial({map:oreMap,normalMap:oreNormal,color:0xc4b7a6,roughness:1});
  for (const node of network.nodes.filter(node => ["draw_point","tipping_point"].includes(node.kind))) {
    const position = new THREE.Vector3(...node.position_m);
    const marker = new THREE.Mesh(new THREE.RingGeometry(1.2,1.7,24),new THREE.MeshBasicMaterial({color:node.kind === "draw_point" ? 0xeab276 : 0x80d9b0,side:THREE.DoubleSide,toneMapped:false}));
    marker.rotation.x = -Math.PI/2; marker.position.copy(position).y += .12; annotations.add(marker);
    // Ore beside each draw point makes the loading location legible at close range.
    const ore = new THREE.InstancedMesh(rockGeometry, oreMaterial, 25);
    const transform = new THREE.Object3D();
    for (let i=0;i<25;i++) {
      transform.position.copy(position).add(new THREE.Vector3(2.4 + Math.sin(i*2.4)*.8, .25+(i%4)*.24, Math.cos(i*1.7)*2));
      transform.rotation.set(i*.4,i*.7,i*.2); transform.scale.setScalar(.28+(i%4)*.08); transform.updateMatrix(); ore.setMatrixAt(i,transform.matrix);
    }
    root.add(ore);
  }
  // One lamp follows the inspected machine; the fleet overview adds no local lights.
  const headlight = new THREE.SpotLight(0xd5edff, 36, 32, .65, .6, 1.3); headlight.visible = false;
  root.add(headlight,headlight.target);
  const loadingRoute=routes.find(route=>route.vehicle_id===excavatorConfig.vehicle_id);
  const drawPoint=network.nodes.find(node=>node.id===loadingRoute.node_ids[0]);
  const loadingMachine=await createLoadingMachine(excavatorConfig,drawPoint);
  root.add(loadingMachine.root);
  let inspecting = false;
  root.userData.setInspection = value => { inspecting=value; floors.material=value?floorMaterial:overviewFloorMaterial; fixtures.visible=value; interiors.visible=value; annotations.visible=!value; cutaway.visible=!value; headlight.visible=value; routeRibbons.visible=!value&&!fleet.optimised; fleet.group.children.filter(item=>item.userData.routeId).forEach(item=>item.visible=!value); };
  root.userData.updateInspection = entry => {
    loadingMachine.update(fleet.entries.find(item=>item.id===excavatorConfig.vehicle_id));
    if (!inspecting || !entry) return;
    for (const shell of interiors.children) shell.visible = (shell.userData.localCap ? shell.position : shell.geometry.boundingSphere.center).distanceTo(entry.truck.position) < shell.geometry.boundingSphere.radius + 45;
    headlight.position.copy(entry.truck.position).add(new THREE.Vector3(0,1.5,3).applyQuaternion(entry.truck.quaternion));
    headlight.target.position.copy(entry.truck.position).add(new THREE.Vector3(0,.4,18).applyQuaternion(entry.truck.quaternion));
  };
  root.userData.extraMaterials=[floorMaterial,overviewFloorMaterial,wallMaterial]; root.userData.excavator=loadingMachine.root; root.userData.routeRibbons=routeRibbons; root.userData.fleet=fleet; root.userData.network=network;
  root.userData.networkId=network.meta.id; root.userData.seed=network.meta.seed;
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
  for(const material of root.userData.extraMaterials||[]) { materials.add(material); for(const value of Object.values(material)) if(value?.isTexture) textures.add(value); }
  geometries.forEach((geometry) => geometry.dispose());
  materials.forEach((material) => material.dispose());
  textures.forEach((texture) => texture.dispose());
}
