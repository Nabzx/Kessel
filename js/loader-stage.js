import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
export function createLoader(model, oreMap) {
  const root = new THREE.Group();
  root.name = model.meta.id;
  const mats = {
    paint: new THREE.MeshStandardMaterial({
      color: model.paint,
      roughness: 0.55,
      metalness: 0.18,
    }),
    dark: new THREE.MeshStandardMaterial({
      color: 0x252b2d,
      roughness: 0.7,
      metalness: 0.2,
    }),
    glass: new THREE.MeshStandardMaterial({
      color: 0x193b42,
      roughness: 0.18,
      metalness: 0.45,
    }),
    steel: new THREE.MeshStandardMaterial({
      color: 0x858b87,
      metalness: 0.7,
      roughness: 0.35,
    }),
  };
  function part(size, position, material, parent = root) {
    const mesh = new THREE.Mesh(
      new RoundedBoxGeometry(...size, 1, 0.025),
      material,
    );
    mesh.position.fromArray(position);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    parent.add(mesh);
    return mesh;
  }
  for (const spec of model.body_parts)
    part(spec.size, spec.position, mats[spec.material]);
  const wheels = [];
  for (const side of [-1, 1])
    for (const z of model.wheels.axles) {
      const pivot = new THREE.Group();
      pivot.position.set(side * model.wheels.side, model.wheels.y, z);
      const wheel = new THREE.Mesh(
        new THREE.CylinderGeometry(
          model.wheels.radius,
          model.wheels.radius,
          model.wheels.width,
          20,
        ),
        mats.dark,
      );
      wheel.rotation.z = Math.PI / 2;
      pivot.add(wheel);
      const hub = new THREE.Mesh(
        new THREE.CylinderGeometry(0.18, 0.18, 0.06, 12),
        mats.steel,
      );
      hub.rotation.z = Math.PI / 2;
      hub.position.x = side * 0.12;
      pivot.add(hub);
      root.add(pivot);
      wheels.push(pivot);
    }
  const boom = new THREE.Group();
  boom.position.fromArray(model.boom.pivot);
  root.add(boom);
  for (const side of [-1, 1]) {
    part(
      [0.13, 0.18, model.boom.length],
      [side * 0.43, 0.05, model.boom.length / 2],
      mats.paint,
      boom,
    );
    const ram = new THREE.Mesh(
      new THREE.CylinderGeometry(0.045, 0.045, 1.25, 8),
      mats.steel,
    );
    ram.rotation.x = Math.PI / 2;
    ram.position.set(side * 0.35, -0.08, 0.65);
    boom.add(ram);
  }
  const bucket = new THREE.Group();
  bucket.position.set(0, -0.2, model.boom.length);
  boom.add(bucket);
  const b = model.bucket;
  part([b.width, 0.08, b.depth], [0, 0, b.depth / 2], mats.steel, bucket);
  part([b.width, b.height, 0.09], [0, b.height / 2, 0], mats.paint, bucket);
  for (const side of [-1, 1])
    part(
      [0.07, b.height, b.depth],
      [side * (b.width / 2 - 0.03), b.height / 2, b.depth / 2],
      mats.paint,
      bucket,
    );
  for (let i = 0; i < 6; i++)
    part(
      [0.12, 0.07, 0.2],
      [(i / 5 - 0.5) * b.width * 0.9, -0.04, b.depth + 0.04],
      mats.steel,
      bucket,
    );
  const cargo = new THREE.Group();
  bucket.add(cargo);
  const rocks = new THREE.InstancedMesh(
    new THREE.IcosahedronGeometry(0.15, 1),
    new THREE.MeshStandardMaterial({
      map: oreMap,
      color: 0xc7bba6,
      roughness: 1,
    }),
    16,
  );
  const pose = new THREE.Object3D();
  for (let i = 0; i < 16; i++) {
    pose.position.set(
      ((i % 4) - 1.5) * 0.24,
      0.19 + Math.floor(i / 8) * 0.15,
      0.15 + (Math.floor(i / 4) % 2) * 0.3,
    );
    pose.scale.setScalar(0.8 + (i % 3) * 0.14);
    pose.rotation.set(i, i * 0.4, i * 0.2);
    pose.updateMatrix();
    rocks.setMatrixAt(i, pose.matrix);
  }
  cargo.add(rocks);
  const lampMaterial = new THREE.MeshBasicMaterial({ color: 0xe6e6d9 });
  for (const side of [-1, 1])
    part([0.12, 0.1, 0.05], [side * 0.5, 1.1, 0.35], lampMaterial);
  return { root, boom, bucket, cargo, wheels };
}
