import * as THREE from "three";

export function createServices(spec, parent) {
  const group = new THREE.Group();
  group.name = "ventilation-and-services";
  const steel = new THREE.MeshStandardMaterial({ color: 0x727975, roughness: 0.61, metalness: 0.75 });
  const vent = new THREE.MeshStandardMaterial({ color: 0xc0b9a3, roughness: 0.92, metalness: 0 });
  const cable = new THREE.MeshStandardMaterial({ color: 0x252b29, roughness: 0.95 });
  const tube = new THREE.CylinderGeometry(1, 1, 1, 12);
  const ring = new THREE.TorusGeometry(spec.vent_radius_m + 0.025, 0.035, 4, 12);
  const pose = new THREE.Object3D(), up = new THREE.Vector3(0, 1, 0);
  const hangers = [];
  const fixtures = [];
  for (const run of spec.runs) {
    const from = new THREE.Vector3(...run.from), to = new THREE.Vector3(...run.to);
    const direction = to.clone().sub(from), length = direction.length();
    const pipe = new THREE.Mesh(tube, vent);
    pipe.position.copy(from).lerp(to, 0.5);
    pipe.scale.set(spec.vent_radius_m, length, spec.vent_radius_m);
    pipe.quaternion.setFromUnitVectors(up, direction.clone().normalize());
    group.add(pipe);
    for (let i = 0; i <= Math.floor(length / spec.hanger_spacing_m); i++) {
      const position = from.clone().addScaledVector(direction, Math.min(1, i * spec.hanger_spacing_m / length));
      const band = new THREE.Mesh(ring, steel);
      band.position.copy(position);
      band.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), direction.clone().normalize());
      group.add(band);
      hangers.push(position.clone().add(new THREE.Vector3(0, 1.1, 0)));
      fixtures.push(position.clone().add(new THREE.Vector3(0.9, -0.8, 0)));
    }
    for (const offset of [1.05, 1.4]) {
      const service = new THREE.Mesh(tube, offset === 1.05 ? steel : cable);
      service.position.copy(from).lerp(to, 0.5).add(new THREE.Vector3(0, offset, 0));
      service.scale.set(spec.pipe_radius_m, length, spec.pipe_radius_m);
      service.quaternion.copy(pipe.quaternion);
      group.add(service);
    }
  }
  const supports = new THREE.InstancedMesh(new THREE.BoxGeometry(0.07, 1.6, 0.07), steel, hangers.length);
  hangers.forEach((position, i) => { pose.position.copy(position); pose.updateMatrix(); supports.setMatrixAt(i, pose.matrix); });
  const lamps = new THREE.InstancedMesh(new THREE.BoxGeometry(1.1, 0.12, 0.24), new THREE.MeshBasicMaterial({ color: 0xf3dfba }), fixtures.length);
  fixtures.forEach((position, i) => { pose.position.copy(position); pose.updateMatrix(); lamps.setMatrixAt(i, pose.matrix); });
  group.add(supports, lamps);
  parent.add(group);
  return group;
}

export function createContactDust(spec, reducedMotion = false) {
  const count = reducedMotion ? 0 : spec.capacity;
  const positions = new Float32Array(count * 3), ages = new Float32Array(count).fill(-1);
  const origin = new Float32Array(count * 3), random = new Float32Array(count);
  for (let i = 0; i < count; i++) random[i] = ((i * 73) % 101) / 101;
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("age", new THREE.BufferAttribute(ages, 1));
  const material = new THREE.ShaderMaterial({
    uniforms: { pointSize: { value: spec.size_m }, lifetime: { value: spec.lifetime_seconds } },
    vertexShader: `attribute float age; varying float opacity; uniform float pointSize,lifetime;
      void main(){vec4 p=modelViewMatrix*vec4(position,1.0);opacity=age<0.0?0.0:pow(1.0-clamp(age/lifetime,0.0,1.0),2.0)*.14;
      gl_Position=projectionMatrix*p;gl_PointSize=min(38.0,pointSize*700.0/max(1.0,-p.z));}`,
    fragmentShader: `varying float opacity; void main(){float r=length(gl_PointCoord-.5)*2.0;
      if(r>1.0)discard;gl_FragColor=vec4(.58,.51,.4,opacity*pow(1.0-r,2.0));
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`,
    transparent: true, depthWrite: false,
  });
  const points = new THREE.Points(geometry, material);
  points.name = "contact-dust"; points.frustumCulled = false;
  let cursor = 0, accumulated = 0;
  function update(delta, entries) {
    if (!count || delta <= 0 || !points.visible) return;
    accumulated += delta;
    if (accumulated >= 0.075) {
      accumulated %= 0.075;
      for (const entry of entries) {
        if (entry.speed <= 0 || entry.queued || (["loading", "tipping"].includes(entry.phase) && (entry.load < .05 || entry.load > .95))) continue;
        const i = cursor++ % count, p = entry.truck.position;
        ages[i] = 0; origin[i * 3] = p.x - 1.2 + random[i] * 2.4;
        origin[i * 3 + 1] = p.y + 0.25; origin[i * 3 + 2] = p.z;
      }
    }
    for (let i = 0; i < count; i++) {
      if (ages[i] < 0) continue;
      ages[i] += delta;
      if (ages[i] > spec.lifetime_seconds) ages[i] = -1;
      positions[i * 3] = origin[i * 3] + ages[i] * (random[i] - .5) * 1.6;
      positions[i * 3 + 1] = origin[i * 3 + 1] + ages[i] * .8;
      positions[i * 3 + 2] = origin[i * 3 + 2] + ages[i] * .35;
    }
    geometry.attributes.position.needsUpdate = geometry.attributes.age.needsUpdate = true;
  }
  return { root: points, update };
}
