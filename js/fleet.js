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
  const cargoMeshes = [];
  for (const panel of bedConfig.panels) {
    addBox(panel, dumpBed);
  }
  for (const cargo of bedConfig.cargo_rocks) {
    const rock = new THREE.Mesh(new THREE.IcosahedronGeometry(cargo.radius_m, 0), materials.cargo);
    rock.position.fromArray(cargo.position_m);
    dumpBed.add(rock);
    cargoMeshes.push(rock);
  }
  const wheelConfig = model.wheels;
  for (const side of [-1, 1]) {
    for (const z of wheelConfig.axle_z_m) {
      const wheel = new THREE.Mesh(new THREE.CylinderGeometry(wheelConfig.radius_m, wheelConfig.radius_m, wheelConfig.width_m, wheelConfig.segments), materials[wheelConfig.material]);
      wheel.rotation.z = Math.PI / 2;
      wheel.position.set(side * wheelConfig.side_offset_m, wheelConfig.centre_y_m, z);
      wheel.userData.vehicleId = id;
      root.add(wheel);
      const hub = new THREE.Mesh(new THREE.CylinderGeometry(wheelConfig.hub_radius_m, wheelConfig.hub_radius_m, 0.07, wheelConfig.segments), materials.body);
      hub.rotation.z = Math.PI / 2;
      hub.position.set(side * (wheelConfig.side_offset_m + 0.16), wheelConfig.centre_y_m, z);
      root.add(hub);
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
  return { root, forward: new THREE.Vector3(...model.forward_axis), dumpBed, cargoMeshes };
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
  const halfWidth = Math.min(0.56, laneSpacing * 1.55) / 2;
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
  const entries = routes.map((route, index) => {
    const { root: truck, forward, dumpBed, cargoMeshes } = makeTruck(route.vehicle_id, vehicleModel);
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
      path,
      truck,
      forward,
      dumpBed,
      cargoMeshes,
      prediction,
      distance: (fleetConfig.vehicles.find((vehicle) => vehicle.id === route.vehicle_id)?.phase_offset ?? index / routes.length) * path.length,
      speed: fleetConfig.speed_mps.unoptimised + index * fleetConfig.vehicle_speed_variation_mps,
    };
  });
  const tangent = new THREE.Vector3();
  const gradePosition = new THREE.Vector3();
  let selectedId = null;
  let optimised = false;
  const optimisedRibbons = [];
  const visitCounts = new Map();
  routes.forEach((route) => route.node_ids.forEach((id) => visitCounts.set(id, (visitCounts.get(id) || 0) + 1)));
  const sharedJunctions = network.nodes.filter((node) => visitCounts.get(node.id) > 1 && ["junction", "portal"].includes(node.kind)).map((node) => new THREE.Vector3(...node.position_m));
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
      entry.cargoMeshes.forEach((rock) => { rock.visible = phase !== "returning"; });
      const predicted = pointAt(entry.path, entry.distance + fleetConfig.prediction_horizon_m, entry.prediction.position);
      entry.prediction.position.y += 1.2;
      entry.prediction.quaternion.setFromUnitVectors(new THREE.Vector3(...vehicleModel.forward_axis), predicted);
    }
  }
  function select(id) {
    selectedId = id;
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
        entry.path = routePoints(network, { ...entry.route, edge_ids: entry.route.optimised_edge_ids });
        entry.distance = distanceRatio * entry.path.length;
        const ribbon = makeRouteRibbon(entry.path, index, entries.length, 0xff4038, network);
        ribbon.name = `optimised-route-${entry.id}`;
        ribbon.userData.routeId = entry.route.id;
        ribbon.userData.vehicleId = entry.id;
        group.add(ribbon);
        optimisedRibbons.push(ribbon);
      });
    } else {
      routeRibbons.visible = true;
      for (const ribbon of optimisedRibbons) {
        group.remove(ribbon);
        ribbon.geometry.dispose();
        ribbon.material.dispose();
      }
      optimisedRibbons.length = 0;
      entries.forEach((entry) => {
        entry.path = routePoints(network, entry.route);
      });
    }
    entries.forEach((entry, index) => { entry.speed = (value ? fleetConfig.speed_mps.converged : fleetConfig.speed_mps.unoptimised) + index * fleetConfig.vehicle_speed_variation_mps; });
  }
  return { group, entries, update, select, get selectedId() { return selectedId; }, get optimised() { return optimised; }, setOptimised };
}
