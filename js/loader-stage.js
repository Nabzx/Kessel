import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
export function createLoader(model, oreMap) {
  const root = new THREE.Group();
  root.name = model.meta.id;
  const mats = {
    paint: new THREE.MeshStandardMaterial({
      color: model.paint,
      roughness: 0.55,
      metalness: 0,
    }),
    dark: new THREE.MeshStandardMaterial({
      color: 0x252b2d,
      roughness: 0.95,
      metalness: 0,
    }),
    glass: new THREE.MeshStandardMaterial({
      color: 0x193b42,
      roughness: 0.18,
      metalness: 0,
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

// Reference rig: rear axle origin, local +z forward, metres. Kept separate from
// the authored concept rig so retained machine poses have an exact physical frame.
export function createReferenceLoader(model, oreMap) {
  const root=new THREE.Group(),front=new THREE.Group();root.name='reference-loader';front.position.z=1.8;root.add(front);
  const paint=new THREE.MeshStandardMaterial({color:model.paint,roughness:.55}),steel=new THREE.MeshStandardMaterial({color:0x7a8582,metalness:.75,roughness:.35}),rubber=new THREE.MeshStandardMaterial({color:0x151b1c,roughness:.96}),glass=new THREE.MeshStandardMaterial({color:0x173b41,roughness:.16});
  const part=(size,position,material,parent=root)=>{const m=new THREE.Mesh(new RoundedBoxGeometry(...size,1,.025),material);m.position.fromArray(position);m.castShadow=m.receiveShadow=true;parent.add(m);return m;};
  part([1.28,.35,3.65],[0,.65,-.025],steel);part([1.3,.65,1.75],[0,1.06,-.9],paint);
  part([1.1,.77,1.15],[0,1.475,.65],paint);part([1.02,.5,.95],[0,1.54,.73],glass);
  for(const side of [-1,1]){part([.055,.045,3.1],[side*.67,1.32,-.25],steel);for(let k=0;k<5;k++)part([.025,.26,.045],[side*.66,1.05,-1.5+k*.19],rubber);}
  part([1.2,.32,1.9],[0,.7,.8],paint,front);
  const wheels=[];
  for(const [axle,parent] of [[0,root],[1.6,front]])for(const side of [1,-1]){
    const pivot=new THREE.Group();pivot.position.set(side*.65,.55,axle);parent.add(pivot);
    const tyre=new THREE.Mesh(new THREE.CylinderGeometry(.55,.55,.2,24),rubber);tyre.rotation.z=Math.PI/2;pivot.add(tyre);
    const hub=new THREE.Mesh(new THREE.CylinderGeometry(.23,.23,.215,16),steel);hub.rotation.z=Math.PI/2;pivot.add(hub);wheels.push(pivot);
    for(let k=0;k<16;k++){const t=k*Math.PI/8,grip=part([.215,.045,.12],[0,.54*Math.cos(t),.54*Math.sin(t)],rubber,pivot);grip.rotation.x=t;}
  }
  const boom=new THREE.Group();boom.position.set(0,.75,1.6);front.add(boom);
  for(const side of [-1,1])part([.12,.15,1],[side*.46,0,.5],paint,boom);
  const bucket=new THREE.Group();front.add(bucket);
  part([1.5,.07,1.2],[0,-.035,.6],steel,bucket);part([1.5,.5,.08],[0,.25,0],paint,bucket);
  for(const side of [-1,1])part([.065,.5,1.2],[side*.717,.25,.6],paint,bucket);
  for(let k=0;k<6;k++)part([.13,.06,.16],[(k-2.5)*.24,-.025,1.2],steel,bucket);
  const cargo=new THREE.Mesh(new THREE.IcosahedronGeometry(1,2),new THREE.MeshStandardMaterial({map:oreMap,color:0x9a8e76,roughness:1}));cargo.position.set(0,.13,.55);cargo.scale.set(.65,.15,.46);bucket.add(cargo);
  function apply(p,wheelAngles=[0,0,0,0],payload=0){
    root.position.set(p[0],0,-p[1]);root.rotation.y=Math.PI/2+p[2];front.rotation.y=p[4];bucket.rotation.x=-p[6];
    bucket.position.set(0,.35+2*Math.sin(p[5])-.6*Math.sin(p[6]),1.6+1.2*Math.cos(p[5])-.6*Math.cos(p[6]));
    const dy=bucket.position.y-.75,dz=bucket.position.z-1.6;boom.rotation.x=-Math.atan2(dy,dz);boom.scale.z=Math.hypot(dy,dz);
    wheels.forEach((w,i)=>w.rotation.x=wheelAngles[i]);cargo.visible=payload>0;cargo.scale.y=.22*Math.min(1,payload/3500);root.updateMatrixWorld(true);
  }
  function geometry(){return {rear:root.localToWorld(new THREE.Vector3()),joint:front.localToWorld(new THREE.Vector3()),front:front.localToWorld(new THREE.Vector3(0,0,1.6)),mouth:bucket.localToWorld(new THREE.Vector3(0,0,.6)),wheels:wheels.map(w=>w.getWorldPosition(new THREE.Vector3()))};}
  return {root,front,boom,bucket,cargo,wheels,apply,geometry};
}
