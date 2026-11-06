import * as THREE from "three";

// Decorative fragments follow authored transfer phases. They do not change
// payload values, simulator mass, rewards or recorded outcomes.
export function createMaterialTransfer(config, material, entries, bucketPosition) {
  const perVehicle = config.fragments_per_vehicle;
  const mesh = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.15, 0), material, entries.length * perVehicle);
  mesh.name = "illustrative-material-transfer";
  const pose = new THREE.Object3D(), from = new THREE.Vector3(), to = new THREE.Vector3();
  mesh.frustumCulled = false;
  function update() {
    let index = 0;
    for (const entry of entries) {
      const active = ["loading", "tipping"].includes(entry.phase) && entry.load > .04 && entry.load < .96;
      if (active) {
        if (entry.phase === "loading") {
          bucketPosition(from);
          entry.dumpBed.localToWorld(to.set(0, .7, -1.1));
        } else {
          entry.dumpBed.localToWorld(from.set(0, .7, -2));
          entry.truck.getWorldPosition(to); to.add(new THREE.Vector3(5.5, .4, 0));
        }
        if(mesh.parent){mesh.parent.worldToLocal(from);mesh.parent.worldToLocal(to);}
      }
      for (let i = 0; i < perVehicle; i++, index++) {
        const t = (entry.dwell * config.rate_hz + i / perVehicle) % 1;
        pose.scale.setScalar(active ? .65 + (i % 3) * .2 : 0);
        if (active) {
          pose.position.copy(from).lerp(to, t);
          pose.position.y += Math.sin(t * Math.PI) * config.arc_height_m;
          pose.position.x += Math.sin(i * 3.4) * .2;
          pose.rotation.set(t * 8 + i, i * .3, t * 5);
        }
        pose.updateMatrix(); mesh.setMatrixAt(index, pose.matrix);
      }
    }
    mesh.instanceMatrix.needsUpdate = true;
  }
  update();
  return { root: mesh, update };
}
