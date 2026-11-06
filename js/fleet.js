import * as THREE from "three";
import { createVehicle } from "./vehicle.js";
const headingMatrix = new THREE.Matrix4();
const headingOrigin = new THREE.Vector3();
const headingUp = new THREE.Vector3(0, 1, 0);
function orient(quaternion, direction) {
  // Preserve world up on descending and returning routes, including a 180° turn.
  return quaternion.setFromRotationMatrix(headingMatrix.lookAt(direction, headingOrigin, headingUp));
}

function routePoints(network, route) {
  const segments = new Map(network.segments.map((segment) => [segment.id, segment]));
  const edges = new Map(network.graph.edges.map((edge) => [edge.id, edge]));
  const points = [];
  const nodePointIndices = [0];
  route.edge_ids.forEach((edgeId, index) => {
    const edge = edges.get(edgeId);
    const segment = edge && segments.get(edge.segment_id);
    const from = route.node_ids[index];
    const to = route.node_ids[index + 1];
    const forward = edge?.from === from && edge?.to === to;
    const reverse = edge?.to === from && edge?.from === to;
    if (!edge || !segment || (!forward && (!reverse || edge.one_way))) throw new Error(`Invalid vehicle route ${route.id} at ${edgeId}`);
    const centreline = forward ? segment.centerline_m : [...segment.centerline_m].reverse();
    for (const coordinate of centreline) {
      const point = new THREE.Vector3(...coordinate);
      if (!points.length || points[points.length - 1].distanceToSquared(point) > 1e-6) points.push(point);
    }
    nodePointIndices.push(points.length - 1);
  });
  const cumulative = [0];
  for (let i = 1; i < points.length; i += 1) cumulative.push(cumulative[i - 1] + points[i].distanceTo(points[i - 1]));
  const tipIndex=route.node_ids.findIndex(id=>network.nodes.find(node=>node.id===id)?.kind==="tipping_point");
  return { points, cumulative, length: cumulative.at(-1) || 1, tipDistance: cumulative[nodePointIndices[tipIndex]] };
}

function pointAt(path, distance, target) {
  const d = THREE.MathUtils.euclideanModulo(distance, path.length);
  let index = 1;
  while (index < path.cumulative.length - 1 && path.cumulative[index] < d) index += 1;
  const start = path.cumulative[index - 1];
  const span = Math.max(1e-6, path.cumulative[index] - start);
  const t = (d - start) / span;
  target.copy(path.points[index - 1]).lerp(path.points[index], t);
  const tangent = path.points[index].clone().sub(path.points[index - 1]).normalize();
  return tangent;
}

