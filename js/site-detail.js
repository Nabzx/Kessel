import * as THREE from "three";
import {seeded,box} from "./scene-utils.js";

export function vegetation(root,count,elevation,seed) {
  const rand=seeded(seed),canvas=document.createElement('canvas');canvas.width=canvas.height=128;
  const c=canvas.getContext('2d');
  // Original cut-out foliage. Small separate leaves make a broken silhouette.
  for(let i=0;i<310;i++){
    const a=rand()*Math.PI*2,r=Math.sqrt(rand());
    const x=64+Math.cos(a)*r*55,y=64+Math.sin(a)*r*49;
    c.fillStyle=`hsl(${78+rand()*30} 23% ${26+rand()*26}%)`;c.beginPath();c.ellipse(x,y,2+rand()*4,1+rand()*2,rand()*3,0,Math.PI*2);c.fill();
  }
  const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;
  const leaves=new THREE.InstancedMesh(new THREE.PlaneGeometry(1,1),new THREE.MeshStandardMaterial({map,alphaTest:.4,side:THREE.DoubleSide,roughness:1,color:0xb6c4a5}),count*6);
  const stems=new THREE.InstancedMesh(new THREE.CylinderGeometry(.10,.18,1,6),new THREE.MeshStandardMaterial({color:0x514838,roughness:1}),count*3);
  const pose=new THREE.Object3D();
  for(let i=0;i<count;i++){
    let x=(rand()-.5)*1100,z=(rand()-.5)*1000;
    if(Math.abs(x)<115&&Math.abs(z)<210)x+=(x<0?-1:1)*150;
    const y=elevation(x,z),h=5+rand()*9,spread=h*(.24+rand()*.16);
    for(let j=0;j<3;j++){
      pose.position.set(x+(j-1)*spread*.20,y+h*.34,z);pose.scale.set(.7,h*.66,.7);pose.rotation.set((rand()-.5)*.18,rand()*6,(j-1)*.17);pose.updateMatrix();stems.setMatrixAt(i*3+j,pose.matrix);
    }
    for(let j=0;j<6;j++){
      const a=j*2.399,r=spread*Math.sqrt((j+1)/6);
      pose.position.set(x+Math.cos(a)*r*.65,y+h*.65+rand()*h*.32,z+Math.sin(a)*r*.65);
      pose.scale.set(spread*(1+rand()*.5),spread*(1+rand()*.55),1);pose.rotation.set((rand()-.5)*.65,a,(rand()-.5)*.8);pose.updateMatrix();leaves.setMatrixAt(i*6+j,pose.matrix);
    }
  }
  stems.castShadow=true;leaves.castShadow=true;leaves.receiveShadow=true;root.add(stems,leaves);
}

export function yardActivity(root,spec) {
  const group=new THREE.Group();group.name='authored-yard-activity';root.add(group);
  const suit=new THREE.MeshStandardMaterial({color:0xc6a969,roughness:.88}),dark=new THREE.MeshStandardMaterial({color:0x303d3d,roughness:1}),helmet=new THREE.MeshStandardMaterial({color:0xcfc8b4,roughness:.5});
  for(const [x,z] of spec.workers){
    const person=new THREE.Group();person.position.set(x,.12,z);group.add(person);
    box([.43,.64,.27],[0,1.13,0],suit,person);
    for(const side of [-1,1]){box([.15,.69,.17],[side*.13,.49,0],dark,person);box([.13,.55,.14],[side*.3,1.1,0],suit,person);}
    const head=new THREE.Mesh(new THREE.SphereGeometry(.14,10,7),helmet);head.position.set(0,1.63,0);person.add(head);
    box([.44,.045,.29],[0,1.19,0],helmet,person);
  }
  const positions=new Float32Array(45*3),particles=new THREE.Points(new THREE.BufferGeometry(),new THREE.PointsMaterial({color:0xb9ac91,size:.7,transparent:true,opacity:.12,depthWrite:false,sizeAttenuation:true}));
  particles.geometry.setAttribute('position',new THREE.BufferAttribute(positions,3));group.add(particles);
  return {update(time,reduced){for(let i=0;i<45;i++){const age=reduced?(i/45):((time*.07+i/45)%1);positions[i*3]=spec.dust_origin[0]+age*18;positions[i*3+1]=spec.dust_origin[1]+age*2.5;positions[i*3+2]=spec.dust_origin[2]+Math.sin(i*2.7)*3;}particles.geometry.attributes.position.needsUpdate=true;}};
}
