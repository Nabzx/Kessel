import { authoredAsset } from "./authored-assets.js";
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { lightRig, box } from "./scene-utils.js";
export async function createRetrofit(config) {
  const root = new THREE.Group();
  root.name = "proposed-retrofit-kit";
  const components = [];
  for (const spec of config.kit.components) {
    const group = new THREE.Group();
    group.name = spec.id;
    const mat = new THREE.MeshStandardMaterial({
      color: spec.colour,
      metalness: ["cover", "enclosure"].includes(spec.id) ? .85 : 0,
      roughness: ["compute", "controls", "power"].includes(spec.id) ? .78 : .48,
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
          metalness: 0,
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
    if (["compute", "controls", "power"].includes(spec.id)) {
      const copper = new THREE.MeshStandardMaterial({ color: 0xb59451, metalness: .85, roughness: .5 });
      const resin = new THREE.MeshStandardMaterial({ color: 0x273329, roughness: .85 });
      for (let i=0;i<7;i++) {
        box([spec.size[0]*.7,.008,.012],[-.08,spec.size[1]/2+.012,(i-3)*.1],copper,group);
      }
      for (const side of [-1,1]) {
        box([.18,.16,spec.size[2]*.65],[side*spec.size[0]*.45,spec.size[1]/2+.07,0],resin,group);
        for(let i=0;i<4;i++)box([.06,.012,.045],[side*spec.size[0]*.48,spec.size[1]/2+.16,(i-1.5)*.16],copper,group);
      }
    }
    if (spec.id === "camera")
      for (const side of [-1, 1]) {
        const lens = new THREE.Mesh(
          new THREE.CylinderGeometry(0.14, 0.14, 0.1, 24),
          new THREE.MeshStandardMaterial({
            color: 0x12242d,
            metalness: 0,
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
          metalness: 0,
          roughness: 0.18,
        }),
      );
      glass.position.y = 0.35;
      group.add(glass);
    }
    if (spec.id === "enclosure") {
      const rubber=new THREE.MeshStandardMaterial({color:0x202724,roughness:.96});
      for(const side of [-1,1]){
        box([.12,.04,2.3],[side*1.52,.25,0],rubber,group);
        box([3.1,.04,.12],[0,.25,side*1.12],rubber,group);
        const mount=box([.42,.16,2.9],[side*1.67,-.18,0],mat,group);
        for(const z of [-.75,0,.75]){
          const port=new THREE.Mesh(new THREE.CylinderGeometry(.11,.11,.16,12),rubber);
          port.rotation.z=Math.PI/2;port.position.set(side*1.76,0,z);group.add(port);
          const collar=new THREE.Mesh(new THREE.TorusGeometry(.11,.025,6,12),mat);
          collar.rotation.y=Math.PI/2;collar.position.set(side*1.85,0,z);group.add(collar);
        }
      }
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
  ground.position.y = -.39;
  const cradleMaterial=new THREE.MeshStandardMaterial({color:0x263036,roughness:.52,metalness:.75});
  box(config.kit.mount.size,config.kit.mount.position,cradleMaterial,root);
  for(const x of [-1.83,1.83])for(const z of [-1.3,1.3])box([.12,.08,.12],[x,-.21,z],cradleMaterial,root);
  ground.receiveShadow = true;
  root.add(ground);
  lightRig(root, 18);
  await authoredAsset(config.visuals.authored?.kit).then(authored=>{
    if(!authored)return;root.userData.authoredAsset=config.visuals.authored.kit.path;
    for(const entry of components){const detail=authored.getObjectByName(entry.spec.id);if(!detail)continue;
      for(const child of entry.group.children)child.visible=false;
      const materials=new Map();detail.traverse(o=>{if(o.isMesh){const own=m=>{if(!materials.has(m))materials.set(m,m.clone());return materials.get(m);};o.material=Array.isArray(o.material)?o.material.map(own):own(o.material);}});
      detail.removeFromParent();detail.scale.multiplyScalar(config.visuals.authored.kit.presentation_scale||1);entry.group.add(detail);
    }
  }).catch(error=>console.warn("Authored kit unavailable",error));
  const cables=(config.kit.harness||[]).map(spec=>{
    const mesh=new THREE.Mesh(new THREE.BufferGeometry(),new THREE.MeshStandardMaterial({color:0x172125,roughness:.85}));root.add(mesh);return {spec,mesh};
  });
  let lastCableAmount=-1;
  let amount = 0, target = 0, playing=true;
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  function update(delta) {
    if(playing) amount = reducedMotion ? target : amount+Math.sign(target-amount)*Math.min(Math.abs(target-amount),delta*.3);
    for (const entry of components) {
      const id=entry.spec.id;
      const start=id==="lidar"||id==="camera"?0:id==="cover"?.2:.55;
      const end=id==="lidar"||id==="camera"?.25:id==="cover"?.55:1;
      const t=id==="enclosure"?0:THREE.MathUtils.smoothstep(amount,start,end);
      entry.group.position.fromArray(entry.spec.position).addScaledVector(new THREE.Vector3(...entry.spec.explode),t);
    }
    if(Math.abs(amount-lastCableAmount)>.001){
      for(const {spec,mesh} of cables){const entry=components.find(c=>c.spec.id===spec.component),from=new THREE.Vector3(...spec.case_anchor),to=entry.group.position.clone().add(new THREE.Vector3(...spec.board_anchor));const middle=from.clone().lerp(to,.5);middle.y-=.08;mesh.geometry.dispose();mesh.geometry=new THREE.TubeGeometry(new THREE.CatmullRomCurve3([from,middle,to]),12,.018,6,false);}
      lastCableAmount=amount;
    }
    root.rotation.y=-.12;
    const label=document.getElementById("kit-stage-label");
    if(label)label.textContent=amount<.1?"01 / Assembled unit":amount<.3?"02 / Sensing and mounting":amount<.58?"03 / Thermal path":"04 / Compute, power and vehicle I/O";
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
        entry.group.traverse(object=>{if(object.isMesh)for(const mat of Array.isArray(object.material)?object.material:[object.material]){if(mat.emissive){mat.emissive.set(entry.spec.id===id?0x554124:0);mat.emissiveIntensity=.3;}}});
        entry.mat.emissive.set(entry.spec.id === id ? 0x554124 : 0x000000);
        entry.mat.emissiveIntensity = 0.3;
      }
    },
    step(direction=1){target=THREE.MathUtils.clamp(target+direction*.25,0,1);playing=true;return target;},
    pause(){playing=!playing;return playing;},
    diagnostics(){return {amount,target,playing,assembled:amount===0};},
    components,
  };
}
