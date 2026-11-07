import * as THREE from "three";
import { createLoader } from "./loader-stage.js";
import { texture, box, lightRig, seeded, line } from "./scene-utils.js";
export async function createLearning(config) {
  const root = new THREE.Group();
  root.name = "world-model-replay";
  const data = config.training;
  const [ore, floor, model] = await Promise.all([
    texture(config.assets.ore),
    texture(config.assets.floor, 4),
    fetch(config.assets.loader, { cache: "no-store" }).then((r) => r.json()),
  ]);
  const floorMesh = new THREE.Mesh(
    new THREE.PlaneGeometry(...data.floor_size),
    new THREE.MeshStandardMaterial({
      map: floor,
      color: 0x68706b,
      roughness: 1,
    }),
  );
  floorMesh.rotation.x = -Math.PI / 2;
  floorMesh.receiveShadow = true;
  root.add(floorMesh);
  const grid = new THREE.GridHelper(32, 32, 0x656d68, 0x263c42);
  grid.position.y = 0.03;
  grid.material.transparent = true;
  grid.material.opacity = 0.22;
  root.add(grid);
  const loader = createLoader(model, ore);
  root.add(loader.root);
  const pile = new THREE.InstancedMesh(
    new THREE.IcosahedronGeometry(0.42, 1),
    new THREE.MeshStandardMaterial({ map: ore, color: 0xc6baa7, roughness: 1 }),
    55,
  );
  const rand = seeded(398),
    pose = new THREE.Object3D();
  for (let i = 0; i < 55; i++) {
    const angle = rand() * 6.28,
      r = rand() * 2;
    pose.position.set(
      data.pile_position[0] + Math.cos(angle) * r,
      0.3 + (2 - r) * 0.6,
      data.pile_position[2] + Math.sin(angle) * r,
    );
    pose.scale.setScalar(0.6 + rand() * 0.5);
    pose.rotation.set(rand(), rand(), rand());
    pose.updateMatrix();
    pile.setMatrixAt(i, pose.matrix);
  }
  pile.castShadow = true;
  root.add(pile);
  const binMaterial = new THREE.MeshStandardMaterial({
    color: 0x5e6965,
    metalness: 0.3,
    roughness: 0.7,
  });
  for (const dx of [-1.7, 1.7])
    box(
      [0.12, 0.6, 3.8],
      [data.bin_position[0] + dx, 0.3, data.bin_position[2]],
      binMaterial,
      root,
    );
  box(
    [3.5, 0.16, 3.8],
    [data.bin_position[0], 0.05, data.bin_position[2]],
    binMaterial,
    root,
  );
  const delivered = new THREE.InstancedMesh(
    new THREE.IcosahedronGeometry(0.2, 0),
    new THREE.MeshStandardMaterial({ map: ore, color: 0xc9bca4, roughness: 1 }),
    18,
  );
  for (let i = 0; i < 18; i++) {
    pose.position.set(
      data.bin_position[0] + ((i % 5) - 2) * 0.5,
      0.3 + Math.floor(i / 10) * 0.3,
      data.bin_position[2] + (Math.floor(i / 5) - 1) * 0.55,
    );
    pose.rotation.set(i, i * 0.2, i * 0.4);
    pose.scale.setScalar(1);
    pose.updateMatrix();
    delivered.setMatrixAt(i, pose.matrix);
  }
  delivered.visible = false;
  root.add(delivered);
  const observationPositions = [];
  for (let i = 0; i < 450; i++) {
    const a = rand() * 6.28,
      r = 2 + rand() * 12;
    observationPositions.push(Math.cos(a) * r, rand() * 1.8, Math.sin(a) * r);
  }
  const pointsGeo = new THREE.BufferGeometry();
  pointsGeo.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(observationPositions, 3),
  );
  const observation = new THREE.Points(
    pointsGeo,
    new THREE.PointsMaterial({
      color: 0xc2d0c9,
      size: 0.065,
      transparent: true,
      opacity: 0.48,
    }),
  );
  root.add(observation);
  const sweep = new THREE.Mesh(
    new THREE.RingGeometry(2.8, 2.83, 80),
    new THREE.MeshBasicMaterial({
      color: 0xd5ac6c,
      transparent: true,
      opacity: 0.4,
      side: THREE.DoubleSide,
    }),
  );
  sweep.rotation.x = -Math.PI / 2;
  root.add(sweep);
  const prediction = new THREE.Mesh(
    new THREE.BoxGeometry(1.6, 1.9, 7),
    new THREE.MeshBasicMaterial({
      color: 0xd5ac6c,
      wireframe: true,
      transparent: true,
      opacity: 0.3,
      depthWrite: false,
    }),
  );
  root.add(prediction);
  const backgroundRollouts = new THREE.InstancedMesh(
    new THREE.BoxGeometry(0.65, 0.18, 1.25),
    new THREE.MeshBasicMaterial({
      color: 0x536f79,
      transparent: true,
      opacity: 0.45,
      wireframe: true,
    }),
    24,
  );
  root.add(backgroundRollouts);
  const boundary = line(
    [
      [-15, 0.05, -17],
      [15, 0.05, -17],
      [15, 0.05, 17],
      [-15, 0.05, 17],
      [-15, 0.05, -17],
    ],
    0x586968,
    0.65,
  );
  root.add(boundary);
  lightRig(root, 30);
  let elapsed = 0,
    running = true,
    paused = false,
    selected = 2,
    singleTime = 0;
  const keys = data.keyframes;
  function sample(phase, index) {
    let hi = 1;
    while (hi < keys.length - 1 && keys[hi].t < phase) hi++;
    const a = keys[hi - 1],
      b = keys[hi],
      t = THREE.MathUtils.smoothstep(phase, a.t, b.t);
    const p = new THREE.Vector3(...a.p).lerp(new THREE.Vector3(...b.p), t);
    const state = {
      position: p,
      yaw: THREE.MathUtils.lerp(a.yaw, b.yaw, t),
      boom: THREE.MathUtils.lerp(a.boom, b.boom, t),
      bucket: THREE.MathUtils.lerp(a.bucket, b.bucket, t),
      fill: THREE.MathUtils.lerp(a.fill, b.fill, t),
      action: a.action,
    };
    state.fill *= data.checkpoints[index].load_t / data.capacity_t;
    if (index === 0) {
      state.boom = -0.38;
      state.fill = 0;
      if (phase > 0.36) state.action = "Missed load";
    } else if (index === 1) {
      if (phase > 0.55) state.fill *= 0.5;
    }
    return state;
  }
  function update(delta) {
    if (paused) delta = 0;
    if (running) elapsed = Math.min(data.replay_seconds, elapsed + delta);
    else singleTime += delta;
    const progress = running
      ? elapsed / data.replay_seconds
      : data.checkpoints[selected].episodes / data.episodes;
    if (running && progress >= 1) {
      running = false;
      selected = 2;
      singleTime = 0;
    }
    const index = running
      ? progress < 0.25
        ? 0
        : progress < 0.5
          ? 1
          : 2
      : selected;
    const local = running
      ? index === 0
        ? progress / 0.25
        : index === 1
          ? (progress - 0.25) / 0.25
          : (progress - 0.5) / 0.5
      : (singleTime % 10) / 10;
    const state = sample(local, index);
    loader.root.position.copy(state.position);
    loader.root.rotation.y = state.yaw;
    loader.boom.rotation.x = state.boom;
    loader.bucket.rotation.x = state.bucket;
    loader.cargo.visible = state.fill > 0.05;
    loader.cargo.scale.y = Math.max(0.01, state.fill);
    for (const wheel of loader.wheels)
      wheel.rotation.x +=
        (state.action === "Reverse clear" ? -1 : 1) * delta * 3;
    sweep.position.set(state.position.x, 0.06, state.position.z);
    sweep.scale.setScalar(1 + ((elapsed * 1.3) % 1));
    sweep.material.opacity = 0.35 * (1 - ((elapsed * 1.3) % 1));
    prediction.position.copy(state.position).add(new THREE.Vector3(0, 1, 0));
    prediction.position.add(
      new THREE.Vector3(0, 0, 1.4).applyAxisAngle(
        new THREE.Vector3(0, 1, 0),
        state.yaw,
      ),
    );
    prediction.rotation.y = state.yaw;
    delivered.visible = index > 0 && local > 0.92;
    for (let i = 0; i < 24; i++) {
      const phase = elapsed * (0.3 + i * 0.007) + i * 0.7;
      pose.position.set(
        -13 + (i % 6) * 4.5,
        0.13,
        12 + Math.sin(phase) * 1.3 + (Math.floor(i / 6) - 1) * 2.3,
      );
      pose.rotation.set(0, phase * 0.35, 0);
      pose.scale.setScalar(0.65);
      pose.updateMatrix();
      backgroundRollouts.setMatrixAt(i, pose.matrix);
    }
    backgroundRollouts.instanceMatrix.needsUpdate = true;
    return {
      progress,
      episodes: running
        ? Math.floor(data.episodes * progress)
        : data.checkpoints[index].episodes,
      index,
      action: state.action,
      reward: data.checkpoints[index].reward,
      load_t: state.fill * data.capacity_t,
      running,
      paused,
      phase: local,
    };
  }
  return {
    root,
    update,
    replay() {
      elapsed = 0;
      singleTime = 0;
      running = true;
      paused = false;
    },
    pause() {
      paused = !paused;
    },
    checkpoint(index) {
      selected = index;
      running = false;
      paused = false;
      singleTime = 0;
    },
    get running() {
      return !paused;
    },
  };
}
