import * as THREE from "three";

function makeTruck(id, model) {
  const root = new THREE.Group();
  root.name = id;
  root.userData.vehicleId = id;
  root.userData.selectable = true;
  const materials = Object.fromEntries(Object.entries(model.materials).map(([name, spec]) => [name, new THREE.MeshStandardMaterial({
    color: spec.colour, roughness: spec.roughness ?? 0.8, metalness: spec.metalness ?? 0,
    ...(spec.emissive ? { emissive: spec.emissive } : {}),
  })]));
  materials.lamp = new THREE.MeshBasicMaterial({ color: model.materials.lamp.colour, toneMapped: false });
  const addBox = (spec, parent = root) => {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(...spec.size_m), materials[spec.material]);
    mesh.position.fromArray(spec.position_m);
    mesh.castShadow = false;
    mesh.userData.vehicleId = id;
    parent.add(mesh);
    return mesh;
  };
  for (const part of model.parts) if (part.type === "box") addBox(part);
  const bedConfig = model.dump_bed;
  const dumpBed = new THREE.Group();
  dumpBed.position.fromArray(bedConfig.position_m);
  dumpBed.name = `${id}-dump-bed`;
  root.add(dumpBed);
  const bedMesh = new THREE.Mesh(new THREE.BoxGeometry(...bedConfig.body_size_m), materials.body);
  bedMesh.position.fromArray(bedConfig.body_position_m);
  dumpBed.add(bedMesh);
  for (const cargo of bedConfig.cargo_rocks) {
    const rock = new THREE.Mesh(new THREE.IcosahedronGeometry(cargo.radius_m, 0), materials.cargo);
    rock.position.fromArray(cargo.position_m);
    dumpBed.add(rock);
  }
  const wheelConfig = model.wheels;
  for (const side of [-1, 1]) {
    for (const z of wheelConfig.axle_z_m) {
      const wheel = new THREE.Mesh(new THREE.CylinderGeometry(wheelConfig.radius_m, wheelConfig.radius_m, wheelConfig.width_m, wheelConfig.segments), materials[wheelConfig.material]);
      wheel.rotation.x = Math.PI / 2;
      wheel.position.set(side * wheelConfig.side_offset_m, wheelConfig.centre_y_m, z);
      wheel.userData.vehicleId = id;
      root.add(wheel);
    }
    const headlight = new THREE.Mesh(new THREE.SphereGeometry(model.headlights.radius_m, 8, 6), materials.lamp);
    headlight.position.set(side * model.headlights.side_offset_m, ...model.headlights.position_m);
    root.add(headlight);
    const beamConfig = model.headlights;
    const beam = new THREE.SpotLight(beamConfig.beam_colour, beamConfig.beam_intensity, beamConfig.beam_distance_m, beamConfig.beam_angle_radians, beamConfig.beam_penumbra, beamConfig.beam_decay);
    beam.position.set(side * beamConfig.side_offset_m, ...beamConfig.beam_position_m);
    beam.target.position.set(side * beamConfig.side_offset_m, ...beamConfig.beam_target_m);
    root.add(beam, beam.target);
  }
  root.userData.unselect = () => { root.scale.setScalar(1); };
  root.userData.select = () => { root.scale.setScalar(model.selection_scale); };
  return { root, forward: new THREE.Vector3(...model.forward_axis), dumpBed };
}

function routePoints(network, route) {
  const segments = new Map(network.segments.map((segment) => [segment.id, segment]));
  const edges = new Map(network.graph.edges.map((edge) => [edge.id, edge]));
  const points = [];
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
  });
  const cumulative = [0];
  for (let i = 1; i < points.length; i += 1) cumulative.push(cumulative[i - 1] + points[i].distanceTo(points[i - 1]));
  return { points, cumulative, length: cumulative.at(-1) || 1 };
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
  const laneSpacing = Math.max(0.04, Math.min(0.36, (network.design.cross_section.width_m - 0.4) / routeCount));
  const laneOffset = (routeIndex - (routeCount - 1) / 2) * laneSpacing;
  const halfWidth = Math.min(0.26, laneSpacing * 0.76) / 2;
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
  const material = new THREE.MeshBasicMaterial({ color: materialColour, side: THREE.DoubleSide, transparent: true, opacity: 0.94, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -1, toneMapped: false });
  return new THREE.Mesh(geometry, material);
}

