import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { lightRig, box } from "./scene-utils.js";
export function createRetrofit(config) {
  const root = new THREE.Group();
  root.name = "proposed-retrofit-kit";
  const components = [];
  for (const spec of config.kit.components) {
    const group = new THREE.Group();
    group.name = spec.id;
    const mat = new THREE.MeshStandardMaterial({
      color: spec.colour,
      metalness: spec.id === "power" ? 0.25 : 0.7,
      roughness: 0.4,
    });
    const mesh = new THREE.Mesh(
      new RoundedBoxGeometry(...spec.size, 2, 0.07),
      mat,
    );
    mesh.castShadow = true;
    group.add(mesh);
    root.add(group);
    components.push({ spec, group, mat });
    if (spec.id === "cover") {
      const fins = new THREE.InstancedMesh(
        new THREE.BoxGeometry(0.08, 0.21, 2.35),
        mat,
        22,
      );
      const pose = new THREE.Object3D();
      for (let i = 0; i < 22; i++) {
        pose.position.set((i / 21 - 0.5) * 3, 0.19, 0);
        pose.updateMatrix();
        fins.setMatrixAt(i, pose.matrix);
      }
      group.add(fins);
    }
    if (spec.id === "compute") {
      const chip = box(
        [0.68, 0.11, 0.68],
        [0.1, 0.21, 0],
        new THREE.MeshStandardMaterial({
          color: 0x22282b,
          metalness: 0.6,
          roughness: 0.35,
        }),
        group,
      );
      for (let i = 0; i < 12; i++)
        box(
          [0.08, 0.025, 0.14],
          [-0.65 + i * 0.115, 0.2, -0.5],
          new THREE.MeshStandardMaterial({
            color: 0xc1a574,
            metalness: 0.8,
            roughness: 0.3,
          }),
          group,
        );
    }
    if (spec.id === "camera")
      for (const side of [-1, 1]) {
        const lens = new THREE.Mesh(
          new THREE.CylinderGeometry(0.14, 0.14, 0.1, 24),
          new THREE.MeshStandardMaterial({
            color: 0x12242d,
            metalness: 0.5,
            roughness: 0.12,
          }),
        );
        lens.rotation.x = Math.PI / 2;
        lens.position.set(side * 0.36, 0, 0.3);
        group.add(lens);
      }
    if (spec.id === "lidar") {
      const glass = new THREE.Mesh(
        new THREE.CylinderGeometry(0.24, 0.24, 0.24, 32),
        new THREE.MeshStandardMaterial({
          color: 0x253c43,
          metalness: 0.6,
          roughness: 0.18,
        }),
      );
      glass.position.y = 0.35;
      group.add(glass);
    }
    if (spec.id === "enclosure") {
      const ports = new THREE.Mesh(
        new THREE.BoxGeometry(2.4, 0.18, 0.09),
        new THREE.MeshStandardMaterial({
          color: 0x7d7766,
          metalness: 0.65,
          roughness: 0.4,
        }),
      );
      ports.position.set(0, 0, 1.34);
      group.add(ports);
      for (const x of [-1.5, 1.5])
        for (const z of [-1.1, 1.1]) {
          const screw = new THREE.Mesh(
            new THREE.CylinderGeometry(0.055, 0.055, 0.045, 12),
            new THREE.MeshStandardMaterial({
              color: 0xaaaaa1,
              metalness: 0.8,
              roughness: 0.3,
            }),
          );
          screw.position.set(x, 0.25, z);
          group.add(screw);
        }
    }
  }
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(100, 100),
    new THREE.ShadowMaterial({ opacity: 0.22 }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -1;
  ground.receiveShadow = true;
  root.add(ground);
  lightRig(root, 18);
  let amount = 1,
    target = 1;
  function update(delta) {
    amount = THREE.MathUtils.damp(amount, target, 3, delta);
    for (const entry of components) {
      entry.group.position
        .fromArray(entry.spec.position)
        .addScaledVector(new THREE.Vector3(...entry.spec.explode), amount);
    }
    root.rotation.y = Math.sin(performance.now() * 0.00008) * 0.08;
  }
  return {
    root,
    update,
    toggle() {
      target = target ? 0 : 1;
      return target;
    },
    focus(id) {
      for (const entry of components) {
        entry.mat.emissive.set(entry.spec.id === id ? 0x554124 : 0x000000);
        entry.mat.emissiveIntensity = 0.3;
      }
    },
    components,
  };
}