function makeRouteRibbon(path, routeIndex, routeCount, materialColour, network) {
  const laneSpacing = Math.max(0.04, Math.min(0.8, (network.design.cross_section.width_m - 0.4) / routeCount));
  const laneOffset = (routeIndex - (routeCount - 1) / 2) * laneSpacing;
  const halfWidth = Math.min(1.1, laneSpacing * 1.35) / 2;
  const positions = [];
  const indices = [];
  for (let index = 0; index < path.points.length; index += 1) {
    const previous = path.points[Math.max(0, index - 1)];
    const next = path.points[Math.min(path.points.length - 1, index + 1)];
    const tangent = next.clone().sub(previous);
    tangent.y = 0;
    if (tangent.lengthSq() < 1e-8) tangent.set(0, 0, -1);
    tangent.normalize();
    const lateral = new THREE.Vector3(-tangent.z, 0, tangent.x);
    const centre = path.points[index].clone().addScaledVector(lateral, laneOffset);
    centre.y += 0.22;
    const left = centre.clone().addScaledVector(lateral, halfWidth);
    const right = centre.clone().addScaledVector(lateral, -halfWidth);
    positions.push(left.x, left.y, left.z, right.x, right.y, right.z);
    if (index < path.points.length - 1) {
      const vertex = index * 2;
      indices.push(vertex, vertex + 2, vertex + 1, vertex + 1, vertex + 2, vertex + 3);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setIndex(indices);
  geometry.computeBoundingSphere();
  const material = new THREE.MeshBasicMaterial({ color: materialColour, side: THREE.DoubleSide, transparent: true, opacity: 0.9, depthTest: false, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -1, toneMapped: false });
  return new THREE.Mesh(geometry, material);
}

export function createFleet(network, routes, fleetConfig, vehicleModel, routeRibbons, predictionPreview, textures = {}) {
  const group = new THREE.Group();
  group.name = "scripted-haul-fleet";
  const entries = routes.map((route, index) => {
    const vehicle = createVehicle(route.vehicle_id, vehicleModel, textures);
    group.add(vehicle.root);
    const prediction = new THREE.Mesh(new THREE.BoxGeometry(...vehicleModel.prediction_dimensions_m), new THREE.MeshBasicMaterial({ color: 0x74d7e8, wireframe: true, transparent: true, opacity: .5, depthWrite: false, toneMapped: false }));
    prediction.visible = false;
    prediction.name = `${route.vehicle_id}-prediction-preview`;
    group.add(prediction);
    const path = routePoints(network, route);
    const distance = (fleetConfig.vehicles[index]?.phase_offset ?? index / routes.length) * path.length;
    return { ...vehicle, truck: vehicle.root, id: route.vehicle_id, route, path, prediction, distance, phase: distance > path.tipDistance ? "returning" : "hauling", dwell: 0, queued: false, speed: fleetConfig.speed_mps.unoptimised + index * fleetConfig.vehicle_speed_variation_mps };
  });
  let selectedId = null;
  let optimised = false;
  let inspectionPlayback = false;
  let sampleIndex = 1;
  const optimisedRibbons = [];
  const tangent = new THREE.Vector3();
  const targetRotation = new THREE.Quaternion();
  const samplePosition = new THREE.Vector3();
  const maxError = Math.max(.25, ...predictionPreview.samples.map(sample => sample.error_m));
  const cyan = new THREE.Color(0x74d7e8), amber = new THREE.Color(0xefbb66), red = new THREE.Color(0xed6b58);
  for (const entry of entries) {
    tangent.copy(pointAt(entry.path, entry.distance, entry.truck.position));
    orient(entry.truck.quaternion, tangent);
  }
  function update(delta) {
    for (const entry of entries) {
      const previousDistance = entry.distance;
      const previousPosition = entry.truck.position.clone();
      const moving = entry.phase === "hauling" || entry.phase === "returning";
      entry.queued = false;
      if (moving) {
        tangent.copy(pointAt(entry.path, entry.distance, samplePosition));
        entry.queued = !optimised && entries.some(other => {
          if (other === entry) return false;
          const separation = other.truck.position.clone().sub(entry.truck.position);
          return separation.length() < fleetConfig.queue_radius_m && separation.dot(tangent) > 1;
        });
        const scale = inspectionPlayback && selectedId === entry.id ? fleetConfig.inspection_time_scale : fleetConfig.time_scale;
        const gradeFactor = 1 - Math.min(fleetConfig.max_grade_speed_reduction, Math.abs(tangent.y) * fleetConfig.grade_speed_sensitivity);
        entry.distance += delta * entry.speed * scale * gradeFactor * (entry.queued ? fleetConfig.queued_speed_factor : 1);
        if (entry.phase === "hauling" && entry.distance >= entry.path.tipDistance) {
          entry.distance = entry.path.tipDistance;
          entry.phase = "tipping"; entry.dwell = 0;
        } else if (entry.phase === "returning" && entry.distance >= entry.path.length) {
          entry.distance = 0; entry.phase = "loading"; entry.dwell = 0;
        }
      } else {
        entry.dwell += delta;
        const dwellSeconds = fleetConfig.dwell_seconds[entry.phase];
        if (entry.dwell >= dwellSeconds) {
          entry.phase = entry.phase === "loading" ? "hauling" : "returning";
          entry.distance += .02;
          entry.dwell = 0;
        }
      }
      tangent.copy(pointAt(entry.path, entry.distance, entry.truck.position));
      const displacement = entry.truck.position.clone().sub(previousPosition);
      const travelling = moving && ["hauling", "returning"].includes(entry.phase) && displacement.lengthSq() > 1e-10;
      const travelDirection = travelling ? displacement.normalize() : tangent;
      orient(targetRotation, travelDirection);
      const tipProgress = entry.phase === "tipping" ? Math.min(1, entry.dwell / fleetConfig.dwell_seconds.tipping) : 0;
      // Lower the bed and align for the return leg before the truck moves.
      // This avoids driving backwards while easing through a 180-degree turn.
      if (entry.phase === "tipping" && tipProgress > .65) {
        orient(targetRotation, pointAt(entry.path, entry.distance + .02, samplePosition));
      }
      const directionRate = moving ? 7 * Math.max(1, (inspectionPlayback && selectedId === entry.id ? fleetConfig.inspection_time_scale : fleetConfig.time_scale) / 4) : 7;
      entry.truck.quaternion.slerp(targetRotation, 1 - Math.exp(-delta * directionRate));
      if (travelling && new THREE.Vector3(0, 0, 1).applyQuaternion(entry.truck.quaternion).dot(travelDirection) < .95) {
        entry.truck.quaternion.copy(targetRotation);
      }
      entry.truck.userData.phase = entry.queued ? "queued" : entry.phase;
      const bedAngle = entry.phase === "tipping" ? Math.sin(Math.min(1, tipProgress / .65) * Math.PI) * vehicleModel.dump_bed.tip_angle_radians : 0;
      entry.dumpBed.rotation.x = THREE.MathUtils.damp(entry.dumpBed.rotation.x, bedAngle, 8, delta);
      const load = entry.phase === "loading" ? THREE.MathUtils.clamp((entry.dwell / fleetConfig.dwell_seconds.loading - .25) / .75, 0, 1) : entry.phase === "returning" ? 0 : entry.phase === "tipping" ? 1 - THREE.MathUtils.smoothstep(tipProgress, .15, .45) : 1;
      entry.cargo.visible = load > .01;
      entry.cargo.scale.y = Math.max(.01, load);
      entry.proxyCargo.visible = load > .01;
      entry.load = load;
      const travelled = moving ? (entry.distance < previousDistance && entry.phase === "loading" ? entry.path.length - previousDistance : Math.max(0, entry.distance - previousDistance)) : 0;
      for (const wheel of entry.wheels) wheel.rotation.x += travelled / vehicleModel.wheels.radius_m;
      if (entry.prediction.visible) {
        const sample = predictionPreview.samples[sampleIndex];
        const sampleDistance = moving ? entry.distance + entry.speed * sample.horizon_seconds : entry.distance;
        const heading = pointAt(entry.path, sampleDistance, entry.prediction.position);
        entry.prediction.position.x += sample.error_m;
        entry.prediction.position.y += vehicleModel.prediction_dimensions_m[1] / 2;
        orient(entry.prediction.quaternion, heading);
        const normalised = Math.min(1, sample.error_m / maxError);
        entry.prediction.material.color.copy(normalised < .5 ? cyan.clone().lerp(amber, normalised * 2) : amber.clone().lerp(red, (normalised - .5) * 2));
      }
    }
  }
  function select(id) {
    selectedId = id;
    inspectionPlayback = false;
    for (const entry of entries) { entry.prediction.visible = entry.id === id; entry.detail.visible=entry.id===id; entry.overview.visible=entry.id!==id; }
    return entries.find(entry => entry.id === id) || null;
  }
  function nearestDistance(path, position, returning) {
    let best = Infinity, distance = 0;
    for (let i = 1; i < path.points.length; i += 1) {
      if (returning ? path.cumulative[i] < path.tipDistance : path.cumulative[i-1] >= path.tipDistance) continue;
      const a = path.points[i - 1], b = path.points[i];
      const direction = b.clone().sub(a);
      const t = THREE.MathUtils.clamp(position.clone().sub(a).dot(direction) / direction.lengthSq(), 0, 1);
      const point = a.clone().addScaledVector(direction, t);
      const error = point.distanceToSquared(position);
      if (error < best) { best = error; distance = path.cumulative[i - 1] + t * direction.length(); }
    }
    return distance;
  }
  function setOptimised(value) {
    if (optimised === value) return;
    optimised = value;
    routeRibbons.visible = !value;
    for (const ribbon of optimisedRibbons) { group.remove(ribbon); ribbon.geometry.dispose(); ribbon.material.dispose(); }
    optimisedRibbons.length = 0;
    entries.forEach((entry, index) => {
      const wasReturning = entry.phase === "returning";
      entry.path = routePoints(network, value ? { ...entry.route, node_ids: entry.route.optimised_node_ids || entry.route.node_ids, edge_ids: entry.route.optimised_edge_ids } : entry.route);
      const distance = nearestDistance(entry.path, entry.truck.position, wasReturning);
      entry.distance = distance;
      entry.speed = (value ? fleetConfig.speed_mps.converged : fleetConfig.speed_mps.unoptimised) + index * fleetConfig.vehicle_speed_variation_mps;
      if (value) {
        const ribbon = makeRouteRibbon(entry.path, index, entries.length, 0xff735f, network);
        ribbon.renderOrder = 5;
        ribbon.userData.routeId = entry.route.id;
        ribbon.userData.vehicleId = entry.id;
        group.add(ribbon); optimisedRibbons.push(ribbon);
      }
    });
  }
  function watchCycle() {
    const entry = entries.find(item => item.id === selectedId);
    if (!entry) return;
    entry.distance = 0; entry.phase = "loading"; entry.dwell = 0;
    inspectionPlayback = true;
    tangent.copy(pointAt(entry.path, 0, entry.truck.position));
    orient(entry.truck.quaternion, tangent);
  }
  return { group, entries, update, select, watchCycle, setOptimised, setPredictionSample(index) { sampleIndex = index; }, get selectedId() { return selectedId; }, get optimised() { return optimised; } };
}