export function createFleet(network, routes, fleetConfig, vehicleModel, routeRibbons) {
  const group = new THREE.Group();
  group.name = "scripted-haul-fleet";
  const waypointTargets = new THREE.Group();
  waypointTargets.name = "valid-waypoint-targets";
  waypointTargets.visible = false;
  group.add(waypointTargets);
  const targetById = new Map();
  for (const node of network.nodes.filter((item) => ["junction", "draw_point", "tipping_point"].includes(item.kind))) {
    const marker = new THREE.Mesh(new THREE.RingGeometry(0.7, 1.05, 24), new THREE.MeshBasicMaterial({ color: 0x70d7e8, side: THREE.DoubleSide, transparent: true, opacity: 0.92, depthWrite: false, toneMapped: false }));
    marker.rotation.x = -Math.PI / 2;
    marker.position.fromArray(node.position_m);
    marker.position.y += 0.3;
    marker.userData.nodeId = node.id;
    marker.userData.baseColour = 0x70d7e8;
    marker.visible = true;
    waypointTargets.add(marker);
    targetById.set(node.id, marker);
  }
  const entries = routes.map((route, index) => {
    const { root: truck, forward, dumpBed } = makeTruck(route.vehicle_id, vehicleModel);
    group.add(truck);
    const prediction = new THREE.Mesh(
      new THREE.BoxGeometry(...vehicleModel.prediction_dimensions_m),
      new THREE.MeshBasicMaterial({ color: vehicleModel.prediction_colour, wireframe: true, transparent: true, opacity: vehicleModel.prediction_opacity, depthWrite: false, toneMapped: false }),
    );
    prediction.visible = false;
    prediction.name = `${route.vehicle_id}-prediction-preview`;
    prediction.userData.vehicleId = route.vehicle_id;
    group.add(prediction);
    const path = routePoints(network, route);
    return {
      id: route.vehicle_id,
      route,
      activeRoute: route,
      path,
      truck,
      forward,
      dumpBed,
      prediction,
      distance: (fleetConfig.vehicles.find((vehicle) => vehicle.id === route.vehicle_id)?.phase_offset ?? index / routes.length) * path.length,
      speed: fleetConfig.speed_mps.unoptimised + index * fleetConfig.vehicle_speed_variation_mps,
    };
  });
  const tangent = new THREE.Vector3();
  const gradePosition = new THREE.Vector3();
  let selectedId = null;
  let optimised = false;
  const nodes = new Map(network.nodes.map((node) => [node.id, node]));
  const segmentLengths = new Map(network.segments.map((segment) => {
    const points = segment.centerline_m.map((coords) => new THREE.Vector3(...coords));
    return [segment.id, points.slice(1).reduce((total, point, index) => total + point.distanceTo(points[index]), 0)];
  }));
  const traffic = new Map();
  routes.forEach((route) => route.edge_ids.forEach((id) => traffic.set(id, (traffic.get(id) || 0) + 1)));
  const adjacency = new Map(network.nodes.map((node) => [node.id, []]));
  for (const edge of network.graph.edges) {
    const segment = network.segments.find((item) => item.id === edge.segment_id);
    const distance = edge.length_m || segmentLengths.get(edge.segment_id) || 1;
    const grade = Math.abs(edge.grade_percent || 0) / 100;
    adjacency.get(edge.from)?.push({ nodeId: edge.to, edge, distance, grade, reverse: false });
    if (!edge.one_way) adjacency.get(edge.to)?.push({ nodeId: edge.from, edge, distance, grade, reverse: true });
  }
  let overrideLine = null;
  const optimisedRibbons = [];
  let originalPath = null;
  let activeEntry = null;
  let pendingWaypointId = null;
  const visitCounts = new Map();
  routes.forEach((route) => route.node_ids.forEach((id) => visitCounts.set(id, (visitCounts.get(id) || 0) + 1)));
  const sharedJunctions = network.nodes.filter((node) => visitCounts.get(node.id) > 1 && ["junction", "portal"].includes(node.kind)).map((node) => new THREE.Vector3(...node.position_m));
  function shortestPath(startId, goalId) {
    const open = new Set([startId]);
    const cameFrom = new Map();
    const g = new Map([[startId, 0]]);
    const f = new Map([[startId, nodes.get(startId).position_m && new THREE.Vector3(...nodes.get(startId).position_m).distanceTo(new THREE.Vector3(...nodes.get(goalId).position_m))]]);
    while (open.size) {
      let current = null;
      for (const id of open) if (current === null || f.get(id) < f.get(current)) current = id;
      if (current === goalId) {
        const nodeIds = [goalId];
        const edgeIds = [];
        while (cameFrom.has(current)) {
          const previous = cameFrom.get(current);
          edgeIds.unshift(previous.edge.id);
          current = previous.nodeId;
          nodeIds.unshift(current);
        }
        return { nodeIds, edgeIds };
      }
      open.delete(current);
      for (const link of adjacency.get(current) || []) {
        const edgeCost = link.distance * (1 + link.grade * fleetConfig.path_cost_weights.grade + (traffic.get(link.edge.id) || 0) * fleetConfig.path_cost_weights.route_traffic);
        const score = g.get(current) + edgeCost;
        if (score >= (g.get(link.nodeId) ?? Infinity)) continue;
        cameFrom.set(link.nodeId, { nodeId: current, edge: link.edge });
        g.set(link.nodeId, score);
        const a = new THREE.Vector3(...nodes.get(link.nodeId).position_m);
        const b = new THREE.Vector3(...nodes.get(goalId).position_m);
        f.set(link.nodeId, score + a.distanceTo(b));
        open.add(link.nodeId);
      }
    }
    return null;
  }
  function nearestNode(position) {
    let nearest = null;
    let distance = Infinity;
    for (const node of network.nodes) {
      const candidate = new THREE.Vector3(...node.position_m).distanceToSquared(position);
      if (candidate < distance) { distance = candidate; nearest = node; }
    }
    return nearest?.id;
  }
  function plannedPathTo(route, targetNodeId) {
    for (let index = 1; index < route.node_ids.length; index += 1) {
      if (route.node_ids[index] === targetNodeId) {
        return {
          nodeIds: route.node_ids.slice(0, index + 1),
          edgeIds: route.edge_ids.slice(0, index),
        };
      }
    }
    return null;
  }
  function makeOverride(entry, waypointId) {
    const startId = nearestNode(entry.truck.position);
    const goalId = entry.route.node_ids[0];
    const first = shortestPath(startId, waypointId);
    const second = shortestPath(waypointId, goalId);
    const third = plannedPathTo(entry.activeRoute, startId) || shortestPath(goalId, startId);
    if (!first || !second || !third) return null;
    const nodeIds = [...first.nodeIds, ...second.nodeIds.slice(1), ...third.nodeIds.slice(1)];
    const edgeIds = [...first.edgeIds, ...second.edgeIds, ...third.edgeIds];
    const path = routePoints(network, { id: "operator-override", node_ids: nodeIds, edge_ids: edgeIds });
    return { path, nodeIds, edgeIds };
  }
  function applyWaypoint(waypointId) {
    if (originalPath) revertRoute();
    activeEntry = entries.find((entry) => entry.id === selectedId);
    if (!activeEntry || !nodes.has(waypointId)) return null;
    const result = makeOverride(activeEntry, waypointId);
    if (!result) return null;
    if (overrideLine) { group.remove(overrideLine); overrideLine.geometry.dispose(); overrideLine.material.dispose(); }
    const geometry = new THREE.BufferGeometry().setFromPoints(result.path.points.map((point) => point.clone().add(new THREE.Vector3(0, 0.32, 0))));
    overrideLine = new THREE.Line(geometry, new THREE.LineBasicMaterial({ color: 0x60e2ed, linewidth: 2, depthTest: false, toneMapped: false }));
    overrideLine.renderOrder = 12;
    group.add(overrideLine);
    originalPath = activeEntry.path;
    const baselineRemaining = originalPath.length;
    activeEntry.path = result.path;
    activeEntry.distance = 0;
    return { distance: result.path.length, baseline: baselineRemaining, nodeIds: result.nodeIds };
  }
  function revertRoute() {
    if (!activeEntry || !originalPath) return false;
    activeEntry.path = originalPath;
    activeEntry.distance = 0;
    if (overrideLine) { group.remove(overrideLine); overrideLine.geometry.dispose(); overrideLine.material.dispose(); overrideLine = null; }
    originalPath = null;
    return true;
  }
  function setPendingWaypoint(id, committed = false) {
    pendingWaypointId = id || null;
    for (const [nodeId, marker] of targetById) {
      marker.material.color.setHex(nodeId === pendingWaypointId ? (committed ? 0x60e2ed : 0xffc879) : marker.userData.baseColour);
      marker.scale.setScalar(nodeId === pendingWaypointId ? 1.45 : 1);
    }
  }
  function update(delta) {
    for (const entry of entries) {
      const atChoke = sharedJunctions.some((node) => entry.truck.position.distanceTo(node) < fleetConfig.congestion_radius_m);
      const queued = !optimised && atChoke && entries.some((other) => other !== entry && other.truck.position.distanceTo(entry.truck.position) < fleetConfig.queue_radius_m);
      const slope = pointAt(entry.path, entry.distance, gradePosition).y;
      const gradeFactor = 1 - Math.min(fleetConfig.max_grade_speed_reduction, Math.abs(slope) * fleetConfig.grade_speed_sensitivity);
      entry.distance += delta * entry.speed * fleetConfig.time_scale * gradeFactor * (queued ? fleetConfig.queued_speed_factor : 1);
      tangent.copy(pointAt(entry.path, entry.distance, entry.truck.position));
      entry.truck.quaternion.setFromUnitVectors(entry.forward, tangent);
      const cycle = THREE.MathUtils.euclideanModulo(entry.distance, entry.path.length) / entry.path.length;
      const phase = Object.entries(fleetConfig.phase_ranges).find(([, range]) => cycle >= range[0] && cycle < range[1])?.[0] || "returning";
      entry.truck.userData.phase = phase;
      entry.dumpBed.rotation.x = phase === "tipping" ? vehicleModel.dump_bed.tip_angle_radians : 0;
      const predicted = pointAt(entry.path, entry.distance + fleetConfig.prediction_horizon_m, entry.prediction.position);
      entry.prediction.position.y += 1.2;
      entry.prediction.quaternion.setFromUnitVectors(new THREE.Vector3(...vehicleModel.forward_axis), predicted);
    }
  }
  function select(id) {
    selectedId = id;
    waypointTargets.visible = Boolean(id);
    for (const entry of entries) {
      entry.truck.scale.setScalar(entry.id === id ? 1.12 : 1);
      entry.prediction.visible = entry.id === id;
    }
    return entries.find((entry) => entry.id === id) || null;
  }
  function setOptimised(value) {
    optimised = value;
    if (value) {
      routeRibbons.visible = false;
      entries.forEach((entry, index) => {
        const distanceRatio = THREE.MathUtils.euclideanModulo(entry.distance, entry.path.length) / entry.path.length;
        entry.activeRoute = { ...entry.route, edge_ids: entry.route.optimised_edge_ids };
        entry.path = routePoints(network, entry.activeRoute);
        entry.distance = distanceRatio * entry.path.length;
        const ribbon = makeRouteRibbon(entry.path, index, entries.length, 0xff4038, network);
        ribbon.name = `optimised-route-${entry.id}`;
        ribbon.userData.routeId = entry.route.id;
        ribbon.userData.vehicleId = entry.id;
        group.add(ribbon);
        optimisedRibbons.push(ribbon);
      });
      traffic.clear();
      entries.forEach((entry) => entry.activeRoute.edge_ids.forEach((id) => traffic.set(id, (traffic.get(id) || 0) + 1)));
    } else {
      routeRibbons.visible = true;
      for (const ribbon of optimisedRibbons) {
        group.remove(ribbon);
        ribbon.geometry.dispose();
        ribbon.material.dispose();
      }
      optimisedRibbons.length = 0;
      entries.forEach((entry) => {
        entry.activeRoute = entry.route;
        entry.path = routePoints(network, entry.activeRoute);
      });
      traffic.clear();
      entries.forEach((entry) => entry.activeRoute.edge_ids.forEach((id) => traffic.set(id, (traffic.get(id) || 0) + 1)));
    }
    entries.forEach((entry, index) => { entry.speed = (value ? fleetConfig.speed_mps.converged : fleetConfig.speed_mps.unoptimised) + index * fleetConfig.vehicle_speed_variation_mps; });
  }
  return { group, entries, update, select, get selectedId() { return selectedId; }, get optimised() { return optimised; }, setOptimised, applyWaypoint, revertRoute, setPendingWaypoint, nodes: network.nodes };
}
